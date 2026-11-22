"""Team management: invitations, members, role changes, removal.

Owner/manager RBAC via require_role. Owner cannot be removed or demoted if
they are the last owner; agents cannot manage the team.
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import current_company, require_role
from app.models import Company, Invitation, Message, User
from app.services.audit import audit_from_request
from app.services.auth import hash_token
from app.services.email import get_email_sender, invitation_email_template

router = APIRouter(prefix="/team", tags=["team"])
log = logging.getLogger("teledesk.team")


class InviteIn(BaseModel):
    email: EmailStr
    role: str = Field(default="agent", max_length=32)


class InviteOut(BaseModel):
    id: int
    email: str
    role: str
    status: str
    expires_at: str


class MemberOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    email_verified: bool
    created_at: str


class ChangeRoleIn(BaseModel):
    role: str = Field(max_length=32)


class RemoveMemberIn(BaseModel):
    user_id: int


def _invite_out(inv: Invitation) -> InviteOut:
    return InviteOut(
        id=inv.id,
        email=inv.email,
        role=inv.role,
        status="accepted" if inv.accepted_at else ("expired" if inv.expires_at < datetime.now(timezone.utc) else "pending"),
        expires_at=inv.expires_at.isoformat(),
    )


def _member_out(user: User) -> MemberOut:
    return MemberOut(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        email_verified=user.email_verified,
        created_at=user.created_at.isoformat(),
    )


@router.post("/invite", status_code=status.HTTP_201_CREATED)
def invite(
    body: InviteIn,
    request: Request,
    response: Response,
    c: Company = Depends(current_company),
    actor: User = Depends(require_role("admin", "owner")),
    db: Session = Depends(get_db),
):
    if actor.role not in ("admin", "owner"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "only admins and owners can invite members")

    email = str(body.email).strip().lower()
    role = body.role.strip().lower() or "agent"
    if role not in ("admin", "agent"):
        raise HTTPException(400, "الدور غير صالح")

    existing = db.scalar(select(User).where(User.email == email, User.company_id == c.id))
    if existing:
        raise HTTPException(400, "المستخدم مسجل بالفعل في هذه الشركة")

    pending = db.scalar(
        select(Invitation).where(
            Invitation.email == email,
            Invitation.company_id == c.id,
            Invitation.accepted_at.is_(None),
            Invitation.expires_at > datetime.now(timezone.utc),
        )
    )
    if pending:
        raise HTTPException(400, "هناك دعوة معلقة لهذا البريد")

    token = secrets.token_urlsafe(32)
    record = Invitation(
        company_id=c.id,
        email=email,
        role=role,
        token_hash=hash_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    sender = get_email_sender()
    subject, text_body, html_body = invitation_email_template(actor.name, email, token, settings.PUBLIC_BASE_URL)
    try:
        import asyncio

        asyncio.get_event_loop().run_until_complete(sender.send(email, subject, text_body, html_body))
    except Exception:
        log.exception("invitation email send failed")

    try:
        audit_from_request(
            db,
            action="team.invite",
            target=email,
            metadata={"role": role, "invited_by": actor.id},
            user=actor,
            ip=request.client.host if request.client else None,
        )
        db.commit()
    except Exception:
        log.exception("audit log write failed for team invite")

    return {"invitation": _invite_out(record)}


@router.get("/members", response_model=list[MemberOut])
def list_members(
    c: Company = Depends(current_company),
    actor: User = Depends(require_role("admin", "owner")),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(User).where(User.company_id == c.id).order_by(User.created_at.desc())
    ).all()
    return [_member_out(r) for r in rows]


@router.get("/invitations", response_model=list[InviteOut])
def list_invitations(
    c: Company = Depends(current_company),
    actor: User = Depends(require_role("admin", "owner")),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(Invitation).where(Invitation.company_id == c.id).order_by(Invitation.created_at.desc())
    ).all()
    return [_invite_out(r) for r in rows]


@router.delete("/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_invitation(
    invitation_id: int,
    request: Request,
    c: Company = Depends(current_company),
    actor: User = Depends(require_role("admin", "owner")),
    db: Session = Depends(get_db),
):
    record = db.scalar(
        select(Invitation).where(
            Invitation.id == invitation_id,
            Invitation.company_id == c.id,
        )
    )
    if not record:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "الدعوة غير موجودة")

    db.delete(record)
    db.commit()

    try:
        audit_from_request(
            db,
            action="team.invite_revoke",
            target=str(invitation_id),
            user=actor,
            ip=request.client.host if request.client else None,
        )
        db.commit()
    except Exception:
        log.exception("audit log write failed for invite revoke")

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/members/{user_id}/role")
def change_role(
    user_id: int,
    body: ChangeRoleIn,
    request: Request,
    c: Company = Depends(current_company),
    actor: User = Depends(require_role("admin", "owner")),
    db: Session = Depends(get_db),
):
    target = db.scalar(select(User).where(User.id == user_id, User.company_id == c.id))
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "المستخدم غير موجود")

    new_role = body.role.strip().lower()
    if new_role not in ("admin", "agent", "owner"):
        raise HTTPException(400, "الدور غير صالح")

    # Owner cannot be demoted if they are the last owner.
    if target.role == "owner" and new_role != "owner":
        owner_count = db.query(User).filter(User.company_id == c.id, User.role == "owner").count()
        if owner_count <= 1:
            raise HTTPException(400, "لا يمكن إزالة دور المالك الأخير")

    target.role = new_role
    db.commit()

    try:
        audit_from_request(
            db,
            action="team.role_change",
            target=str(user_id),
            metadata={"new_role": new_role, "changed_by": actor.id},
            user=actor,
            ip=request.client.host if request.client else None,
        )
        db.commit()
    except Exception:
        log.exception("audit log write failed for role change")

    return _member_out(target)


@router.delete("/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    user_id: int,
    request: Request,
    c: Company = Depends(current_company),
    actor: User = Depends(require_role("admin", "owner")),
    db: Session = Depends(get_db),
):
    target = db.scalar(select(User).where(User.id == user_id, User.company_id == c.id))
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "المستخدم غير موجود")

    # Owner cannot be removed if they are the last owner.
    if target.role == "owner":
        owner_count = db.query(User).filter(User.company_id == c.id, User.role == "owner").count()
        if owner_count <= 1:
            raise HTTPException(400, "لا يمكن إزالة المالك الأخير")

    db.delete(target)
    db.commit()

    try:
        audit_from_request(
            db,
            action="team.remove_member",
            target=str(user_id),
            user=actor,
            ip=request.client.host if request.client else None,
        )
        db.commit()
    except Exception:
        log.exception("audit log write failed for member removal")

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Failed jobs (dead-letter) view
# ---------------------------------------------------------------------------


class FailedJobOut(BaseModel):
    id: int
    conversation_id: int
    channel_id: int | None
    direction: str | None
    sender_type: str | None
    content: str
    error_code: str | None
    error_message: str | None
    created_at: str


@router.get("/failed-jobs", response_model=list[FailedJobOut], tags=["team"])
def failed_jobs(
    limit: int = 50,
    offset: int = 0,
    c: Company = Depends(current_company),
    actor: User = Depends(require_role("admin", "owner")),
    db: Session = Depends(get_db),
):
    if limit < 1 or limit > 200:
        raise HTTPException(400, "limit يجب أن يكون بين 1 و 200")
    if offset < 0:
        raise HTTPException(400, "offset غير صالح")

    rows = (
        db.query(Message)
        .filter(Message.company_id == c.id, Message.delivery_status == "failed")
        .order_by(Message.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        FailedJobOut(
            id=m.id,
            conversation_id=m.conversation_id,
            channel_id=m.channel_id,
            direction=m.direction,
            sender_type=m.sender_type,
            content=m.content,
            error_code=m.error_code,
            error_message=m.error_message,
            created_at=m.created_at.isoformat(),
        )
        for m in rows
    ]

