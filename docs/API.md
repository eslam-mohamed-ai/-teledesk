# API Reference

TeleDesk exposes a REST API under `/api`, plus generic webhook ingestion at
`/webhooks/{provider}/{channel_id}`. OpenAPI docs are at `/docs` when the API is
running.

## Authentication

Endpoints are cookie-based (session + refresh + CSRF). A `demo` endpoint exists
for local exploration; production flows use `POST /api/auth/register` then
`POST /api/auth/login`.

Routes requiring auth resolve `current_user` from the session cookie or Bearer
header (when `ENABLE_BEARER_AUTH` is on).

## RBAC

Roles: `owner` > `admin` > `agent`. Routes are gated by `require_role(...)`.

| Minimum role | Example routes |
|--------------|----------------|
| `agent` | `GET /api/auth/me`, conversations list/reply/take/close/read, documents |
| `admin` | `PUT /api/company`, contacts field-definitions/tags/notes, team invite/members, channel connect/disconnect/toggle, `GET /api/team/failed-jobs` |
| `owner` | company settings, billing plan |

## Channels

- `GET /api/channels` — list connected channels (agent+)
- `GET /api/channels/providers` — provider metadata
- `POST /api/channels/{provider}/connect` — connect via adapter (admin+)
- `POST /api/channels/{channel_id}/disconnect` — disconnect (admin+)
- `POST /api/channels/{channel_id}/toggle` — active/inactive (admin+)
- `POST /webhooks/{provider}/{channel_id}` — inbound ingestion (provider-signed)

Adding a channel = one adapter file + one registry line. See `docs/ADDING_A_CHANNEL.md`.

## Conversations

- `GET /api/conversations` — list (agent+)
- `POST /api/conversations/{cid}/reply` — agent reply, status → `human` (agent+)
- `POST /api/conversations/{cid}/take` — assign to self, status → `human` (agent+)
- `POST /api/conversations/{cid}/close` — status → `closed` (agent+)
- `POST /api/conversations/{cid}/read` — clear unread (agent+)
- `POST /api/conversations/{cid}/messages/{mid}/retry` — retry a failed outbound (agent+)

Customer `/human` requests (via inbound webhook) set status `needs_human` and
stop AI replies until an agent takes over.

## Failed jobs (dead letter)

- `GET /api/team/failed-jobs` — list failed outbound messages (admin+)

Returns `id`, `conversation_id`, `channel_id`, `direction`, `sender_type`,
`content`, `error_code`, `error_message`, `created_at`. Paginated with
`limit` (1–200) and `offset`.

## Documents (knowledge base)

- `GET /api/documents` — list (agent+)
- `POST /api/documents/upload` — upload (magic-byte + size + AV-scan validated)
- `GET /api/documents/{id}` — status (`processing` | `ready` | `failed`)

Documents power grounded AI replies (`source` on bot messages).

## Onboarding

- `GET /api/onboarding/state` — per-step progress (admin+)
- `PUT /api/onboarding/step` — mark a step done (admin+)

Steps: `profile`, `ai`, `channel`, `knowledge`, `test`, `team`.

## Health

- `GET /api/healthz` — liveness (returns `{"status": "ok"}`)
- `GET /api/readyz` — readiness (database, redis, storage; 503 if any down)

## Webhook payload limits

- Body capped at 2 MB (413 if exceeded)
- Invalid JSON → 400
- Unsigned/tampered → 403
- Acknowledged within 1 second; processing continues in Celery
