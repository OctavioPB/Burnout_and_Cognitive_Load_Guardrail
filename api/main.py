"""Backend API — Team Resilience Dashboard.

Serves dashboard, team, and alert data to the React frontend.
In staging this uses seeded mock data (api.services.mock_data).

Ports:
  - This service: 8000
  - ML Inference:  8001

CORS is configured for the Vite dev server (localhost:5173) and any
staging origin listed in ALLOWED_ORIGINS.
"""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routers import alerts, dashboard, teams

logger = logging.getLogger(__name__)

_ALLOWED_ORIGINS: list[str] = [
    "http://localhost:5173",   # Vite dev
    "http://localhost:4173",   # Vite preview
    *(os.getenv("ALLOWED_ORIGINS", "").split(",") if os.getenv("ALLOWED_ORIGINS") else []),
]

app = FastAPI(
    title="Burnout Guardrail — Backend API",
    version="0.1.0",
    description="Dashboard data API for the Team Resilience Dashboard.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def audit_log(request: Request, call_next):  # type: ignore[no-untyped-def]
    """Log every request that reads resilience data with actor identity."""
    response = await call_next(request)
    actor = request.headers.get("X-User-Id", "anonymous")
    logger.info(
        "audit actor=%s method=%s path=%s status=%d",
        actor, request.method, request.url.path, response.status_code,
    )
    return response


@app.get("/health", tags=["ops"])
def health() -> dict:
    return {"status": "ok", "version": app.version}


@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled error on %s: %s", request.url.path, exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(dashboard.router)
app.include_router(teams.router)
app.include_router(alerts.router)
