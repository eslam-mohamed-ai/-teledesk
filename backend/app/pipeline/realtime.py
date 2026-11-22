"""Realtime presence/events over Redis pub/sub + SSE.

Multiple API workers can publish to the same Redis channel; each worker
subscribes and fans out to its own SSE clients. Messages are company-scoped
so a client only receives events for its own company.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from redis import Redis

from app.config import settings

log = logging.getLogger("teledesk.realtime")

_publisher: Redis | None = None


def _get_publisher() -> Redis:
    global _publisher
    if _publisher is None:
        _publisher = Redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=2,
            socket_timeout=2,
            decode_responses=True,
        )
    return _publisher


def _channel(company_id: int | str) -> str:
    return f"teledesk:realtime:company:{company_id}"


def publish(company_id: int | str, event: dict[str, Any]) -> None:
    """Publish an event to a company's Redis channel (fire and forget)."""
    try:
        _get_publisher().publish(_channel(company_id), json.dumps(event, default=str))
    except Exception:
        # Redis unavailable must not break request handling.
        log.exception("realtime publish failed for company=%s", company_id)


class Subscriber:
    """Async Redis pub/sub subscriber for one company."""

    def __init__(self, company_id: int | str):
        self.company_id = company_id
        self._redis: Redis | None = None
        self._pubsub: Any = None
        self._queue: asyncio.Queue[str | None] = asyncio.Queue()
        self._stop = False

    async def connect(self) -> None:
        self._redis = Redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=2,
            socket_timeout=2,
            decode_responses=True,
        )
        self._pubsub = self._redis.pubsub()
        await asyncio.to_thread(self._pubsub.subscribe, _channel(self.company_id))

    async def __aiter__(self):
        return self

    async def __anext__(self) -> dict:
        if self._stop:
            raise StopAsyncIteration
        # read one message, blocking briefly
        assert self._pubsub is not None, "call connect() first"
        msg = await asyncio.to_thread(
            self._pubsub.get_message, timeout=1.0, ignore_subscribe_messages=True
        )
        if msg is None:
            # no message; yield a heartbeat so SSE stays open
            return {"type": "heartbeat"}
        data = msg.get("data")
        if isinstance(data, str):
            try:
                return json.loads(data)
            except ValueError:
                return {"type": "raw", "data": data}
        return {"type": "heartbeat"}

    async def close(self) -> None:
        self._stop = True
        if self._pubsub is not None:
            try:
                await asyncio.to_thread(self._pubsub.unsubscribe, _channel(self.company_id))
                await asyncio.to_thread(self._pubsub.close)
            except Exception:
                pass
        if self._redis is not None:
            try:
                self._redis.close()
            except Exception:
                pass
