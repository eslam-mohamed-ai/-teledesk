"""Outbound message delivery (Celery): adapter send, retry policy, status tracking."""

from __future__ import annotations

import logging
import random
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.channels.types import (
    BlockedByUser,
    OutboundMessage,
    PermanentSendError,
    RateLimited,
    TokenInvalid,
    TransientSendError,
    WindowExpired,
)
from app.channels.registry import get as get_adapter
from app.database import SessionLocal
from app.models import Channel, ContactIdentity, Conversation, Message
from app.pipeline.realtime import publish
from app.workers.celery_app import celery

log = logging.getLogger("teledesk.pipeline.outbound")

MAX_SEND_RETRIES = 5
BASE_COUNTDOWN = 4  # seconds


def _now() -> datetime:
    return datetime.now(timezone.utc)


def enqueue_send(message_id: int) -> None:
    """Enqueue (or immediately schedule) delivery of an outbound message."""
    celery.send_task("app.pipeline.outbound.send_outbound", args=[int(message_id)])


@celery.task(
    name="app.pipeline.outbound.send_outbound",
    bind=True,
    max_retries=MAX_SEND_RETRIES,
    acks_late=True,
    reject_on_worker_lost=True,
)
def send_outbound(self, message_id: int) -> dict:
    with SessionLocal() as db:
        msg = db.get(Message, message_id)
        if not msg:
            return {"status": "error", "error": "message not found"}

        conv = db.get(Conversation, msg.conversation_id)
        if not conv or not conv.channel_id:
            msg.delivery_status = "failed"
            msg.error_code = "no_channel"
            msg.error_message = "conversation has no channel"
            db.commit()
            return {"status": "failed", "reason": "no channel"}

        channel = db.get(Channel, conv.channel_id)
        if not channel or not channel.active:
            msg.delivery_status = "failed"
            msg.error_code = "channel_inactive"
            msg.error_message = "channel inactive"
            db.commit()
            return {"status": "failed", "reason": "channel inactive"}

        # Resolve the contact's external user id on this channel.
        identity = db.scalar(
            select(ContactIdentity).where(
                ContactIdentity.channel_id == channel.id,
                ContactIdentity.contact_id == conv.contact_id,
            )
        )
        external_user_id = identity.external_user_id if identity else str(conv.tg_chat_id or "")

        adapter_cls = get_adapter(channel.provider)
        if adapter_cls is None:
            _mark_failed(db, msg, "no_adapter", f"no adapter for {channel.provider}")
            return {"status": "failed", "reason": "no adapter"}
        adapter = adapter_cls()

        out = OutboundMessage(text=msg.content)

        try:
            # sync httpx adapter -> run in thread
            import asyncio

            result = asyncio.run(adapter.send_message(channel, external_user_id, out))
        except RateLimited as exc:
            countdown = min(BASE_COUNTDOWN * (2 ** self.request.retries) + random.randint(0, 3), 300)
            log.warning(
                "send rate limited message_id=%s retry_after=%s countdown=%s",
                message_id,
                exc.retry_after,
                countdown,
            )
            raise self.retry(exc=exc, countdown=max(countdown, exc.retry_after))
        except TokenInvalid as exc:
            log.warning("token invalid message_id=%s: %s", message_id, exc)
            channel.status = "token_expired"
            db.add(channel)
            _mark_failed(db, msg, "token_invalid", str(exc))
            return {"status": "failed", "reason": "token_invalid"}
        except (BlockedByUser, WindowExpired, PermanentSendError) as exc:
            log.warning("permanent send failure message_id=%s: %s", message_id, exc)
            _mark_failed(db, msg, "permanent", str(exc))
            return {"status": "failed", "reason": type(exc).__name__}
        except TransientSendError as exc:
            countdown = min(BASE_COUNTDOWN * (2 ** self.request.retries) + random.randint(0, 3), 300)
            log.warning("transient send error message_id=%s countdown=%s", message_id, countdown)
            raise self.retry(exc=exc, countdown=countdown)
        except Exception as exc:
            # Unknown provider error: treat as transient with backoff.
            countdown = min(BASE_COUNTDOWN * (2 ** self.request.retries) + random.randint(0, 3), 300)
            log.exception("send error message_id=%s", message_id)
            raise self.retry(exc=exc, countdown=countdown)

        # Success: mark delivered within the same session.
        msg.delivery_status = "delivered"
        msg.error_code = None
        msg.error_message = None
        db.add(msg)
        db.commit()
        company_id = conv.company_id
        external_message_id = result.external_message_id if result else None

    if company_id:
        publish(
            company_id,
            {"type": "message_status", "message_id": message_id, "status": "delivered"},
        )
    return {"status": "delivered", "external_message_id": external_message_id}


def _mark_failed(db: Session, msg: Message, code: str, message: str) -> None:
    msg.delivery_status = "failed"
    msg.error_code = code
    msg.error_message = message
    db.add(msg)
    db.commit()
    conv = db.get(Conversation, msg.conversation_id)
    if conv:
        publish(
            conv.company_id,
            {"type": "message_status", "message_id": msg.id, "status": "failed", "code": code},
        )
