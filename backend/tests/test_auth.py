"""Auth route tests using dependency overrides (no live PostgreSQL required)."""

from __future__ import annotations

import asyncio
import base64
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import csrf_protect, current_user, hash_password
from app.models import User
from app.services.auth import make_access_token
from app.services.email import get_email_sender


def _make_session() -> Session:
    session = MagicMock(spec=Session)
    session.scalar = MagicMock(return_value=None)
    session.get = MagicMock(return_value=None)
    session.query = MagicMock(return_value=MagicMock())
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.flush = MagicMock()
    added: list[Any] = []

    def _add(obj):
        added.append(obj)

    def _commit():
        for obj in added:
            if hasattr(obj, "id") and obj.id is None:
                obj.id = 1

    session.add = _add
    session.commit = _commit
    session.refresh = MagicMock()
    session.execute = MagicMock()
    session.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    return session


class FakeSender:
    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    async def send(self, to: str, subject: str, text_body: str, html_body: str) -> None:
        self.sent.append({"to": to, "subject": subject, "text_body": text_body, "html_body": html_body})


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
def fake_sender():
    return FakeSender()


@pytest.fixture
def client(event_loop, fake_sender):
    from app.main import app

    session = _make_session()
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_email_sender] = lambda: fake_sender
    app.dependency_overrides[csrf_protect] = lambda: None
    yield TestClient(app)
    app.dependency_overrides.clear()


def _hash_token(token: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(token.encode()).digest()).rstrip(b"=").decode()


def _mock_user(id_=1, email="alice@example.com", name="Alice", role="owner", email_verified=True):
    user = MagicMock(spec=User)
    user.id = id_
    user.email = email
    user.name = name
    user.role = role
    user.email_verified = email_verified
    return user


def test_register_creates_user_and_issues_cookies(client, fake_sender, event_loop):
    session = _make_session()
    session.scalar.return_value = None  # no existing user
    client.app.dependency_overrides[get_db] = lambda: session

    with patch("app.deps.hash_password", return_value="hashed"), patch(
        "asyncio.get_event_loop", return_value=event_loop
    ), patch(
        "app.routes.auth.get_email_sender", return_value=fake_sender
    ):
        resp = client.post(
            "/api/auth/register",
            json={"name": "Alice", "email": "alice@example.com", "password": "SecurePass123"},
        )

    assert resp.status_code == 201, resp.text
    assert resp.json()["user"]["email"] == "alice@example.com"
    assert settings.SESSION_COOKIE_NAME in resp.cookies
    assert settings.REFRESH_COOKIE_NAME in resp.cookies
    assert settings.CSRF_COOKIE_NAME in resp.cookies


def test_login_issues_tokens(client):
    session = _make_session()
    user = _mock_user()
    user.password_hash = hash_password("SecurePass123")
    session.scalar.return_value = user
    client.app.dependency_overrides[get_db] = lambda: session

    with patch("app.services.auth.authenticate_user", return_value=user), patch(
        "app.services.auth.clear_attempts"
    ), patch("app.routes.auth.service_make_access_token", return_value="access-token"), patch(
        "app.routes.auth.create_refresh_token", return_value=("refresh-token", MagicMock())
    ):
        resp = client.post(
            "/api/auth/login",
            json={"email": "alice@example.com", "password": "SecurePass123"},
        )

    assert resp.status_code == 200, resp.text
    assert resp.json()["user"]["email"] == "alice@example.com"
    assert settings.SESSION_COOKIE_NAME in resp.cookies


def test_login_wrong_password_400(client):
    session = _make_session()
    session.scalar.return_value = None
    client.app.dependency_overrides[get_db] = lambda: session

    with patch("app.services.auth.authenticate_user", return_value=None), patch(
        "app.services.auth.record_failed_attempt"
    ):
        resp = client.post(
            "/api/auth/login",
            json={"email": "alice@example.com", "password": "wrong"},
        )

    assert resp.status_code == 400


def test_me_requires_auth(client):
    session = _make_session()
    client.app.dependency_overrides[get_db] = lambda: session
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_forgot_password_uniform_response(client):
    session = _make_session()
    session.scalar.return_value = None  # no user found
    client.app.dependency_overrides[get_db] = lambda: session

    with patch("app.services.auth.check_rate_limit", return_value=(True, 0)):
        resp = client.post("/api/auth/forgot-password", json={"email": "none@example.com"})

    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_reset_password_valid_token(client):
    session = _make_session()
    user = _mock_user(id_=1, email="alice@example.com")
    user.password_hash = "old-hash"
    token = "reset-token-abc"
    token_hash = _hash_token(token)
    record = MagicMock()
    record.token_hash = token_hash
    record.used_at = None
    record.expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
    session.scalar.return_value = record
    session.get.return_value = user
    client.app.dependency_overrides[get_db] = lambda: session

    with patch("app.services.auth.hash_token", return_value=token_hash), patch(
        "app.routes.auth.hash_password", return_value="new-hash"
    ), patch("app.services.auth.revoke_all_user_tokens"):
        resp = client.post(
            "/api/auth/reset-password",
            json={"token": token, "password": "NewSecurePass123"},
        )

    assert resp.status_code == 200, resp.text
    assert user.password_hash == "new-hash"


def test_verify_email_valid_token(client):
    session = _make_session()
    user = _mock_user(id_=1, email="alice@example.com", email_verified=False)
    token = "verify-token-abc"
    token_hash = _hash_token(token)
    record = MagicMock()
    record.token_hash = token_hash
    record.used_at = None
    record.expires_at = datetime.now(timezone.utc) + timedelta(minutes=60)
    session.scalar.return_value = record
    session.get.return_value = user
    client.app.dependency_overrides[get_db] = lambda: session

    with patch("app.services.auth.hash_token", return_value=token_hash):
        resp = client.post("/api/auth/verify-email", json={"token": token})

    assert resp.status_code == 200, resp.text
    assert resp.json()["email_verified"] is True


def test_change_password(client):
    session = _make_session()
    user = _mock_user(id_=1)
    user.password_hash = hash_password("current-pass")
    client.app.dependency_overrides[get_db] = lambda: session
    client.app.dependency_overrides[current_user] = lambda: user

    with patch("app.routes.auth.verify_password", return_value=True), patch(
        "app.routes.auth.hash_password", return_value="new-hash"
    ), patch("app.services.auth.revoke_all_user_tokens"):
        resp = client.post(
            "/api/auth/change-password",
            json={"current_password": "current-pass", "new_password": "NewSecurePass123"},
        )

    assert resp.status_code == 200, resp.text


def test_access_token_encode_decode():
    token = make_access_token(42)
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    assert payload["sub"] == "42"
    assert payload["type"] == "access"
