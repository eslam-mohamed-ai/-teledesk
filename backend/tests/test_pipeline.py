"""Pipeline tests: ingestion idempotency, send retry vs no-retry, tenant isolation.

Require a live PostgreSQL test DB (TEST_DATABASE_URL). Skipped otherwise.
"""

from __future__ import annotations

import asyncio
from unittest import mock

import pytest
from sqlalchemy import select

from app.channels.types import (
    EventKind,
    InboundEvent,
    InboundMessage,
    PermanentSendError,
    SendResult,
    TokenInvalid,
    TransientSendError,
)
from app.models import (
    Channel,
    Company,
    Contact,
    ContactIdentity,
    Conversation,
    Message,
    ProcessedEvent,
)
from app.pipeline.ingest import ingest_inbound
from app.pipeline.outbound import send_outbound

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def dummy_adapter_cls():
    from tests.channels.dummy_adapter import DummyAdapter

    return DummyAdapter


@pytest.fixture
def company(db_session) -> Company:
    c = Company(
        name="Test Co",
        industry="retail",
        description="",
        welcome="أهلاً",
        tone="friendly",
        reply_language="ar",
        handoff_on_request=True,
        handoff_out_of_scope=True,
        handoff_keywords="شكوى",
        handoff_after_two=False,
        work_hours="",
        plan="free",
    )
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c


@pytest.fixture
def channel(db_session, company) -> Channel:
    ch = Channel(
        company_id=company.id,
        provider="dummy-for-tests",
        external_id="page_1",
        display_name="Test Page",
        credentials_encrypted="enc",
        webhook_secret="secret",
        status="connected",
        active=True,
        config={},
    )
    db_session.add(ch)
    db_session.commit()
    db_session.refresh(ch)
    return ch


# ---------------------------------------------------------------------------
# Ingestion idempotency
# ---------------------------------------------------------------------------


def _event(text: str) -> InboundEvent:
    return InboundEvent(
        kind=EventKind.message,
        message=InboundMessage(
            external_message_id="ext_msg_1",
            external_conversation_id="conv_1",
            external_user_id="user_1",
            text=text,
        ),
        provider_event_id="evt_msg_1",
        external_user_id="user_1",
        external_conversation_id="conv_1",
    )


def test_ingest_inbound_is_idempotent(db_session, company, channel):
    """Same external event processed twice → one contact, one conversation,
    one inbound message, one processed_event."""
    r1 = asyncio.run(ingest_inbound(db_session, channel, _event("مرحبا")))
    assert r1["status"] == "ok"
    contact_id = r1["contact_id"]
    conv_id = r1["conversation_id"]
    r1["message_id"]

    db_session.commit()

    r2 = asyncio.run(ingest_inbound(db_session, channel, _event("مرحبا")))
    assert r2["status"] == "duplicate"

    db_session.commit()

    assert (
        db_session.execute(select(Contact).where(Contact.company_id == company.id)).scalars().all().__len__()
        == 1
    )
    assert (
        db_session.execute(
            select(ContactIdentity).where(ContactIdentity.channel_id == channel.id)
        ).scalars().all().__len__()
        == 1
    )
    assert (
        db_session.execute(
            select(Conversation).where(Conversation.company_id == company.id)
        ).scalars().all().__len__()
        == 1
    )
    assert (
        db_session.execute(
            select(Message).where(Message.conversation_id == conv_id)
        ).scalars().all().__len__()
        == 1
    )
    assert (
        db_session.execute(
            select(ProcessedEvent).where(
                ProcessedEvent.provider == "dummy-for-tests",
                ProcessedEvent.event_id == "evt_msg_1",
            )
        ).scalars().all().__len__()
        == 1
    )

    identity = db_session.scalar(
        select(ContactIdentity).where(ContactIdentity.contact_id == contact_id)
    )
    assert identity is not None
    assert identity.external_user_id == "user_1"


# ---------------------------------------------------------------------------
# Send retry vs no-retry
# ---------------------------------------------------------------------------


def _make_conversation_and_message(db_session, company, channel, text: str) -> Message:
    contact = Contact(
        company_id=company.id,
        display_name="User",
        custom_fields={"provider": "dummy-for-tests"},
    )
    db_session.add(contact)
    db_session.flush()

    identity = ContactIdentity(
        contact_id=contact.id,
        channel_id=channel.id,
        external_user_id="user_1",
    )
    db_session.add(identity)
    db_session.flush()

    conv = Conversation(
        company_id=company.id,
        channel_id=channel.id,
        contact_id=contact.id,
        customer_name="User",
        status="open",
        unread_count=0,
    )
    db_session.add(conv)
    db_session.flush()

    m = Message(
        company_id=company.id,
        conversation_id=conv.id,
        channel_id=channel.id,
        role="bot",
        direction="outbound",
        sender_type="ai",
        content=text,
        delivery_status="queued",
    )
    db_session.add(m)
    db_session.commit()
    db_session.refresh(m)
    return m


class FlakyAdapter:
    provider = "dummy-for-tests"

    def __init__(self):
        self.calls = 0

    async def send_message(self, ch, external_user_id, message):
        self.calls += 1
        if self.calls < 3:
            raise TransientSendError("blip")
        return SendResult(ok=True, external_message_id="out_1")


def test_send_transient_retries_then_delivered(
    db_session, company, channel
):
    flaky = FlakyAdapter()
    msg = _make_conversation_and_message(db_session, company, channel, "hello")

    with mock.patch(
        "app.pipeline.outbound.get_adapter",
        lambda provider: flaky,
    ):
        result = send_outbound(msg.id)

    assert result["status"] == "delivered"
    assert flaky.calls == 3
    db_session.expire_all()
    m = db_session.get(Message, msg.id)
    assert m.delivery_status == "delivered"


def test_send_permanent_no_retry(db_session, company, channel):
    permanent = mock.Mock()
    permanent.send_message = mock.AsyncMock(side_effect=PermanentSendError("blocked"))
    msg = _make_conversation_and_message(db_session, company, channel, "bye")

    with mock.patch(
        "app.pipeline.outbound.get_adapter",
        lambda provider: permanent,
    ):
        result = send_outbound(msg.id)

    assert result["status"] == "failed"
    assert permanent.send_message.call_count == 1
    db_session.expire_all()
    m = db_session.get(Message, msg.id)
    assert m.delivery_status == "failed"
    assert m.error_code == "permanent"


def test_send_token_invalid_marks_channel_expired(db_session, company, channel):
    broken = mock.Mock()
    broken.send_message = mock.AsyncMock(side_effect=TokenInvalid("bad token"))
    msg = _make_conversation_and_message(db_session, company, channel, "bye")

    with mock.patch(
        "app.pipeline.outbound.get_adapter",
        lambda provider: broken,
    ):
        result = send_outbound(msg.id)

    assert result["status"] == "failed"
    db_session.expire_all()
    ch = db_session.get(Channel, channel.id)
    assert ch.status == "token_expired"


# ---------------------------------------------------------------------------
# Tenant isolation
# ---------------------------------------------------------------------------


def test_conversation_list_is_tenant_isolated(db_session):
    c1 = Company(name="Co 1", industry="r", plan="free")
    c2 = Company(name="Co 2", industry="r", plan="free")
    db_session.add_all([c1, c2])
    db_session.commit()
    db_session.refresh(c1)
    db_session.refresh(c2)

    ch1 = Channel(
        company_id=c1.id,
        provider="dummy-for-tests",
        external_id="p1",
        status="connected",
        active=True,
    )
    ch2 = Channel(
        company_id=c2.id,
        provider="dummy-for-tests",
        external_id="p2",
        status="connected",
        active=True,
    )
    db_session.add_all([ch1, ch2])
    db_session.commit()
    db_session.refresh(ch1)
    db_session.refresh(ch2)

    conv1 = Conversation(
        company_id=c1.id, channel_id=ch1.id, customer_name="U1", status="open", unread_count=1
    )
    conv2 = Conversation(
        company_id=c2.id, channel_id=ch2.id, customer_name="U2", status="open", unread_count=1
    )
    db_session.add_all([conv1, conv2])
    db_session.commit()

    rows_c1 = (
        db_session.execute(select(Conversation).where(Conversation.company_id == c1.id))
        .scalars()
        .all()
    )
    rows_c2 = (
        db_session.execute(select(Conversation).where(Conversation.company_id == c2.id))
        .scalars()
        .all()
    )
    assert len(rows_c1) == 1
    assert len(rows_c2) == 1
    assert rows_c1[0].id == conv1.id
    assert rows_c2[0].id == conv2.id
    assert rows_c1[0].company_id != rows_c2[0].company_id
