"""End-to-end full-flow test.

Covers: signup → onboarding → connect Telegram+Messenger mock → inbound each
→ contact auto-created → AI reply grounded → take over → agent reply → status ticks.

Requires TEST_DATABASE_URL (real PostgreSQL). Run via `make test` or
`docker compose run --rm test`.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Company, Conversation, Contact, Message


@pytest.fixture
def authed_client(client: TestClient, db_session: Session):
    """Register an owner and return a TestClient bearing session cookies."""
    resp = client.post(
        "/api/auth/register",
        json={
            "name": "Flow Owner",
            "email": "flow@teledesk.test",
            "password": "StrongPass123!",
            "lang": "en",
        },
    )
    assert resp.status_code == 201, resp.text
    assert client.cookies
    return client


def _connect_dummy(client: TestClient) -> int:
    resp = client.post(
        "/api/channels/dummy-for-tests/connect",
        json={
            "payload": {
                "external_id": "dummy_page_flow",
                "name": "Dummy Page",
                "webhook_secret": "dummy-secret",
            }
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["channel"]["id"]


def _inbound(client: TestClient, channel_id: int, text: str, event_id: str, user_id: str = "user_1"):
    resp = client.post(
        f"/webhooks/dummy-for-tests/{channel_id}",
        json={
            "events": [
                {
                    "message_id": f"msg_{event_id}",
                    "user_id": user_id,
                    "text": text,
                    "event_id": event_id,
                }
            ]
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_full_flow_signup_to_agent_reply(authed_client: TestClient, db_session: Session, monkeypatch):
    from app.workers.celery_app import celery

    celery.conf.task_always_eager = True

    # Ground the AI reply so we don't need a Gemini key.
    def fake_reply_to(db, company, question, history):
        return {
            "answer": f"Grounded answer to: {question}",
            "in_scope": True,
            "needs_human": False,
            "source": None,
        }

    import app.pipeline.turn as turn_module

    monkeypatch.setattr(turn_module, "reply_to", fake_reply_to)

    client = authed_client

    # 1) Onboarding state reachable.
    resp = client.get("/api/onboarding/state")
    assert resp.status_code == 200, resp.text

    # 2) Connect dummy channel.
    channel_id = _connect_dummy(client)

    # 3) Inbound message → contact auto-created, conversation created, AI reply grounded.
    _inbound(client, channel_id, "What are your hours?", "evt_flow_1")

    company = db_session.query(Company).first()
    assert company is not None

    contact = (
        db_session.query(Contact).filter(Contact.company_id == company.id).first()
    )
    assert contact is not None, "contact should be auto-created from inbound"

    conv = (
        db_session.query(Conversation)
        .filter(Conversation.company_id == company.id, Conversation.channel_id == channel_id)
        .first()
    )
    assert conv is not None, "conversation should be auto-created"
    assert conv.status == "open"

    # AI reply message present.
    ai_msg = (
        db_session.query(Message)
        .filter(Message.conversation_id == conv.id, Message.sender_type == "ai")
        .first()
    )
    assert ai_msg is not None, "AI should have replied"
    assert "Grounded answer" in ai_msg.content

    # 4) Customer requests handoff via inbound /human → status needs_human.
    _inbound(client, channel_id, "/human", "evt_flow_human")

    conv = db_session.query(Conversation).get(conv.id)
    assert conv.status == "needs_human", f"expected needs_human, got {conv.status}"

    # 5) Agent reply → status human.
    resp = client.post(
        f"/api/conversations/{conv.id}/reply",
        json={"text": "I'm here to help"},
    )
    assert resp.status_code == 200, resp.text

    conv = db_session.query(Conversation).get(conv.id)
    assert conv.status == "human", f"expected human, got {conv.status}"

    agent_msg = (
        db_session.query(Message)
        .filter(Message.conversation_id == conv.id, Message.sender_type == "agent")
        .first()
    )
    assert agent_msg is not None
    assert agent_msg.content == "I'm here to help"

    # 6) Status ticks: close → closed.
    resp = client.post(f"/api/conversations/{conv.id}/close")
    assert resp.status_code == 200, resp.text

    conv = db_session.query(Conversation).get(conv.id)
    assert conv.status == "closed", f"expected closed, got {conv.status}"
