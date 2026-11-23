# TeleDesk Project Status Audit

Audit date: 2026-11-23  
Branch: `feat/omnichannel` at `a1a8d4d`  
Scope: read-only inspection and checks. The report itself is the only requested deliverable. Existing local changes were left untouched; `.env` was never opened or printed.

## (1) Executive summary

- The branch contains commits labeled for Phases 0, 1, 2, 5, and 6; Phase 3/4 intent is inferred from commit subjects, not a phase prompt in the repository.
- The exact earlier phase prompts and Final Acceptance Checklist were not present in this audit context or tracked docs; checklist coverage below is reconstructed and explicitly marked.
- Ruff and mypy pass. Frontend build fails on duplicate keys in the current `i18n.ts` working copy.
- Backend pytest: 52 passed, 6 failed, 56 errors; PostgreSQL was unavailable. Two failures concern the dummy adapter.
- Vitest passes 9/9 when run with one worker. Playwright passes 1/1, but all API calls are mocked.
- Fresh-database migration and downgrade/upgrade checks are unverified: Docker Desktop’s daemon is unavailable.
- Static review found likely CSRF and RBAC gaps in legacy bot routes, and AV scanning is a no-op.
- No common private-key/API-token patterns were found in tracked non-env files; this is a limited pattern scan, not proof that no secret exists.
- Production launch is blocked pending security fixes, database migration validation, functional test repairs, and live provider validation.

## (2) Phase-by-phase status table

**Phase prompt caveat:** No document containing the original phase prompts or their itemized tasks was found in `docs/` or the tracked repository. Items below are reconstructed from phase-labeled commits, architecture docs, CI, and code. They are not represented as an exact transcription of those prompts. Status reflects this audit, not earlier reports. Relevant code and docs are linked as evidence.

| Phase | Reconstructed task | Status | Evidence |
|---|---|---|---|
| 0 | Establish Alembic baseline, ORM relationships, and query indexes | PARTIAL | Foundation revisions/models exist in `backend/migrations/versions/` and `backend/app/models/`; actual fresh-DB upgrade was not run because Docker daemon is unavailable. |
| 0 | Add structured logs, redaction, request IDs, and health/readiness endpoints | PARTIAL | Implementations exist in [logging_config.py](../backend/app/logging_config.py), [middleware.py](../backend/app/middleware.py), and [health.py](../backend/app/routes/health.py); runtime behavior was not integration-tested here. |
| 0 | Add environment validation, lint/type/test tooling, and CI | PARTIAL | [config.py](../backend/app/config.py), `pyproject.toml`, `Makefile`, and `.github/workflows/ci.yml` exist; Ruff/mypy pass, while pytest errors due to missing PostgreSQL. |
| 0 | Record architecture scope and decisions | DONE (verified) | [ARCHITECTURE.md](ARCHITECTURE.md) and [DECISIONS.md](DECISIONS.md) are present and describe the planned schema and rollout. |
| 1 | Add channel-agnostic schema additively while retaining legacy Telegram data | PARTIAL | Migrations `202611220002` onward add/backfill tables and columns; migration tests fail or error without PostgreSQL, so DB effects remain unverified. ADR-010 in [DECISIONS.md](DECISIONS.md) explicitly preserves old columns. |
| 1 | Backfill legacy bots/conversations and enforce provider identity constraints | PARTIAL | [202611220004_backfill_legacy_telegram.py](../backend/migrations/versions/202611220004_backfill_legacy_telegram.py) and later constraint revisions exist; four migration tests fail in this run and no real DB round trip completed. |
| 1 | Add ORM models and a migration verification utility | PARTIAL | Channel/contact/event models and [verify_migration.py](../backend/scripts/verify_migration.py) exist; the verifier was not run against a database. |
| 2 | Define channel adapter contract and Telegram/Messenger adapters | MOCKED-ONLY | [base.py](../backend/app/channels/base.py), [telegram.py](../backend/app/channels/telegram.py), and [messenger.py](../backend/app/channels/messenger.py) implement the boundary; test suites use fake/mocked providers, and no live credentials were used. |
| 2 | Build shared ingest/turn/outbound processing and deduplication | PARTIAL | [ingest.py](../backend/app/pipeline/ingest.py), [turn.py](../backend/app/pipeline/turn.py), and [outbound.py](../backend/app/pipeline/outbound.py) exist; PostgreSQL-dependent tests did not execute successfully. |
| 2 | Add generic webhook, channel CRUD, conversation endpoints, and realtime | PARTIAL | [channels.py](../backend/app/routes/channels.py), [conversations.py](../backend/app/routes/conversations.py), and [realtime.py](../backend/app/routes/realtime.py) exist; DB and tenant behavior are unverified in this run. |
| 3 | Add cookie sessions, rotating refresh tokens, password reset, and email verification | PARTIAL | Implemented in [auth.py](../backend/app/routes/auth.py) and [auth.py service](../backend/app/services/auth.py); database tests errored, and no SMTP end-to-end test was run. |
| 3 | Add RBAC, team invitations, onboarding, lead capture, contacts, and audit logging | PARTIAL | Routes/services exist in `backend/app/routes/` and [audit.py](../backend/app/services/audit.py); DB-backed tests errored. Static review found legacy bot mutators lack admin-role enforcement. |
| 4 | Close out audit writes, SSE, phone parsing, type-checking, and database test guards | PARTIAL | Commit `649377c` claims these changes; mypy passes, but database checks and runtime SSE/phone flows are unverified. |
| 5 | Replace old static frontend with the React/Vite application and typed API client | PARTIAL | Current app is under `frontend/src/`; old static assets remain in `HEAD` but are deleted in the working tree (`frontend/css/style.css`, `frontend/js/api.js`, `frontend/js/layout.js`). Current build fails in modified [i18n.ts](../frontend/src/lib/i18n.ts). |
| 5 | Deliver inbox, shell, auth, onboarding, channels, and frontend docs/lint | PARTIAL | Pages/components and frontend docs exist; Vitest passes 9/9 and mocked Playwright passes 1/1, but build fails and live backend/browser integration is unverified. |
| 6 | Harden secrets, tenant boundaries, RBAC, CSRF, CORS, uploads, SSRF, and headers | PARTIAL | Controls are present in [SECURITY.md](SECURITY.md), [security.py](../backend/app/security.py), and [security_middleware.py](../backend/app/security_middleware.py); findings below identify gaps, including missing CSRF/admin guards and a no-op AV hook. |
| 6 | Add backend/frontend tests and deployment/runbook/API documentation | PARTIAL | CI, [RUNBOOK.md](RUNBOOK.md), [API.md](API.md), and tests exist; pytest has 62 unsuccessful outcomes (6 failures + 56 errors), and frontend build fails. |

### Phase commits observed

`git log --oneline --decorate -30` on `feat/omnichannel` includes explicit commits for:

- Phase 0/foundation: `adf3d8e`, `741d5b3`, `8b30cd7`, `7d6bb83`, `638a17d`.
- Phase 1/schema: `49666ee`, `a62ce39`, `4596fb8`, `4a55169`, `3941f5b`.
- Phase 2/channels and processing: `6a58cfe`, `34de6b9`, `d740f1d`.
- Phase 3/4 intent is not explicitly labeled in commits; auth and product work appear in `8e455e4`, `b296e58`, `649377c`.
- Phase 5: `50bd734`, `fd0b9e9`, `36df157`.
- Phase 6: `d69cd13`, `cb81b09`, `a1a8d4d`.

## (3) Failing/unverified checks

| Check | Result | Evidence / exact output |
|---|---|---|
| `git status --short --branch` | Informational | `## feat/omnichannel`; the pre-existing working tree had deletions `frontend/css/style.css`, `frontend/js/api.js`, `frontend/js/layout.js`; modified smoke test and React files; untracked `.kilo/`, `Microsoft/`, `docker`, `ToastListener.tsx`, `frontend/test-results/`, and `vite-temp/`. They were left untouched. |
| `git log --oneline --decorate -30` | Pass | HEAD is `a1a8d4d (HEAD -> feat/omnichannel) Phase 6: deployment and docs`; phase commit groups are listed above. |
| Ruff: `.venv\Scripts\ruff.exe check backend/app backend/migrations backend/tests` | PASS | `All checks passed!` |
| mypy: `.venv\Scripts\mypy.exe` | PASS | `Success: no issues found in 79 source files` |
| pytest: `.venv\Scripts\pytest.exe -q --tb=no` with a deliberately unavailable local test DB URL | FAIL / DB-dependent results unverified | `6 failed, 52 passed, 1 warning, 56 errors in 169.04s (0:02:49)`. Errors include `psycopg2.OperationalError: connection to server at "127.0.0.1", port 65432 failed: Connection refused`. The six failures were four migration tests and `test_dummy_adapter_registered` / `test_dummy_adapter_parses_message` in `test_webhook_burst.py`. Errors affected migration, RBAC, tenant-isolation, pipeline, and webhook tests. |
| Alembic fresh upgrade | UNVERIFIED | CI requires a fresh pgvector/PostgreSQL service in `.github/workflows/ci.yml`; `docker version` showed `failed to connect to the docker API ... dockerDesktopLinuxEngine ... The system cannot find the file specified.` No database migration was applied. |
| Alembic downgrade/upgrade round trip | UNVERIFIED | Same missing PostgreSQL/pgvector service; no DB was available for the round trip. `test_migrations.py` has coverage, but its migration tests failed in this run. |
| Frontend build: `npm run build` | FAIL | `src/lib/i18n.ts(213,7): error TS1117: An object literal cannot have multiple properties with the same name.` Same error at lines 214, 216, 222, 224, 225, 227, and 228. |
| Vitest: `npm run test` | PASS on serial rerun | Default parallel run reported 2 files/2 tests passed plus 2 worker-start errors (`Timeout waiting for worker to respond`). Rerun `npx vitest run --pool=threads --maxWorkers=1`: `Test Files 4 passed (4); Tests 9 passed (9)`. |
| Playwright smoke: `npm run test:e2e` | PASS, mocked only | `1 passed`; `smoke.spec.ts` routes all `/api/**` calls to fixtures and explicitly mocks verification, channel connect, upload, chat, and invite. It is not a live-stack test. |
| Frontend lint/typecheck | Not requested in command list; unverified | CI defines both, but neither was separately run in this audit. |

## (4) Mocked-only integrations and what real credentials/manual steps are needed

- **Playwright onboarding/inbox smoke:** the API is intercepted in [smoke.spec.ts](../frontend/e2e/smoke.spec.ts); sign-up verification, login, channel connection, knowledge upload, AI reply, and invitations are fixture responses. A real-stack smoke with disposable SMTP, DB, storage, and authenticated test user remains necessary.
- **Messenger:** [messenger.py](../backend/app/channels/messenger.py) accepts a Page ID and Page Access Token directly and makes Graph API calls, but no OAuth start/callback, selectable-Page flow, or persisted OAuth state flow was found in the channel route implementation. Needed: Meta app/page credentials, webhook subscription and public HTTPS callback configuration, least-privilege permissions, and a real connect/inbound/reply/revocation run.
- **Telegram:** adapter code exists, but this audit used no BotFather token or live webhook/API credentials. Needed: non-production bot token, public HTTPS webhook URL, configured webhook secret, and a real inbound/outbound test.
- **AI/Gemini:** no API credential was used in the mocked browser smoke; AI behavior and grounding against a configured model are unverified. Needed: test API key, representative tenant knowledge data, quota/rate-limit validation, and response-quality checks.
- **SMTP, object storage, Redis, and worker delivery:** live service paths were not exercised. Needed: disposable production-like SMTP/S3/Redis services and verification of migration-before-worker startup, failed-send retries, and readiness behavior.
- **AV scanning:** [av_scan](../backend/app/security.py) returns `None` unconditionally and is documented as a deployment hook. It works only as a pass-through stub until a real scanner is wired and verified.
- **WhatsApp/other channels:** provider metadata says unavailable/coming soon in the browser mock; no live implementation was validated.

## (5) Skipped or partial items

- Exact original phase task lists and the Phase 6 Final Acceptance Checklist were unavailable. The statuses and checklist items in this report are reconstructed from commit subjects and tracked architecture/CI docs, not an authoritative prompt copy.
- Database-dependent verification, including fresh migration, rollback, tenant isolation, and DB-backed business flows, was blocked by the absent Docker daemon/PostgreSQL endpoint.
- Real Telegram, Messenger, Gemini, SMTP, Redis, object-storage, and AV integrations were not exercised; no real credentials were used.
- OAuth-based Messenger onboarding is simplified to direct Page ID/token connection in [channels.py](../backend/app/routes/channels.py) and [messenger.py](../backend/app/channels/messenger.py), despite the architecture target describing an OAuth state/callback and Page selection flow in [ARCHITECTURE.md](ARCHITECTURE.md).
- Legacy Telegram `/api/bots` compatibility endpoints remain implemented in [bots.py](../backend/app/routes/bots.py); old `bot_id` and `tg_chat_id` columns remain in models/migrations as ADR-010 intentionally preserves them. They are not removed/deprecated wrappers yet.
- Static HTML/CSS/JS files remain in the committed `HEAD`, although the current working tree marks the old CSS/JS files deleted; `frontend/index.html` is still used as the SPA entry point. The working tree deletion is uncommitted.
- Frontend UI includes hard-coded English text outside translation lookup, for example text in `frontend/src/pages/contacts/Contacts.tsx`, `frontend/src/pages/inbox/Inbox.tsx`, and `frontend/src/pages/ai/AI.tsx`; the current modified `i18n.ts` also has duplicate object keys and prevents a build.
- CI currently runs Ruff, mypy, frontend lint/typecheck, migrations, pytest, and dependency audits, but `.github/workflows/ci.yml` does not run `npm run build`, Vitest, or Playwright.
- Keyword search found no `TODO`, `FIXME`, `XXX`, `not implemented`, or `NotImplementedError` matches in app/test/frontend source. `mock` and `placeholder` do occur in test fixtures and user-facing input hints; these are intentional in several cases, not a global proof that all behavior is real.
- The requested exact failing output is summarized above: pytest ends `6 failed, 52 passed, 1 warning, 56 errors`; the repeated DB failure is PostgreSQL `Connection refused`; frontend build ends with eight TS1117 duplicate-property diagnostics; default Vitest parallel mode had two worker startup timeouts before the serial rerun passed.

## (6) Security findings, ranked by severity

### High

1. **CSRF protection is not consistently applied to cookie-authenticated state changes.** `current_user` accepts the session cookie in [deps.py](../backend/app/deps.py), and `csrf_protect` exists there, but conversation mutation handlers in [conversations.py](../backend/app/routes/conversations.py) do not depend on it; the same pattern is present on document/channel/team/other state-changing routes. I found explicit CSRF dependencies in selected auth handlers, not a global enforcement middleware. Because CORS is not a substitute for CSRF protection, this is a production security gap. Static code review; no exploit test was run.
2. **Legacy `/api/bots` mutators omit admin RBAC.** Connect/toggle/disconnect/test handlers in [bots.py](../backend/app/routes/bots.py) depend on `current_company` and do not call `require_role`, even though [API.md](API.md) documents channel mutators as admin+. An authenticated agent can reach these operations. Verify/close this gap before launch.

### Medium

3. **Upload malware scanning is not implemented.** [av_scan](../backend/app/security.py) always returns `None`; [documents.py](../backend/app/routes/documents.py) calls it as if validation were complete. Magic-byte/size/extension checks are present, but they do not replace AV scanning. The code comments and [SECURITY.md](SECURITY.md) acknowledge production wiring is required.
4. **Production cookie security is not fail-closed.** [config.py](../backend/app/config.py) defaults `COOKIE_SECURE=False`; its production validator checks signing/encryption/database/storage defaults but does not reject an insecure session-cookie setting. `_set_session_cookies` in [auth.py](../backend/app/routes/auth.py) uses that setting. Require Secure cookies and validate the production setting.
5. **SSRF DNS validation has a time-of-check/time-of-use gap.** [security.py](../backend/app/security.py) resolves and checks a hostname, then `httpx` resolves it again when connecting. A DNS rebinding race can therefore return a public IP during validation and a private IP at connection time. Redirect targets are rechecked, but the initial DNS result is not pinned to the connection. The helper also makes redirect requests after leaving the `AsyncClient` context, which likely breaks redirect handling; redirect behavior is unverified.
6. **Production-origin configuration and TLS remain operationally unverified.** CORS uses an explicit configured origin list and no wildcard in [security_middleware.py](../backend/app/security_middleware.py), but no production deployment values were reviewed or exercised. Confirm TLS termination, secure cookies, correct CORS origins, and HSTS behavior in deployment.

### Low / evidence limits

7. **Credential exposure in API responses:** static response schemas reviewed do not include credentials: [ChannelOut](../backend/app/routes/channels.py) omits encrypted token fields, and `/api/bots` list output omits the bot token in [bots.py](../backend/app/routes/bots.py). Auth routes issue tokens as HttpOnly cookies and return user data. This was not confirmed through a live response. A filename-only scan of tracked files (excluding `.env` and `.env.*`) found no common private-key/GitHub/OpenAI/Meta token patterns; this is not an exhaustive secret scan.
8. **Secrets in logs:** centralized [logging_config.py](../backend/app/logging_config.py) redacts bot-token URL paths, authorization/bearer strings, and token/password assignments in log records and exceptions. The development console email sender prints email bodies (which contain verification/reset links) in [email.py](../backend/app/services/email.py); it is selected only when `APP_ENV == "development"`. Do not use development mode or retain those console logs in production. `.env` was excluded from inspection.
9. **Tenant isolation:** routes commonly scope queries by `company_id`, including conversations and channels, and tenant sweep tests exist; the test suite could not execute those checks because the database was unavailable. Full route-by-route isolation is therefore **unverified**, not certified.

## (7) Production-launch blockers

- Add enforced CSRF checks to every cookie-authenticated state-changing API route and tests proving rejection without the matching token.
- Apply admin/owner RBAC to legacy bot connect/toggle/disconnect/test routes and run the full role matrix.
- Wire a real AV scanner and fail closed when it is unavailable.
- Make `COOKIE_SECURE=True` mandatory in production and verify production CORS/TLS/HSTS settings.
- Resolve SSRF DNS rebinding and redirect handling; test public, private, redirect, IPv6, and rebinding cases.
- Run all migrations from an empty PostgreSQL/pgvector database and a downgrade/upgrade round trip in an isolated service; inspect backfill behavior with representative legacy data.
- Repair six failing backend tests and provide PostgreSQL so the 56 errored tests can run; repeat RBAC/tenant-sweep acceptance afterward.
- Resolve duplicate keys in the current `frontend/src/lib/i18n.ts` working copy and obtain a successful production frontend build.
- Validate Messenger and Telegram using non-production real credentials, including webhook signature/replay behavior, outbound send, revocation, and retry paths. Implement/confirm Meta OAuth onboarding if it remains a product requirement.
- Exercise real SMTP, Redis/Celery, object storage, Gemini, and readiness behavior in a production-like deployment.
- Reconcile the existing dirty working tree before release; current modifications and deletions are not represented by the phase commits and include the build-breaking `i18n.ts` changes.

## (8) Recommended next tasks, ordered by priority

1. Enforce CSRF and legacy bot RBAC; add focused regression coverage.
2. Require Secure cookies in production; wire fail-closed AV scanning; fix and test SSRF connection pinning/redirect behavior.
3. Start an isolated PostgreSQL/pgvector service, then rerun fresh upgrade, downgrade/upgrade, all migrations, pytest, tenant isolation, and RBAC matrix.
4. Fix `frontend/src/lib/i18n.ts` duplicate keys; run frontend build, lint/typecheck, Vitest, and Playwright in CI.
5. Validate Telegram and Messenger end-to-end with isolated real credentials; add the Meta OAuth/Page selection flow if required by the original plan.
6. Add CI coverage for frontend build, Vitest, and the Playwright smoke; preserve the existing mock smoke but distinguish it from real-stack acceptance.
7. Review the pending working-tree files/deletions, settle the retained `/api/bots` compatibility policy and legacy-column removal milestone, then repeat this audit against the exact Phase 0–6 prompts and Phase 6 acceptance checklist.
