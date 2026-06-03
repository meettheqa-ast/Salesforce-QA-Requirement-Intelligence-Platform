"""HTTP middleware: request-id assignment and structured-log binding.

Authentication (populating tenant/user into the request context) is handled by
the auth module's dependency, not here. This middleware only guarantees that
every request has a request_id and that structlog contextvars are bound/cleared.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.context import new_request_id, set_request_context

_HEADER_REQUEST_ID = "x-request-id"


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get(_HEADER_REQUEST_ID) or new_request_id()

        # Seed context with no tenant/user yet; auth dependency fills them in.
        set_request_context(request_id=request_id, tenant_id=None, user_id=None)
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            path=request.url.path,
            method=request.method,
        )
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.clear_contextvars()
        response.headers[_HEADER_REQUEST_ID] = request_id
        return response
