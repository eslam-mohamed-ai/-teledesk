# Runbook

Operations, health checks, failed-jobs review, and incident response.

## Service layout (Docker Compose)

| Service | Role | Profile |
|---------|------|---------|
| `postgres` | PostgreSQL 16 + pgvector | db/dev/prod |
| `redis` | Celery broker + result backend | cache/dev/prod |
| `minio` | Object storage (documents) | storage/dev/prod |
| `migrate` | Alembic `upgrade head` (one-shot) | dev/prod |
| `backend` | FastAPI API + SPA | dev/prod |
| `worker` | Celery worker (`default`, `turns`, `outbound`) | dev/prod |
| `test` | pytest suite in Compose | test |

Start the dev stack:
```bash
docker compose up -d --profile dev
docker compose run --rm migrate
```

## Health checks

- `GET /api/healthz` — liveness (container restart target)
- `GET /api/readyz` — readiness (database + redis + storage; 503 if any down)

Docker `HEALTHCHECK` hits `/api/healthz` every 10s.

## Failed jobs (dead-letter queue)

Failed outbound messages are recorded with `delivery_status = "failed"` plus
`error_code` / `error_message`. Review them:

```bash
# Via the API (admin token required)
curl -H "Cookie: session=<token>" http://localhost:8000/api/team/failed-jobs?limit=50
```

Retried via `POST /api/conversations/{cid}/messages/{mid}/retry` (sets
`delivery_status = "queued"` and re-enqueues).

## Celery worker

Queues: `default`, `turns`, `outbound`. Acknowledgment is late; tasks are
rejected on worker loss. Time limits: hard 300s, soft 270s.

Restart the worker:
```bash
docker compose restart worker
```

## Logs

```bash
docker compose logs -f backend
docker compose logs -f worker
docker compose logs -f postgres
```

Secret headers (`Authorization`, `Cookie`, `Set-Cookie`, `X-Signature`,
`x-csrf-token`) are redacted before logging. Failed login attempts trigger
progressive lockout per identifier.

## Incident response

| Symptom | First response |
|---------|----------------|
| Webhooks not ingested | Check `GET /api/readyz` (redis/minio up?), channel `active`, webhook secret |
| AI not replying | Verify `GEMINI_API_KEY`; check worker logs for `reply failed` |
| Messages stuck `queued` | Confirm worker is running on the `outbound` queue; retry failed messages |
| Credentials decrypt failure | Confirm `ENCRYPTION_KEYS` contains the key version used at connect time |
| 403 on state-changing routes | Send `x-csrf-token` matching the CSRF cookie (double-submit) |

## Backups

- PostgreSQL: `pg_dump` the `teledesk` database nightly.
- MinIO: back up the `miniodata` volume (documents).
- Encryption keys: back up `ENCRYPTION_KEYS` / `ENCRYPTION_KEY` separately from
  the database; losing them makes channel credentials undecryptable.
