"""Onboarding: per-step progress, resume state, getting-started checklist."""

from __future__ import annotations

import logging
from typing import Any

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_company, require_role
from app.models import Channel, Company, Document, Conversation, User
from app.services.ai import generate_onboarding_suggestion

router = APIRouter(prefix="/onboarding", tags=["onboarding"])
log = logging.getLogger("teledesk.onboarding")

ONBOARDING_STEPS = ["profile", "ai", "channel", "knowledge", "test", "team"]


class OnboardingStepIn(BaseModel):
    step: str = Field(min_length=1, max_length=40)
    data: dict[str, Any] = Field(default_factory=dict)


class OnboardingStepOut(BaseModel):
    step: str
    done: bool
    data: dict[str, Any] = {}


class OnboardingStateOut(BaseModel):
    current_step: str | None
    completed: bool
    completed_at: str | None
    steps: list[OnboardingStepOut]


class ChecklistItemOut(BaseModel):
    key: str
    label: str
    done: bool


class ChecklistOut(BaseModel):
    items: list[ChecklistItemOut]


def _step_done(c: Company, step: str) -> bool:
    profile = c.profile or {}
    step_key = f"step_{step}"
    return bool(profile.get(step_key, {}).get("done"))


@router.get("/state", response_model=OnboardingStateOut)
def onboarding_state(
    c: Company = Depends(current_company),
    actor: User = Depends(require_role("admin", "owner")),
):
    profile = c.profile or {}
    steps = [
        OnboardingStepOut(
            step=s,
            done=_step_done(c, s),
            data=profile.get(f"step_{s}", {}).get("data", {}),
        )
        for s in ONBOARDING_STEPS
    ]
    completed = c.onboarding_completed_at is not None
    return OnboardingStateOut(
        current_step=c.onboarding_step,
        completed=completed,
        completed_at=c.onboarding_completed_at.isoformat() if c.onboarding_completed_at else None,
        steps=steps,
    )


@router.post("/step", response_model=OnboardingStepOut)
def save_onboarding_step(
    body: OnboardingStepIn,
    request: Request,
    c: Company = Depends(current_company),
    actor: User = Depends(require_role("admin", "owner")),
    db: Session = Depends(get_db),
):
    step = body.step.strip().lower()
    if step not in ONBOARDING_STEPS:
        raise HTTPException(400, "خطوة غير صالحة")

    profile = dict(c.profile or {})
    profile[f"step_{step}"] = {
        "done": True,
        "data": body.data,
        "updated_by": actor.id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    c.profile = profile

    # Advance to next incomplete step
    next_step = None
    for s in ONBOARDING_STEPS:
        if s != step and not _step_done_from_profile(profile, s):
            next_step = s
            break
    if next_step is None:
        c.onboarding_step = None
        c.onboarding_completed_at = datetime.now(timezone.utc)
    else:
        c.onboarding_step = next_step

    db.commit()
    db.refresh(c)

    return OnboardingStepOut(
        step=step,
        done=True,
        data=body.data,
    )


def _step_done_from_profile(profile: dict[str, Any], step: str) -> bool:
    return bool(profile.get(f"step_{step}", {}).get("done"))


@router.get("/checklist", response_model=ChecklistOut)
def onboarding_checklist(
    c: Company = Depends(current_company),
    actor: User = Depends(require_role("admin", "owner")),
    db: Session = Depends(get_db),
):
    profile = c.profile or {}

    # Profile step done
    profile_done = _step_done_from_profile(profile, "profile")

    # AI configured: welcome/tone/handoff_keywords have meaningful values
    ai_configured = bool(
        c.welcome and c.tone and c.handoff_keywords
    )

    # Channel connected: at least one active channel
    channel_connected = db.scalars(
        select(Channel).where(Channel.company_id == c.id, Channel.active == True)  # noqa: E712
    ).first() is not None

    # Knowledge uploaded: at least one document
    knowledge_uploaded = db.scalars(
        select(Document).where(Document.company_id == c.id)
    ).first() is not None

    # Tested: at least one conversation
    tested = db.scalars(
        select(Conversation).where(Conversation.company_id == c.id)
    ).first() is not None

    # Teammates invited: at least one other user or pending invitation
    from app.models import Invitation

    other_members = db.scalars(
        select(User).where(User.company_id == c.id, User.id != actor.id)
    ).first() is not None
    pending_invites = db.scalars(
        select(Invitation).where(Invitation.company_id == c.id, Invitation.accepted_at.is_(None))
    ).first() is not None
    teammates_invited = other_members or pending_invites

    items = [
        ChecklistItemOut(key="profile", label="الملف التعريفي للشركة" if _ar(actor) else "Company profile", done=profile_done),
        ChecklistItemOut(key="ai", label="إعداد الذكاء الاصطناعي" if _ar(actor) else "AI configuration", done=ai_configured),
        ChecklistItemOut(key="channel", label="توصيل قناة" if _ar(actor) else "Connect a channel", done=channel_connected),
        ChecklistItemOut(key="knowledge", label="رفع قاعدة المعرفة" if _ar(actor) else "Upload knowledge", done=knowledge_uploaded),
        ChecklistItemOut(key="test", label="تجربة النظام" if _ar(actor) else "Test the system", done=tested),
        ChecklistItemOut(key="team", label="دعوة زملاء" if _ar(actor) else "Invite teammates", done=teammates_invited),
    ]
    return ChecklistOut(items=items)


def _ar(user: User) -> bool:
    return (getattr(user, "language", None) or "ar").startswith("ar")


@router.post("/suggest", response_model=dict[str, str])
def onboarding_suggest(
    c: Company = Depends(current_company),
    actor: User = Depends(require_role("admin", "owner")),
):
    """Gemini-based suggestion of welcome message, tone, handoff keywords.

    Editable suggestions, never auto-applied.
    """
    description = c.description or ""
    if not description.strip():
        raise HTTPException(400, "يجب وصف الشركة أولاً لإنشاء اقتراحات")

    try:
        suggestion = generate_onboarding_suggestion(description)
        return suggestion
    except Exception:
        log.exception("onboarding suggestion failed")
        return {
            "welcome": c.welcome or "أهلاً! كيف يمكنني مساعدتك؟",
            "tone": c.tone or "friendly",
            "handoff_keywords": c.handoff_keywords or "شكوى,استرداد,مكسور",
            "note": "الاقتراح افتراضي، يمكنك تعديله قبل التطبيق",
        }
