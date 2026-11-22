# TeleDesk

Omnichannel customer-messaging platform: Telegram, Facebook Messenger, and any
custom channel through a single adapter file. AI-grounded replies, RBAC, tenant
isolation, encrypted credentials, document knowledge base, and a realtime
inbox.

## Architecture

| Layer | Technology |
|-------|------------|
| API | FastAPI + SQLAlchemy + Alembic |
| Background jobs | Celery + Redis (queues: `default`, `turns`, `outbound`) |
| Database | PostgreSQL 16 + pgvector |
| Object storage | MinIO / S3-compatible (SeaweedFS in compose) |
| Frontend | Vite + React (served by the API) |
| AI | Google Gemini (grounded on company documents) |
| Tests | pytest (backend), vitest + Playwright (frontend) |

## Quick start (Docker Compose)

```bash
# 1) Clone and configure
git clone <repo> teledesk
cd teledesk
cp .env.example .env
# Edit .env: set GEMINI_API_KEY, ENCRYPTION_KEY, JWT_SECRET, DATABASE_URL, REDIS_URL, MINIO_*

# 2) Bring up the stack (postgres, redis, minio, backend, worker)
docker compose up -d --profile dev

# 3) Run migrations (auto-run via the `migrate` service; or manually)
docker compose run --rm migrate

# 4) Open the API docs
open http://localhost:8000/docs
```

The `backend` service runs as a non-root user (`appuser`) and exposes a liveness
healthcheck at `/api/healthz` and a readiness probe at `/api/readyz`.

### Without Docker (local dev)

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate   |   Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # then fill in GEMINI_API_KEY, ENCRYPTION_KEY, JWT_SECRET

python -m alembic -c alembic.ini upgrade head
uvicorn app.main:app --reload
# Terminal 2:
celery -A app.workers.celery_app worker --loglevel=info --pool=solo
```

Open `http://localhost:8000/docs`.

## Environment variables

Copy `.env.example` to `.env`. Required at minimum:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `MINIO_ENDPOINT` | S3-compatible endpoint |
| `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` | Object-storage credentials |
| `GEMINI_API_KEY` | Google Gemini for AI replies |
| `JWT_SECRET` | Signing access tokens |
| `ENCRYPTION_KEY` / `ENCRYPTION_KEY_VERSION` / `ENCRYPTION_KEYS` | Credential encryption keyring |
| `CORS_ALLOWED_ORIGINS` | Comma-separated allowed origins |
| `PUBLIC_BASE_URL` | Public URL for webhook/verify links |

See `.env.example` for the full list and defaults.

## Connecting a channel

TeleDesk accepts new channels through a single adapter file plus one registry
line — no pipeline, route, or model changes. See `docs/ADDING_A_CHANNEL.md`.

Bundled adapters:
- `telegram` — `docs/TELEGRAM_SETUP.md`
- `messenger` (Facebook) — `docs/MESSENGER_SETUP.md`

Each channel connects via `POST /api/channels/{provider}/connect`; inbound
messages arrive at `POST /webhooks/{provider}/{channel_id}`.

## Testing

Backend (requires a real PostgreSQL via `TEST_DATABASE_URL`):

```bash
pip install -r backend/requirements-dev.txt
make test            # lint + mypy + pytest
# or the full CI suite in Docker:
docker compose run --rm test
```

Frontend:

```bash
cd frontend
npm ci
npm run lint
npm run typecheck
npm run test
npm run test:e2e
```

## Continuous integration

`.github/workflows/ci.yml` runs:
- `checks` job: ruff, mypy, frontend lint/typecheck, alembic upgrade, pytest
- `audit` job: `pip-audit` (Python) and `npm audit` (Node)

## Security

See `docs/SECURITY.md` for the threat model, SSRF protection, upload scanning,
key rotation, and CORS/headers policy.

## Operations

See `docs/RUNBOOK.md` for health checks, failed-jobs review, log redaction, and
incident response.

## Docs index

- `docs/SECURITY.md` — security controls and hardening
- `docs/API.md` — API reference and integration notes
- `docs/RUNBOOK.md` — operations, health checks, incident response
- `docs/ADDING_A_CHANNEL.md` — adding a new channel adapter
- `docs/TELEGRAM_SETUP.md` — Telegram channel setup
- `docs/MESSENGER_SETUP.md` — Facebook Messenger setup
- `docs/ARCHITECTURE.md` — system design
- `docs/DECISIONS.md` — architectural decision records
