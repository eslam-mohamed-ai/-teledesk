"""Telegram adapter tests with recorded fixtures (no real Telegram network)."""

from __future__ import annotations

import asyncio

import httpx
import pytest

from app.channels.telegram import (
    BlockedByUser,
    PermanentSendError,
    RateLimited,
    TelegramAdapter,
    TransientSendError,
)


class FakeResponse:
    def __init__(self, json_data, status_code=200):
        self._json = json_data
        self.status_code = status_code

    def json(self):
        return self._json


def fake_ok(result):
    return FakeResponse({"ok": True, "result": result})


def fake_error(description, status_code=400):
    return FakeResponse({"ok": False, "description": description}, status_code=status_code)


def _patch_post(monkeypatch, response):
    monkeypatch.setattr("httpx.post", lambda url, **kwargs: response)


def _make_channel():
    return type("C", (), {"credentials_encrypted": "enc", "external_id": "bot"})()


def _make_msg(text="hi"):
    return type("M", (), {"text": text})()


def test_send_message_blocked_by_user(monkeypatch):
    _patch_post(monkeypatch, fake_error("bot was blocked by the user"))
    monkeypatch.setattr("app.channels.telegram.decrypt", lambda e: "token")
    adapter = TelegramAdapter()
    with pytest.raises(BlockedByUser):
        asyncio.run(adapter.send_message(_make_channel(), "123", _make_msg()))


def test_send_message_rate_limited(monkeypatch):
    _patch_post(monkeypatch, fake_error("Too Many Requests: retry after 3"))
    monkeypatch.setattr("app.channels.telegram.decrypt", lambda e: "token")
    adapter = TelegramAdapter()
    with pytest.raises(RateLimited) as exc:
        asyncio.run(adapter.send_message(_make_channel(), "123", _make_msg()))
    assert exc.value.retry_after == 3


def test_send_message_chat_not_found(monkeypatch):
    _patch_post(monkeypatch, fake_error("chat not found"))
    monkeypatch.setattr("app.channels.telegram.decrypt", lambda e: "token")
    adapter = TelegramAdapter()
    with pytest.raises(BlockedByUser):
        asyncio.run(adapter.send_message(_make_channel(), "123", _make_msg()))


def test_send_message_permanent(monkeypatch):
    _patch_post(monkeypatch, fake_error("invalid token", 401))
    monkeypatch.setattr("app.channels.telegram.decrypt", lambda e: "token")
    adapter = TelegramAdapter()
    with pytest.raises(PermanentSendError):
        asyncio.run(adapter.send_message(_make_channel(), "123", _make_msg()))


def test_send_message_transient(monkeypatch):
    _patch_post(monkeypatch, FakeResponse({"ok": False, "description": "internal error"}, 500))
    monkeypatch.setattr("app.channels.telegram.decrypt", lambda e: "token")
    adapter = TelegramAdapter()
    with pytest.raises(TransientSendError):
        asyncio.run(adapter.send_message(_make_channel(), "123", _make_msg()))


def test_send_message_success(monkeypatch):
    _patch_post(monkeypatch, fake_ok({"message_id": 100}))
    monkeypatch.setattr("app.channels.telegram.decrypt", lambda e: "token")
    adapter = TelegramAdapter()
    result = asyncio.run(adapter.send_message(_make_channel(), "123", _make_msg("hello")))
    assert result.ok is True
    assert result.external_message_id == "100"


def test_send_message_no_text_returns_ok(monkeypatch):
    _patch_post(monkeypatch, fake_ok({}))
    monkeypatch.setattr("app.channels.telegram.decrypt", lambda e: "token")
    adapter = TelegramAdapter()
    result = asyncio.run(adapter.send_message(_make_channel(), "123", _make_msg(None)))
    assert result.ok is True


def test_parse_webhook_dedupes_by_update_id():
    adapter = TelegramAdapter()
    update = {
        "update_id": 555,
        "message": {
            "message_id": 1,
            "chat": {"id": 9, "first_name": "Sam"},
            "text": "hi",
        },
    }
    events = adapter.parse_webhook(update)
    assert len(events) == 1
    assert events[0].provider_event_id == "555"
    assert events[0].message.external_message_id == "1"
    assert events[0].external_user_id == "9"
    assert events[0].message.text == "hi"

    assert adapter.parse_webhook({"update_id": 556, "callback_query": {}}) == []


def test_verify_webhook_request():
    adapter = TelegramAdapter()

    class FakeRequest:
        def __init__(self, headers):
            self.headers = headers

    req_ok = FakeRequest({"x-telegram-bot-api-secret-token": "correct"})
    req_bad = FakeRequest({"x-telegram-bot-api-secret-token": "wrong"})
    assert adapter.verify_webhook_request(req_ok, "correct") is True
    assert adapter.verify_webhook_request(req_bad, "correct") is False
    assert adapter.verify_webhook_request(req_ok, "") is False
