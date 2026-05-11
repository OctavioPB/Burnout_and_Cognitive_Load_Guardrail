"""Structured JSON logging middleware using structlog.

Every request receives a unique correlation ID (UUID4).  If the caller
already set an ``X-Request-Id`` header that value is used instead, making
distributed tracing across services possible.

The correlation ID is injected into every structlog log record via a
context variable so it appears in all log lines emitted during the request
lifetime, even those deep inside business-logic functions.

Output format (JSON, one line per record):
  {"event": "...", "request_id": "...", "method": "GET", "path": "/...",
   "status_code": 200, "duration_ms": 12.4, "timestamp": "..."}
"""

from __future__ import annotations

import time
import uuid
from contextvars import ContextVar
from typing import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# ── Context variable — holds request_id for the current async task ────────────

_request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    """Return the correlation ID bound to the current async context."""
    return _request_id_ctx.get()


# ── structlog configuration ───────────────────────────────────────────────────

def configure_structlog() -> None:
    """Configure structlog with JSON rendering.

    Call once at application startup.  Idempotent — safe to call multiple times.
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.ExceptionRenderer(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


# ── Middleware ─────────────────────────────────────────────────────────────────

class CorrelationLoggingMiddleware(BaseHTTPMiddleware):
    """Attach a correlation ID to every request and emit structured access logs."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._logger = structlog.get_logger()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:  # type: ignore[override]
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        _request_id_ctx.set(request_id)

        # Bind request_id to structlog context for this async scope
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        actor_id = request.headers.get("X-User-Id", "anonymous")
        start = time.perf_counter()

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        self._logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            actor_id=actor_id,
        )

        # Echo the correlation ID back to the caller
        response.headers["X-Request-Id"] = request_id
        return response
