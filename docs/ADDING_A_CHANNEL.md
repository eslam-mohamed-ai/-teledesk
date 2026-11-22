# Adding a Channel to TeleDesk

This guide walks through adding a new messaging channel (e.g. WhatsApp,
Instagram, Facebook Messenger) to TeleDesk. The architecture is designed so
that adding a channel requires **only one adapter file, one registry line, and
one provider enum/value**, with no changes to the shared pipeline, conversation
routes, or realtime layer.

## The adapter contract

Every channel provider implements `app.channels.base.ChannelAdapter`. The
pipeline calls only this interface, so provider-specific HTTP, signatures, and
error shapes stay inside the adapter.

Required members:

| Member | Purpose |
|--------|---------|
| `provider` | Provider key string (e.g. `"telegram"`, `"messenger"`). |
| `capabilities` | `ChannelCapabilities` describing what the provider supports. |
| `connect(company_id, payload)` | Validate credentials, return channel fields to persist (never return raw tokens). |
| `disconnect(channel)` | Revoke the provider webhook/subscription. |
| `verify_webhook_request(request, channel_secret)` | Verify the provider's webhook signature before enqueuing. |
| `parse_webhook(payload)` | Normalize a provider webhook into `list[InboundEvent]`. |
| `send_message(channel, external_user_id, OutboundMessage)` | Send one outbound message; return `SendResult`. |
| `send_typing(channel, external_user_id, on)` | Optional typing indicator. |
| `fetch_profile(channel, external_user_id)` | Return a `ContactProfile` (used once per contact). |
| `health_check(channel)` | Return `ChannelHealth.ok/degraded/down`. |

Typed errors to raise from `send_message`:

- `TransientSendError` → retried with exponential backoff + jitter.
- `RateLimited(retry_after=…)` → retried after `retry_after` seconds.
- `TokenInvalid` → channel marked `token_expired`, no retry.
- `BlockedByUser`, `WindowExpired`, `PermanentSendError` → message marked
  `failed`, no retry.

## Step-by-step checklist

1. **Create the adapter file** `backend/app/channels/<provider>.py` subclassing
   `ChannelAdapter`. See the skeleton below.
2. **Register it** in `backend/app/channels/registry.py`:
   ```python
   from app.channels.<provider> import <Provider>Adapter
   register("<provider>", <Provider>Adapter)
   ```
   Or declare an entry point under the `teledesk.channels` group for
   auto-discovery.
3. **Add the provider value** to any provider check/enum your adapter references
   (the `channels.provider` column is a free string; no DB migration is needed
   for a new provider).
4. **Write a contract test** using the reusable suite
   `tests/channels/test_contract.py::test_adapter_contract` and run it against
   your adapter (and the bundled `dummy` adapter).
5. **Add adapter tests with recorded fixtures** (no real provider credentials;
   see `tests/channels/test_telegram.py` for the pattern).
6. **Wire the webhook** — the generic route `POST /webhooks/{provider}/{channel_id}`
   already verifies via `verify_webhook_request` and enqueues the pipeline.
7. **Run lint/type/tests**: `make lint`, `make typecheck`, `make test`.

## Adapter skeleton

```python
from app.channels.base import ChannelAdapter
from app.channels.registry import register
from app.channels.types import (
    ChannelCapabilities,
    ChannelHealth,
    ContactProfile,
    InboundEvent,
    InboundMessage,
    OutboundMessage,
    SendResult,
    TransientSendError,
)


class ExampleAdapter(ChannelAdapter):
    provider = "example"
    capabilities = ChannelCapabilities(
        supports_typing=True,
        supports_attachments=False,
        supports_read_receipts=False,
        max_text_length=1000,
    )

    async def connect(self, company_id, payload):
        # validate credentials, return fields to persist (encrypted only)
        return {
            "provider": "example",
            "external_id": payload["external_id"],
            "display_name": payload.get("name"),
            "credentials_encrypted": "...encrypted...",
            "webhook_secret": "...",
            "status": "connected",
            "active": True,
        }

    async def disconnect(self, channel):
        # revoke webhook using channel.credentials_encrypted
        ...

    def verify_webhook_request(self, request, channel_secret):
        # hmac.compare_digest against the provider signature header
        return True

    def parse_webhook(self, payload):
        return [
            InboundEvent(
                kind=EventKind.message,
                message=InboundMessage(
                    external_message_id="msg_1",
                    external_user_id="user_1",
                    text="hello",
                ),
                provider_event_id="evt_1",
                raw=payload,
            )
        ]

    async def send_message(self, channel, external_user_id, message):
        try:
            # provider HTTP call
            return SendResult(ok=True, external_message_id="out_1")
        except TransientSendError:
            raise
        except PermanentError as exc:
            raise TransientSendError(str(exc)) from exc

    async def fetch_profile(self, channel, external_user_id):
        return ContactProfile(external_user_id=external_user_id)

    async def health_check(self, channel):
        return ChannelHealth.ok


register("example", ExampleAdapter)
```

## Proving "one adapter file is enough"

The test suite `tests/channels/test_contract.py` runs `test_adapter_contract`
against every registered adapter, including the bundled `dummy` adapter
(`tests/channels/dummy_adapter.py`). The `dummy` adapter is a complete,
functioning channel implemented in a single file plus one registry line — it
demonstrates that no pipeline, route, or model changes are needed to add a
channel.

Run the contract suite:
```
pytest tests/channels/test_contract.py
```

## Security notes

- Never return or log raw provider access tokens. Store them encrypted via
  `app.services.crypto` on `Channel.credentials_encrypted`.
- `verify_webhook_request` must reject unsigned/tampered webhooks before
  enqueuing; invalid webhooks return 403.
- The webhook route caps payloads at 2 MB and acknowledges within 1 second.
