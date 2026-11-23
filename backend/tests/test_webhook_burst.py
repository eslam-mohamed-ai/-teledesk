"""Webhook burst test: endpoints respond <1s under load; payload size limits enforced.

Requires TEST_DATABASE_URL and REDIS_URL (real PostgreSQL + Redis). Run via
`make test` or `docker compose run --rm test`.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
from fastapi.testclient import TestClient

from app.channels.base import ChannelAdapter
from app.channels.registry import get, register
from app.channels.types import (
    ChannelCapabilities,
    ChannelHealth,
    ContactProfile,
    EventKind,
    InboundEvent,
    InboundMessage,
    OutboundMessage,
    SendResult,
)
from app.models import Channel, Company


class DummyAdapter(ChannelAdapter):
    """Test-only adapter used by the webhook contract tests."""

    provider = "dummy-for-tests"

    @property
    def capabilities(self) -> ChannelCapabilities:
        return ChannelCapabilities()

    async def connect(self, company_id, payload):
        return {"provider": self.provider, "external_id": "dummy", "display_name": "Dummy"}

    async def disconnect(self, channel):
        return None

    def verify_webhook_request(self, request, channel_secret):
        return True

    def parse_webhook(self, payload):
        return [
            InboundEvent(
                kind=EventKind.message,
                provider_event_id=event.get("event_id"),
                message=InboundMessage(
                    external_message_id=event.get("message_id"),
                    external_conversation_id=event.get("user_id"),
                    external_user_id=event["user_id"],
                    text=event.get("text"),
                ),
            )
            for event in payload.get("events", [])
        ]

    async def send_message(self, channel, external_user_id, message: OutboundMessage):
        return SendResult(ok=True, external_message_id="dummy-message")

    async def fetch_profile(self, channel, external_user_id):
        return ContactProfile(external_user_id=external_user_id)

    async def health_check(self, channel):
        return ChannelHealth.ok


register("dummy-for-tests", DummyAdapter)


@pytest.fixture
def channel(db_session):
    company = Company(name="Burst Co")
    db_session.add(company)
    db_session.flush()
    channel = Channel(
        company_id=company.id,
        provider="dummy-for-tests",
        external_id="burst_channel",
        display_name="Burst",
        webhook_secret="burst-secret",
        active=True,
    )
    db_session.add(channel)
    db_session.commit()
    db_session.refresh(channel)
    return channel


def _post_webhook(client: TestClient, channel_id: int, payload: dict):
    return client.post(
        f"/webhooks/dummy-for-tests/{channel_id}",
        json=payload,
    )


def test_webhook_responds_under_one_second_under_load(client, channel, db_session):
    payload = {
        "events": [
            {
                "message_id": "m1",
                "user_id": "user_1",
                "text": "hello",
                "event_id": "evt_1",
            }
        ]
    }

    def one_request(_):
        start = time.perf_counter()
        resp = _post_webhook(client, channel.id, payload)
        elapsed = time.perf_counter() - start
        return resp.status_code, elapsed

    concurrency = 20
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futures = [pool.submit(one_request, i) for i in range(concurrency)]
        results = [f.result() for f in as_completed(futures)]

    for status, elapsed in results:
        assert status == 200, status
        assert elapsed < 1.0, f"webhook took {elapsed:.3f}s"


def test_webhook_payload_size_limit(client, channel):
    oversize = {"events": [{"text": "x" * (3 * 1024 * 1024), "event_id": "big"}]}
    resp = _post_webhook(client, channel.id, oversize)
    assert resp.status_code == 413, resp.text


def test_webhook_invalid_json_rejected(client, channel):
    resp = client.post(
        f"/webhooks/dummy-for-tests/{channel.id}",
        content="not json",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 400, resp.text


def test_dummy_adapter_registered():
    assert get("dummy-for-tests") is not None


def test_dummy_adapter_parses_message():
    from app.channels.types import EventKind

    adapter = get("dummy-for-tests")()
    events = adapter.parse_webhook(
        {"events": [{"message_id": "m1", "user_id": "u1", "text": "hi", "event_id": "e1"}]}
    )
    assert len(events) == 1
    assert events[0].kind == EventKind.message
    assert events[0].message.external_user_id == "u1"
