"""Admin failed-jobs (dead-letter) view.

Requires TEST_DATABASE_URL (real PostgreSQL). Run via `make test` or
`docker compose run --rm test`.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user, hash_password
from app.models import Channel, Company, Conversation, Contact, Message, User


def _create_user(db: Session, company: Company, email: str, role: str) -> User:
    u = User(
        company_id=company.id,
        name=email.split("@")[0],
        email=email,
        password_hash=hash_password("SecurePass123"),
        role=role,
        email_verified=True,
    )
    db.add(u)
    db.flush()
    return u


def _client_for_user(client: TestClient, user: User, db: Session) -> TestClient:
    def _get_db():
        yield db

    client.app.dependency_overrides[get_db] = _get_db
    client.app.dependency_overrides[current_user] = lambda: user
    return client


def _failed_message(db, company, channel, conversation, error_code="timeout", content="retry me"):
    m = Message(
        company_id=company.id,
        conversation_id=conversation.id,
        channel_id=channel.id,
        role="bot",
        direction="outbound",
        sender_type="ai",
        content=content,
        delivery_status="failed",
        error_code=error_code,
        error_message="provider timed out",
        created_at=datetime.now(timezone.utc),
    )
    db.add(m)
    return m


@pytest.fixture
def fx(db_session: Session):
    comp = Company(name="FJ Co")
    db_session.add(comp)
    db_session.flush()
    owner = _create_user(db_session, comp, "owner@fj.com", "owner")
    admin = _create_user(db_session, comp, "admin@fj.com", "admin")
    agent = _create_user(db_session, comp, "agent@fj.com", "agent")
    channel = Channel(
        company_id=comp.id, provider="dummy-for-tests", external_id="ch", display_name="Ch"
    )
    contact = Contact(company_id=comp.id, display_name="C", email="c@x.com")
    db_session.add_all([channel, contact])
    db_session.flush()
    conv = Conversation(
        company_id=comp.id,
        contact_id=contact.id,
        channel_id=channel.id,
        customer_name="Conv",
        status="open",
    )
    db_session.add(conv)
    db_session.commit()
    db_session.refresh(channel)
    db_session.refresh(contact)
    db_session.refresh(conv)
    return type(
        "Fx",
        (),
        {
            "db": db_session,
            "comp": comp,
            "owner": owner,
            "admin": admin,
            "agent": agent,
            "channel": channel,
            "contact": contact,
            "conv": conv,
        },
    )()


def test_failed_jobs_returns_failed_messages(client: TestClient, fx):
    _failed_message(fx.db, fx.comp, fx.channel, fx.conv, error_code="timeout")
    _failed_message(fx.db, fx.comp, fx.channel, fx.conv, error_code="token_invalid")
    # a queued (not failed) message must not appear
    ok = Message(
        company_id=fx.comp.id,
        conversation_id=fx.conv.id,
        channel_id=fx.channel.id,
        role="bot",
        direction="outbound",
        sender_type="ai",
        content="ok msg",
        delivery_status="queued",
    )
    fx.db.add(ok)
    fx.db.commit()

    _client_for_user(client, fx.admin, fx.db)
    resp = client.get("/api/team/failed-jobs")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) == 2
    codes = {j["error_code"] for j in body}
    assert codes == {"timeout", "token_invalid"}
    for j in body:
        assert j["content"] in ("retry me",)
        assert "created_at" in j


def test_failed_jobs_agent_forbidden(client: TestClient, fx):
    _client_for_user(client, fx.agent, fx.db)
    resp = client.get("/api/team/failed-jobs")
    assert resp.status_code == 403, resp.text


def test_failed_jobs_empty(client: TestClient, fx):
    _client_for_user(client, fx.owner, fx.db)
    resp = client.get("/api/team/failed-jobs")
    assert resp.status_code == 200, resp.text
    assert resp.json() == []
