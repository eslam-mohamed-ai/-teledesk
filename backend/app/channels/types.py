"""Provider-neutral channel types and typed errors.

All channel-specific adapters translate their provider's wire format into
these shared types so the pipeline never branches on provider names.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class EventKind(str, Enum):
    message = "message"
    delivery = "delivery"
    read = "read"
    echo = "echo"
    postback = "postback"
    unsupported = "unsupported"


class Attachment(BaseModel):
    storage_key: str | None = None
    mime: str | None = None
    size: int | None = None
    original_url: str | None = None


class ContactProfile(BaseModel):
    external_user_id: str
    display_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    avatar_url: str | None = None
    language: str | None = None


class InboundMessage(BaseModel):
    external_message_id: str | None = None
    external_conversation_id: str | None = None
    external_user_id: str
    text: str | None = None
    kind: EventKind = EventKind.message
    attachments: list[Attachment] = []
    timestamp: datetime | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class InboundEvent(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    kind: EventKind
    message: InboundMessage | None = None
    external_user_id: str | None = None
    external_conversation_id: str | None = None
    provider_event_id: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class OutboundMessage(BaseModel):
    text: str | None = None
    attachments: list[Attachment] = []
    reply_to_external_id: str | None = None


class SendResult(BaseModel):
    ok: bool
    external_message_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None


class ChannelCapabilities(BaseModel):
    supports_typing: bool = False
    supports_attachments: bool = False
    supports_read_receipts: bool = False
    messaging_window_hours: int | None = None
    max_text_length: int | None = None


class ChannelError(Exception):
    """Base error raised by an adapter."""


class RateLimited(ChannelError):
    """Provider rate limit; retry after these seconds."""

    def __init__(self, retry_after: int, message: str = "rate limited"):
        super().__init__(message)
        self.retry_after = retry_after


class WindowExpired(ChannelError):
    """Outbound messaging window closed (permanent)."""


class TokenInvalid(ChannelError):
    """Channel credentials are invalid/expired (permanent)."""


class BlockedByUser(ChannelError):
    """User blocked the bot/page (permanent)."""


class PermanentSendError(ChannelError):
    """Non-retryable send failure."""


class TransientSendError(ChannelError):
    """Retryable send failure."""


class ChannelHealth(str, Enum):
    ok = "ok"
    degraded = "degraded"
    down = "down"
