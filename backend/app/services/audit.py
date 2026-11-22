"""Audit log service: append-only record of security-relevant events."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog, User


def audit(
    db: Session,
    *,
    company_id: int | None = None,
    user_id: int | None = None,
    action: str,
    target: str | None = None,
    metadata: dict[str, Any] | None = None,
    ip: str | None = None,
) -> AuditLog:
    """Write an audit log entry. Never raises on failure (best-effort)."""
    entry = AuditLog(
        company_id=company_id,
        user_id=user_id,
        action=action,
        target=target,
        event_metadata=metadata,
        ip=ip,
    )
    db.add(entry)
    db.flush()
    return entry


def audit_from_request(
    db: Session,
    *,
    action: str,
    target: str | None = None,
    metadata: dict[str, Any] | None = None,
    user: User | None = None,
    ip: str | None = None,
) -> AuditLog | None:
    """Convenience: derive company_id from the user and write an audit entry."""
    if user is None:
        return None
    company_id = getattr(user, "company_id", None)
    return audit(
        db,
        company_id=company_id,
        user_id=user.id,
        action=action,
        target=target,
        metadata=metadata,
        ip=ip,
    )
