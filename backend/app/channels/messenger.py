"""Messenger (Meta) channel adapter.

Implements the provider boundary for Facebook Messenger using the Graph API.
Credentials are stored encrypted; this module never logs tokens. The adapter is
stateless and safe to instantiate per request/task.

Webhook format (Meta):
    {"object":"page","entry":[{"id":"<page_id>","time":...,"messaging":[...]}]}

Signature: ``X-Hub-Signature-256: sha256=<hmac>`` computed with the Meta app
secret over the raw request body.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any

import httpx
from fastapi import Request

from app.channels.base import ChannelAdapter
from app.channels.registry import register
from app.channels.types import (
    Attachment,
    BlockedByUser,
    ChannelCapabilities,
    ChannelHealth,
    ContactProfile,
    EventKind,
    InboundEvent,
    InboundMessage,
    OutboundMessage,
    PermanentSendError,
    RateLimited,
    SendResult,
    TokenInvalid,
    TransientSendError,
    WindowExpired,
)
from app.services.crypto import decrypt, encrypt

GRAPH = "https://graph.facebook.com/v21.0"
TIMEOUT = 20.0

log = logging.getLogger("teledesk.channels.messenger")


def _post(access_token: str, path: str, payload: dict | None = None) -> dict:
    url = f"{GRAPH}/{path.lstrip('/')}"
    try:
        r = httpx.post(url, params={"access_token": access_token}, json=payload or {}, timeout=TIMEOUT)
    except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as exc:
        raise TransientSendError(str(exc)) from exc
    try:
        data = r.json()
    except ValueError:
        raise TransientSendError(f"messenger http {r.status_code}")
    if r.status_code >= 500:
        raise TransientSendError(str(data))
    error = data.get("error") or {}
    code = error.get("code")
    subcode = error.get("error_subcode") or error.get("error_subcode")
    message = str(error.get("message", ""))
    if code in (190, 102):
        raise TokenInvalid(message)
    if code == 4 or code == 613 or "rate limit" in message.lower():
        raise RateLimited(int(error.get("retry_after", 5) or 5), message)
    if code == 10 or subcode == 2018 or "window" in message.lower():
        raise WindowExpired(message)
    if code in (200, 230) or "blocked" in message.lower():
        raise BlockedByUser(message)
    if code:
        raise PermanentSendError(message or f"messenger error {code}")
    return data


def _get(access_token: str, path: str, params: dict | None = None) -> dict:
    url = f"{GRAPH}/{path.lstrip('/')}"
    try:
        r = httpx.get(url, params={**(params or {}), "access_token": access_token}, timeout=TIMEOUT)
    except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as exc:
        raise TransientSendError(str(exc)) from exc
    try:
        data = r.json()
    except ValueError:
        raise TransientSendError(f"messenger http {r.status_code}")
    error = data.get("error") or {}
    if error:
        code = error.get("code")
        message = str(error.get("message", ""))
        if code in (190, 102):
            raise TokenInvalid(message)
        if code == 4 or code == 613:
            raise RateLimited(5, message)
        raise TransientSendError(message or f"messenger error {code}")
    return data


class MessengerAdapter(ChannelAdapter):
    provider = "messenger"

    @property
    def capabilities(self) -> ChannelCapabilities:
        return ChannelCapabilities(
            supports_typing=True,
            supports_attachments=True,
            supports_read_receipts=True,
            messaging_window_hours=24,
            max_text_length=2000,
        )

    async def connect(self, company_id: Any, payload: dict[str, Any]) -> dict[str, Any]:
        page_id = str(payload.get("page_id") or "").strip()
        token = str(payload.get("page_access_token") or "").strip()
        if not page_id or not token:
            raise TokenInvalid("page_id and page_access_token are required")

        # Validate the token against the Graph API. Tests can inject a fake
        # transport via monkeypatching httpx.
        me = _get(token, page_id, {"fields": "id,name"})
        if str(me.get("id")) != page_id:
            raise TokenInvalid("token does not belong to this page")

        app_secret = str(payload.get("app_secret") or "").strip()
        return {
            "provider": "messenger",
            "external_id": page_id,
            "display_name": me.get("name") or page_id,
            "credentials_encrypted": encrypt(token),
            "credentials_key_version": 1,
            "webhook_secret": app_secret or None,
            "status": "connected",
            "active": True,
            "config": {"app_secret": app_secret} if app_secret else {},
        }

    async def disconnect(self, channel: Any) -> None:
        # Page-level webhook subscription is managed in Meta; nothing to revoke
        # per conversation. Kept for interface completeness.
        return None

    def verify_webhook_request(self, request: Request, channel_secret: str) -> bool:
        signature = request.headers.get("x-hub-signature-256", "")
        if not signature.startswith("sha256="):
            return False
        if not channel_secret:
            return False
        # The raw body is cached by the generic webhook route.
        body = getattr(request.state, "raw_body", b"") or b""
        expected = hmac.new(channel_secret.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(f"sha256={expected}", signature)

    def parse_webhook(self, payload: dict[str, Any]) -> list[InboundEvent]:
        events: list[InboundEvent] = []
        if payload.get("object") != "page":
            return events
        for entry in payload.get("entry", []) or []:
            page_id = entry.get("id")
            for item in entry.get("messaging", []) or []:
                sender = (item.get("sender") or {}).get("id")
                recipient = (item.get("recipient") or {}).get("id")
                if item.get("is_echo"):
                    continue
                message = item.get("message") or {}
                text = message.get("text")
                attachments: list[Attachment] = []
                for att in message.get("attachments", []) or []:
                    if att.get("type") == "image":
                        attachments.append(Attachment(original_url=(att.get("payload") or {}).get("url")))
                if not text and not attachments:
                    continue
                events.append(
                    InboundEvent(
                        kind=EventKind.message,
                        external_user_id=sender,
                        external_conversation_id=recipient or page_id,
                        provider_event_id=f"{page_id}:{sender}:{message.get('mid')}",
                        message=InboundMessage(
                            external_message_id=message.get("mid"),
                            external_conversation_id=recipient or page_id,
                            external_user_id=sender or "",
                            text=text,
                            attachments=attachments,
                            timestamp=entry.get("time"),
                            raw=item,
                        ),
                        raw=item,
                    )
                )
        return events

    async def send_message(
        self,
        channel: Any,
        external_user_id: str,
        message: OutboundMessage,
    ) -> SendResult:
        token = decrypt(channel.credentials_encrypted, key_version=channel.credentials_key_version)
        payload: dict[str, Any] = {
            "recipient": {"id": external_user_id},
            "messaging_type": "RESPONSE",
        }
        if message.text:
            payload["message"] = {"text": message.text}
        else:
            raise PermanentSendError("messenger adapter only supports text in this phase")
        try:
            data = _post(token, "me/messages", payload)
        except WindowExpired as exc:
            return SendResult(ok=False, error_code="window_closed", error_message=str(exc))
        except BlockedByUser as exc:
            return SendResult(ok=False, error_code="blocked", error_message=str(exc))
        return SendResult(ok=True, external_message_id=(data.get("message_id")))

    async def fetch_profile(self, channel: Any, external_user_id: str) -> ContactProfile:
        token = decrypt(channel.credentials_encrypted, key_version=channel.credentials_key_version)
        try:
            data = _get(token, external_user_id, {"fields": "first_name,last_name,profile_pic,locale"})
        except Exception:
            log.exception("messenger profile fetch failed user=%s", external_user_id)
            return ContactProfile(external_user_id=external_user_id)
        return ContactProfile(
            external_user_id=external_user_id,
            display_name=" ".join(filter(None, [data.get("first_name"), data.get("last_name")])) or None,
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            avatar_url=data.get("profile_pic"),
            language=data.get("locale"),
        )

    async def health_check(self, channel: Any) -> ChannelHealth:
        token = decrypt(channel.credentials_encrypted, key_version=channel.credentials_key_version)
        try:
            data = _get(token, "me", {"fields": "id"})
        except Exception:
            return ChannelHealth.down
        return ChannelHealth.ok if data.get("id") else ChannelHealth.degraded


register("messenger", MessengerAdapter)