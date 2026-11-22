"""Security tests: key rotation, log redaction, SSRF, upload validation.

These tests do not require a live PostgreSQL database.
"""

from __future__ import annotations

import json

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app.config import settings
from app.logging_config import redact_sensitive_data
from app.main import app
from app.security import av_scan, is_safe_fetch_url, validate_magic_bytes


# ---------------------------------------------------------------------------
# Key rotation
# ---------------------------------------------------------------------------


def _rotate(monkeypatch, active_key: str, active_version: int, previous: dict[int, str]) -> None:
    monkeypatch.setattr(settings, "ENCRYPTION_KEY", active_key, raising=False)
    monkeypatch.setattr(settings, "ENCRYPTION_KEY_VERSION", active_version, raising=False)
    monkeypatch.setattr(settings, "ENCRYPTION_KEYS", json.dumps(previous), raising=False)
    import app.services.crypto as crypto

    crypto._KEYRING_CACHE = None


def test_key_rotation_decrypts_older_versions(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import crypto

    k_v1 = Fernet.generate_key().decode()
    k_v2 = Fernet.generate_key().decode()

    _rotate(monkeypatch, k_v1, 1, {})
    token_v1 = crypto.encrypt("tenant-secret", key_version=1)
    assert crypto.decrypt(token_v1, key_version=1) == "tenant-secret"
    assert crypto.active_key_version() == 1

    # Rotate to v2, keep v1 in the keyring for decryption.
    _rotate(monkeypatch, k_v2, 2, {1: k_v1})
    assert crypto.active_key_version() == 2
    assert crypto.configured_key_versions() == [1, 2]

    # Old ciphertext still decrypts via keyring fallback.
    assert crypto.decrypt(token_v1) == "tenant-secret"
    assert crypto.decrypt(token_v1, key_version=1) == "tenant-secret"

    # New ciphertext uses v2 and is not decryptable under v1.
    token_v2 = crypto.encrypt("tenant-secret")
    assert crypto.decrypt(token_v2) == "tenant-secret"
    with pytest.raises(Exception):
        crypto.decrypt(token_v2, key_version=1)


def test_key_version_mirrored_on_channel() -> None:
    # The Channel model carries credentials_key_version so every stored
    # credential records which key encrypted it (server default = 1).
    from app.models import Channel

    col = Channel.__table__.c.credentials_key_version
    assert col.default is not None or col.server_default is not None


# ---------------------------------------------------------------------------
# Log redaction
# ---------------------------------------------------------------------------


def test_redaction_removes_tokens_and_secrets() -> None:
    cases = [
        (
            "https://api.telegram.org/bot123456:ABC-DEF/sendMessage",
            "123456:ABC-DEF",
        ),
        ("Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", "eyJ"),
        ("bearer abcdef1234567890", "abcdef1234567890"),
        ('password="super-secret-app-password"', "super-secret-app-password"),
        ("app_secret=sk-live-0123456789abcdef", "sk-live-0123456789abcdef"),
        ("https://user:pass@internal.host/metadata", "pass"),
    ]
    for text, secret in cases:
        redacted = redact_sensitive_data(text)
        assert secret not in redacted, f"secret leaked: {text!r} -> {redacted!r}"
        assert "[REDACTED]" in redacted


def test_redaction_preserves_safe_messages() -> None:
    safe = "new_message conversation_id=5 contact_id=9 channel_id=2"
    assert redact_sensitive_data(safe) == safe


# ---------------------------------------------------------------------------
# SSRF protection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:5432/",
        "http://127.0.0.1:80/",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.1/",
        "http://172.16.0.1/",
        "http://192.168.1.1/",
        "http://[::1]/",
        "http://[fc00::1]/",
        "ftp://example.com/",
        "file:///etc/passwd",
    ],
)
def test_ssrf_blocks_private_and_non_http(url: str) -> None:
    assert is_safe_fetch_url(url) is False


@pytest.mark.parametrize(
    "url",
    [
        "https://api.telegram.org/",
        "https://graph.facebook.com/",
        "http://example.com/",
    ],
)
def test_ssrf_allows_public_https(url: str) -> None:
    assert is_safe_fetch_url(url) is True


# ---------------------------------------------------------------------------
# Upload validation
# ---------------------------------------------------------------------------


def test_validate_magic_bytes_pdf() -> None:
    assert validate_magic_bytes(b"%PDF-1.4 some content", "pdf") == "pdf"


def test_validate_magic_bytes_rejects_mismatch() -> None:
    with pytest.raises(ValueError):
        validate_magic_bytes(b"not a pdf", "pdf")


def test_validate_magic_bytes_txt() -> None:
    assert validate_magic_bytes(b"plain text", "txt") == "txt"


def test_validate_magic_bytes_size_cap() -> None:
    with pytest.raises(ValueError):
        validate_magic_bytes(b"%PDF" + b"x" * (10 * 1024 * 1024 + 1), "pdf")


def test_av_scan_hook_passes_by_default() -> None:
    # Default hook is a no-op so deployments without an AV daemon are not
    # blocked; production wires a real scanner here.
    av_scan(b"%PDF-1.4", "doc.pdf")


def test_security_headers_present() -> None:
    client = TestClient(app)
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "frame-ancestors 'none'" in resp.headers["Content-Security-Policy"]
    assert resp.headers["X-Frame-Options"] == "DENY"
