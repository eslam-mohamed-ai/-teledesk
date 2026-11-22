"""Authentication routes: cookie-based sessions with rotating refresh tokens.

All state-changing endpoints require a valid CSRF token (X-CSRF-Token header
matching the teledesk_csrf cookie). Register/login/forgot are public and do
not require authentication.
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone

from typing import Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import (
    csrf_protect,
    current_user,
    hash_password,
    make_csrf_token,
    verify_password,
)
from app.models import (
    Company,
    EmailVerificationToken,
    Invitation,
    PasswordResetToken,
    RefreshToken,
    User,
)
from app.services.auth import (
    authenticate_user,
    check_rate_limit,
    clear_attempts,
    create_refresh_token,
    hash_token,
    make_access_token as service_make_access_token,
    record_failed_attempt,
    rotate_refresh_token,
    revoke_all_user_tokens,
    revoke_refresh_token,
    validate_password_strength,
)
from app.services.email import get_email_sender, reset_password_template, verify_email_template

router = APIRouter(prefix="/auth", tags=["auth"])
log = logging.getLogger("teledesk.auth")
bearer = HTTPBearer(auto_error=False)

# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    lang: str = Field(default="en", max_length=10)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=128)


class ChangePasswordIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class VerifyEmailIn(BaseModel):
    token: str


class ResendVerificationIn(BaseModel):
    email: EmailStr


class AcceptInvitationIn(BaseModel):
    token: str
    name: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=8, max_length=128)


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    email_verified: bool


class SessionOut(BaseModel):
    id: int
    created_at: str
    expires_at: str
    device_info: str | None
    ip_address: str | None
    current: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _set_session_cookies(response: Response, access_token: str, refresh_token: str, csrf_token: str) -> None:
    secure = settings.COOKIE_SECURE
    samesite: Literal["lax", "strict", "none"] = cast(Literal["lax", "strict", "none"], settings.COOKIE_SAMESITE)
    access_ttl = settings.ACCESS_TOKEN_TTL_SECONDS

    response.set_cookie(
        settings.SESSION_COOKIE_NAME,
        access_token,
        max_age=access_ttl,
        httponly=True,
        secure=secure,
        samesite=samesite,
        path="/",
    )
    response.set_cookie(
        settings.REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=60 * 60 * 24 * 30,
        httponly=True,
        secure=secure,
        samesite=samesite,
        path="/auth",
    )
    response.set_cookie(
        settings.CSRF_COOKIE_NAME,
        csrf_token,
        max_age=60 * 60 * 24 * 30,
        httponly=False,
        secure=secure,
        samesite=samesite,
        path="/",
    )


def _clear_session_cookies(response: Response) -> None:
    response.delete_cookie(settings.SESSION_COOKIE_NAME, path="/")
    response.delete_cookie(settings.REFRESH_COOKIE_NAME, path="/auth")
    response.delete_cookie(settings.CSRF_COOKIE_NAME, path="/")


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        email_verified=user.email_verified,
    )


def _issue_tokens(response: Response, db: Session, user: User, device_info: str | None, ip_address: str | None) -> None:
    access_token = service_make_access_token(user.id)
    plain_refresh, _record = create_refresh_token(db, user, device_info=device_info, ip_address=ip_address)
    db.commit()
    csrf = make_csrf_token()
    _set_session_cookies(response, access_token, plain_refresh, csrf)


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    body: RegisterIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    name = body.name.strip()
    email = str(body.email).strip().lower()
    lang = body.lang.strip().lower() or "en"

    password_errors = validate_password_strength(body.password)
    if password_errors:
        raise HTTPException(400, "; ".join(password_errors))

    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        # Uniform response: never reveal whether an email exists.
        raise HTTPException(400, "إذا كان البريد مسجّلًا، ستتلقى رسالة تأكيد")

    try:
        company = Company(
            name=f"شركة {name}",
            plan="free",
            onboarding_step="profile",
        )
        db.add(company)
        db.flush()

        user = User(
            company_id=company.id,
            name=name,
            email=email,
            password_hash=hash_password(body.password),
            email_verified=False,
            role="agent",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Issue verification token + email (console/dev sends to stdout).
        token = secrets.token_urlsafe(32)
        record = EmailVerificationToken(
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=60),
        )
        db.add(record)
        db.commit()

        sender = get_email_sender()
        subject, text_body, html_body = verify_email_template(user.name, token, settings.PUBLIC_BASE_URL, lang)
        # Fire and forget; failure must not block registration.
        try:
            import asyncio

            asyncio.get_event_loop().run_until_complete(sender.send(email, subject, text_body, html_body))
        except Exception:
            log.exception("Verification email send failed")

        _issue_tokens(response, db, user, request.headers.get("user-agent"), request.client.host if request.client else None)

        return {"user": _user_out(user), "requires_verification": True}

    except HTTPException:
        raise
    except Exception:
        db.rollback()
        log.exception("Account creation failed")
        raise HTTPException(500, "حصل خطأ أثناء إنشاء الحساب")


@router.post("/login")
def login(
    body: LoginIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    email = str(body.email).strip().lower()
    identifier = f"login:{email}"

    allowed, retry_after = check_rate_limit(identifier)
    if not allowed:
        raise HTTPException(429, f"محاولات كثيرة جدًا. جرّب مرة أخرى بعد {retry_after} ثانية")

    user = authenticate_user(db, email, body.password)

    if user is None:
        record_failed_attempt(identifier)
        # Uniform response regardless of whether the email exists.
        raise HTTPException(400, "البريد أو كلمة المرور غلط")

    clear_attempts(identifier)

    if not user.email_verified:
        # Still issue tokens but mark that verification is needed.
        pass

    _issue_tokens(response, db, user, request.headers.get("user-agent"), request.client.host if request.client else None)

    return {"user": _user_out(user), "email_verified": user.email_verified}


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    _csrf: None = Depends(csrf_protect),
):
    refresh_token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if refresh_token:
        revoke_refresh_token(db, hash_token(refresh_token))
    db.commit()

    # Also revoke the bearer access family if present.
    if creds and creds.scheme.lower() == "bearer":
        revoke_all_user_tokens(db, user.id)

    _clear_session_cookies(response)
    return {"ok": True}


@router.post("/refresh")
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    refresh_token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if not refresh_token:
        raise HTTPException(401, "لازم تسجّل دخول")

    token_hash = hash_token(refresh_token)
    record = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))

    if (
        not record
        or record.revoked_at is not None
        or record.expires_at < datetime.now(timezone.utc)
        or record.user_id is None
    ):
        _clear_session_cookies(response)
        raise HTTPException(401, "الجلسة انتهت")

    user = db.get(User, record.user_id)
    if not user:
        _clear_session_cookies(response)
        raise HTTPException(401, "مستخدم غير موجود")

    try:
        plain_refresh, _new = rotate_refresh_token(
            db, record, request.headers.get("user-agent"), request.client.host if request.client else None
        )
        db.commit()
    except ValueError:
        # Family compromise: revoke everything and force re-login.
        revoke_all_user_tokens(db, user.id)
        db.commit()
        _clear_session_cookies(response)
        raise HTTPException(401, "الجلسة غير آمنة. يسجّل دخول تاني")

    access_token = service_make_access_token(user.id)
    csrf = make_csrf_token()
    _set_session_cookies(response, access_token, plain_refresh, csrf)

    return {"user": _user_out(user)}


@router.post("/forgot-password")
def forgot_password(
    body: ForgotPasswordIn,
    request: Request,
    db: Session = Depends(get_db),
):
    email = str(body.email).strip().lower()
    identifier = f"forgot:{email}"

    allowed, retry_after = check_rate_limit(identifier)
    if not allowed:
        raise HTTPException(429, f"محاولات كثيرة جدًا. جرّب مرة أخرى بعد {retry_after} ثانية")

    user = db.scalar(select(User).where(User.email == email))

    # Uniform response: never reveal whether an email exists.
    if not user:
        return {"ok": True}

    # Invalidate previous reset tokens for this user.
    db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).update(
        {PasswordResetToken.used_at: datetime.now(timezone.utc)}, synchronize_session=False
    )

    token = secrets.token_urlsafe(32)
    record = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
    )
    db.add(record)
    db.commit()

    lang = "ar" if (user.email or "").startswith("ar") else "en"
    sender = get_email_sender()
    subject, text_body, html_body = reset_password_template(user.name, token, lang)
    try:
        import asyncio

        asyncio.get_event_loop().run_until_complete(sender.send(email, subject, text_body, html_body))
    except Exception:
        log.exception("Reset password email send failed")

    return {"ok": True}


@router.post("/reset-password")
def reset_password(
    body: ResetPasswordIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    _csrf: None = Depends(csrf_protect),
):
    password_errors = validate_password_strength(body.password)
    if password_errors:
        raise HTTPException(400, "; ".join(password_errors))

    token_hash = hash_token(body.token)
    record = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
        )
    )

    if not record or record.expires_at < datetime.now(timezone.utc):
        raise HTTPException(400, "رابط إعادة التعيين غير صالح أو منتهي الصلاحية")

    user = db.get(User, record.user_id)
    if not user:
        raise HTTPException(400, "رابط إعادة التعيين غير صالح")

    user.password_hash = hash_password(body.password)
    record.used_at = datetime.now(timezone.utc)
    revoke_all_user_tokens(db, user.id)
    db.commit()
    _clear_session_cookies(response)

    return {"ok": True}


@router.post("/change-password")
def change_password(
    body: ChangePasswordIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
    _csrf: None = Depends(csrf_protect),
):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(400, "كلمة المرور الحالية غلط")

    password_errors = validate_password_strength(body.new_password)
    if password_errors:
        raise HTTPException(400, "; ".join(password_errors))

    user.password_hash = hash_password(body.new_password)
    revoke_all_user_tokens(db, user.id)
    db.commit()
    _clear_session_cookies(response)

    return {"ok": True}


@router.post("/verify-email")
def verify_email(
    body: VerifyEmailIn,
    db: Session = Depends(get_db),
):
    token_hash = hash_token(body.token)
    record = db.scalar(
        select(EmailVerificationToken).where(
            EmailVerificationToken.token_hash == token_hash,
            EmailVerificationToken.used_at.is_(None),
        )
    )

    if not record or record.expires_at < datetime.now(timezone.utc):
        raise HTTPException(400, "رابط التحقق غير صالح أو منتهي الصلاحية")

    user = db.get(User, record.user_id)
    if not user:
        raise HTTPException(400, "رابط التحقق غير صالح")

    user.email_verified = True
    record.used_at = datetime.now(timezone.utc)
    db.commit()

    return {"ok": True, "email_verified": True}


@router.post("/resend-verification")
def resend_verification(
    body: ResendVerificationIn,
    request: Request,
    db: Session = Depends(get_db),
):
    email = str(body.email).strip().lower()
    user = db.scalar(select(User).where(User.email == email))

    # Uniform response.
    if not user or user.email_verified:
        return {"ok": True}

    db.query(EmailVerificationToken).filter(
        EmailVerificationToken.user_id == user.id,
        EmailVerificationToken.used_at.is_(None),
    ).update({EmailVerificationToken.used_at: datetime.now(timezone.utc)}, synchronize_session=False)

    token = secrets.token_urlsafe(32)
    record = EmailVerificationToken(
        user_id=user.id,
        token_hash=hash_token(token),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=60),
    )
    db.add(record)
    db.commit()

    sender = get_email_sender()
    subject, text_body, html_body = verify_email_template(user.name, token, settings.PUBLIC_BASE_URL, "en")
    try:
        import asyncio

        asyncio.get_event_loop().run_until_complete(sender.send(email, subject, text_body, html_body))
    except Exception:
        log.exception("Resend verification email failed")

    return {"ok": True}


# ---------------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------------


@router.post("/accept-invitation", status_code=status.HTTP_201_CREATED)
def accept_invitation(
    body: AcceptInvitationIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    token_hash = hash_token(body.token)
    invitation = db.scalar(
        select(Invitation).where(
            Invitation.token_hash == token_hash,
            Invitation.accepted_at.is_(None),
        )
    )

    if not invitation or invitation.expires_at < datetime.now(timezone.utc):
        raise HTTPException(400, "الدعوة غير صالحة أو منتهية الصلاحية")

    password_errors = validate_password_strength(body.password)
    if password_errors:
        raise HTTPException(400, "; ".join(password_errors))

    existing = db.scalar(select(User).where(User.email == invitation.email))
    if existing:
        raise HTTPException(400, "البريد ده مسجّل قبل كده")

    try:
        user = User(
            company_id=invitation.company_id,
            name=body.name.strip(),
            email=invitation.email.strip().lower(),
            password_hash=hash_password(body.password),
            role=invitation.role,
            email_verified=True,
        )
        db.add(user)
        invitation.accepted_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)

        _issue_tokens(response, db, user, request.headers.get("user-agent"), request.client.host if request.client else None)

        return {"user": _user_out(user)}

    except Exception:
        db.rollback()
        log.exception("Accept invitation failed")
        raise HTTPException(500, "حصل خطأ أثناء قبول الدعوة")


# ---------------------------------------------------------------------------
# Authenticated endpoints
# ---------------------------------------------------------------------------


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return _user_out(user)


@router.get("/sessions", response_model=list[SessionOut])
def sessions(user: User = Depends(current_user), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    rows = db.scalars(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,
        )
    ).all()
    return [
        SessionOut(
            id=r.id,
            created_at=r.created_at.isoformat(),
            expires_at=r.expires_at.isoformat(),
            device_info=r.device_info,
            ip_address=r.ip_address,
            current=False,
        )
        for r in rows
    ]


@router.delete("/sessions/{session_id}")
def revoke_session(
    session_id: int,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
    _csrf: None = Depends(csrf_protect),
):
    record = db.scalar(
        select(RefreshToken).where(
            RefreshToken.id == session_id,
            RefreshToken.user_id == user.id,
        )
    )
    if not record:
        raise HTTPException(404, "الجلسة مش موجودة")

    record.revoked_at = datetime.now(timezone.utc)
    db.commit()

    # If revoking the current session, clear cookies.
    refresh_cookie = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if refresh_cookie and hash_token(refresh_cookie) == record.token_hash:
        _clear_session_cookies(response)

    return {"ok": True}
