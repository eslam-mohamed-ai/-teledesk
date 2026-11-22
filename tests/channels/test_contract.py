"""Reusable channel-adapter contract suite.

Runs against every registered adapter (dummy-for-tests and telegram) to prove
that adding a channel only needs one adapter file + one registry line.
"""

from typing import Any

from typing import Any

import pytest

# Import telegram adapter to trigger registry registration.
from app.channels.telegram import TelegramAdapter  # noqa: F401

from app.channels.registry import get
from app.channels.types import (
    BlockedByUser,
    EventKind,
    InboundEvent,
    InboundMessage,
    OutboundMessage,
    PermanentSendError,
    RateLimited,
    SendResult,
    TokenInvalid,
    TransientSendError,
    WindowExpired,
)

ADAPTERS = ["dummy-for-tests", "telegram"]

TELEGRAM_UPDATE = {
    "update_id": 123456789,
    "message": {
        "message_id": 42,
        "from": {"id": 7, "first_name": "Alaa", "username": "alaa"},
        "chat": {"id": 9012, "first_name": "Alaa", "type": "private"},
        "date": 1600000000,
        "text": "أهلاً",
    },
}


def _check_capabilities(adapter) -> None:
    caps = adapter.capabilities
    assert isinstance(caps.supports_typing, bool)
    assert isinstance(caps.supports_attachments, bool)
    assert isinstance(caps.supports_read_receipts, bool)
    assert caps.max_text_length is None or isinstance(caps.max_text_length, int)


def _check_send_result(result: SendResult) -> None:
    assert isinstance(result.ok, bool)
    assert result.external_message_id is None or isinstance(result.external_message_id, str)


def _check_error_types() -> None:
    for exc in (RateLimited, TokenInvalid, BlockedByUser, WindowExpired, PermanentSendError, TransientSendError):
        assert issubclass(exc, Exception)
    r = RateLimited(retry_after=10, message="slow down")
    assert r.retry_after == 10


def _fake_me() -> dict[str, Any]:
    return {"id": 123, "username": "fake_bot", "first_name": "Fake Bot"}


@pytest.mark.parametrize("provider", ADAPTERS)
def test_adapter_contract(provider, monkeypatch):
    adapter_cls = get(provider)
    assert adapter_cls is not None, f"adapter {provider} not registered"

    adapter = adapter_cls()
    assert adapter.provider == provider
    _check_capabilities(adapter)
    _check_error_types()

    # Telegram connect() calls get_me over HTTP; fake it for the contract run.
    if provider == "telegram":
        from app.channels import telegram as tg_module

        monkeypatch.setattr(tg_module, "_post", lambda token, method, payload=None: _fake_me())

    # connect must return channel-persistable fields without raw tokens.
    fields = None
    import asyncio

    fields = asyncio.run(
        adapter.connect(
            1,
            {
                "token": "fake_token",
                "external_id": "ext_1",
                "name": "Test Page",
                "webhook_secret": "s3cr3t",
            },
        )
    )
    assert fields["provider"] == provider
    assert fields["external_id"]  # dummy: from payload; telegram: bot username from get_me
    assert fields["display_name"]  # dummy: payload name; telegram: get_me first_name
    assert fields["credentials_encrypted"]
    assert fields["webhook_secret"] == "s3cr3t"

    # disconnect must not raise.
    asyncio.run(adapter.disconnect(fields))

    # verify_webhook_request signature.
    assert callable(adapter.verify_webhook_request)

    # parse_webhook returns list of InboundEvent.
    events = adapter.parse_webhook({})
    assert isinstance(events, list)

    # send_message returns SendResult.
    result = asyncio.run(
        adapter.send_message(fields, "9012", OutboundMessage(text="hello"))
    )
    _check_send_result(result)

    # send_typing / fetch_profile / health_check.
    import inspect

    assert inspect.iscoroutinefunction(adapter.send_typing)
    assert inspect.iscoroutinefunction(adapter.fetch_profile)
    assert inspect.iscoroutinefunction(adapter.health_check)
    profile = asyncio.run(adapter.fetch_profile(fields, "user_1"))
    assert profile.external_user_id == "user_1"
    health = asyncio.run(adapter.health_check(fields))
    assert health.value in ("ok", "degraded", "down")


def test_telegram_parse_webhook_normalizes_recorded_update():
    from app.channels.telegram import TelegramAdapter

    adapter = TelegramAdapter()
    events = adapter.parse_webhook(TELEGRAM_UPDATE)
    assert len(events) == 1
    event = events[0]
    assert isinstance(event, InboundEvent)
    assert event.kind == EventKind.message
    assert event.provider_event_id == "123456789"
    assert event.external_user_id == "9012"
    assert event.message is not None
    assert event.message.external_user_id == "9012"
    assert event.message.text == "أهلاً"
    assert event.message.external_message_id == "42"


def test_error_types_are_distinct():
    _check_error_types()
    assert RateLimited is not TokenInvalid
    assert BlockedByUser is not PermanentSendError
