"""Lead capture service: conversational field collection with validation."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

try:
    import phonenumbers
except Exception:  # pragma: no cover - optional dependency
    phonenumbers = None

from app.models import Company, Contact, ContactFieldDefinition
from app.services.ai import generate_reply

log = logging.getLogger("teledesk.lead_capture")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass
class FieldState:
    key: str
    label: str
    type: str
    prompt_text: str | None
    required: bool
    collected: bool
    value: str | None


def _normalize_phone(value: str) -> str | None:
    if phonenumbers is None:
        return value
    try:
        parsed = phonenumbers.parse(value, None)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except Exception:
        return None
    return None


def _validate_value(field_type: str, value: str) -> str | None:
    """Return normalized value or None if invalid."""
    if field_type == "email":
        if not _EMAIL_RE.match(value or ""):
            return None
        return value.strip().lower()
    if field_type == "phone":
        return _normalize_phone(value)
    return value.strip() if value else None


def sensitive_data_detected(text: str) -> str | None:
    """Return reason string if sensitive data detected, else None."""
    card_re = re.compile(r"\b(?:\d[ -]*){13,16}\b")
    national_id_re = re.compile(r"\b\d{9,14}\b")
    password_hint_re = re.compile(r"(كلمة مرور|password|secret|رمز|pin|رقم سري)", re.IGNORECASE)
    if card_re.search(text):
        return "رقم بطاقة ائتمانية"
    if national_id_re.search(text) and password_hint_re.search(text):
        return "رقم وطني مع كلمة مرور/سري"
    if password_hint_re.search(text) and re.search(r"\d{4,}", text):
        return "كلمة مرور أو رمز سري"
    return None


def _collected_fields(contact: Contact) -> dict[str, Any]:
    return contact.custom_fields or {}


def _mark_collected(db, contact: Contact, key: str, value: Any) -> None:
    fields = dict(contact.custom_fields or {})
    fields[key] = value
    contact.custom_fields = fields
    db.add(contact)


def missing_ask_fields(
    company: Company, contact: Contact, db
) -> list[FieldState]:
    """Return list of ask_in_chat field definitions not yet collected."""
    definitions = db.scalars(
        select(ContactFieldDefinition).where(
            ContactFieldDefinition.company_id == company.id,
            ContactFieldDefinition.ask_in_chat == True,  # noqa: E712
        )
    ).all()
    collected = _collected_fields(contact)
    result: list[FieldState] = []
    for d in definitions:
        result.append(
            FieldState(
                key=d.key,
                label=d.label,
                type=d.type,
                prompt_text=d.prompt_text,
                required=d.required,
                collected=d.key in collected and collected[d.key] not in (None, ""),
                value=collected.get(d.key),
            )
        )
    return result


async def handle_lead_capture(
    db,
    company: Company,
    contact: Contact,
    customer_text: str,
) -> str | None:
    """Process an inbound customer message for lead capture.

    Returns an answer string to append to the AI reply (or None if no lead
    capture action needed). Handles:
    - Sensitive data refusal
    - Field extraction from customer replies
    - Asking for one missing field at a time
    """
    if not company.lead_capture_enabled:
        return None

    # 1) Sensitive data check on the raw customer text.
    reason = sensitive_data_detected(customer_text)
    if reason:
        return (
            "يُرجى عدم مشاركة بيانات حساسة مثل كلمات المرور أو أرقام بطاقات الائتمان أو "
            "أرقام الهويات الوطنية. يمكنني مساعدتك في استفسارك بدون هذه البيانات."
        )

    missing = missing_ask_fields(company, contact, db)
    pending = [f for f in missing if not f.collected]

    if not pending:
        return None  # All fields collected

    # 2) Try to extract a value for the first missing field from this message.
    first = pending[0]
    extracted = await _extract_value(first, customer_text, company, contact, db)
    if extracted is not None:
        _mark_collected(db, contact, first.key, extracted)
        db.flush()
        # Check if more fields remain
        missing2 = missing_ask_fields(company, contact, db)
        pending2 = [f for f in missing2 if not f.collected]
        if pending2:
            next_field = pending2[0]
            return _ask_question(next_field)
        return None  # Done collecting

    # 3) Nothing extracted: ask for the first missing field.
    return _ask_question(first)


def _ask_question(field: FieldState) -> str:
    prompt = field.prompt_text or f"هل يمكنك تزويدنا بـ {field.label}؟"
    return prompt


async def _extract_value(
    field: FieldState,
    customer_text: str,
    company: Company,
    contact: Contact,
    db,
) -> str | None:
    """Use Gemini structured output to extract a field value from the message."""
    system_prompt = (
        "أنت مستخرج بيانات لدُفعة جمع العملاء (lead capture). العميل أرسل رسالة، "
        "وحقل البيانات المطلوب استخراجه هو: {key} ({type}).\n"
        "أرجع JSON فقط: {{\"value\": \"الاستخراج أو null\", \"confident\": true/false}}\n"
        "إذا لم تكن الرسالة تحتوي على قيمة واضحة للحقل، أعد {{\"value\": null, \"confident\": false}}."
    ).format(key=field.key, type=field.type)

    try:
        result = generate_reply(
            system_prompt=system_prompt,
            context=f"العميل: {contact.display_name or 'غير معروف'}",
            history=[],
            question=customer_text,
        )
        answer = result.get("answer", "")
        if not answer:
            return None
        import json as _json

        data = _json.loads(answer)
        value = data.get("value")
        if value is None:
            return None
        return _validate_value(field.type, str(value))
    except Exception:
        log.exception("lead capture extraction failed")
        return None


# Import select here to avoid circular issues at module load
from sqlalchemy import select  # noqa: E402
