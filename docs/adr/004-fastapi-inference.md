# ADR-004 — FastAPI for the ML Inference Service

**Status:** Accepted  
**Date:** 2026-05-06  
**Deciders:** Data Science Team, Backend Team

---

## Context

The ML inference service exposes the trained Isolation Forest + LSTM ensemble to the rest of the system. It must:

- Serve real-time predictions for the dashboard (`POST /predict`).
- Support batch scoring (called by an Airflow DAG, not by end users).
- Load and manage ML model artifacts from disk.
- Meet a strict latency SLA: p99 < 200ms under 50 RPS.
- Be developed and iterated on primarily by data scientists familiar with Python.

Candidates evaluated:
1. **FastAPI** (Python, async, automatic OpenAPI)
2. **Flask** (Python, sync by default)
3. **NestJS** (TypeScript, used for the main backend API)
4. **BentoML** (ML-specific serving framework)
5. **TorchServe** (for PyTorch models specifically)

---

## Decision

Use **FastAPI + Uvicorn** for the ML inference service, deployed as a separate microservice from the main backend API.

---

## Rationale

**Why not Flask:**
Flask is synchronous by default. The inference service must handle concurrent requests without blocking on I/O (loading features, hitting Redis cache). FastAPI's native `async def` support and ASGI foundation allow true concurrency without threading complexity.

**Why not NestJS:**
The inference service is owned by the Data Science team, who work primarily in Python. Scikit-learn and PyTorch models would require serialization to cross a language boundary. Keeping the inference layer in Python eliminates this friction. The main backend API (also FastAPI) handles the data and auth concerns.

**Why not BentoML:**
BentoML is a strong choice but adds abstraction over the standard Python serving stack that would require the team to learn BentoML-specific concepts. Given the team's FastAPI familiarity and the relatively contained scope of this service (two model types, one endpoint), BentoML's benefits don't outweigh the learning cost.

**Why not TorchServe:**
Only the LSTM component is a PyTorch model; the Isolation Forest is scikit-learn. TorchServe serves PyTorch models exclusively and would require splitting the ensemble across two serving frameworks.

**Why FastAPI wins:**
- Native `async def` routes — non-blocking under load.
- Pydantic v2 integration — request/response validation is automatic and fast.
- Auto-generated OpenAPI spec — `/predict` and `/health` endpoints are self-documenting.
- First-class Python ecosystem — scikit-learn, PyTorch, NumPy all work without shims.
- Uvicorn ASGI server is production-grade and meets the p99 < 200ms target.
- Data scientists already know FastAPI from the broader team stack.

---

## Consequences

**Positive:**
- Single Python process handles both Isolation Forest and LSTM inference — the ensemble logic runs in the same memory space, no network hops between models.
- Pydantic schemas in `ml/inference/schemas.py` are shared with `api/schemas/` for request/response consistency.
- `/health` endpoint exposes model version — makes rolling deployments observable.
- FastAPI's `BackgroundTasks` can handle async logging and metric emission without blocking the response.

**Negative:**
- Python GIL limits true CPU parallelism within a single process. Under high load, multiple Uvicorn workers (managed by Gunicorn) are required.
- Model loading from disk at startup adds cold-start time. Mitigated by pre-loading models at startup via FastAPI `lifespan` event.
- No built-in model versioning — model version is tracked manually in `ml/inference/config.py` and exposed in `/health`.

**Service boundary:**
The ML inference service (`port 8001`) is an internal service only — not exposed to the public internet. The main backend API (`port 8000`) proxies prediction requests to it. This keeps authentication and authorization concerns in one place.
