# TeleDesk Omnichannel Architecture

## Status and scope

This document describes the current foundation and the intended design for adding
Facebook Messenger while keeping Telegram behavior and allowing additional
channels (such as WhatsApp and Instagram) to be added as provider adapters.
Provider credentials, Meta app configuration, and production deployment details
are environment-specific and are not documented here.

## Current system

```text
Browser (static HTML + shared JavaScript)
  └── FastAPI /api/* ── JWT authentication ── PostgreSQL / SQLAlchemy
          ├── Telegram connection and conversation routes
          ├── Documents ── SeaweedFS S3 ── Celery/Redis ingestion worker
          └── /webhooks/telegram/{bot_id} ── Celery/Redis message worker
                                                   ├── Telegram Bot API
                                                   └── chat service
                                                         ├── pgvector retrieval
                                                         └── Gemini
```

FastAPI serves the frontend and API. PostgreSQL stores tenant, channel, message,
and document metadata; document objects are stored in the S3-compatible service.
Celery uses Redis for message and document tasks. The shared chat service performs
company-scoped document retrieval and Gemini response generation.

The current Telegram schema is provider-specific: `Bot` stores an encrypted bot
token and webhook secret; `Conversation` stores `bot_id` and numeric
`tg_chat_id`. Messages have no provider message ID. The current agent-reply route
also sends directly through Telegram.

## Target data model

The following is a design target, not a description of current columns. Existing
columns should remain until an explicit, reviewed migration changes them.

### Channel integration

Introduce a tenant-owned channel integration record (name is provisional) with:

- Internal ID and `company_id` foreign key.
- Provider key, such as `telegram` or `messenger`.
- Provider account identifier (Messenger Page ID), display name, and connection
  status.
- Encrypted provider credential material; for Messenger, the Page Access Token.
- Granted scopes/permissions and token expiry/last-validated timestamps where
  applicable.
- Created/updated timestamps and a disconnected/revoked state.

Use an appropriate uniqueness rule for provider account ownership. A provider
account must not be silently reassigned to another company. OAuth callback state
must be short-lived, single-use, and bound to the initiating authenticated
company/user.

### Conversations and messages

Evolve conversations toward a channel-neutral identity:

- A conversation belongs to a company and one channel integration.
- Provider participant and conversation identifiers are strings; do not model
  external identifiers as integers.
- Keep status, handoff, notes, preview, and timestamps independent of provider.
- Messages retain the existing roles/content/source/flags and gain a provider
  message/event identifier for idempotent ingestion.
- Enforce tenant consistency and prevent duplicate provider events with database
  constraints, not only process-local checks.

Telegram data must be migrated/backfilled without losing existing history.
Avoid a destructive rename/removal of `bot_id` or `tg_chat_id` until all routes,
workers, UI consumers, and existing records are migrated and verified.

## Adapter and processing contract

Keep provider-specific API details out of the conversation workflow. Each
adapter should implement the same typed contract, conceptually:

- Identify its provider and supported capabilities.
- Verify provider webhook requests and normalize one or more inbound events into
  a common `InboundMessage` shape.
- Send a text reply using a channel integration and normalized recipient.
- Validate/establish and disconnect a channel integration.
- Translate provider errors into classified retryable, permanent, or
  policy-rejected errors without exposing credentials.

The normalized inbound message should include the integration/company context,
string external participant and conversation IDs, provider message ID,
timestamp, text (or an explicit unsupported-content representation), and only
necessary safe metadata. It must not include access tokens.

The shared worker should own deduplication, loading the company/integration,
conversation creation/lookup, quotas, history, persistence, handoff, and retry
policy. It should call `chat.reply_to()` for the AI decision and then call the
selected adapter to deliver the response. Persist delivery state so a failed
send can be retried without generating a second AI answer or duplicate outbound
message.

Meta channel adapters can share Graph API transport, OAuth utilities, webhook
signature validation, and Page/business account models. Adding Instagram or
WhatsApp should require a provider adapter plus any channel-specific onboarding
or webhook registration, not changes throughout shared conversation logic.

## API surface (target)

Existing Telegram routes remain supported during migration:

- Existing `/api/bots` and `/api/bots/connect`, `/toggle`, `/disconnect`, and
  `/test` remain Telegram-specific or become compatibility wrappers.
- Authenticated channel listing/status and disconnect endpoints, for example
  `GET /api/channels` and `DELETE /api/channels/{channel_id}`.
- Authenticated OAuth start and callback endpoints. The callback validates
  `state`, exchanges the code server-side, fetches selectable Pages, and binds
  the final selection to the authenticated tenant.
- A page-selection/connection endpoint that accepts an integration reference,
  not a raw access token.
- Public provider-specific webhook endpoints (for example
  `/webhooks/messenger`) that verify signatures, durably enqueue valid events,
  and respond according to provider delivery requirements.
- Existing conversation list/detail/take/close/note/reply endpoints should work
  across providers using the conversation's integration.
- `/healthz` is process liveness; `/readyz` checks required dependencies.

Exact route names and versioning should be settled before the feature phase.

## Migrations and rollout

1. Establish Alembic and a reviewed initial migration matching the pre-foundation
   schema. New indexes are in a following migration so existing databases can
   stamp the baseline and then receive those indexes normally.
2. Before stamping an existing database, inspect it against the baseline;
   stamping records migration history and does not create or verify schema
   objects. Stamp the baseline revision, then upgrade to head.
3. Stop using ORM `create_all()` for schema evolution. Startup may still ensure
   the PostgreSQL `vector` extension exists.
4. Add channel integration and provider event/delivery storage in a separate
   additive migration.
5. Backfill existing Telegram bots/conversations and verify row counts,
   foreign keys, tenant ownership, and representative conversation histories.
6. Deploy provider-neutral reads/writes while preserving Telegram compatibility.
7. Add Messenger onboarding/webhooks/send behavior; only later remove legacy
   Telegram-only columns in a separately reviewed migration.

All production schema changes must use Alembic revisions. Do not run `stamp` or
migrations against an unverified database.

## Observability and security

- Emit structured logs with a request ID and redaction applied to messages,
  arguments, and exception text. Never log credentials, authorization headers,
  or URLs carrying access tokens.
- Verify webhook signatures against the exact provider-defined payload and
  reject invalid requests before enqueueing.
- Persist event IDs and make task retries idempotent.
- Resolve each webhook's Page/account ID to a channel integration and company;
  never trust tenant IDs supplied by an event or browser request.
- Encrypt integration tokens at rest and keep OAuth tokens server-side.
- Use liveness/readiness checks without returning connection strings or
  dependency exception details to callers.
- Apply tenant filters to every conversation/document/message access and test
  cross-tenant access explicitly.

## Testing and operations

Use unit tests for adapters, normalization, error classification, redaction, and
OAuth state. Use an isolated PostgreSQL/pgvector test database for ORM, migration,
deduplication, and tenant-isolation tests. CI should run Ruff, lenient mypy,
pytest, and an Alembic upgrade against a fresh PostgreSQL database. The Compose
migration job must complete successfully before the API and worker start.
