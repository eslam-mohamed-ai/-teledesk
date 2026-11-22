"""Static asset serving with SPA history fallback.

``StaticFiles`` returns 404 for unknown paths, which breaks client-side routes
such as ``/inbox`` on a hard refresh. ``SPAFiles`` serves ``index.html`` for
any non-API path that does not map to a real file, so the React router can
take over. API 404s are preserved so clients see real JSON errors.
"""

from __future__ import annotations

from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles


class SPAFiles(StaticFiles):
    async def get_response(self, path: str, scope):  # type: ignore[override]
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            is_api = path.startswith("api/") or path.startswith("api")
            is_file = "." in path.rsplit("/", 1)[-1]
            if exc.status_code == 404 and not is_api and not is_file:
                return await super().get_response("index.html", scope)
            raise