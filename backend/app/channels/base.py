"""Abstract channel adapter interface.

Every provider adapter subclasses ChannelAdapter and implements the provider
specific wire details. The shared pipeline only depends on this interface.
"""

from abc import ABC, abstractmethod
from typing import Any

from fastapi import Request

from app.channels.types import (
    ChannelCapabilities,
    ChannelHealth,
    ContactProfile,
    InboundEvent,
    OutboundMessage,
    SendResult,
)


class ChannelAdapter(ABC):
    """Provider boundary for one channel provider.

    Subclasses must be stateless where possible and must never log credentials.
    """

    @property
    @abstractmethod
    def provider(self) -> str:
        """Provider key, e.g. ``telegram`` or ``messenger``."""

    @property
    @abstractmethod
    def capabilities(self) -> ChannelCapabilities:
        """What this provider can do."""

    @abstractmethod
    async def connect(self, company_id: Any, payload: dict[str, Any]) -> dict[str, Any]:
        """Validate credentials and return channel fields to persist.

        Returns at least ``external_id`` and ``display_name`` plus optional
        encrypted credentials. Must not return raw access tokens.
        """

    @abstractmethod
    async def disconnect(self, channel: Any) -> None:
        """Revoke the provider webhook/subscription for a channel.

        ``channel`` is the persisted channel record (mapping or ORM object)
        exposing at least ``credentials_encrypted`` and the provider external
        identifier so the adapter can revoke without the caller leaking tokens.
        """

    @abstractmethod
    def verify_webhook_request(self, request: Request, channel_secret: str) -> bool:
        """Verify the provider's webhook signature before enqueuing."""

    @abstractmethod
    def parse_webhook(self, payload: dict[str, Any]) -> list[InboundEvent]:
        """Normalize a provider webhook payload into provider-neutral events."""

    @abstractmethod
    async def send_message(
        self,
        channel: Any,
        external_user_id: str,
        message: OutboundMessage,
    ) -> SendResult:
        """Send one outbound message through the provider.

        ``channel`` is the persisted channel record exposing
        ``credentials_encrypted`` (and ``external_id``) so the adapter can
        authenticate without the caller handling raw tokens.
        """

    async def send_typing(
        self,
        channel: Any,
        external_user_id: str,
        on: bool = True,
    ) -> None:
        """Send typing indicator (optional)."""

    @abstractmethod
    async def fetch_profile(self, channel: Any, external_user_id: str) -> ContactProfile:
        """Fetch the contact profile from the provider."""

    @abstractmethod
    async def health_check(self, channel: Any) -> ChannelHealth:
        """Provider-specific reachability check."""
