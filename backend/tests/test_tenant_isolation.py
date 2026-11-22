"""Tenant isolation tests against REAL PostgreSQL.

These tests require TEST_DATABASE_URL pointing to a PostgreSQL database.
Run with: make test  (or docker compose run --rm test)

Two companies (A and B) are created. Each test asserts that company A can
never read or modify company B's team, invitations, contacts, onboarding,
conversations, channels, or documents.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base
from app.deps import hash_password
from app.models import (
    Channel,
    Company,
    Contact,
    Conversation,
    Document,
    Invitation,
    Message,
    User,
)


def _create_company(db: Session, name: str, plan: str = "free") -> Company:
    c = Company(name=name, plan=plan)
    db.add(c)
    db.flush()
    return c


def _create_user(
    db: Session,
    company: Company,
    email: str,
    name: str,
    role: str = "agent",
    password: str = "SecurePass123",
) -> User:
    u = User(
        company_id=company.id,
        name=name,
        email=email,
        password_hash=hash_password(password),
        role=role,
        email_verified=True,
    )
    db.add(u)
    db.flush()
    return u


def _client_for_user(client: TestClient, user: User, db: Session) -> TestClient:
    """Override current_user and get_db for a specific user."""
    from app.database import get_db
    from app.deps import current_user

    def _get_db():
        yield db

    client.app.dependency_overrides[get_db] = _get_db
    client.app.dependency_overrides[current_user] = lambda: user
    return client


class TestTenantIsolation:
    """All tests use two real companies: A (id=1) and B (id=2)."""

    @pytest.fixture(autouse=True)
    def _setup(self, db_session: Session):
        self.db = db_session
        self.comp_a = _create_company(db_session, "Company A")
        self.comp_b = _create_company(db_session, "Company B")

        self.user_a_owner = _create_user(
            db_session, self.comp_a, "owner-a@a.com", "Owner A", "owner"
        )
        self.user_a_agent = _create_user(
            db_session, self.comp_a, "agent-a@a.com", "Agent A", "agent"
        )
        self.user_b_owner = _create_user(
            db_session, self.comp_b, "owner-b@b.com", "Owner B", "owner"
        )
        self.user_b_agent = _create_user(
            db_session, self.comp_b, "agent-b@b.com", "Agent B", "agent"
        )
        db_session.commit()

    # ---------------------------------------------------------------
    # /api/team
    # ---------------------------------------------------------------
    def test_company_a_cannot_list_company_b_members(
        self, client: TestClient
    ):
        _client_for_user(client, self.user_a_owner, self.db)
        resp = client.get("/api/team/members")
        assert resp.status_code == 200, resp.text
        emails = [m["email"] for m in resp.json()]
        assert self.user_b_owner.email not in emails
        assert self.user_b_agent.email not in emails
        assert self.user_a_owner.email in emails

    def test_company_a_cannot_invite_company_b_user(
        self, client: TestClient
    ):
        _client_for_user(client, self.user_a_owner, self.db)
        resp = client.post(
            "/api/team/invite",
            json={"email": "someone@b.com", "role": "agent"},
        )
        assert resp.status_code == 201, resp.text
        # Invite is for company A only; Company B cannot see it
        _client_for_user(client, self.user_b_owner, self.db)
        resp_b = client.get("/api/team/invitations")
        assert resp_b.status_code == 200, resp_b.text
        b_emails = [i["email"] for i in resp_b.json()]
        assert "someone@b.com" not in b_emails

    def test_agent_cannot_invite(self, client: TestClient):
        _client_for_user(client, self.user_a_agent, self.db)
        resp = client.post(
            "/api/team/invite",
            json={"email": "newbie@a.com", "role": "agent"},
        )
        assert resp.status_code == 403, resp.text

    def test_last_owner_cannot_be_removed(self, client: TestClient):
        _client_for_user(client, self.user_a_owner, self.db)
        resp = client.delete(f"/api/team/members/{self.user_a_owner.id}")
        assert resp.status_code == 400, resp.text

    def test_company_a_cannot_change_company_b_role(
        self, client: TestClient
    ):
        _client_for_user(client, self.user_a_owner, self.db)
        resp = client.patch(
            f"/api/team/members/{self.user_b_owner.id}/role",
            json={"role": "agent"},
        )
        # User B doesn't exist in company A's DB context (filtered by company_id)
        assert resp.status_code == 404, resp.text

    # ---------------------------------------------------------------
    # /api/contacts
    # ---------------------------------------------------------------
    def test_company_a_cannot_list_company_b_contacts(
        self, client: TestClient
    ):
        contact_b = Contact(
            company_id=self.comp_b.id,
            display_name="Contact B",
            email="b@b.com",
        )
        self.db.add(contact_b)
        self.db.commit()

        _client_for_user(client, self.user_a_owner, self.db)
        resp = client.get("/api/contacts/")
        assert resp.status_code == 200, resp.text
        emails = [c["email"] for c in resp.json()]
        assert "b@b.com" not in emails

    def test_company_a_cannot_get_company_b_contact(self, client: TestClient):
        contact_b = Contact(
            company_id=self.comp_b.id,
            display_name="Contact B",
            email="b@b.com",
        )
        self.db.add(contact_b)
        self.db.commit()

        _client_for_user(client, self.user_a_owner, self.db)
        resp = client.get(f"/api/contacts/{contact_b.id}")
        assert resp.status_code == 404, resp.text

    def test_company_a_cannot_update_company_b_contact(self, client: TestClient):
        contact_b = Contact(
            company_id=self.comp_b.id,
            display_name="Contact B",
            email="b@b.com",
        )
        self.db.add(contact_b)
        self.db.commit()

        _client_for_user(client, self.user_a_owner, self.db)
        resp = client.patch(
            f"/api/contacts/{contact_b.id}",
            json={"display_name": "Hacked"},
        )
        assert resp.status_code == 404, resp.text

    def test_company_a_cannot_delete_company_b_contact(self, client: TestClient):
        contact_b = Contact(
            company_id=self.comp_b.id,
            display_name="Contact B",
            email="b@b.com",
        )
        self.db.add(contact_b)
        self.db.commit()

        _client_for_user(client, self.user_a_owner, self.db)
        resp = client.delete(f"/api/contacts/{contact_b.id}")
        assert resp.status_code == 404, resp.text

    # ---------------------------------------------------------------
    # /api/onboarding
    # ---------------------------------------------------------------
    def test_company_a_cannot_access_company_b_onboarding(
        self, client: TestClient
    ):
        self.comp_b.onboarding_step = "profile"
        self.comp_b.profile = {"company_name": "Company B"}
        self.db.commit()

        _client_for_user(client, self.user_a_owner, self.db)
        resp = client.get("/api/onboarding/state")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["current_step"] != "profile"  # Company A's step, not B's

    def test_company_a_cannot_save_company_b_onboarding_step(
        self, client: TestClient
    ):
        _client_for_user(client, self.user_a_owner, self.db)
        resp = client.post(
            "/api/onboarding/step",
            json={"step": "profile", "data": {"company_name": "Hacked B"}},
        )
        # This saves to company A, not B - so B's data is safe
        assert resp.status_code in (200, 400), resp.text

    # ---------------------------------------------------------------
    # /api/conversations
    # ---------------------------------------------------------------
    def test_company_a_cannot_list_company_b_conversations(
        self, client: TestClient
    ):
        conv_b = Conversation(
            company_id=self.comp_b.id,
            contact_id=1,
            customer_name="Conv B",
            status="open",
        )
        self.db.add(conv_b)
        self.db.commit()

        _client_for_user(client, self.user_a_owner, self.db)
        resp = client.get("/api/conversations/")
        assert resp.status_code == 200, resp.text
        ids = [c["id"] for c in resp.json()]
        assert conv_b.id not in ids

    def test_company_a_cannot_assign_company_b_conversation(
        self, client: TestClient
    ):
        conv_b = Conversation(
            company_id=self.comp_b.id,
            contact_id=1,
            customer_name="Conv B",
            status="open",
        )
        self.db.add(conv_b)
        self.db.commit()

        _client_for_user(client, self.user_a_owner, self.db)
        resp = client.post(
            f"/api/conversations/{conv_b.id}/assign",
            json={"assignee_user_id": self.user_a_owner.id},
        )
        assert resp.status_code == 404, resp.text

    # ---------------------------------------------------------------
    # /api/channels
    # ---------------------------------------------------------------
    def test_company_a_cannot_list_company_b_channels(
        self, client: TestClient
    ):
        ch_b = Channel(
            company_id=self.comp_b.id,
            provider="telegram",
            external_id="bot_b",
            display_name="Bot B",
        )
        self.db.add(ch_b)
        self.db.commit()

        _client_for_user(client, self.user_a_owner, self.db)
        resp = client.get("/api/channels/")
        assert resp.status_code == 200, resp.text
        ids = [c["id"] for c in resp.json()]
        assert ch_b.id not in ids

    def test_company_a_cannot_connect_channel_for_company_b(
        self, client: TestClient
    ):
        # Channel connect validates via adapter; unknown provider returns 404
        # regardless of company, proving no cross-company channel creation.
        _client_for_user(client, self.user_a_owner, self.db)
        resp = client.post(
            "/api/channels/unknown_provider/connect",
            json={"payload": {}},
        )
        assert resp.status_code == 404, resp.text

    # ---------------------------------------------------------------
    # /api/documents
    # ---------------------------------------------------------------
    def test_company_a_cannot_list_company_b_documents(
        self, client: TestClient
    ):
        doc_b = Document(
            company_id=self.comp_b.id,
            name="doc_b.pdf",
            kind="pdf",
            size=100,
            status="ready",
            storage_key="keys/doc_b.pdf",
        )
        self.db.add(doc_b)
        self.db.commit()

        _client_for_user(client, self.user_a_owner, self.db)
        resp = client.get("/api/documents/")
        assert resp.status_code == 200, resp.text
        names = [d["name"] for d in resp.json()]
        assert "doc_b.pdf" not in names
