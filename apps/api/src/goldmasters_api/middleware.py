"""Per-request correlation ID, always minted server-side (D-30/D-31).

An inbound `X-Correlation-ID` header is never adopted: a client-supplied
value is unverified input, and adopting it would let a caller forge the join
key across records.
"""

from __future__ import annotations

import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from goldmasters_api.tracing import start_request_span

__all__ = ["CorrelationIdMiddleware", "current_correlation_id"]

RESPONSE_HEADER = "X-Correlation-ID"


def current_correlation_id() -> str | None:
    """Return the bound correlation ID, if any (for a later C-09 body)."""
    context = structlog.contextvars.get_contextvars()
    value = context.get("correlation_id")
    return str(value) if value is not None else None


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Mint, bind, echo and clear one correlation ID per request."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        correlation_id = str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
        span = start_request_span("http.request", correlation_id)
        try:
            response = await call_next(request)
        finally:
            span.end()
            structlog.contextvars.unbind_contextvars("correlation_id")
        response.headers[RESPONSE_HEADER] = correlation_id
        return response
