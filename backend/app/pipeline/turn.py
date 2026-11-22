"""Conversation turn processing (Celery): commands, quotas, handoff, AI reply, queue outbound."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.deps import current_user  # noqa: F401  (kept for symmetry; not used here)
from app.models import (
    Channel,
    Company,
    Contact,
    Conversation,
    Document,
    Message,
)
from app.pipeline.outbound import enqueue_send
from app.services.chat import HANDOFF, is_arabic, reply_to
from app.services.lead_capture import handle_lead_capture
from app.services.plans import usage
from app.workers.celery_app import celery

log = logging.getLogger("teledesk.pipeline.turn")

HOURLY_LIMIT = 20


def _now() -> datetime:
    return datetime.now(timezone.utc)


@celery.task(name="app.pipeline.turn.process_conversation_turn", bind=True, max_retries=3)
def process_conversation_turn(self, conversation_id: str) -> dict:
    """Process one inbound turn for a conversation.

    The AI reply is persisted as ``queued`` first, then outbound delivery is
    enqueued as a separate task (never commit-before-send).
    """
    conv_id = int(conversation_id)
    with SessionLocal() as db:
        conv = db.get(Conversation, conv_id)
        if not conv:
            return {"status": "error", "error": "conversation not found"}

        company = db.get(Company, conv.company_id)
        if not company:
            return {"status": "error", "error": "company not found"}
        assert company is not None

        channel = db.get(Channel, conv.channel_id) if conv.channel_id else None

        # The inbound customer message is the latest inbound message.
        latest_in = db.scalar(
            select(Message)
            .where(
                Message.conversation_id == conv.id,
                Message.direction == "inbound",
            )
            .order_by(Message.id.desc())
        )
        if not latest_in:
            return {"status": "skipped", "reason": "no inbound message"}

        text = (latest_in.content or "").strip()
        command = text.split(maxsplit=1)[0].split("@", 1)[0].lower()

        # 1) Channel-neutral commands.
        if command == "/start":
            return _handle_start(db, conv, company, channel, latest_in)

        if command == "/human":
            return _handle_human(db, conv, company, channel, latest_in)

        # 2) If a human owns the conversation, the AI does not reply.
        if conv.status in ("needs_human", "human", "closed"):
            return {"status": "skipped", "reason": f"status={conv.status}"}

        # 3) Hourly rate limit per conversation.
        now = _now()
        hour_ago = now - timedelta(hours=1)
        recent = db.scalar(
            select(func.count())
            .select_from(Message)
            .where(
                Message.conversation_id == conv.id,
                Message.role == "customer",
                Message.created_at >= hour_ago,
            )
        ) or 0
        if recent >= HOURLY_LIMIT:
            return {"status": "skipped", "reason": "hourly limit"}

        # 4) Plan quota.
        plan_usage = usage(db, company.id, company.plan)
        if (
            plan_usage["messages_limit"] is not None
            and plan_usage["messages"] >= plan_usage["messages_limit"]
        ):
            _enqueue_outbound(db, conv, channel, "الخدمة مش متاحة دلوقتي. جرّب تتواصل مع الفريق مباشرة.")
            return {"status": "skipped", "reason": "quota exceeded"}

        # 5) Build history for the AI.
        history = [
            {"role": m.role, "content": m.content or ""}
            for m in db.scalars(
                select(Message)
                .where(
                    Message.conversation_id == conv.id,
                    Message.role.in_(["customer", "bot", "agent"]),
                )
                .order_by(Message.id.desc())
                .limit(6)
            ).all()
        ][::-1]

        prev_flag = db.scalar(
            select(Message.flag)
            .where(Message.conversation_id == conv.id, Message.role == "bot")
            .order_by(Message.id.desc())
        )

        # 6) Persist customer message (if not already) and update conv.
        latest_in.unanswered = False
        conv.last_preview = text[:200]
        conv.last_message_at = _now()
        db.add(latest_in)
        db.add(conv)
        db.flush()

        # 6b) Lead capture: field extraction via Gemini (safe to block here; we're in Celery).
        contact = db.get(Contact, conv.contact_id) if conv.contact_id else None
        lead_capture_answer: str | None = None
        if contact and contact.custom_fields and contact.custom_fields.get("lead_capture_pending"):
            assert company is not None
            raw_text = contact.custom_fields.get("lead_capture_raw_text") or text
            try:
                lead_capture_answer = handle_lead_capture(db, company, contact, raw_text)
            except Exception:
                log.exception("lead capture extraction failed for conversation_id=%s", conv.id)
            # Clear the pending flag so we don't re-process.
            if contact.custom_fields:
                fields = dict(contact.custom_fields)
                fields.pop("lead_capture_pending", None)
                fields.pop("lead_capture_raw_text", None)
                contact.custom_fields = fields
                db.add(contact)

        # 7) AI reply.
        t0 = time.time()
        try:
            result = reply_to(db, company, text, history)
            latency = int((time.time() - t0) * 1000)
        except Exception:
            log.exception("reply failed for conversation_id=%s", conv.id)
            db.rollback()
            _enqueue_outbound(
                db,
                conv,
                channel,
                "حصلت مشكلة مؤقتة. جرّب تبعت رسالتك تاني بعد شوية.",
            )
            return {"status": "error", "reason": "ai failure"}

        in_scope = bool(result.get("in_scope", False))
        needs_human = bool(result.get("needs_human", False))

        immediate_handoff = not in_scope and company.handoff_out_of_scope
        second_failed_attempt = (
            not in_scope
            and company.handoff_after_two
            and prev_flag == "out_of_scope"
        )
        handoff = needs_human or immediate_handoff or second_failed_attempt

        if handoff:
            flag = "handoff"
        elif not in_scope:
            flag = "out_of_scope"
        else:
            flag = "auto"

        if not in_scope:
            latest_in.unanswered = True

        answer = result.get("answer") or "مش قادر أجاوب على السؤال ده حاليًا."

        # --- Lead capture: append the next field question (one at a time) ---
        if lead_capture_answer:
            answer = f"{answer}\n\n{lead_capture_answer}"

        # 8) Persist AI message as `queued` FIRST (delivery status tracked separately).
        ai_msg = Message(
            company_id=company.id,
            conversation_id=conv.id,
            channel_id=conv.channel_id,
            role="bot",
            direction="outbound",
            sender_type="ai",
            content=answer,
            content_type="text",
            source=result.get("source"),
            flag=flag,
            latency_ms=latency,
            delivery_status="queued",
            created_at=_now(),
        )
        db.add(ai_msg)
        conv.last_preview = answer[:200]
        conv.last_message_at = _now()

        # 9) Handoff state.
        if handoff:
            conv.status = "needs_human"
            if needs_human:
                conv.handoff_reason = result.get("reason") or "طلب موظف"
            elif second_failed_attempt:
                conv.handoff_reason = "فشل البوت في الإجابة مرتين متتاليتين"
            else:
                conv.handoff_reason = "السؤال خارج نطاق معلومات الشركة"
            db.add(
                Message(
                    company_id=company.id,
                    conversation_id=conv.id,
                    channel_id=conv.channel_id,
                    role="system",
                    content=f"البوت حوّل المحادثة: {conv.handoff_reason} · الرد التلقائي متوقف",
                    direction="outbound",
                    sender_type="system",
                    delivery_status="delivered",
                    created_at=_now(),
                )
            )

        source = result.get("source")
        if source:
            db.execute(
                update(Document)
                .where(
                    Document.company_id == company.id,
                    Document.name == str(source),
                )
                .values(uses=Document.uses + 1)
            )

        db.commit()
        db.refresh(ai_msg)

        # 10) Enqueue outbound delivery (separate task; never commit-before-send).
        enqueue_send(ai_msg.id)

        return {
            "status": "ok",
            "message_id": ai_msg.id,
            "answer": answer,
            "needs_human": handoff,
            "in_scope": in_scope,
        }


def _handle_start(
    db: Session,
    conv: Conversation,
    company: Company,
    channel: Channel | None,
    latest_in: Message,
) -> dict:
    welcome = company.welcome or "أهلا بيك!"
    latest_in.unanswered = False
    conv.status = "open"
    conv.last_preview = welcome[:200]
    conv.last_message_at = _now()
    db.add(latest_in)
    db.add(conv)
    db.commit()
    _enqueue_outbound(db, conv, channel, welcome)
    return {"status": "ok", "reason": "welcome sent"}


def _handle_human(
    db: Session, conv: Conversation, company: Company, channel: Channel | None, latest_in: Message
) -> dict:
    lang = "ar" if is_arabic(latest_in.content or "") else "en"
    reply = HANDOFF[lang]
    latest_in.unanswered = False
    conv.status = "needs_human"
    conv.handoff_reason = "طلب موظف"
    conv.last_preview = reply[:200]
    conv.last_message_at = _now()
    db.add(latest_in)
    db.add(conv)
    db.add(
        Message(
            company_id=company.id,
            conversation_id=conv.id,
            channel_id=conv.channel_id,
            role="system",
            content="البوت حوّل المحادثة: طلب موظف · الرد التلقائي متوقف",
            direction="outbound",
            sender_type="system",
            delivery_status="delivered",
            created_at=_now(),
        )
    )
    db.commit()
    _enqueue_outbound(db, conv, channel, reply)
    return {"status": "ok", "reason": "handed to human"}


def _enqueue_outbound(db: Session, conv: Conversation, channel: Channel | None, text: str) -> None:
    """Persist an outbound message as `queued` and enqueue delivery."""
    ai_msg = Message(
        company_id=conv.company_id,
        conversation_id=conv.id,
        channel_id=conv.channel_id,
        role="bot",
        direction="outbound",
        sender_type="ai",
        content=text,
        content_type="text",
        delivery_status="queued",
        created_at=_now(),
    )
    db.add(ai_msg)
    conv.last_preview = text[:200]
    conv.last_message_at = _now()
    db.add(conv)
    db.commit()
    db.refresh(ai_msg)
    enqueue_send(ai_msg.id)
