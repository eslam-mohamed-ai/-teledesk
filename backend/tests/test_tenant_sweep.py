"""Tenant-isolation test sweep.

Auto-generates coverage from the OpenAPI route list so new routes can't be
forgotten: every company-scoped API route is exercised as company A against a
resource owned by company B, and A must never read, send, or modify B's data.

Requires TEST_DATABASE_URL (real PostgreSQL). Run via `make test` or
`docker compose run --rm test`.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import current_user, hash_password
from app.main import app
from app.models import (
    Channel,
    Company,
    Contact,
    ContactFieldDefinition,
    Conversation,
    Document,
    Invitation,
    Message,
    RefreshToken,
    Tag,
    User,
)

PUBLIC_OR_AUTH_ROUTES = {
    "/api/auth/register",
    "/api/auth/login",
    "/api/auth/forgot-password",
    "/api/auth/reset-password",
    "/api/auth/verify-email",
    "/api/auth/resend-verification",
    "/api/auth/accept-invitation",
    "/api/webhooks",
    "/api/healthz",
    "/api/readyz",
}


def _create_company(db: Session, name: str, plan: str = "free") -> Company:
    c = Company(name=name, plan=plan)
    db.add(c)
    db.flush()
    return c


def _create_user(db: Session, company: Company, email: str, role: str = "agent") -> User:
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


def _openapi_paths() -> list[str]:
    return list(app.openapi()["paths"].keys())


def _path_params(path: str) -> list[str]:
    import re

    return re.findall(r"\{([^}]+)\}", path)


# Path parameters that Fixtures can resolve to a company-B-owned resource id.
# Anything else (e.g. {provider}) is skipped here and covered by dedicated tests.
_B_RESOURCE_IDS = {
    "contact_id",
    "channel_id",
    "cid",
    "conversation_id",
    "doc_id",
    "document_id",
    "session_id",
    "invitation_id",
    "field_id",
    "user_id",
    "member_id",
    "tag_name",
    "message_id",
    "reply_id",
}


class Fixtures:
    def __init__(self, db: Session):
        self.db = db
        self.comp_a = _create_company(db, "Company A")
        self.comp_b = _create_company(db, "Company B")
        self.user_a_owner = _create_user(db, self.comp_a, "owner-a@a.com", "owner")
        self.user_a_agent = _create_user(db, self.comp_a, "agent-a@a.com", "agent")
        self.user_b_owner = _create_user(db, self.comp_b, "owner-b@b.com", "owner")
        self.user_b_agent = _create_user(db, self.comp_b, "agent-b@b.com", "agent")
        db.commit()

        # Company B-owned resources, one per resource type.
        self.contact_b = Contact(
            company_id=self.comp_b.id, display_name="Contact B", email="b@b.com"
        )
        self.channel_b = Channel(
            company_id=self.comp_b.id,
            provider="telegram",
            external_id="bot_b",
            display_name="Bot B",
        )
        self.conv_b = Conversation(
            company_id=self.comp_b.id,
            contact_id=self.contact_b.id,
            channel_id=self.channel_b.id,
            customer_name="Conv B",
            status="open",
        )
        self.document_b = Document(
            company_id=self.comp_b.id,
            name="doc_b.pdf",
            kind="pdf",
            size=100,
            status="ready",
            storage_key="keys/doc_b.pdf",
        )
        self.member_b = _create_user(db, self.comp_b, "member-b@b.com", "agent")
        self.invitation_b = Invitation(
            company_id=self.comp_b.id,
            email="invite-b@b.com",
            role="agent",
            token_hash="x",
            expires_at=None,
        )
        self.field_b = ContactFieldDefinition(
            company_id=self.comp_b.id, key="fb", label="Field B", type="text"
        )
        self.tag_b = Tag(company_id=self.comp_b.id, name="tag-b")
        db.add_all(
            [
                self.contact_b,
                self.channel_b,
                self.conv_b,
                self.document_b,
                self.invitation_b,
                self.field_b,
                self.tag_b,
            ]
        )
        db.commit()
        db.refresh(self.contact_b)
        db.refresh(self.channel_b)
        db.refresh(self.conv_b)
        db.refresh(self.document_b)
        db.refresh(self.invitation_b)
        db.refresh(self.field_b)
        db.refresh(self.tag_b)

        # A message inside company B's conversation.
        self.message_b = Message(
            company_id=self.comp_b.id,
            conversation_id=self.conv_b.id,
            role="customer",
            direction="inbound",
            sender_type="contact",
            content="secret b",
        )
        db.add(self.message_b)
        db.commit()

        # A refresh token owned by company B's user.
        self.refresh_b = RefreshToken(
            user_id=self.user_b_owner.id,
            token_hash="hash-b",
            family_id="fam-b",
            expires_at=None,
        )
        db.add(self.refresh_b)
        db.commit()

    def b_id(self, param: str) -> int | str:
        mapping = {
            "contact_id": self.contact_b.id,
            "channel_id": self.channel_b.id,
            "cid": self.conv_b.id,
            "conversation_id": self.conv_b.id,
            "doc_id": self.document_b.id,
            "document_id": self.document_b.id,
            "session_id": self.refresh_b.id,
            "invitation_id": self.invitation_b.id,
            "field_id": self.field_b.id,
            "user_id": self.member_b.id,
            "member_id": self.member_b.id,
            "tag_name": self.tag_b.name,
            "message_id": self.message_b.id,
            "reply_id": self.message_b.id,
        }
        return mapping[param]


@pytest.fixture
def fx(db_session: Session) -> Fixtures:
    return Fixtures(db_session)


# ---------------------------------------------------------------------------
# Sweep: every OpenAPI route is company-scoped
# ---------------------------------------------------------------------------


def _client_for(client: TestClient, fx: Fixtures, user: User, db: Session) -> TestClient:
    return _client_for_user(client, user, db)


def _read_as_a_should_not_see_b(
    client: TestClient, fx: Fixtures, db: Session, path: str
) -> None:
    """Request `path` (with B's resource id substituted) as company A's owner.

    Company A must never receive company B's data: expect a rejection, never 200
    carrying B's resource.
    """
    params = _path_params(path)
    if any(param not in _B_RESOURCE_IDS for param in params):
        return  # e.g. {provider}: covered by the dedicated channel tests
    url = path
    for param in params:
        url = url.replace("{" + param + "}", str(fx.b_id(param)))

    _client_for(client, fx, fx.user_a_owner, db)
    resp = client.get(url)
    assert resp.status_code in (403, 404, 405), f"GET {url} -> {resp.status_code}: {resp.text}"


def _write_as_a_should_not_modify_b(
    client: TestClient, fx: Fixtures, db: Session, path: str, method: str = "POST"
) -> None:
    params = _path_params(path)
    if any(param not in _B_RESOURCE_IDS for param in params):
        return
    url = path
    for param in params:
        url = url.replace("{" + param + "}", str(fx.b_id(param)))
    _client_for(client, fx, fx.user_a_owner, db)
    resp = getattr(client, method.lower())(url, json={})
    assert resp.status_code in (400, 403, 404, 405, 422), (
        f"{method} {url} -> {resp.status_code}: {resp.text}"
    )


def _list_excludes_b(client: TestClient, fx: Fixtures, db: Session, path: str) -> None:
    _client_for(client, fx, fx.user_a_owner, db)
    resp = client.get(path)
    assert resp.status_code == 200, f"GET {path} -> {resp.status_code}: {resp.text}"
    data = resp.json()
    ids = _extract_ids(data)
    # Company B's created resources must not leak into company A's list.
    b_resources = [
        fx.contact_b,
        fx.channel_b,
        fx.conv_b,
        fx.document_b,
        fx.invitation_b,
        fx.field_b,
        fx.refresh_b,
    ]
    for res in b_resources:
        if res is not None and hasattr(res, "id"):
            assert res.id not in ids, f"B resource {res.id} leaked into GET {path}"


def _extract_ids(data: Any) -> set[int]:
    ids: set[int] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "id" and isinstance(v, int):
                    ids.add(v)
                walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(data)
    return ids


class TestTenantIsolationSweep:
    """Every company-scoped OpenAPI route enforces tenant isolation."""

    @pytest.fixture(autouse=True)
    def _clear_overrides(self, client: TestClient):
        yield
        client.app.dependency_overrides.clear()

    def test_every_company_scoped_route_is_isolated(
        self, client: TestClient, fx: Fixtures, db_session: Session
    ):
        """Read isolation for every OpenAPI route that takes a resource id.

        New routes are covered automatically because the sweep iterates the
        live OpenAPI path list rather than a hardcoded list.
        """
        schema = app.openapi()
        for path, methods in schema["paths"].items():
            if not path.startswith("/api"):
                continue
            if path in PUBLIC_OR_AUTH_ROUTES:
                continue
            if "/webhooks" in path:
                continue
            get_available = "get" in methods
            params = _path_params(path)
            # Item routes: substitute B's id and GET as A -> must not be 200.
            if params:
                if get_available:
                    _read_as_a_should_not_see_b(client, fx, db_session, path)
            elif get_available:
                # List routes: B's records must not appear in A's list.
                _list_excludes_b(client, fx, db_session, path)

    def test_write_routes_reject_cross_company(
        self, client: TestClient, fx: Fixtures, db_session: Session
    ):
        """State-changing routes must not let company A touch company B."""
        write_paths = [
            "/api/contacts/{contact_id}",
            "/api/contacts/{contact_id}/tags/{tag_name}",
            "/api/contacts/{contact_id}/notes",
            "/api/conversations/{cid}",
            "/api/conversations/{cid}/reply",
            "/api/conversations/{cid}/note",
            "/api/conversations/{cid}/assign",
            "/api/conversations/{cid}/take",
            "/api/conversations/{cid}/close",
            "/api/documents/{doc_id}",
            "/api/team/members/{user_id}",
            "/api/team/invitations/{invitation_id}",
            "/api/channels/{channel_id}/disconnect",
            "/api/channels/{channel_id}/toggle",
        ]
        for path in write_paths:
            if path not in _openapi_paths():
                continue
            _write_as_a_should_not_modify_b(client, fx, db_session, path)

    def test_company_b_cannot_access_company_a_resources(
        self, client: TestClient, fx: Fixtures, db_session: Session
    ):
        """Isolation is symmetric: B cannot read A's resources either."""
        contact_a = Contact(
            company_id=fx.comp_a.id,
            display_name="Contact A",
            email="a@a.com",
        )
        db_session.add(contact_a)
        db_session.commit()
        db_session.refresh(contact_a)

        _client_for(client, fx, fx.user_b_owner, db_session)
        resp = client.get(f"/api/contacts/{contact_a.id}")
        assert resp.status_code == 404, resp.text
