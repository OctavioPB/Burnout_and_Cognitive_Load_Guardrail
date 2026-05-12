"""Prometheus metrics middleware and /metrics endpoint.

Exposes:
  http_requests_total{method, path_template, status_code}  — Counter
  http_request_duration_seconds{method, path_template}     — Histogram (p50/p95/p99)
  http_requests_in_flight                                   — Gauge
  intervention_actions_total{action}                        — Counter (incremented by routers)
  ml_alert_fires_total                                      — Counter (incremented by AlertEngine)

The /metrics endpoint is intentionally unauthenticated so Prometheus can
scrape it from inside the cluster without needing a service account token.
In production, restrict access via network policy (scraper pod only).
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import PlainTextResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Match
from starlette.types import ASGIApp

try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )
    _PROMETHEUS_AVAILABLE = True
except ImportError:
    _PROMETHEUS_AVAILABLE = False


# ── Metric definitions ────────────────────────────────────────────────────────

if _PROMETHEUS_AVAILABLE:
    REQUEST_COUNT = Counter(
        "http_requests_total",
        "Total HTTP requests",
        ["method", "path_template", "status_code"],
    )
    REQUEST_LATENCY = Histogram(
        "http_request_duration_seconds",
        "HTTP request duration in seconds",
        ["method", "path_template"],
        buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
    )
    IN_FLIGHT = Gauge(
        "http_requests_in_flight",
        "HTTP requests currently being processed",
    )
    INTERVENTION_ACTIONS = Counter(
        "intervention_actions_total",
        "Intervention accept/dismiss actions",
        ["action"],
    )
    ALERT_FIRES = Counter(
        "ml_alert_fires_total",
        "Red-zone alerts fired by the AlertEngine",
    )


def track_intervention(action: str) -> None:
    """Increment the intervention action counter. Call from the intervention router."""
    if _PROMETHEUS_AVAILABLE:
        INTERVENTION_ACTIONS.labels(action=action).inc()


def track_alert_fire() -> None:
    """Increment the alert fire counter. Call from the AlertEngine."""
    if _PROMETHEUS_AVAILABLE:
        ALERT_FIRES.inc()


# ── Middleware ─────────────────────────────────────────────────────────────────

def _resolve_path_template(request: Request) -> str:
    """Return the matched route template (e.g. '/teams/{team_id}/history').

    Falls back to the raw path so metrics are always emitted.
    High-cardinality paths (with IDs) collapse to their template, keeping
    the label set bounded.
    """
    for route in request.app.routes:
        match, _ = route.matches(request.scope)
        if match == Match.FULL:
            return getattr(route, "path", request.url.path)
    return request.url.path


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Record Prometheus metrics for every HTTP request."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if not _PROMETHEUS_AVAILABLE:
            return await call_next(request)

        path_template = _resolve_path_template(request)

        # Skip the /metrics endpoint itself to avoid self-referential noise
        if path_template == "/metrics":
            return await call_next(request)

        IN_FLIGHT.inc()
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            IN_FLIGHT.dec()

        duration = time.perf_counter() - start
        REQUEST_COUNT.labels(
            method=request.method,
            path_template=path_template,
            status_code=str(response.status_code),
        ).inc()
        REQUEST_LATENCY.labels(
            method=request.method,
            path_template=path_template,
        ).observe(duration)

        return response


# ── /metrics endpoint handler ─────────────────────────────────────────────────

def metrics_endpoint() -> PlainTextResponse:
    """Expose all registered Prometheus metrics in text exposition format."""
    if not _PROMETHEUS_AVAILABLE:
        return PlainTextResponse(
            "prometheus_client not installed — metrics unavailable",
            status_code=503,
        )
    return PlainTextResponse(
        generate_latest().decode("utf-8"),
        media_type=CONTENT_TYPE_LATEST,
    )
