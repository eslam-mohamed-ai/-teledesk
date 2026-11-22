from uuid import UUID, uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.request_context import request_id_context


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        incoming_id = request.headers.get("x-request-id")
        try:
            request_id = str(UUID(incoming_id)) if incoming_id else str(uuid4())
        except (ValueError, AttributeError):
            request_id = str(uuid4())

        context_token = request_id_context.set(request_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            request_id_context.reset(context_token)
