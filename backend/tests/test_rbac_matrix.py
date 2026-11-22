"""RBAC matrix test: owner / admin / agent access per route.

Requires TEST_DATABASE_URL (real PostgreSQL). Run via `make test` or
`docker compose run --rm test`.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user, hash_password
from app.models import Channel, Company, Conversation, Contact, Document, User

# Role hierarchy: owner > admin > agent. A route listed with min_role "admin"
# returns 403 for agent; "owner" returns 403 for admin and agent; "agent" is
# reachable by every authenticated user.
ROUTES: list[tuple[str, str, str]] = [
    ("GET", "/api/auth/me", "agent"),
    ("GET", "/api/company", "agent"),
    ("PUT", "/api/company", "admin"),
    ("GET", "/api/contacts/", "agent"),
    ("POST", "/api/contacts/field-definitions", "admin"),
    ("POST", "/api/contacts/{contact_id}/tags", "admin"),
    ("POST", "/api/contacts/{contact_id}/notes", "admin"),
    ("GET", "/api/conversations/", "agent"),
    ("POST", "/api/conversations/{cid}/reply", "agent"),
    ("POST", "/api/conversations/{cid}/take", "agent"),
    ("POST", "/api/conversations/{cid}/close", "agent"),
    ("POST", "/api/conversations/{cid}/read", "agent"),
    ("GET", "/api/channels/", "agent"),
    ("POST", "/api/channels/{provider}/connect", "admin"),
    ("POST", "/api/channels/{channel_id}/disconnect", "admin"),
    ("POST", "/api/channels/{channel_id}/toggle", "admin"),
    ("GET", "/api/documents/", "agent"),
    ("POST", "/api/documents/upload", "agent"),
    ("GET", "/api/team/members", "admin"),
    ("POST", "/api/team/invite", "admin"),
    ("GET", "/api/team/failed-jobs", "admin"),
    ("GET", "/api/onboarding/state", "admin"),
    ("GET", "/api/stats/overview", "agent"),
    ("GET", "/api/billing", "agent"),
]

# Substitute a real A-owned resource id for parametrized paths.
PATH_IDS = {
    "{contact_id}": "contact_id",
    "{cid}": "conversation_id",
    "{channel_id}": "channel_id",
    "{provider}": "provider",
}


def _create_company(db: Session, name: str, plan: str = "free") -> Company:
    c = Company(name=name, plan=plan)
    db.add(c)
    db.flush()
    return c


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


class Fixtures:
    def __init__(self, db: Session):
        self.db = db
        self.comp = _create_company(db, "RBAC Co")
        self.owner = _create_user(db, self.comp, "owner@rbac.com", "owner")
        self.admin = _create_user(db, self.comp, "admin@rbac.com", "admin")
        self.agent = _create_user(db, self.comp, "agent@rbac.com", "agent")
        db.commit()

        self.contact = Contact(company_id=self.comp.id, display_name="C", email="c@x.com")
        self.channel = Channel(
            company_id=self.comp.id, provider="telegram", external_id="bot", display_name="Bot"
        )
        self.conv = Conversation(
            company_id=self.comp.id,
            contact_id=self.contact.id,
            channel_id=self.channel.id,
            customer_name="Conv",
            status="open",
        )
        self.document = Document(
            company_id=self.comp.id,
            name="doc.pdf",
            kind="pdf",
            size=1,
            status="ready",
            storage_key="k/doc.pdf",
        )
        db.add_all([self.contact, self.channel, self.conv, self.document])
        db.commit()
        for obj in (self.contact, self.channel, self.conv, self.document):
            db.refresh(obj)

    def url_for(self, path: str) -> str:
        for token, attr in PATH_IDS.items():
            if token in path:
                val = getattr(self, attr)
                if attr == "provider":
                    val = "unknown_provider"
                path = path.replace(token, str(val))
        return path


@pytest.fixture
def fx(db_session: Session) -> Fixtures:
    return Fixtures(db_session)


ROLE_ORDER = {"agent": 0, "admin": 1, "owner": 2}


@pytest.mark.parametrize("method,path,min_role", ROUTES)
class TestRBACMatrix:
    def test_route_enforces_min_role(
        self, method: str, path: str, min_role: str, client: TestClient, fx: Fixtures
    ):
        url = fx.url_for(path)
        for role in ("owner", "admin", "agent"):
            user = {"owner": fx.owner, "admin": fx.admin, "agent": fx.agent}[role]
            _client_for_user(client, user, fx.db)
            resp = getattr(client, method.lower())(url, json={})
            allowed = ROLE_ORDER[role] >= ROLE_ORDER[min_role]
            if allowed:
                # Authenticated and permitted: anything but a 403 (route may
                # still return 200/400/404/422 depending on state).
                assert resp.status_code != 403, (
                    f"{role} got 403 on {method} {url} though min_role={min_role}: {resp.text}"
                )
            else:
                # Below the required role: must be forbidden.
                assert resp.status_code == 403, (
                    f"{role} got {resp.status_code} on {method} {url} (min_role={min_role}): {resp.text}"
                )
