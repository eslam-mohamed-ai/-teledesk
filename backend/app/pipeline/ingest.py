"""Inbound message ingestion: dedupe, contact/identity resolution, conversation resolution, persist."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.channels.registry import get as get_adapter
from app.channels.types import InboundEvent
from app.models import (
    Channel,
    Company,
    Contact,
    ContactIdentity,
    Conversation,
    InternalNote,
    Message,
    ProcessedEvent,
)
from app.pipeline.realtime import publish
from app.services.lead_capture import handle_lead_capture

log = logging.getLogger("teledesk.pipeline.ingest")

HOURLY_LIMIT = 20


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _provider_event_id(event: InboundEvent) -> str:
    return (
        event.provider_event_id
        or (event.message.external_message_id if event.message else None)
        or event.id
    )


async def _fetch_profile(adapter, channel: Channel, external_user_id: str):
    try:
        return await adapter.fetch_profile(channel, external_user_id)
    except Exception:
        log.exception("profile fetch failed; using defaults")
        from app.channels.types import ContactProfile

        return ContactProfile(external_user_id=external_user_id)


async def ingest_inbound(db: Session, channel: Channel, event: InboundEvent) -> dict:
    """Process one inbound event. Idempotent via processed_events.

    Returns a dict with keys: status, contact_id, conversation_id, message_id.
    """
    provider_event_id = _provider_event_id(event)

    # 1) Dedupe against processed_events.
    existing = db.scalar(
        select(ProcessedEvent).where(
            ProcessedEvent.provider == channel.provider,
            ProcessedEvent.event_id == provider_event_id,
        )
    )
    if existing:
        log.info("duplicate event ignored provider=%s event_id=%s", channel.provider, provider_event_id)
        return {"status": "duplicate", "event_id": provider_event_id}

    db.add(
        ProcessedEvent(
            provider=channel.provider,
            event_id=provider_event_id,
            processed=True,
            received_at=_now(),
        )
    )
    db.flush()

    company = db.get(Company, channel.company_id)
    if not company:
        return {"status": "error", "error": "company not found"}

    external_user_id = event.external_user_id or (
        event.message.external_user_id if event.message else None
    )
    text = event.message.text if event.message else None

    # 2) Resolve or create contact + identity (fetch profile ONCE).
    adapter_cls = get_adapter(channel.provider)
    adapter = adapter_cls() if adapter_cls is not None else None
    if adapter is not None:
        profile = await _fetch_profile(adapter, channel, external_user_id or "")
    else:
        from app.channels.types import ContactProfile

        profile = ContactProfile(external_user_id=external_user_id or "")

    identity = db.scalar(
        select(ContactIdentity).where(
            ContactIdentity.channel_id == channel.id,
            ContactIdentity.external_user_id == external_user_id,
        )
    )
    if identity:
        contact = db.get(Contact, identity.contact_id)
    else:
        contact = Contact(
            company_id=company.id,
            display_name=profile.display_name or external_user_id,
            first_name=profile.first_name,
            last_name=profile.last_name,
            language=profile.language,
            avatar_url=profile.avatar_url,
            custom_fields={"provider": channel.provider, "profile": profile.model_dump()},
            created_at=_now(),
            last_seen_at=_now(),
        )
        db.add(contact)
        db.flush()
        db.add(
            ContactIdentity(
                contact_id=contact.id,
                channel_id=channel.id,
                external_user_id=external_user_id,
                profile_snapshot=profile.model_dump(),
                created_at=_now(),
            )
        )
        db.flush()

    assert contact is not None, "contact must be resolved or created"
    # touch last_seen
    contact.last_seen_at = _now()
    db.add(contact)

    # 3) Resolve or create conversation (reuse latest non-closed one).
    conv = db.execute(
        select(Conversation)
        .where(
            Conversation.company_id == company.id,
            Conversation.channel_id == channel.id,
            Conversation.contact_id == contact.id,
            Conversation.status != "closed",
        )
        .order_by(Conversation.last_message_at.desc().nullslast(), Conversation.id.desc())
    ).scalar_one_or_none()
    if conv is None:
        lang = profile.language or ("ar" if _is_arabic(text or "") else "en")
        conv = Conversation(
            company_id=company.id,
            channel_id=channel.id,
            contact_id=contact.id,
            customer_name=profile.display_name or external_user_id,
            lang=lang,
            status="open",
            priority="normal",
            unread_count=0,
            created_at=_now(),
            last_message_at=_now(),
        )
        db.add(conv)
        db.flush()

    # --- Lead capture: extract values, refuse sensitive data, track next question ---
    lead_capture_next_question: str | None = None
    if company.lead_capture_enabled and text:
        try:
            refusal = await handle_lead_capture(db, company, contact, text)
        except Exception:
            log.exception("lead capture handling failed")
            refusal = None
        if refusal:
            from app.services.lead_capture import sensitive_data_detected

            sensitive = sensitive_data_detected(text)
            if sensitive:
                # Replace sensitive content with a refusal notice and write a timeline note.
                text = f"[تم حجب محتوى حساس: {sensitive}]"
                db.add(
                    InternalNote(
                        conversation_id=conv.id,
                        user_id=None,
                        body=f"تم رفض تخزين بيانات حساسة من العميل: {sensitive}",
                    )
                )
            # Store the lead-capture prompt (if any) so the turn processor can include it in the AI reply.
            lead_capture_next_question = refusal if not sensitive else None
    # Persist any next_question on the contact for the turn processor.
    if lead_capture_next_question:
        fields = dict(contact.custom_fields or {})
        fields["lead_capture_next_question"] = lead_capture_next_question
        contact.custom_fields = fields
        db.add(contact)

    # 3) Resolve or create conversation (reuse latest non-closed one).
    conv = db.execute(
        select(Conversation)
        .where(
            Conversation.company_id == company.id,
            Conversation.channel_id == channel.id,
            Conversation.contact_id == contact.id,
            Conversation.status != "closed",
        )
        .order_by(Conversation.last_message_at.desc().nullslast(), Conversation.id.desc())
    ).scalar_one_or_none()
    if conv is None:
        lang = profile.language or ("ar" if _is_arabic(text or "") else "en")
        conv = Conversation(
            company_id=company.id,
            channel_id=channel.id,
            contact_id=contact.id,
            customer_name=profile.display_name or external_user_id,
            lang=lang,
            status="open",
            priority="normal",
            unread_count=0,
            created_at=_now(),
            last_message_at=_now(),
        )
        db.add(conv)
        db.flush()

    # 4) Persist inbound message.
    inbound = Message(
        company_id=company.id,
        conversation_id=conv.id,
        channel_id=channel.id,
        role="customer",
        direction="inbound",
        sender_type="contact",
        content=text or "",
        content_type="text",
        external_message_id=(
            event.message.external_message_id if event.message else None
        ),
        delivery_status="delivered",
        created_at=_now(),
    )
    db.add(inbound)
    db.flush()

    conv.last_inbound_at = _now()
    conv.last_message_at = _now()
    conv.unread_count = (conv.unread_count or 0) + 1
    conv.last_preview = (text or "")[:200]
    db.add(conv)
    db.commit()
    db.refresh(inbound)
    db.refresh(conv)

    # 5) Publish realtime event.
    publish(
        company.id,
        {
            "type": "new_message",
            "conversation_id": conv.id,
            "message_id": inbound.id,
            "contact_id": contact.id,
            "channel_id": channel.id,
            "text": text,
            "at": conv.last_message_at.isoformat(),
        },
    )

    # 6) Enqueue turn processing.
    from app.workers.celery_app import celery

    celery.send_task(
        "app.pipeline.turn.process_conversation_turn",
        args=[str(conv.id)],
        kwargs={},
    )

    return {
        "status": "ok",
        "contact_id": contact.id,
        "conversation_id": conv.id,
        "message_id": inbound.id,
    }


def _is_arabic(text: str) -> bool:
    import re

    return bool(re.search(r"[\u0600-\u06FF]", text or ""))
