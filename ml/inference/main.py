"""FastAPI inference service for the Burnout & Cognitive Load Guardrail.

Endpoints
---------
POST /predict        Single-team prediction (AFS + Resilience Zone)
POST /predict/batch  Up to 500 teams in one call
GET  /health         Liveness + model version

Run locally
-----------
    uvicorn ml.inference.main:app --reload --port 8001

Privacy / compliance
--------------------
Every call to /predict is audit-logged with the requesting actor's identity
(X-Actor-Id header, defaulting to "anonymous").  See CLAUDE.md §Privacy.
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI, Header, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ml.inference.alert_engine import Alert, AlertEngine
from ml.inference.config import MODEL_VERSION
from ml.inference.model_loader import ModelBundle, load_models
from ml.inference.notifications import SendGridNotifier, SlackNotifier
from ml.inference.predictor import BurnoutPredictor
from ml.inference.schemas import (
    BatchPredictRequest,
    BatchPredictResponse,
    HealthResponse,
    Intervention,
    PredictRequest,
    PredictResponse,
)

logger = logging.getLogger(__name__)

# ── Application state ─────────────────────────────────────────────────────────

_bundle: ModelBundle | None = None
_predictor: BurnoutPredictor | None = None
_alert_engine: AlertEngine = AlertEngine()
_slack: SlackNotifier = SlackNotifier()
_sendgrid: SendGridNotifier = SendGridNotifier()


# ── Lifespan ──────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Load model artifacts once at startup; clean up on shutdown."""
    global _bundle, _predictor
    logger.info("Loading model bundle...")
    _bundle = load_models()
    _predictor = BurnoutPredictor(_bundle)
    logger.info("Inference service ready — model_version=%s", _bundle.model_version)
    yield
    logger.info("Inference service shutting down")


# ── App ───────────────────────────────────────────────────────────────────────


app = FastAPI(
    title="Burnout & Cognitive Load Guardrail — Inference API",
    version=MODEL_VERSION,
    description="Real-time team burnout risk scoring.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ── Middleware: audit logging ─────────────────────────────────────────────────


@app.middleware("http")
async def audit_log(request: Request, call_next: Any) -> Any:
    """Log every request with actor identity and response time."""
    actor = request.headers.get("X-Actor-Id", "anonymous")
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "AUDIT path=%s method=%s actor=%s status=%d elapsed_ms=%.1f",
        request.url.path,
        request.method,
        actor,
        response.status_code,
        elapsed_ms,
    )
    return response


# ── Helper ────────────────────────────────────────────────────────────────────


async def _dispatch_alert(alert: Alert) -> None:
    """Fire Slack + SendGrid notifications in parallel (best-effort)."""
    import asyncio

    results = await asyncio.gather(
        _slack.send(alert),
        _sendgrid.send(alert),
        return_exceptions=True,
    )
    logger.info("Alert dispatch results: slack=%s sendgrid=%s", results[0], results[1])


def _build_response(req: PredictRequest, result: Any) -> PredictResponse:
    from ml.inference.interventions import suggest_interventions

    features = req.current_features()
    interventions = (
        suggest_interventions(features) if result.resilience_zone == "red" else []
    )
    return PredictResponse(
        team_id=req.team_id,
        workspace_id=req.workspace_id,
        date_utc=req.date_utc,
        afs=result.afs,
        resilience_zone=result.resilience_zone,
        zone_label=result.zone_label,
        probabilities=result.probabilities,
        interventions=[
            Intervention(id=i.id, title=i.title, description=i.description)
            for i in interventions
        ],
        cold_start=result.cold_start,
        model_version=result.model_version,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────


@app.get("/health", response_model=HealthResponse, tags=["ops"])
async def health() -> HealthResponse:
    """Liveness check and model component status."""
    if _bundle is None:
        return HealthResponse(
            status="degraded",
            model_version=MODEL_VERSION,
            models_loaded={},
            message="Models not yet loaded",
        )
    loaded = _bundle.status()
    all_ok = loaded.get("isolation_forest") and loaded.get("baseline")
    return HealthResponse(
        status="ok" if all_ok else "degraded",
        model_version=_bundle.model_version,
        models_loaded=loaded,
    )


@app.post(
    "/predict",
    response_model=PredictResponse,
    status_code=status.HTTP_200_OK,
    tags=["inference"],
)
async def predict(
    req: PredictRequest,
    x_actor_id: str = Header(default="anonymous"),
) -> PredictResponse:
    """Predict the resilience zone for a single team-day.

    Accepts the current day's features and an optional 13-day history for LSTM.
    Returns AFS score, zone, class probabilities, and suggested interventions
    (populated only when zone = "red").
    """
    if _predictor is None:
        return JSONResponse(  # type: ignore[return-value]
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Model not loaded"},
        )

    history_dicts = [h.model_dump() for h in req.history] if req.history else None
    result = _predictor.predict(req.current_features(), history_dicts)
    response = _build_response(req, result)

    # Alert engine + async notifications
    alert = _alert_engine.process(
        team_id=req.team_id,
        workspace_id=req.workspace_id,
        date_utc=req.date_utc,
        resilience_zone=result.resilience_zone,
        features=req.current_features(),
    )
    if alert is not None:
        await _dispatch_alert(alert)

    return response


@app.post(
    "/predict/batch",
    response_model=BatchPredictResponse,
    status_code=status.HTTP_200_OK,
    tags=["inference"],
)
async def predict_batch(
    req: BatchPredictRequest,
    x_actor_id: str = Header(default="anonymous"),
) -> BatchPredictResponse:
    """Score up to 500 teams in a single request.

    Each item is processed independently; a failure in one item does not
    block the others (failed items are omitted from the results).
    """
    if _predictor is None:
        return JSONResponse(  # type: ignore[return-value]
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": "Model not loaded"},
        )

    results: list[PredictResponse] = []
    for item in req.items:
        try:
            history_dicts = [h.model_dump() for h in item.history] if item.history else None
            result = _predictor.predict(item.current_features(), history_dicts)
            response = _build_response(item, result)
            results.append(response)

            alert = _alert_engine.process(
                team_id=item.team_id,
                workspace_id=item.workspace_id,
                date_utc=item.date_utc,
                resilience_zone=result.resilience_zone,
                features=item.current_features(),
            )
            if alert is not None:
                await _dispatch_alert(alert)

        except Exception as exc:  # noqa: BLE001
            logger.error("Batch item team=%s failed: %s", item.team_id, exc)

    return BatchPredictResponse(
        results=results,
        n_items=len(results),
        model_version=MODEL_VERSION,
    )
