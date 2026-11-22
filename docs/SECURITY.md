# Security

TeleDesk security controls, threat model, and hardening checklist.

## Threat model

| Threat | Mitigation |
|--------|------------|
| Credential theft in transit | All provider credentials encrypted at rest (Fernet keyring); TLS termination at the edge. |
| Provider account hijacking | External ID bound to the owning company; cross-company connect rejected. |
| SSRF via webhook fetch | `safe_fetch` blocks private/loopback/link-local IPv4/IPv6 and re-validates after redirects. |
| Malicious file uploads | Magic-byte validation, size cap, MIME allowlist, AV-scan hook. |
| Log leaking secrets | Redaction of `Authorization`, `Cookie`, `Set-Cookie`, `X-Signature`, and `x-csrf-token`. |
| Webhook forgery | Adapter `verify_webhook_request` before enqueuing; 403 on invalid signature. |
| Brute-force login | PBKDF2 (200k iterations), progressive lockout, token-family revocation on reuse. |
| Privilege escalation | RBAC (owner > admin > agent); every state-changing route gated by `require_role`. |
| CSRF | Double-submit cookie token on state-changing requests. |
| Clickjacking / MIME sniffing | CSP, X-Content-Type-Options, Referrer-Policy, X-Frame-Options, frame-ancestors. |

## Encryption key rotation

Channel credentials are encrypted via `app.services.crypto` with a keyring:

- `ENCRYPTION_KEY` — active encryption key (Fernet base64).
- `ENCRYPTION_KEY_VERSION` — version tag stamped on each ciphertext.
- `ENCRYPTION_KEYS` — JSON map of `version -> key` for decrypting old ciphertexts.

To rotate: add the new key to `ENCRYPTION_KEYS`, bump `ENCRYPTION_KEY_VERSION`, and
set `ENCRYPTION_KEY` to the new value. Decryption falls back through all known
keys, so historical ciphertexts remain readable. Re-encrypt lazily on next write.

## CORS

`CORS_ALLOWED_ORIGINS` is a comma-separated allowlist. The default allows nothing;
set it explicitly in production. The `SecurityHeadersMiddleware` applies CSP,
HSTS, X-Content-Type-Options, Referrer-Policy, X-Frame-Options, and
frame-ancestors to every response.

## Upload validation

`POST /api/documents/upload` enforces:
- Magic-byte check (file signature, not extension)
- Size cap (default 10 MB)
- MIME type allowlist
- `av_scan()` hook (connect your AV scanner here)

## SSRF protection

Outbound fetches (provider profile, webhook verification, outbound delivery) go
through `safe_fetch`, which:
- Rejects private, loopback, and link-local addresses (IPv4 and IPv6)
- Follows redirects but re-validates each hop
- Caps the response body
- Surfaces provider errors without leaking internal URLs

## Audit & redaction

All admin/actions are written to the audit log. Secret headers (`Authorization`,
`Cookie`, `Set-Cookie`, `X-Signature`, `x-csrf-token`) are redacted before
logging. Failed login attempts are tracked per identifier with progressive
lockout; reuse of a revoked refresh token revokes the whole family (theft
detection).

## Hardening checklist

- [ ] `CORS_ALLOWED_ORIGINS` set to production origins only
- [ ] `ENCRYPTION_KEY`/`ENCRYPTION_KEYS` rotated regularly; old keys retained
- [ ] `JWT_SECRET` strong and unique per environment
- [ ] Docker backend runs as non-root (`appuser`); read-only app dir
- [ ] `pip-audit` and `npm audit` pass in CI
- [ ] AV scanner wired into `av_scan()` before enabling uploads in prod
- [ ] Webhook secrets unique per channel; never logged
