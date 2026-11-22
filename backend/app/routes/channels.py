"""Channel management and generic webhooks.

Channel lifecycle (connect/disconnect/toggle/list) lives here. Webhook
ingestion is split into the legacy Telegram URL (kept working) and a generic
provider URL that verifies via the adapter and enqueues the pipeline.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.channels.registry import get as get_adapter
from app.channels.types import EventKind
from app.database import get_db
from app.deps import current_company, require_role
from app.models import Channel, Company, User
from app.pipeline.ingest import ingest_inbound

router = APIRouter(prefix="/api/channels", tags=["channels"])
log = logging.getLogger("teledesk.channels")


class ChannelConnectIn(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)


class ChannelOut(BaseModel):
    id: int
    provider: str
    external_id: str | None
    display_name: str | None
    status: str | None
    active: bool
    capabilities: dict[str, Any] = {}


def _channel_out(channel: Channel) -> ChannelOut:
    adapter_cls = get_adapter(channel.provider)
    caps = {}
    if adapter_cls is not None:
        caps = adapter_cls().capabilities.model_dump()
    return ChannelOut(
        id=channel.id,
        provider=channel.provider,
        external_id=channel.external_id,
        display_name=channel.display_name,
        status=channel.status,
        active=channel.active,
        capabilities=caps,
    )


@router.get("")
def list_channels(
    c: Company = Depends(current_company),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(Channel).where(Channel.company_id == c.id).order_by(Channel.id.desc())
    ).all()
    return {"items": [_channel_out(r) for r in rows]}


@router.post("/{provider}/connect", status_code=status.HTTP_201_CREATED)
async def connect_channel(
    provider: str,
    body: ChannelConnectIn,
    c: Company = Depends(current_company),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_role("admin", "owner")),
):
    adapter_cls = get_adapter(provider)
    if adapter_cls is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "provider not supported")

    # A provider account must not be hijacked by another company. The external
    # id is only known after connect() validates credentials, so we check after.
    adapter = adapter_cls()
    try:
        fields = await adapter.connect(c.id, body.payload)
    except Exception:
        log.exception("channel connect failed provider=%s company_id=%s", provider, c.id)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "provider credentials were rejected")

    taken = db.scalar(
        select(Channel).where(
            Channel.provider == fields["provider"],
            Channel.external_id == fields["external_id"],
        )
    )
    if taken and taken.company_id != c.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "this provider account is already connected")

    existing = db.scalar(
        select(Channel).where(
            Channel.company_id == c.id,
            Channel.provider == fields["provider"],
            Channel.external_id == fields["external_id"],
        )
    )
    channel = existing or Channel(company_id=c.id)
    channel.provider = fields["provider"]
    channel.external_id = fields["external_id"]
    channel.display_name = fields.get("display_name")
    channel.credentials_encrypted = fields.get("credentials_encrypted")
    channel.credentials_key_version = fields.get("credentials_key_version", 1)
    channel.webhook_secret = fields.get("webhook_secret")
    channel.status = fields.get("status", "connected")
    channel.active = fields.get("active", True)
    channel.config = fields.get("config") or {}

    db.add(channel)
    db.commit()
    db.refresh(channel)
    return {"channel": _channel_out(channel)}


@router.post("/{channel_id}/disconnect")
def disconnect_channel(
    channel_id: int,
    c: Company = Depends(current_company),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_role("admin", "owner")),
):
    channel = db.scalar(
        select(Channel).where(Channel.id == channel_id, Channel.company_id == c.id)
    )
    if not channel:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "channel not found")

    adapter_cls = get_adapter(channel.provider)
    if adapter_cls is not None:
        try:
            asyncio.run(adapter_cls().disconnect(channel))
        except Exception:
            log.exception("channel disconnect failed channel_id=%s", channel_id)
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "provider disconnect failed")

    channel.status = "disconnected"
    channel.active = False
    db.add(channel)
    db.commit()
    return {"ok": True}


@router.post("/{channel_id}/toggle")
def toggle_channel(
    channel_id: int,
    c: Company = Depends(current_company),
    db: Session = Depends(get_db),
):
    channel = db.scalar(
        select(Channel).where(Channel.id == channel_id, Channel.company_id == c.id)
    )
    if not channel:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "channel not found")
    channel.active = not channel.active
    db.add(channel)
    db.commit()
    return {"active": channel.active}


@router.get("/{channel_id}/health")
def channel_health(
    channel_id: int,
    c: Company = Depends(current_company),
    db: Session = Depends(get_db),
):
    channel = db.scalar(
        select(Channel).where(Channel.id == channel_id, Channel.company_id == c.id)
    )
    if not channel:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "channel not found")
    adapter_cls = get_adapter(channel.provider)
    if adapter_cls is None:
        return {"status": "unknown"}
    try:
        health = asyncio.run(adapter_cls().health_check(channel))
    except Exception:
        log.exception("channel health check failed channel_id=%s", channel_id)
        return {"status": "down"}
    return {"status": health.value}


# ---------------------------------------------------------------------------
# Generic webhook: POST /webhooks/{provider}/{channel_id}
# ---------------------------------------------------------------------------

webhook_router = APIRouter(tags=["webhooks"])


@webhook_router.post("/webhooks/{provider}/{channel_id}")
async def generic_webhook(
    provider: str,
    channel_id: int,
    request: Request,
    x_signature: str | None = Header(None, alias="X-Signature"),
    db: Session = Depends(get_db),
):
    channel = db.get(Channel, channel_id)
    if not channel or channel.provider != provider:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "channel not found")

    adapter_cls = get_adapter(provider)
    if adapter_cls is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "provider not supported")

    adapter = adapter_cls()

    # Bound payload size: read body, cap at 2 MB.
    body = await request.body()
    if len(body) > 2 * 1024 * 1024:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "payload too large")

    import json

    try:
        payload = json.loads(body)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid json")

    # Verify via adapter before enqueuing.
    # Telegram sends its secret in a header; other providers may use a signature header.
    secret = channel.webhook_secret or ""
    if not adapter.verify_webhook_request(request, secret):
        if x_signature and not _compare(x_signature, secret):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "invalid webhook signature")

    try:
        events = adapter.parse_webhook(payload)
    except Exception:
        log.exception("webhook parse failed provider=%s channel_id=%s", provider, channel_id)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "unparseable webhook payload")

    # Respond < 1s: enqueue each event and ack immediately.
    for event in events:
        if event.kind in (EventKind.echo, EventKind.unsupported):
            continue
        try:
            await ingest_inbound(db, channel, event)
        except Exception:
            # Ingestion failures must not make Telegram retry indefinitely;
            # log and ack so the provider stops redelivering a poison pill.
            log.exception("ingestion failed provider=%s channel_id=%s", provider, channel_id)

    return {"ok": True, "accepted": len(events)}


def _compare(a: str, b: str) -> bool:
    import hmac

    return hmac.compare_digest(a or "", b or "")
