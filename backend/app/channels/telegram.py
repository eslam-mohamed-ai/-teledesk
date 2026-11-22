"""Telegram channel adapter.

Refactors the legacy ``app/services/telegram.py`` Bot API calls into the
channel adapter interface so the pipeline stays provider-neutral. The module
level helpers (``get_me``, ``set_webhook``, ...) remain for existing callers
and are thin wrappers around the adapter's HTTP client.
"""

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
    ChannelCapabilities,
    ChannelHealth,
    ContactProfile,
    EventKind,
    InboundEvent,
    InboundMessage,
    OutboundMessage,
    SendResult,
    BlockedByUser,
    PermanentSendError,
    RateLimited,
    TransientSendError,
)
from app.services.crypto import decrypt, encrypt

API = "https://api.telegram.org"
TIMEOUT = 20.0

log = logging.getLogger("teledesk.channels.telegram")


def _url(token: str, method: str) -> str:
    return f"{API}/bot{token}/{method}"


def _post(token: str, method: str, payload: dict | None = None) -> dict:
    payload = payload or {}
    try:
        r = httpx.post(_url(token, method), json=payload, timeout=TIMEOUT)
    except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as exc:
        raise TransientSendError(str(exc)) from exc
    try:
        data = r.json()
    except ValueError:
        raise TransientSendError(f"telegram http {r.status_code}")
    if not data.get("ok"):
        desc = str(data.get("description", "telegram error"))
        code_map = {
            "bot was blocked by the user": BlockedByUser,
            "blocked by the user": BlockedByUser,
            "chat not found": BlockedByUser,
        }
        cls = next((c for k, c in code_map.items() if k in desc.lower()), None)
        if cls is not None:
            raise cls(desc)
        if "Too Many Requests" in desc or "flood control" in desc.lower():
            retry_after = _retry_after(desc)
            raise RateLimited(retry_after, desc)
        if r.status_code >= 500:
            raise TransientSendError(desc)
        raise PermanentSendError(desc)
    return data.get("result", {})


def _retry_after(description: str) -> int:
    # Telegram includes "retry after N seconds" in flood control messages.
    import re as _re

    m = _re.search(r"retry after (\d+)", description, _re.I)
    return int(m.group(1)) if m else 5


# ---------------------------------------------------------------------------
# Legacy compatibility wrappers (used by routes/bots.py and old worker).
# These live after the class so the class is defined first.
# ---------------------------------------------------------------------------


class TelegramAdapter(ChannelAdapter):
    provider = "telegram"

    capabilities = ChannelCapabilities(
        supports_typing=True,
        supports_attachments=True,
        supports_read_receipts=False,
        max_text_length=4096,
    )

    # ---- connect / disconnect ------------------------------------------

    async def connect(self, company_id, payload: dict[str, Any]) -> dict[str, Any]:
        token = payload.get("token")
        if not token:
            raise ValueError("telegram token required")
        me = await self._async_get_me(token)
        username = me.get("username")
        if not username:
            raise ValueError("telegram bot has no public username")
        return {
            "provider": "telegram",
            "external_id": username,
            "display_name": me.get("first_name") or username,
            "credentials_encrypted": encrypt(token),
            "credentials_key_version": 1,
            "webhook_secret": payload.get("webhook_secret") or hashlib.sha256(token.encode()).hexdigest()[:32],
            "status": "connected",
            "active": True,
        }

    async def disconnect(self, channel: Any) -> None:
        token = self._token(channel)
        try:
            _post(token, "deleteWebhook")
        except Exception:
            log.exception("telegram deleteWebhook failed")

    # ---- webhook verification / parsing --------------------------------

    def verify_webhook_request(self, request: Request, channel_secret: str) -> bool:
        # FastAPI Request body is consumed by the caller; we compare the
        # Telegram secret token header against the stored channel secret.
        provided = request.headers.get("x-telegram-bot-api-secret-token", "")
        return hmac.compare_digest(provided or "", channel_secret or "")

    def parse_webhook(self, payload: dict[str, Any]) -> list[InboundEvent]:
        events: list[InboundEvent] = []
        update_id = payload.get("update_id")
        msg = payload.get("message") or payload.get("edited_message") or {}
        if not msg:
            return events

        chat = msg.get("chat") or {}
        chat_id = chat.get("id")
        if chat_id is None:
            return events

        external_user_id = str(chat_id)
        text = msg.get("text")
        kind = EventKind.message
        attachments: list[Attachment] = []
        if msg.get("photo"):
            attachments.append(Attachment(mime="image/jpeg", original_url=msg["photo"][-1].get("file_id")))
        elif msg.get("document"):
            doc = msg["document"]
            attachments.append(Attachment(mime=doc.get("mime_type"), original_url=doc.get("file_id")))
        elif msg.get("voice"):
            attachments.append(Attachment(mime="audio/ogg", original_url=msg["voice"].get("file_id")))

        events.append(
            InboundEvent(
                kind=kind,
                message=InboundMessage(
                    external_message_id=str(msg.get("message_id")) or str(update_id),
                    external_conversation_id=external_user_id,
                    external_user_id=external_user_id,
                    text=text,
                    kind=kind,
                    attachments=attachments,
                    raw=payload,
                ),
                external_user_id=external_user_id,
                external_conversation_id=external_user_id,
                provider_event_id=str(update_id),
                raw=payload,
            )
        )
        return events

    # ---- send ----------------------------------------------------------

    async def send_message(
        self,
        channel: Any,
        external_user_id: str,
        message: OutboundMessage,
    ) -> SendResult:
        token = self._token(channel)
        chat_id = int(external_user_id)
        payload: dict[str, Any] = {"chat_id": chat_id}
        if message.text:
            payload["text"] = message.text[: self.capabilities.max_text_length or 4096]
            result = _post(token, "sendMessage", payload)
        else:
            result = {}
        return SendResult(
            ok=True,
            external_message_id=str(result.get("message_id")) if isinstance(result, dict) else None,
        )

    async def send_typing(self, channel: Any, external_user_id: str, on: bool = True) -> None:
        token = self._token(channel)
        try:
            _post(
                token,
                "sendChatAction",
                {"chat_id": int(external_user_id), "action": "typing" if on else "cancel"},
            )
        except Exception:
            log.exception("telegram typing failed")

    # ---- profile / health ----------------------------------------------

    async def fetch_profile(self, channel: Any, external_user_id: str) -> ContactProfile:
        # Telegram: getChat returns chat metadata.
        token = self._token(channel)
        try:
            data = _post(token, "getChat", {"chat_id": int(external_user_id)})
        except Exception:
            log.exception("telegram getChat failed")
            return ContactProfile(external_user_id=external_user_id)
        return ContactProfile(
            external_user_id=external_user_id,
            display_name=data.get("first_name") or data.get("title"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            language=None,
        )

    async def health_check(self, channel: Any) -> ChannelHealth:
        token = self._token(channel)
        try:
            await self._async_get_me(token)
            return ChannelHealth.ok
        except Exception:
            return ChannelHealth.down

    # ---- internal helpers ----------------------------------------------

    def _token(self, channel: Any) -> str:
        encrypted = getattr(channel, "credentials_encrypted", None)
        if encrypted is None and isinstance(channel, dict):
            encrypted = channel.get("credentials_encrypted")
        if not encrypted:
            raise PermanentSendError("telegram channel has no credentials")
        return decrypt(encrypted)

    async def _async_get_me(self, token: str) -> dict:
        # httpx is sync; run in executor to keep the async interface.
        import asyncio

        return await asyncio.get_event_loop().run_in_executor(None, lambda: _post(token, "getMe"))

    def raw_send(self, token: str, chat_id: int, text: str):
        return _post(token, "sendMessage", {"chat_id": chat_id, "text": text})

    def raw_typing(self, token: str, chat_id: int) -> None:
        try:
            _post(token, "sendChatAction", {"chat_id": chat_id, "action": "typing"})
        except Exception:
            pass


_legacy_adapter = TelegramAdapter()


def get_me(token: str) -> dict:
    return _post(token, "getMe")


def set_webhook(token: str, url: str, secret: str, allowed_updates: list | None = None):
    return _post(
        token,
        "setWebhook",
        {"url": url, "secret_token": secret, "allowed_updates": allowed_updates or ["message"]},
    )


def delete_webhook(token: str):
    return _post(token, "deleteWebhook")


def send_message(token: str, chat_id: int, text: str):
    return _legacy_adapter.raw_send(token, chat_id, text)


def typing(token: str, chat_id: int) -> None:
    _legacy_adapter.raw_typing(token, chat_id)


register("telegram", TelegramAdapter)
