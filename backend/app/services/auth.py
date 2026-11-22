"""Authentication service: tokens, password validation, rate limiting.

Access tokens are short-lived JWTs (~15 min). Refresh tokens are rotating,
opaque strings stored hashed in the DB and issued in an httpOnly cookie.
Refreshing rotates both tokens and revokes the previous refresh token; reuse
of a revoked token revokes the whole family (token theft detection).
"""

from __future__ import annotations

import hashlib
import secrets
import time
from datetime import datetime, timedelta, timezone

import jwt
from redis import Redis

from app.config import settings
from app.deps import verify_password
from app.models import RefreshToken, User
from sqlalchemy.orm import Session

ACCESS_TOKEN_TTL_SECONDS = 15 * 60
REFRESH_TOKEN_TTL_DAYS = 30
LOCKOUT_WINDOW_SECONDS = 15 * 60
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MULTIPLIER_BASE = 300  # 5 min initial lockout

_RATE_LIMIT_PREFIX = "teledesk:rl:"
_LOCKOUT_PREFIX = "teledesk:lockout:"


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def make_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(seconds=ACCESS_TOKEN_TTL_SECONDS),
        "type": "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def _redis() -> Redis:
    return Redis.from_url(
        settings.REDIS_URL,
        socket_connect_timeout=2,
        socket_timeout=2,
        decode_responses=True,
    )


def _rate_limit_key(identifier: str) -> str:
    return f"{_RATE_LIMIT_PREFIX}{identifier}"


def _lockout_key(identifier: str) -> str:
    return f"{_LOCKOUT_PREFIX}{identifier}"


def check_rate_limit(identifier: str) -> tuple[bool, int]:
    """Return (allowed, retry_after_seconds).

    Tracks failed login attempts per identifier with progressive lockout.
    """
    try:
        r = _redis()
        lockout_until = r.get(_lockout_key(identifier))
        now = time.time()
        if lockout_until and float(lockout_until) > now:
            return False, int(float(lockout_until) - now)
        attempts = int(r.get(_rate_limit_key(identifier)) or 0)
        if attempts >= MAX_FAILED_ATTEMPTS:
            backoff = LOCKOUT_MULTIPLIER_BASE * (2 ** (attempts - MAX_FAILED_ATTEMPTS))
            lockout_until = now + backoff
            r.setex(_lockout_key(identifier), int(backoff) + 3600, lockout_until)
            return False, int(backoff)
        return True, 0
    except Exception:
        # Redis unavailable: fail open but do not record.
        return True, 0


def record_failed_attempt(identifier: str) -> None:
    try:
        r = _redis()
        r.incr(_rate_limit_key(identifier))
        r.expire(_rate_limit_key(identifier), LOCKOUT_WINDOW_SECONDS + 3600)
    except Exception:
        pass


def clear_attempts(identifier: str) -> None:
    try:
        r = _redis()
        r.delete(_rate_limit_key(identifier), _lockout_key(identifier))
    except Exception:
        pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_refresh_token(
    db: Session,
    user: User,
    device_info: str | None = None,
    ip_address: str | None = None,
) -> tuple[str, RefreshToken]:
    """Create a rotating refresh token. Returns (plain_token, record)."""
    plain_token = secrets.token_urlsafe(48)
    family_id = secrets.token_hex(16)
    expires_at = _now() + timedelta(days=REFRESH_TOKEN_TTL_DAYS)
    record = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(plain_token),
        family_id=family_id,
        expires_at=expires_at,
        device_info=device_info,
        ip_address=ip_address,
    )
    db.add(record)
    db.flush()
    return plain_token, record


def rotate_refresh_token(
    db: Session,
    used_record: RefreshToken,
    device_info: str | None = None,
    ip_address: str | None = None,
) -> tuple[str, RefreshToken]:
    """Revoke the used token and issue a new one in the same family.

    Raises if the token's family has been compromised (reuse of a revoked
    token from a different family member).
    """
    # Revoke current token if not already.
    if used_record.revoked_at is None:
        used_record.revoked_at = _now()
        db.add(used_record)

    # Family compromise detection: any other revoked token in this family
    # means the family was stolen; revoke everything.
    compromised = db.query(RefreshToken).filter(
        RefreshToken.family_id == used_record.family_id,
        RefreshToken.revoked_at.isnot(None),
        RefreshToken.id != used_record.id,
    ).first()
    if compromised:
        db.query(RefreshToken).filter(
            RefreshToken.family_id == used_record.family_id
        ).update({RefreshToken.revoked_at: _now()}, synchronize_session=False)
        from app.services.crypto import decrypt  # noqa: F401  (kept for symmetry)

        raise ValueError("refresh token family compromised")

    plain_token, new_record = create_refresh_token(
        db,
        used_record.user,
        device_info=device_info,
        ip_address=ip_address,
    )
    new_record.family_id = used_record.family_id
    db.add(new_record)
    db.flush()
    return plain_token, new_record


def revoke_refresh_token(db: Session, token_hash: str) -> None:
    record = db.scalar(
        __import__("sqlalchemy").select(RefreshToken).where(
            RefreshToken.token_hash == token_hash
        )
    )
    if record and record.revoked_at is None:
        record.revoked_at = _now()
        db.add(record)


def revoke_all_user_tokens(db: Session, user_id: int) -> None:
    db.query(RefreshToken).filter(RefreshToken.user_id == user_id).update(
        {RefreshToken.revoked_at: _now()}, synchronize_session=False
    )


def validate_password_strength(password: str) -> list[str]:
    """Return list of validation error messages (empty if valid)."""
    errors: list[str] = []
    if len(password) < 8:
        errors.append("كلمة المرور قصيرة جدًا (الحد الأدنى 8 حروف)")
    if len(password) > 128:
        errors.append("كلمة المرور طويلة جدًا")
    if not any(c.isupper() for c in password):
        errors.append("لزم تحتوي كلمة المرور على حرف كبير واحد على الأقل")
    if not any(c.islower() for c in password):
        errors.append("لزم تحتوي كلمة المرور على حرف صغير واحد على الأقل")
    if not any(c.isdigit() for c in password):
        errors.append("لزم تحتوي كلمة المرور على رقم واحد على الأقل")
    return errors


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """Constant-time-ish authentication. Returns None on any failure."""
    email = (email or "").strip().lower()
    user = db.scalar(__import__("sqlalchemy").select(User).where(User.email == email))
    if user is None:
        # Hash a dummy password to keep timing similar.
        verify_password(password, "$2b$unused$" + "x" * 60)
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def require_email_verified(user: User) -> None:
    if not user.email_verified:
        raise ValueError("email not verified")
