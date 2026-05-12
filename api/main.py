"""Backend API — Team Resilience Dashboard.

Serves dashboard, team, alert, intervention, and audit data to the React frontend.
In staging this uses seeded mock data (api.services.mock_data).

Ports:
  - This service: 8000
  - ML Inference:  8001

CORS is configured for the Vite dev server (localhost:5173) and any
staging origin listed in ALLOWED_ORIGINS.

Auth contract (staging):
  All authenticated requests send X-User-Id, X-User-Name, X-User-Role,
  and optionally X-User-Team-Id headers.  In production these are derived
  from a verified JWT issued by Okta/Auth0.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from api.middleware.logging import CorrelationLoggingMiddleware, configure_structlog
from api.middleware.metrics import PrometheusMiddleware, metrics_endpoint
from api.middleware.security import SecurityHeadersMiddleware
from api.routers import alerts, audit, dashboard, interventions, teams

logger = logging.getLogger(__name__)
configure_structlog()

_ALLOWED_ORIGINS: list[str] = [
    "http://localhost:5173",
    "http://localhost:4173",
    *(os.getenv("ALLOWED_ORIGINS", "").split(",") if os.getenv("ALLOWED_ORIGINS") else []),
]

# Read-path audit: map URL prefixes to audit action labels
_READ_AUDIT: dict[str, str] = {
    "/dashboard": "view_dashboard",
    "/alerts":    "view_alerts",
    "/audit":     "view_audit",
}

app = FastAPI(
    title="Burnout Guardrail — Backend API",
    version="0.2.0",
    description="Dashboard data API for the Team Resilience Dashboard.",
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(PrometheusMiddleware)
app.add_middleware(CorrelationLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def audit_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Record read events for data privacy compliance.

    Only GET requests from authenticated actors are written to the audit log.
    POST requests (intervention apply/dismiss) record their own audit entries
    inside the router handler.
    """
    response = await call_next(request)

    if request.method == "GET" and response.status_code < 400:
        actor_id   = request.headers.get("X-User-Id",   "anonymous")
        actor_name = request.headers.get("X-User-Name",  "Anonymous")
        actor_role = request.headers.get("X-User-Role",  "viewer")
        path       = request.url.path

        if actor_id != "anonymous":
            from api.services.intervention_store import audit_store

            # Determine action from path
            action = "view_team" if path.startswith("/teams/") else None
            for prefix, label in _READ_AUDIT.items():
                if path.startswith(prefix):
                    action = label
                    break

            if action:
                resource = (
                    path.split("/")[2]
                    if path.startswith("/teams/")
                    else path.lstrip("/").split("/")[0]
                )
                audit_store.record(
                    actor_id=actor_id,
                    actor_name=actor_name,
                    actor_role=actor_role,
                    action=action,  # type: ignore[arg-type]
                    resource=resource,
                )

        logger.info(
            "audit actor=%s role=%s method=%s path=%s status=%d",
            actor_id, actor_role, request.method, path, response.status_code,
        )

    return response


@app.get("/health", tags=["ops"])
def health() -> dict[str, str]:
    return {"status": "ok", "version": app.version}


@app.get("/metrics", tags=["ops"], include_in_schema=False)
def get_metrics() -> Response:
    """Prometheus metrics scrape endpoint (cluster-internal only)."""
    return metrics_endpoint()


@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled error on %s: %s", request.url.path, exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(dashboard.router)
app.include_router(teams.router)
app.include_router(alerts.router)
app.include_router(interventions.router)
app.include_router(audit.router)
