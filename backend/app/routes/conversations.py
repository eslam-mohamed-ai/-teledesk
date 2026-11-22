"""Conversation inbox: list, get, messages, agent replies, notes, assignment, handoff."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_company, current_user
from app.models import (
    Channel,
    Company,
    Contact,
    Conversation,
    InternalNote,
    Message,
    User,
)
from app.pipeline.outbound import enqueue_send

router = APIRouter(prefix="/conversations", tags=["conversations"])
log = logging.getLogger("teledesk.conversations")


class ReplyIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class NoteIn(BaseModel):
    note: str = Field(max_length=2000)


class AssignIn(BaseModel):
    assignee_user_id: int | None = None


class ConversationOut(BaseModel):
    id: int
    channel_id: int | None
    provider: str | None
    contact_id: int | None
    contact_name: str | None
    assignee_user_id: int | None
    assignee_name: str | None
    status: str
    priority: str | None
    unread_count: int
    last_preview: str | None
    last_message_at: str | None
    last_inbound_at: str | None
    created_at: str | None


class MessageOut(BaseModel):
    id: int
    role: str
    direction: str | None
    sender_type: str | None
    content: str | None
    content_type: str | None
    delivery_status: str | None
    error_code: str | None
    created_at: str | None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _conv_out(db: Session, conv: Conversation) -> ConversationOut:
    contact_name = None
    provider = None
    if conv.contact_id:
        contact = db.get(Contact, conv.contact_id)
        if contact:
            contact_name = contact.display_name
    if conv.channel_id:
        channel = db.get(Channel, conv.channel_id)
        if channel:
            provider = channel.provider
    assignee_name = None
    if conv.assignee_user_id:
        u = db.get(User, conv.assignee_user_id)
        if u:
            assignee_name = u.name
    return ConversationOut(
        id=conv.id,
        channel_id=conv.channel_id,
        provider=provider,
        contact_id=conv.contact_id,
        contact_name=contact_name,
        assignee_user_id=conv.assignee_user_id,
        assignee_name=assignee_name,
        status=conv.status,
        priority=conv.priority,
        unread_count=conv.unread_count or 0,
        last_preview=conv.last_preview,
        last_message_at=conv.last_message_at.isoformat() if conv.last_message_at else None,
        last_inbound_at=conv.last_inbound_at.isoformat() if conv.last_inbound_at else None,
        created_at=conv.created_at.isoformat() if conv.created_at else None,
    )


def _get_conv(db: Session, c: Company, cid: int) -> Conversation:
    conv = db.scalar(
        select(Conversation).where(
            Conversation.id == cid,
            Conversation.company_id == c.id,
        )
    )
    if not conv:
        raise HTTPException(404, "المحادثة مش موجودة")
    return conv


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


@router.get("")
def list_conversations(
    status: str = "all",
    assignee: str = "all",
    channel: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    unread: str = "false",
    q: str = "",
    before: str | None = Query(default=None, description="cursor: conversation id"),
    limit: int = Query(default=50, le=100),
    c: Company = Depends(current_company),
    actor: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    base = select(Conversation).where(Conversation.company_id == c.id)

    if status != "all":
        base = base.where(Conversation.status == status)
    if assignee != "all":
        if assignee == "me":
            base = base.where(Conversation.assignee_user_id == actor.id)
        elif assignee == "unassigned":
            base = base.where(Conversation.assignee_user_id.is_(None))
        else:
            try:
                base = base.where(Conversation.assignee_user_id == int(assignee))
            except ValueError:
                pass
    if channel:
        base = base.where(Conversation.channel_id == int(channel))
    if unread == "true":
        base = base.where(Conversation.unread_count > 0)
    if q.strip():
        like = f"%{q.strip()}%"
        base = base.where(
            or_(
                Conversation.customer_name.ilike(like),
                Conversation.last_preview.ilike(like),
            )
        )
    if before:
        try:
            base = base.where(Conversation.id < int(before))
        except ValueError:
            pass

    rows = db.scalars(base.order_by(Conversation.last_message_at.desc().nullslast(), Conversation.id.desc()).limit(limit + 1)).all()
    has_more = len(rows) > limit
    rows = rows[:limit]

    return {
        "items": [_conv_out(db, r) for r in rows],
        "has_more": has_more,
        "next_cursor": rows[-1].id if has_more else None,
    }


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------


@router.get("/{cid}")
def detail(cid: int, c: Company = Depends(current_company), db: Session = Depends(get_db)):
    conv = _get_conv(db, c, cid)
    return _conv_out(db, conv)


# ---------------------------------------------------------------------------
# Messages (cursor pagination)
# ---------------------------------------------------------------------------


@router.get("/{cid}/messages")
def messages(
    cid: int,
    after: str | None = Query(default=None, description="cursor: message id"),
    before: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    c: Company = Depends(current_company),
    db: Session = Depends(get_db),
):
    _get_conv(db, c, cid)
    base = select(Message).where(Message.conversation_id == cid)
    if after:
        try:
            base = base.where(Message.id > int(after))
        except ValueError:
            pass
    if before:
        try:
            base = base.where(Message.id < int(before))
        except ValueError:
            pass
    rows = db.scalars(base.order_by(Message.id.asc()).limit(limit + 1)).all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    return {
        "items": [
            MessageOut(
                id=m.id,
                role=m.role,
                direction=m.direction,
                sender_type=m.sender_type,
                content=m.content,
                content_type=m.content_type,
                delivery_status=m.delivery_status,
                error_code=m.error_code,
                created_at=m.created_at.isoformat() if m.created_at else None,
            )
            for m in rows
        ],
        "has_more": has_more,
        "next_cursor": rows[-1].id if has_more else None,
    }


# ---------------------------------------------------------------------------
# Agent reply (via pipeline -> adapter)
# ---------------------------------------------------------------------------


@router.post("/{cid}/reply")
def reply(cid: int, body: ReplyIn, c: Company = Depends(current_company), db: Session = Depends(get_db)):
    conv = _get_conv(db, c, cid)

    if conv.status == "closed":
        raise HTTPException(400, "المحادثة مغلقة، افتحها قبل إرسال رد")

    text = body.text.strip()
    if not text:
        raise HTTPException(400, "اكتب الرد")

    # Persist agent message as `queued` first, then enqueue delivery.
    msg = Message(
        company_id=c.id,
        conversation_id=cid,
        channel_id=conv.channel_id,
        role="agent",
        direction="outbound",
        sender_type="agent",
        sender_user_id=None,
        content=text,
        content_type="text",
        delivery_status="queued",
        created_at=_now(),
    )
    db.add(msg)
    conv.status = "human"
    conv.last_preview = text[:200]
    conv.last_message_at = _now()
    conv.unread_count = 0
    db.add(conv)
    db.commit()
    db.refresh(msg)

    enqueue_send(msg.id)

    return {"ok": True, "message_id": msg.id, "status": "queued"}


# ---------------------------------------------------------------------------
# Internal notes
# ---------------------------------------------------------------------------


@router.post("/{cid}/note")
def note(cid: int, body: NoteIn, c: Company = Depends(current_company), db: Session = Depends(get_db)):
    _get_conv(db, c, cid)
    note = InternalNote(
        conversation_id=cid,
        user_id=None,
        body=body.note.strip(),
        created_at=_now(),
    )
    db.add(note)
    db.commit()
    return {"ok": True}


@router.get("/{cid}/notes")
def notes(cid: int, c: Company = Depends(current_company), db: Session = Depends(get_db)):
    _get_conv(db, c, cid)
    rows = db.scalars(
        select(InternalNote).where(InternalNote.conversation_id == cid).order_by(InternalNote.created_at.desc())
    ).all()
    return {"items": [{"id": n.id, "body": n.body, "at": n.created_at.isoformat() if n.created_at else None} for n in rows]}


# ---------------------------------------------------------------------------
# Assignment
# ---------------------------------------------------------------------------


@router.post("/{cid}/assign")
def assign(cid: int, body: AssignIn, c: Company = Depends(current_company), db: Session = Depends(get_db)):
    conv = _get_conv(db, c, cid)
    if body.assignee_user_id is not None:
        u = db.get(User, body.assignee_user_id)
        if not u or u.company_id != c.id:
            raise HTTPException(400, "المستخدم غير صالح")
    conv.assignee_user_id = body.assignee_user_id
    db.add(conv)
    db.commit()
    publish_event(c.id, "assignment_changed", conversation_id=cid, assignee_user_id=body.assignee_user_id)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Take over / hand back to AI
# ---------------------------------------------------------------------------


@router.post("/{cid}/take")
def take(cid: int, c: Company = Depends(current_company), db: Session = Depends(get_db)):
    conv = _get_conv(db, c, cid)
    if conv.status == "closed":
        raise HTTPException(400, "المحادثة مغلقة")
    conv.status = "human"
    db.add(conv)
    db.commit()
    publish_event(c.id, "conversation_updated", conversation_id=cid, status="human")
    return {"ok": True}


@router.post("/{cid}/hand-back")
def hand_back(cid: int, c: Company = Depends(current_company), db: Session = Depends(get_db)):
    conv = _get_conv(db, c, cid)
    conv.status = "open"
    conv.assignee_user_id = None
    db.add(conv)
    db.commit()
    publish_event(c.id, "conversation_updated", conversation_id=cid, status="open")
    return {"ok": True}


# ---------------------------------------------------------------------------
# Close / reopen
# ---------------------------------------------------------------------------


@router.post("/{cid}/close")
def close(cid: int, c: Company = Depends(current_company), db: Session = Depends(get_db)):
    conv = _get_conv(db, c, cid)
    conv.status = "closed"
    db.add(conv)
    db.commit()
    publish_event(c.id, "conversation_updated", conversation_id=cid, status="closed")
    return {"ok": True}


@router.post("/{cid}/reopen")
def reopen(cid: int, c: Company = Depends(current_company), db: Session = Depends(get_db)):
    conv = _get_conv(db, c, cid)
    conv.status = "open"
    db.add(conv)
    db.commit()
    publish_event(c.id, "conversation_updated", conversation_id=cid, status="open")
    return {"ok": True}


# ---------------------------------------------------------------------------
# Mark read
# ---------------------------------------------------------------------------


@router.post("/{cid}/read")
def mark_read(cid: int, c: Company = Depends(current_company), db: Session = Depends(get_db)):
    conv = _get_conv(db, c, cid)
    conv.unread_count = 0
    db.add(conv)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Retry failed message
# ---------------------------------------------------------------------------


@router.post("/{cid}/messages/{mid}/retry")
def retry_message(cid: int, mid: int, c: Company = Depends(current_company), db: Session = Depends(get_db)):
    _get_conv(db, c, cid)
    msg = db.get(Message, mid)
    if not msg or msg.conversation_id != cid:
        raise HTTPException(404, "الرسالة مش موجودة")
    if msg.direction != "outbound":
        raise HTTPException(400, "مفيش فايدة إعادة إرسال رسالة واردة")
    msg.delivery_status = "queued"
    msg.error_code = None
    msg.error_message = None
    db.add(msg)
    db.commit()
    enqueue_send(msg.id)
    return {"ok": True, "message_id": msg.id, "status": "queued"}


def publish_event(company_id: int, event_type: str, **payload: Any) -> None:
    from app.pipeline.realtime import publish

    publish(company_id, {"type": event_type, **payload})
