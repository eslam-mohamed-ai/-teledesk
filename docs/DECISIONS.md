# TeleDesk Architecture Decisions

This is the decision record for the omnichannel foundation. Proposed decisions
are architectural direction; they do not imply that the corresponding feature
or schema already exists.

## ADR-001: Use Alembic for schema evolution

**Decision:** Establish a reviewed Alembic baseline and use explicit migrations
for all later schema changes. Keep only the pgvector extension ensure step in
application startup.

**Rationale:** `Base.metadata.create_all()` does not safely evolve deployed
schemas, and cannot provide an auditable deployment history. A baseline gives
fresh databases a reproducible schema and lets verified existing databases be
stamped without rerunning table creation.

**Consequence:** Existing databases must be compared with the baseline before
`alembic stamp head`. A stamp changes migration bookkeeping, not schema objects.
Compose and CI must run migrations before the application starts.

## ADR-002: Model channels as tenant-owned integrations

**Decision:** Represent each connected provider account as a channel integration
owned by one company. Conversations reference the integration; channel-specific
credentials and provider account IDs live on that integration.

**Rationale:** Telegram bots and Messenger Pages have different credentials,
setup flows, identity formats, and webhook subscriptions. An integration
boundary supports multiple accounts and providers without placing provider
secrets on Company or User.

**Consequence:** Existing Telegram bot and conversation columns need a
backwards-compatible migration and backfill. Provider account ownership and
tenant checks require database constraints and service-level validation.

## ADR-003: Use a provider adapter boundary

**Decision:** Keep webhook verification/normalization, connection management,
and outbound delivery in provider adapters behind one typed interface. Keep
conversation policy, quotas, history, persistence, and AI orchestration in
shared services/workers.

**Rationale:** Provider API shapes and delivery rules differ, while tenant
conversation behavior and AI processing should be consistent. A clear adapter
boundary makes future channel additions local and testable.

**Consequence:** The shared worker must not branch on Telegram/Messenger field
names or call provider APIs directly. OAuth onboarding can use shared Meta
utilities while each provider still implements its own account setup and event
capabilities.

## ADR-004: Store external identities as strings and deduplicate by provider ID

**Decision:** New generic external account, participant, conversation, and
message identifiers are strings. Persist provider event/message IDs and enforce
uniqueness in PostgreSQL.

**Rationale:** Providers use different identifier formats and sizes. Durable
deduplication is necessary because webhook delivery may be retried and workers
may execute more than once.

**Consequence:** Do not overload numeric `tg_chat_id` for new providers. Preserve
it for Telegram until a reviewed migration moves existing records to the
generic representation.

## ADR-005: Encrypt provider credentials and never return them to browsers

**Decision:** Store integration credentials encrypted at rest, exchange OAuth
codes only on the backend, and keep tokens out of browser storage and logs.

**Rationale:** A Page token grants authority to act on a business Page. The
existing Fernet service provides an initial encryption utility, but key
management and rotation remain operational requirements.

**Consequence:** Production must fail fast when encryption configuration is
missing. OAuth state must be verified, single-use, short-lived, and linked to
the initiating tenant.

## ADR-006: Redact logs centrally and correlate requests

**Decision:** Use structured logs, a redaction filter that covers formatted
messages and exception text, and a validated request ID propagated to response
headers and log records.

**Rationale:** Provider URLs and exception messages can contain credentials.
Ad-hoc safe logging at each call site is easy to regress.

**Consequence:** Tests must prove that Telegram bot URL tokens, access tokens,
authorization headers, passwords, and app secrets are absent from emitted
records, including exceptions.

## ADR-007: Separate liveness from dependency readiness

**Decision:** `/healthz` indicates that the process is responding;
`/readyz` checks PostgreSQL, Redis, and object storage and returns a non-ready
status if a required dependency is unavailable.

**Rationale:** Orchestrators need to distinguish a live process from one able to
serve requests. Readiness must not create storage resources or expose secrets.

**Consequence:** Dependency checks should be bounded, individually observable,
and return only safe status information.

## ADR-008: Keep production configuration fail-closed

**Decision:** Add an explicit `APP_ENV`. In non-development environments, reject
known development defaults and missing encryption configuration at settings
validation/startup.

**Rationale:** Silent fallback to a development signing key or credentials would
undermine tenant security.

**Consequence:** Local development can retain documented defaults; deployment
environments must inject strong secrets and production service credentials.

## ADR-009: Make CI validate migrations on a disposable database

**Decision:** CI provisions a fresh PostgreSQL/pgvector-compatible database,
runs `alembic upgrade head`, then runs lint, type checks, and tests.

**Rationale:** Import/unit tests alone do not catch migration errors, missing
extensions, or schema drift.

**Consequence:** CI credentials are test-only. Never use a developer's `.env` or
production database for the migration check.

## ADR-010: Preserve legacy Telegram columns during channel-agnostic migration

**Decision:** Phase 1 adds the channel-agnostic tables and columns additively and
keeps all legacy Telegram-specific columns (`bots.token_encrypted`,
`conversations.bot_id`, `conversations.tg_chat_id`, `Message.content` Text,
`Conversation.status` bot/needs_human/human/closed) nullable and unchanged.
Legacy rows are backfilled into the new model, but the channel-agnostic
`Conversation.status` (open/pending/closed) and structured `Message.content`
(JSONB) are intentionally not introduced yet, because they collide with existing
columns of different semantics and changing them would alter runtime behavior.

**Rationale:** The ground rule requires existing Telegram behavior to keep
working and no columns to be dropped in Phase 1. Repurposing `status` or
`content` in-place would break the bots/conversations routes and message
rendering that read them as plain text/status strings.

**Consequence:** A later phase must map legacy `status` values to the new
open/pending/closed model and migrate `content` to a JSONB representation under
a non-colliding column or a careful in-place conversion, each with its own
migration and backfill.
