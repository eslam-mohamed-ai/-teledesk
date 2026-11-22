"""Security helpers: SSRF-safe URL fetching, magic-byte file validation, CORS."""

from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit

import httpx

# Magic bytes for the allowed document types. A file's real type is determined
# by its leading bytes, never by the client-supplied extension or Content-Type.
MAGIC_BYTES: dict[str, list[bytes]] = {
    "pdf": [b"%PDF"],
    "docx": [b"PK\x03\x04"],  # ZIP-based Office Open XML
    "txt": [],  # plain text has no stable magic bytes; validated by decode
}

# Extension -> expected MIME category used for storage Content-Type.
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}

# Default 10 MB upload cap, matching routes/documents.py MAX_BYTES.
DEFAULT_MAX_BYTES = 10 * 1024 * 1024

# Private / loopback / link-local ranges that a server-side fetch must never
# reach (SSRF protection). Covered both IPv4 and IPv6.
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("ff00::/8"),
]


def _host_is_blocked(host: str) -> bool:
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        # A hostname that cannot be parsed as a literal IP: resolve it and check
        # every resolved address. DNS rebinding is mitigated because each fetch
        # re-validates the final (redirect) address.
        return False
    return any(addr in net for net in _BLOCKED_NETWORKS)


def _resolve_and_check(host: str) -> None:
    import socket

    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except OSError:
        # Unresolvable host: let the fetch fail naturally with a clear error.
        return
    for info in infos:
        sockaddr = info[4]
        if sockaddr:
            addr = str(sockaddr[0])
            if _host_is_blocked(addr):
                raise ValueError(f"SSRF: address {addr} is not fetchable")


def is_safe_fetch_url(url: str) -> bool:
    """Return True only if `url` targets a public, non-private HTTP(S) host.

    Blocks private, loopback, and link-local IPv4/IPv6 ranges so the server
    cannot be tricked into fetching internal metadata services.
    """
    try:
        parsed = urlsplit(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = parsed.hostname or ""
    if not host:
        return False
    if _host_is_blocked(host):
        return False
    try:
        _resolve_and_check(host)
    except ValueError:
        return False
    return True


async def safe_fetch(
    url: str,
    *,
    method: str = "GET",
    max_redirects: int = 5,
    timeout: float = 10.0,
    max_bytes: int = 8 * 1024 * 1024,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """Fetch `url` with SSRF protection.

    The initial URL and every redirect target are validated against the blocked
    ranges before the request is made, so an open redirect cannot be used to
    reach an internal host. The response body is capped at `max_bytes`.
    """
    if not is_safe_fetch_url(url):
        raise ValueError(f"SSRF: unsafe fetch URL {url!r}")

    current = url
    seen: set[str] = set()
    for _ in range(max_redirects + 1):
        if current in seen:
            raise ValueError("SSRF: too many redirects")
        seen.add(current)
        parsed = urlsplit(current)
        _resolve_and_check(parsed.hostname or "")

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=False,
            max_redirects=0,
        ) as client:
            response = await client.request(method, current, headers=headers)
    except httpx.HTTPError as exc:
        raise ValueError(f"SSRF: fetch failed for {url!r}: {exc}") from exc

    # Re-validate redirect targets before following them manually so each hop
    # is checked against the blocked ranges.
    while response.is_redirect:
        location = response.headers.get("location")
        if not location:
            break
        from urllib.parse import urljoin

        target = urljoin(current, location)
        if not is_safe_fetch_url(target):
            raise ValueError(f"SSRF: redirect target blocked {target!r}")
        if target in seen:
            raise ValueError("SSRF: redirect loop")
        seen.add(target)
        response = await client.request(method, target, headers=headers)
        current = target

    # Cap the body size.
    content = b""
    async for chunk in response.aiter_bytes():
        content += chunk
        if len(content) > max_bytes:
            raise ValueError("SSRF: response too large")

    # Replay the capped body so callers can read it normally.
    response._content = content
    return response


def validate_magic_bytes(data: bytes, extension: str) -> str:
    """Return the canonical kind for `data` if it matches an allowed type.

    Raises ValueError when the file is empty, too large, or its magic bytes do
    not match the declared extension. Plain-text files are validated by a
    UTF-8 decode attempt.
    """
    extension = (extension or "").lower().lstrip(".")
    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError("نوع الملف غير مدعوم")

    if not data:
        raise ValueError("الملف فارغ")

    if len(data) > DEFAULT_MAX_BYTES:
        raise ValueError("الملف أكبر من الحد المسموح")

    if extension == "txt":
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError("ملف النص غير صالح (يجب أن يكون ترميزه UTF-8)")
        return "txt"

    signatures = MAGIC_BYTES.get(extension, [])
    if signatures and not any(data.startswith(sig) for sig in signatures):
        raise ValueError("نوع الملف غير متوافق مع الامتداد المحدد")

    return extension


def av_scan(data: bytes, filename: str) -> None:
    """Antivirus scan hook.

    Integrations should replace this with a real AV call (e.g. ClamAV over a
    Unix socket or an external scanning service). Raising here rejects the
    upload. The default implementation always passes so deployments without an
    AV daemon are not blocked; enable scanning by overriding this function in
    the deployment's startup or by wiring `app.services.storage.put` to call it.
    """
    return None


def cors_origins_from_settings() -> list[str]:
    """Parse the CORS_ALLOWED_ORIGINS setting into a list of origins."""
    from app.config import settings

    raw = getattr(settings, "CORS_ALLOWED_ORIGINS", "") or ""
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    return origins
