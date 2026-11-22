"""Field-level encryption with key rotation support.

``ENCRYPTION_KEY`` is the active key used to encrypt new values. Previous keys
are kept (via ``ENCRYPTION_KEYS`` JSON map of ``version -> key``) so values
encrypted under an older version can still be decrypted during rotation.

``ENCRYPTION_KEY_VERSION`` selects the active key version (default 1) and is
mirrored on ``Channel.credentials_key_version`` so every stored credential
carries the version that encrypted it.

Rotation procedure (see docs/SECURITY.md):
  1. Add the old active key to ``ENCRYPTION_KEYS`` under its version.
  2. Set ``ENCRYPTION_KEY`` to the new key and bump ``ENCRYPTION_KEY_VERSION``.
  3. Re-encrypt credentials lazily at next use (read with old key, write with new).
"""

from __future__ import annotations

import json

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


def _parse_key_map(raw: str | None) -> dict[int, str]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return {}
    out: dict[int, str] = {}
    for key, value in data.items():
        try:
            out[int(key)] = str(value)
        except (ValueError, TypeError):
            continue
    return out


def _active_version() -> int:
    try:
        return int(settings.ENCRYPTION_KEY_VERSION or 1)
    except (TypeError, ValueError):
        return 1


def _keyring() -> dict[int, Fernet]:
    """Build the active key plus all previously configured keys."""
    keys: dict[int, Fernet] = {}
    version = _active_version()
    if settings.ENCRYPTION_KEY:
        keys[version] = Fernet(settings.ENCRYPTION_KEY.encode())
    for other_version, key in _parse_key_map(settings.ENCRYPTION_KEYS).items():
        if other_version == version:
            continue
        try:
            keys[other_version] = Fernet(key.encode())
        except (TypeError, ValueError):
            continue
    return keys


_KEYRING_CACHE: dict[int, Fernet] | None = None


def _fernet(version: int | None = None) -> Fernet:
    global _KEYRING_CACHE
    if _KEYRING_CACHE is None:
        _KEYRING_CACHE = _keyring()
    ring = _KEYRING_CACHE
    target = version if version is not None else _active_version()
    f = ring.get(target)
    if f is None:
        raise RuntimeError(f"إصدار مفتاح التشفير غير متاح: {target}")
    return f


def encrypt(value: str, key_version: int | None = None) -> str:
    """Encrypt ``value`` with the active key (or the given version)."""
    version = _active_version() if key_version is None else int(key_version)
    return _fernet(version).encrypt(value.encode()).decode()


def decrypt(value: str, key_version: int | None = None) -> str:
    """Decrypt ``value``.

    When ``key_version`` is given, use that key. Otherwise try the active key
    first, then every key in the keyring so credentials encrypted under a
    rotated-out key remain readable.
    """
    if key_version is not None:
        return _fernet(int(key_version)).decrypt(value.encode()).decode()

    last_error: Exception | None = None
    for version, f in _keyring().items():
        try:
            return f.decrypt(value.encode()).decode()
        except InvalidToken as exc:
            last_error = exc
            continue
    if last_error is not None:
        raise last_error
    raise RuntimeError("مفتاح التشفير غير متاح")


def active_key_version() -> int:
    """Return the version of the key used to encrypt new values."""
    return _active_version()


def configured_key_versions() -> list[int]:
    """Return every key version currently configured for decryption."""
    return sorted(_keyring().keys())
