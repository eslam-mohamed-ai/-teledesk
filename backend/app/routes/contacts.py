"""Contacts API + contact field definitions + lead capture config."""

from __future__ import annotations

import csv
import io
import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_company, current_user, require_role
from app.models import (
    Attachment,
    Channel,
    Company,
    Contact,
    ContactFieldDefinition,
    ContactIdentity,
    Conversation,
    Message,
    Tag,
    User,
)
from app.services.audit import audit_from_request

router = APIRouter(prefix="/contacts", tags=["contacts"])
log = logging.getLogger("teledesk.contacts")

# ---------------------------------------------------------------------------
# Sensitive data detection
# ---------------------------------------------------------------------------

_CARD_RE = re.compile(r"\b(?:\d[ -]*){13,16}\b")
_NATIONAL_ID_RE = re.compile(r"\b\d{9,14}\b")
_PASSWORD_HINT_RE = re.compile(r"(كلمة مرور|password|secret|رمز|pin|رقم سري)", re.IGNORECASE)


def _detect_sensitive(text: str) -> str | None:
    """Return a human-readable reason if sensitive data detected, else None."""
    if _CARD_RE.search(text):
        return "رقم بطاقة ائتمانية"
    if _NATIONAL_ID_RE.search(text) and _PASSWORD_HINT_RE.search(text):
        return "رقم وطني مع كلمة مرور/سري"
    if _PASSWORD_HINT_RE.search(text) and re.search(r"\d{4,}", text):
        return "كلمة مرور أو رمز سري"
    return None


# ---------------------------------------------------------------------------
# Contact field definitions CRUD
# ---------------------------------------------------------------------------


class FieldDefIn(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=200)
    type: str = Field(default="text", max_length=32)
    required: bool = False
    ask_in_chat: bool = False
    prompt_text: str | None = Field(default=None, max_length=500)
    sort_order: int = Field(default=0)


class FieldDefOut(BaseModel):
    id: int
    key: str
    label: str
    type: str
    required: bool
    ask_in_chat: bool
    prompt_text: str | None
    sort_order: int


@router.get("/field-definitions", response_model=list[FieldDefOut])
def list_field_definitions(
    c: Company = Depends(current_company),
    actor: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(ContactFieldDefinition)
        .where(ContactFieldDefinition.company_id == c.id)
        .order_by(ContactFieldDefinition.sort_order, ContactFieldDefinition.id)
    ).all()
    return [
        FieldDefOut(
            id=r.id,
            key=r.key,
            label=r.label,
            type=r.type,
            required=r.required,
            ask_in_chat=r.ask_in_chat,
            prompt_text=r.prompt_text,
            sort_order=r.sort_order,
        )
        for r in rows
    ]


@router.post("/field-definitions", status_code=201, response_model=FieldDefOut)
def create_field_definition(
    body: FieldDefIn,
    c: Company = Depends(current_company),
    actor: User = Depends(require_role("admin", "owner")),
    db: Session = Depends(get_db),
):
    existing = db.scalar(
        select(ContactFieldDefinition).where(
            ContactFieldDefinition.company_id == c.id,
            ContactFieldDefinition.key == body.key,
        )
    )
    if existing:
        raise HTTPException(400, "المفتاح موجود بالفعل")

    record = ContactFieldDefinition(
        company_id=c.id,
        key=body.key,
        label=body.label,
        type=body.type,
        required=body.required,
        ask_in_chat=body.ask_in_chat,
        prompt_text=body.prompt_text,
        sort_order=body.sort_order,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return FieldDefOut(
        id=record.id,
        key=record.key,
        label=record.label,
        type=record.type,
        required=record.required,
        ask_in_chat=record.ask_in_chat,
        prompt_text=record.prompt_text,
        sort_order=record.sort_order,
    )


@router.put("/field-definitions/{field_id}", response_model=FieldDefOut)
def update_field_definition(
    field_id: int,
    body: FieldDefIn,
    c: Company = Depends(current_company),
    actor: User = Depends(require_role("admin", "owner")),
    db: Session = Depends(get_db),
):
    record = db.scalar(
        select(ContactFieldDefinition).where(
            ContactFieldDefinition.id == field_id,
            ContactFieldDefinition.company_id == c.id,
        )
    )
    if not record:
        raise HTTPException(404, "التعريف غير موجود")

    record.label = body.label
    record.type = body.type
    record.required = body.required
    record.ask_in_chat = body.ask_in_chat
    record.prompt_text = body.prompt_text
    record.sort_order = body.sort_order
    db.commit()
    db.refresh(record)
    return FieldDefOut(
        id=record.id,
        key=record.key,
        label=record.label,
        type=record.type,
        required=record.required,
        ask_in_chat=record.ask_in_chat,
        prompt_text=record.prompt_text,
        sort_order=record.sort_order,
    )


@router.delete("/field-definitions/{field_id}", status_code=204)
def delete_field_definition(
    field_id: int,
    c: Company = Depends(current_company),
    actor: User = Depends(require_role("admin", "owner")),
    db: Session = Depends(get_db),
):
    record = db.scalar(
        select(ContactFieldDefinition).where(
            ContactFieldDefinition.id == field_id,
            ContactFieldDefinition.company_id == c.id,
        )
    )
    if not record:
        raise HTTPException(404, "التعريف غير موجود")
    db.delete(record)
    db.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Lead capture config
# ---------------------------------------------------------------------------


class LeadCaptureConfigIn(BaseModel):
    enabled: bool
    consent_text: str | None = None


class LeadCaptureConfigOut(BaseModel):
    enabled: bool
    consent_text: str


@router.get("/lead-capture-config", response_model=LeadCaptureConfigOut)
def get_lead_capture_config(
    c: Company = Depends(current_company),
    actor: User = Depends(current_user),
):
    return LeadCaptureConfigOut(
        enabled=c.lead_capture_enabled,
        consent_text=c.lead_capture_consent_text,
    )


@router.put("/lead-capture-config", response_model=LeadCaptureConfigOut)
def update_lead_capture_config(
    body: LeadCaptureConfigIn,
    c: Company = Depends(current_company),
    actor: User = Depends(require_role("admin", "owner")),
    db: Session = Depends(get_db),
):
    c.lead_capture_enabled = body.enabled
    if body.consent_text is not None:
        c.lead_capture_consent_text = body.consent_text
    db.commit()
    return LeadCaptureConfigOut(
        enabled=c.lead_capture_enabled,
        consent_text=c.lead_capture_consent_text,
    )


# ---------------------------------------------------------------------------
# Contacts list / search / filter
# ---------------------------------------------------------------------------


class ContactOut(BaseModel):
    id: int
    display_name: str | None
    first_name: str | None
    last_name: str | None
    email: str | None
    phone: str | None
    avatar_url: str | None
    language: str | None
    country: str | None
    timezone: str | None
    status: str | None
    custom_fields: dict | None
    tags: list[str] = []
    ai_collected_fields: list[str] = []
    created_at: str
    last_seen_at: str | None


def _ai_collected_keys(db: Session, c: Company, contact: Contact) -> list[str]:
    """Keys the AI collected in chat (ask_in_chat fields with a stored value)."""
    definitions = db.scalars(
        select(ContactFieldDefinition).where(
            ContactFieldDefinition.company_id == c.id,
            ContactFieldDefinition.ask_in_chat.is_(True),
        )
    ).all()
    fields = contact.custom_fields or {}
    return [d.key for d in definitions if fields.get(d.key) not in (None, "")]


def _contact_out(contact: Contact, ai_collected_fields: list[str] | None = None) -> ContactOut:
    return ContactOut(
        id=contact.id,
        display_name=contact.display_name,
        first_name=contact.first_name,
        last_name=contact.last_name,
        email=contact.email,
        phone=contact.phone,
        avatar_url=contact.avatar_url,
        language=contact.language,
        country=contact.country,
        timezone=contact.timezone,
        status=contact.status,
        custom_fields=contact.custom_fields,
        tags=[t.name for t in contact.tags],
        ai_collected_fields=ai_collected_fields or [],
        created_at=contact.created_at.isoformat(),
        last_seen_at=contact.last_seen_at.isoformat() if contact.last_seen_at else None,
    )


@router.get("", response_model=list[ContactOut])
def list_contacts(
    q: str | None = Query(None, description="search name/email/phone"),
    tag: str | None = Query(None),
    c: Company = Depends(current_company),
    actor: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Contact).where(Contact.company_id == c.id, Contact.merged_into_id.is_(None))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                Contact.display_name.ilike(like),
                Contact.first_name.ilike(like),
                Contact.last_name.ilike(like),
                Contact.email.ilike(like),
                Contact.phone.ilike(like),
            )
        )
    if tag:
        stmt = stmt.join(Contact.tags).where(Tag.name == tag)
    rows = db.scalars(stmt.order_by(Contact.last_seen_at.desc().nullslast(), Contact.id.desc())).all()
    return [_contact_out(r, _ai_collected_keys(db, c, r)) for r in rows]


@router.get("/{contact_id}", response_model=ContactOut)
def get_contact(
    contact_id: int,
    c: Company = Depends(current_company),
    actor: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    contact = db.scalar(
        select(Contact).where(Contact.id == contact_id, Contact.company_id == c.id)
    )
    if not contact:
        raise HTTPException(404, "الجهة غير موجودة")
    return _contact_out(contact, _ai_collected_keys(db, c, contact))


class ContactUpdate(BaseModel):
    display_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    language: str | None = None
    country: str | None = None
    timezone: str | None = None
    status: str | None = None
    custom_fields: dict | None = None


@router.get("/{contact_id}/conversations")
def contact_conversations(
    contact_id: int,
    c: Company = Depends(current_company),
    actor: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Previous conversations for a contact (contact panel history)."""
    contact = db.scalar(
        select(Contact).where(Contact.id == contact_id, Contact.company_id == c.id)
    )
    if not contact:
        raise HTTPException(404, "الجهة غير موجودة")

    rows = db.scalars(
        select(Conversation)
        .where(Conversation.contact_id == contact_id)
        .order_by(Conversation.created_at.desc())
    ).all()
    items = []
    for conv in rows:
        provider = None
        if conv.channel_id:
            channel = db.get(Channel, conv.channel_id)
            if channel is not None:
                provider = channel.provider
        items.append(
            {
                "id": conv.id,
                "provider": provider,
                "status": conv.status,
                "last_preview": conv.last_preview,
                "created_at": conv.created_at.isoformat() if conv.created_at else None,
                "last_message_at": conv.last_message_at.isoformat() if conv.last_message_at else None,
            }
        )
    return {"items": items}


@router.patch("/{contact_id}", response_model=ContactOut)
def update_contact(
    contact_id: int,
    body: ContactUpdate,
    c: Company = Depends(current_company),
    actor: User = Depends(require_role("admin", "owner")),
    db: Session = Depends(get_db),
):
    contact = db.scalar(
        select(Contact).where(Contact.id == contact_id, Contact.company_id == c.id)
    )
    if not contact:
        raise HTTPException(404, "الجهة غير موجودة")

    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(contact, key, value)
    db.commit()
    db.refresh(contact)
    return _contact_out(contact)


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------


class TagIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    color: str | None = None


@router.post("/{contact_id}/tags", status_code=201)
def add_tag(
    contact_id: int,
    body: TagIn,
    c: Company = Depends(current_company),
    actor: User = Depends(require_role("admin", "owner")),
    db: Session = Depends(get_db),
):
    contact = db.scalar(
        select(Contact).where(Contact.id == contact_id, Contact.company_id == c.id)
    )
    if not contact:
        raise HTTPException(404, "الجهة غير موجودة")

    tag = db.scalar(select(Tag).where(Tag.company_id == c.id, Tag.name == body.name))
    if not tag:
        tag = Tag(company_id=c.id, name=body.name, color=body.color)
        db.add(tag)
        db.flush()
    if tag not in contact.tags:
        contact.tags.append(tag)
    db.commit()
    return {"ok": True}


@router.delete("/{contact_id}/tags/{tag_name}", status_code=204)
def remove_tag(
    contact_id: int,
    tag_name: str,
    c: Company = Depends(current_company),
    actor: User = Depends(require_role("admin", "owner")),
    db: Session = Depends(get_db),
):
    contact = db.scalar(
        select(Contact).where(Contact.id == contact_id, Contact.company_id == c.id)
    )
    if not contact:
        raise HTTPException(404, "الجهة غير موجودة")
    tag = db.scalar(select(Tag).where(Tag.company_id == c.id, Tag.name == tag_name))
    if tag and tag in contact.tags:
        contact.tags.remove(tag)
        db.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Notes + timeline
# ---------------------------------------------------------------------------


class NoteIn(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class NoteOut(BaseModel):
    id: int
    body: str
    created_at: str
    user_name: str | None


@router.get("/{contact_id}/notes", response_model=list[NoteOut])
def list_notes(
    contact_id: int,
    c: Company = Depends(current_company),
    actor: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    contact = db.scalar(
        select(Contact).where(Contact.id == contact_id, Contact.company_id == c.id)
    )
    if not contact:
        raise HTTPException(404, "الجهة غير موجودة")
    from app.models import InternalNote

    rows = db.scalars(
        select(InternalNote)
        .where(InternalNote.conversation_id.in_(
            select(Conversation.id).where(Conversation.contact_id == contact_id)
        ))
        .order_by(InternalNote.created_at.desc())
    ).all()
    return [
        NoteOut(
            id=r.id,
            body=r.body,
            created_at=r.created_at.isoformat(),
            user_name=r.user.name if r.user else None,
        )
        for r in rows
    ]


@router.post("/{contact_id}/notes", status_code=201, response_model=NoteOut)
def add_note(
    contact_id: int,
    body: NoteIn,
    c: Company = Depends(current_company),
    actor: User = Depends(require_role("admin", "owner")),
    db: Session = Depends(get_db),
):
    contact = db.scalar(
        select(Contact).where(Contact.id == contact_id, Contact.company_id == c.id)
    )
    if not contact:
        raise HTTPException(404, "الجهة غير موجودة")

    conv = db.scalar(
        select(Conversation).where(Conversation.contact_id == contact_id).order_by(Conversation.id.desc()).limit(1)
    )
    if not conv:
        conv = Conversation(
            company_id=c.id,
            contact_id=contact.id,
            customer_name=contact.display_name or "",
            status="open",
            created_at=datetime.now(timezone.utc),
            last_message_at=datetime.now(timezone.utc),
        )
        db.add(conv)
        db.flush()

    from app.models import InternalNote

    note = InternalNote(conversation_id=conv.id, user_id=actor.id, body=body.body)
    db.add(note)
    db.commit()
    db.refresh(note)
    return NoteOut(
        id=note.id,
        body=note.body,
        created_at=note.created_at.isoformat(),
        user_name=actor.name,
    )


@router.get("/{contact_id}/timeline")
def contact_timeline(
    contact_id: int,
    c: Company = Depends(current_company),
    actor: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    contact = db.scalar(
        select(Contact).where(Contact.id == contact_id, Contact.company_id == c.id)
    )
    if not contact:
        raise HTTPException(404, "الجهة غير موجودة")

    messages = db.scalars(
        select(Message)
        .where(Message.conversation_id.in_(
            select(Conversation.id).where(Conversation.contact_id == contact_id)
        ))
        .order_by(Message.created_at.desc())
    ).all()
    return {
        "contact_id": contact_id,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "direction": m.direction,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    }


# ---------------------------------------------------------------------------
# Duplicates + merge
# ---------------------------------------------------------------------------


@router.get("/duplicates")
def duplicate_suggestions(
    c: Company = Depends(current_company),
    actor: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Suggest possible duplicates: same phone or email across contacts."""
    contacts = db.scalars(
        select(Contact).where(Contact.company_id == c.id, Contact.merged_into_id.is_(None))
    ).all()

    by_email: dict[str, list[Contact]] = {}
    by_phone: dict[str, list[Contact]] = {}
    for contact in contacts:
        if contact.email:
            by_email.setdefault(contact.email.lower(), []).append(contact)
        if contact.phone:
            by_phone.setdefault(contact.phone, []).append(contact)

    suggestions = []
    seen_pairs = set()
    for group in list(by_email.values()) + list(by_phone.values()):
        if len(group) < 2:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                pair = tuple(sorted((group[i].id, group[j].id)))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                suggestions.append(
                    {
                        "contact_a": _contact_out(group[i]),
                        "contact_b": _contact_out(group[j]),
                        "reason": "same_email_or_phone",
                    }
                )
    return {"suggestions": suggestions}


@router.post("/merge")
def merge_contacts(
    body: dict,
    c: Company = Depends(current_company),
    actor: User = Depends(require_role("admin", "owner")),
    db: Session = Depends(get_db),
):
    """Merge contact_b into contact_a. contact_b is marked merged_into_id=contact_a."""
    a_id = body.get("contact_a_id")
    b_id = body.get("contact_b_id")
    if not a_id or not b_id or a_id == b_id:
        raise HTTPException(400, "معرفتي جهتين مختلفتين مطلوبتان")

    a = db.scalar(select(Contact).where(Contact.id == a_id, Contact.company_id == c.id))
    b = db.scalar(select(Contact).where(Contact.id == b_id, Contact.company_id == c.id))
    if not a or not b:
        raise HTTPException(404, "أحد الجهات غير موجود")

    # Fill missing fields from b into a
    for field in ("display_name", "first_name", "last_name", "email", "phone", "language", "country", "timezone", "status"):
        if not getattr(a, field) and getattr(b, field):
            setattr(a, field, getattr(b, field))

    if b.custom_fields and not a.custom_fields:
        a.custom_fields = b.custom_fields
    elif b.custom_fields and a.custom_fields:
        merged = dict(a.custom_fields)
        merged.update(b.custom_fields)
        a.custom_fields = merged

    # Move identities
    identities = db.scalars(
        select(ContactIdentity).where(ContactIdentity.contact_id == b.id)
    ).all()
    for ident in identities:
        ident.contact_id = a.id
        db.add(ident)

    # Move conversations
    convs = db.scalars(
        select(Conversation).where(Conversation.contact_id == b.id)
    ).all()
    for conv in convs:
        conv.contact_id = a.id
        db.add(conv)

    b.merged_into_id = a.id
    db.commit()

    try:
        audit_from_request(
            db,
            action="contact.merge",
            target=str(b.id),
            metadata={"merged_into": a.id, "merged_by": actor.id},
            user=actor,
        )
        db.commit()
    except Exception:
        log.exception("audit log write failed for contact merge")

    return {"ok": True, "merged_into": a.id}


# ---------------------------------------------------------------------------
# GDPR delete
# ---------------------------------------------------------------------------


@router.delete("/{contact_id}", status_code=204)
def delete_contact(
    contact_id: int,
    request: Request,
    c: Company = Depends(current_company),
    actor: User = Depends(require_role("admin", "owner")),
    db: Session = Depends(get_db),
):
    """GDPR-style delete: anonymize contact, delete messages + attachments."""
    contact = db.scalar(
        select(Contact).where(Contact.id == contact_id, Contact.company_id == c.id)
    )
    if not contact:
        raise HTTPException(404, "الجهة غير موجودة")

    # Delete messages + attachments for this contact's conversations
    conv_ids = [row[0] for row in db.execute(
        select(Conversation.id).where(Conversation.contact_id == contact_id)
    ).all()]
    if conv_ids:
        db.execute(delete(Attachment).where(Attachment.message_id.in_(
            select(Message.id).where(Message.conversation_id.in_(conv_ids))
        )))
        db.execute(delete(Message).where(Message.conversation_id.in_(conv_ids)))
        db.execute(delete(Conversation).where(Conversation.contact_id == contact_id))

    # Anonymize contact instead of hard delete (preserve referential integrity)
    contact.display_name = None
    contact.first_name = None
    contact.last_name = None
    contact.email = None
    contact.phone = None
    contact.custom_fields = {}
    contact.merged_into_id = None
    db.add(contact)
    db.commit()

    try:
        audit_from_request(
            db,
            action="contact.gdpr_delete",
            target=str(contact_id),
            user=actor,
            ip=request.client.host if request.client else None,
        )
        db.commit()
    except Exception:
        log.exception("audit log write failed for contact GDPR delete")

    return Response(status_code=204)


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------


@router.get("/export.csv")
def export_contacts_csv(
    c: Company = Depends(current_company),
    actor: User = Depends(require_role("admin", "owner")),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(Contact).where(Contact.company_id == c.id, Contact.merged_into_id.is_(None))
        .order_by(Contact.id.desc())
    ).all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        ["id", "display_name", "first_name", "last_name", "email", "phone", "language", "country", "timezone", "status", "created_at", "tags"]
    )
    for r in rows:
        writer.writerow(
            [
                r.id,
                r.display_name or "",
                r.first_name or "",
                r.last_name or "",
                r.email or "",
                r.phone or "",
                r.language or "",
                r.country or "",
                r.timezone or "",
                r.status or "",
                r.created_at.isoformat(),
                ";".join(t.name for t in r.tags),
            ]
        )

    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="contacts.csv"'},
    )
