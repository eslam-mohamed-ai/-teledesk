"""HTTP security middleware: locked-down CORS and defensive response headers."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add defensive headers to every response.

    - Content-Security-Policy: restrictive default-src, frame-ancestors 'none'.
    - Strict-Transport-Security: enforce HTTPS for the configured TTL.
    - X-Content-Type-Options: nosniff.
    - Referrer-Policy: strict-origin-when-cross-origin.
    """

    def __init__(self, app: FastAPI) -> None:
        super().__init__(app)
        self.csp = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        is_secure = settings.APP_ENV == "production" or request.url.scheme == "https"

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = self.csp
        # frame-ancestors is enforced above via CSP; X-Frame-Options as a belt
        # and braces for older clients.
        response.headers["X-Frame-Options"] = "DENY"

        if is_secure:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        return response


def add_security_middleware(app: FastAPI) -> None:
    """Wire CORS (locked to configured origins) and security headers."""

    origins = [o.strip() for o in (settings.CORS_ALLOWED_ORIGINS or "").split(",") if o.strip()]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins if origins else [],
        allow_origin_regex=None,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["content-type", "x-csrf-token", "x-request-id", "authorization"],
        expose_headers=["x-request-id"],
        max_age=600,
    )

    app.add_middleware(SecurityHeadersMiddleware)  # type: ignore[arg-type]
