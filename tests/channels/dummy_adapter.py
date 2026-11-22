"""A complete channel adapter in a single file.

Proves that adding a channel to TeleDesk requires only one adapter file, one
registry line, and one provider value — no pipeline, route, or model changes.
"""

from app.channels.base import ChannelAdapter
from app.channels.registry import register
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


class DummyAdapter(ChannelAdapter):
    """In-memory dummy channel for contract testing."""

    provider = "dummy-for-tests"
    capabilities = ChannelCapabilities(
        supports_typing=True,
        supports_attachments=True,
        supports_read_receipts=True,
        messaging_window_hours=24,
        max_text_length=1000,
    )

    def __init__(self):
        self.sent = []

    async def connect(self, company_id, payload):
        return {
            "provider": "dummy-for-tests",
            "external_id": payload.get("external_id", "dummy_page"),
            "display_name": payload.get("name", "Dummy Page"),
            "credentials_encrypted": "encrypted-dummy-credentials",
            "webhook_secret": payload.get("webhook_secret", "dummy-secret"),
            "status": "connected",
            "active": True,
        }

    async def disconnect(self, channel):
        return None

    def verify_webhook_request(self, request, channel_secret):
        return True

    def parse_webhook(self, payload):
        events = []
        for item in payload.get("events", []):
            events.append(
                InboundEvent(
                    kind=EventKind.message,
                    message=InboundMessage(
                        external_message_id=item.get("message_id"),
                        external_user_id=item.get("user_id"),
                        text=item.get("text"),
                    ),
                    provider_event_id=item.get("event_id"),
                    raw=item,
                )
            )
        return events

    async def send_message(self, channel, external_user_id, message):
        self.sent.append((external_user_id, message.text))
        return SendResult(ok=True, external_message_id="dummy_out_1")

    async def send_typing(self, channel, external_user_id, on=True):
        return None

    async def fetch_profile(self, channel, external_user_id):
        return ContactProfile(
            external_user_id=external_user_id,
            display_name="Dummy Contact",
            language="en",
        )

    async def health_check(self, channel):
        return ChannelHealth.ok


register("dummy-for-tests", DummyAdapter)
