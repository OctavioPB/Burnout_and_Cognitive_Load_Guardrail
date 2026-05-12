# Burnout & Cognitive Load Guardrail

> **Real-time digital exhaust monitoring that predicts team burnout before it happens.**

The Burnout & Cognitive Load Guardrail ingests collaboration *metadata* (calendar density, after-hours activity, context-switching frequency) from your team's existing tools, runs it through an ML anomaly detection pipeline, and surfaces a **Team Resilience Dashboard** for HR teams. No message content is ever read. All scoring happens at the team level — individual scores are never surfaced.

---

## How it works

```
Slack / Google Calendar / Jira / GitHub
           │  (metadata only — no content)
           ▼
  ┌─────────────────────────────┐
  │   Apache Kafka              │  Digital exhaust event stream
  └──────────┬──────────────────┘
             │
             ▼
  ┌─────────────────────────────┐
  │   Airflow ETL Pipeline      │  Feature engineering & aggregation
  └──────────┬──────────────────┘
             │  team-level daily features
             ▼
  ┌─────────────────────────────┐
  │   ML Inference (FastAPI)    │  Isolation Forest + LSTM → AFS score
  └──────────┬──────────────────┘
             │
             ▼
  ┌─────────────────────────────┐
  │   Backend API (FastAPI)     │  REST API with RBAC
  └──────────┬──────────────────┘
             │
             ▼
  ┌─────────────────────────────┐
  │   React Dashboard           │  HR Admin, Team Manager, Viewer roles
  └─────────────────────────────┘
```

The core output metric is the **Attention Fragmentation Score (AFS)** — a 0–100 index of how fragmented a team's focused work time is. Higher means more fragmented (worse).

| Zone | AFS | Meaning |
|------|-----|---------|
| 🟢 Green  | 0–39  | Healthy — no action needed |
| 🟡 Yellow | 40–69 | Monitor — watch the trend |
| 🔴 Red    | 70–100 | Intervene — sustained high fragmentation |

When a team hits Red for 3+ consecutive days, an alert fires and HR is notified with suggested interventions: Meeting-Free Friday, Async-First Week, Load Redistribution, or Deep Work Blocks. HR can accept, customise, or dismiss each suggestion directly from the dashboard. Accepted interventions dispatch automatically to Google Calendar, Jira, or Slack.

---

## Tech stack

| Layer | Technology |
|---|---|
| Event streaming | Apache Kafka (Confluent) + Avro + Schema Registry |
| Orchestration | Apache Airflow |
| ML | scikit-learn (Isolation Forest) + PyTorch (LSTM) |
| Inference API | FastAPI + Uvicorn (port 8001) |
| Backend API | FastAPI + Uvicorn (port 8000) |
| Frontend | React 18 + TypeScript + Recharts + Zustand + React Query |
| Auth | OAuth 2.0 / JWT (Auth0) — header-based in staging |
| Infrastructure | Docker Compose (local) · Terraform + EKS (production) |
| Observability | structlog JSON logging · Prometheus metrics · Grafana dashboards |

---

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | ≥ 3.11 | `python --version` |
| Node.js | ≥ 18 | `node --version` |
| Docker + Docker Compose | any recent | `docker compose version` |
| Git | any | — |

Optional (for production connectors):
- Google Cloud service account with Calendar API + Admin SDK
- Jira API token
- Slack bot token
- GitHub App credentials

---

## Quick start — 5 minutes to running dashboard

### 1. Clone and configure

```bash
git clone https://github.com/your-org/burnout-guardrail.git
cd burnout-guardrail

# Copy and review the environment template
cp .env.example .env
```

The defaults in `.env.example` work for local development without any external service credentials. The dashboard runs entirely on seeded mock data out of the box.

### 2. Start infrastructure

```bash
docker compose up -d
```

This starts Kafka, Zookeeper, Schema Registry, Postgres, and Redis. **Docker Compose runs infrastructure only — the Python API and React dashboard are started separately in steps 4 and 5.**

Wait ~60 seconds for all health checks to pass:

```bash
docker compose ps   # all services should show "healthy"
```

> **Windows note:** Port 9101 (Kafka JMX) is not exposed on the host to avoid conflicts with Docker's internal port reservations. JMX remains active inside the container if needed by a monitoring sidecar.

### 3. Install Python dependencies

```bash
pip install -e ".[dev]"
```

### 4. Start the backend API

Open a dedicated terminal and run:

```bash
uvicorn api.main:app --reload --port 8000
```

Keep this terminal open — the server runs in the foreground. Verify it is up in a second terminal:

```bash
# bash / macOS / Linux
curl http://localhost:8000/health

# PowerShell (Windows) — curl is an alias for Invoke-WebRequest and behaves differently
Invoke-RestMethod http://localhost:8000/health
```

Expected response: `{"status": "ok", "version": "0.2.0"}`

Interactive API docs are available at **http://localhost:8000/docs**.

### 5. Start the dashboard

```bash
cd dashboard
npm install
npm run dev
```

Open **http://localhost:5173** in your browser.

### 6. Log in

Three demo users are pre-seeded. Select one on the login page:

| Role | What they see |
|---|---|
| **HR Admin** | Full dashboard, all teams, alert feed, interventions, audit log |
| **Team Manager** | Their own team's drill-down only |
| **Viewer** | Dashboard and alert feed, read-only |

No password required in staging mode.

---

## Full development setup

### Python project

```bash
# Install all extras
pip install -e ".[dev,ml,pipeline]"

# Verify the setup
python -c "from api.main import app; print('API OK')"

# Run linter
ruff check .

# Run type checker
mypy api/ ml/ ingestion/ pipeline/
```

### Frontend

```bash
cd dashboard

# Install dependencies
npm install

# Type-check only (no output = no errors)
npm run type-check

# Development server with hot reload
npm run dev          # → http://localhost:5173

# Production build
npm run build

# Preview the production build
npm run preview      # → http://localhost:4173
```

### ML inference service (optional for full pipeline)

The dashboard API serves seeded mock data by default. To run the real ML inference service:

```bash
# Requires a trained model artifact in ml/models/
uvicorn ml.inference.main:app --reload --port 8001
```

---

## Running services — ports reference

| Service | Command | Port |
|---|---|---|
| Backend API | `uvicorn api.main:app --reload` | 8000 |
| ML Inference API | `uvicorn ml.inference.main:app --reload` | 8001 |
| React Dashboard | `npm run dev --prefix dashboard` | 5173 |
| Kafka | `docker compose up kafka` | 9092 |
| Schema Registry | `docker compose up schema-registry` | 8081 |
| Postgres | `docker compose up postgres` | 5432 |
| Redis | `docker compose up redis` | 6379 |
| Prometheus metrics | auto-exposed by API | `/metrics` on port 8000 |

---

## Environment variables

All variables are documented in [.env.example](.env.example). Copy it to `.env` — it is git-ignored.

**Required for full functionality:**

| Variable | Description |
|---|---|
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka broker address (default: `localhost:9092`) |
| `DATABASE_URL` | Async Postgres connection string |
| `REDIS_URL` | Redis connection string |
| `ENVIRONMENT` | `development` or `production` |

**Required only for external integrations (optional in staging):**

| Variable | Integration |
|---|---|
| `SLACK_BOT_TOKEN` | Slack connector + Async-First Week intervention |
| `GOOGLE_SERVICE_ACCOUNT_PATH` | Google Calendar connector + Meeting-Free Friday |
| `JIRA_BASE_URL` / `JIRA_API_TOKEN` | Jira connector + Load Redistribution intervention |
| `GITHUB_APP_ID` / `GITHUB_PRIVATE_KEY_PATH` | GitHub connector (Sprint Health Index) |
| `SENDGRID_API_KEY` | Email alert notifications |

If integration credentials are absent, the system falls back to a simulated response — all dashboard flows remain fully testable without real API keys.

---

## Running tests

```bash
# Full test suite with coverage (≥80% required)
pytest tests/unit/

# Specific test module
pytest tests/unit/api/test_routes.py -v

# ML module only
pytest tests/unit/ml/ -v

# Skip coverage for faster iteration
pytest tests/unit/ --no-cov

# Frontend type-check
cd dashboard && npx tsc --noEmit

# Frontend tests
cd dashboard && npm test
```

Coverage report is printed to the terminal after each run. The minimum threshold is **80%**; the suite currently achieves **~89%**.

---

## Load testing

The Locust load test simulates three user populations (HR Admin, Viewer, Team Manager) against the live API:

```bash
# Install Locust (included in dev dependencies)
pip install locust

# Run headless smoke test — 10 users for 30s
locust -f tests/load/locustfile.py \
       --host http://localhost:8000 \
       --users 10 --spawn-rate 2 --run-time 30s --headless

# Full load test — open browser UI at http://localhost:8089
locust -f tests/load/locustfile.py --host http://localhost:8000
```

Target thresholds: **200 RPS sustained, p99 < 300ms**.

---

## Project structure

```
burnout-guardrail/
│
├── api/                        # Backend REST API (FastAPI)
│   ├── main.py                 # App factory, middleware wiring
│   ├── dependencies.py         # RBAC dependency functions
│   ├── middleware/
│   │   ├── logging.py          # structlog JSON + correlation IDs
│   │   ├── metrics.py          # Prometheus metrics middleware + /metrics
│   │   └── security.py         # OWASP security headers
│   ├── routers/                # Endpoint definitions (dashboard, teams, alerts, interventions, audit)
│   ├── schemas/                # Pydantic response models
│   └── services/
│       ├── mock_data.py        # Seeded deterministic mock data (12 teams, 30-day histories)
│       ├── intervention_store.py  # In-memory intervention + audit stores
│       └── integrations/       # Calendar, Jira, Slack adapters (staging + production paths)
│
├── ml/                         # Machine learning
│   ├── training/               # Feature engineering, Isolation Forest, LSTM, ensemble
│   ├── inference/              # FastAPI inference service, AlertEngine, intervention rules
│   └── evaluation/             # Metrics, drift detection, evaluation scripts
│
├── ingestion/                  # Kafka producers & consumers
│   ├── connectors/             # Slack, Google Calendar, Jira, GitHub adapters
│   ├── schemas/                # Avro event schemas
│   └── config/                 # Kafka topic configuration
│
├── pipeline/                   # Airflow ETL
│   ├── transforms/             # Feature aggregation (calendar density, after-hours, context-switch, sprint health)
│   └── quality/                # Data quality checks
│
├── dashboard/                  # React + TypeScript frontend
│   ├── src/
│   │   ├── pages/              # LoginPage, DashboardHome, TeamDrillDown, AlertsPage, AuditLogPage
│   │   ├── components/         # Nav, ZoneBadge, ResilienceTrendChart, DepartmentHeatmap,
│   │   │                       #   InterventionPanel, EfficacyChart, LoadingSkeleton, ...
│   │   ├── hooks/              # useDashboard (React Query hooks for all endpoints)
│   │   ├── stores/             # authStore (Zustand + localStorage persistence)
│   │   ├── types/              # TypeScript interfaces matching API schemas
│   │   └── lib/
│   │       └── apiClient.ts    # Axios instance with auth header interceptor
│   └── package.json
│
├── infra/
│   ├── terraform/              # VPC, EKS, Kafka Terraform modules
│   ├── nginx/nginx.conf        # Reverse-proxy, TLS, caching, rate limiting
│   └── monitoring/
│       ├── prometheus/alerts.yaml  # Alerting rules (API, Kafka, ML, interventions)
│       └── grafana/dashboard.json  # 8-panel service health dashboard
│
├── tests/
│   ├── unit/
│   │   ├── api/                # Route tests (TestClient), RBAC tests, store tests, middleware tests
│   │   ├── ml/                 # AlertEngine, notifications, predictor, model training
│   │   ├── ingestion/          # Connector tests
│   │   └── pipeline/           # Transform function tests
│   ├── integration/            # Kafka round-trip tests (requires running broker)
│   └── load/locustfile.py      # Locust load test (3 user populations)
│
├── docs/
│   ├── adr/                    # Architecture Decision Records
│   ├── user-guides/            # HR Admin guide, Onboarding checklist
│   ├── runbooks/               # On-call runbook, Secrets rotation
│   ├── security/               # OWASP Top 10 checklist
│   └── legal/                  # DPA template
│
├── docker-compose.yml          # Local: Kafka, Postgres, Redis, Schema Registry
├── pyproject.toml              # Python dependencies, ruff, mypy, pytest config
├── .env.example                # All required environment variable keys
├── BRAND.md                    # UI/UX design system (colours, typography, components)
└── PLAN.md                     # Sprint roadmap and acceptance criteria
```

---

## API reference

All endpoints are served at `http://localhost:8000`. Interactive docs: `http://localhost:8000/docs`.

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | None | Service health check |
| GET | `/metrics` | None (cluster-internal) | Prometheus metrics |
| GET | `/dashboard/summary` | None | Org-wide zone distribution |
| GET | `/dashboard/teams` | None | All team cards, sorted by AFS |
| GET | `/teams/{team_id}/history` | Required | 30-day AFS history + features |
| GET | `/alerts` | None | Red Zone alerts, newest first |
| GET | `/interventions/{team_id}` | Required | Intervention records for a team |
| POST | `/interventions/{team_id}/apply` | Required | Accept and execute intervention |
| POST | `/interventions/{team_id}/dismiss` | Required | Dismiss intervention |
| GET | `/interventions/{team_id}/efficacy/{id}` | Required | Before/after AFS view |
| GET | `/audit` | HR Admin only | Full audit log |

**Staging auth headers** (sent automatically by the dashboard):

```
X-User-Id:      <user-id>
X-User-Name:    <display-name>
X-User-Role:    hr_admin | team_manager | viewer
X-User-Team-Id: <team-id>   (team_manager only)
```

---

## Privacy & compliance

The system is designed around four constraints that are enforced in code, not just policy:

1. **No content capture** — ingestion connectors extract timestamps, durations, and counts only. Message and document bodies are explicitly discarded.
2. **Team-level aggregation only** — individual user data is aggregated into team units before any score is computed. No individual AFS is stored or displayed.
3. **Consent-first** — data collection is disabled by default and must be explicitly enabled per workspace.
4. **Audit logging** — every dashboard read and intervention action is logged with actor identity and timestamp, accessible to HR Admins via the Audit Log page.

Full details in [docs/legal/dpa-template.md](docs/legal/dpa-template.md) and [docs/security/owasp-checklist.md](docs/security/owasp-checklist.md).

---

## Code quality

All quality gates pass on `main`. Run them before opening a PR:

```bash
# Python — lint (0 errors)
ruff check .

# Python — types (0 errors across 74 source files)
mypy api/ ml/ ingestion/ pipeline/

# Python — tests (≥80% coverage required, currently ~89%)
pytest tests/unit/

# TypeScript — types (0 errors)
cd dashboard && npm run type-check
```

**mypy configuration notes** (see `pyproject.toml`):
- `ignore_missing_imports = true` is set for `fastavro`, `confluent_kafka`, `joblib`, `sklearn`, and `respx` — none of these ship typed stubs.
- `ignore_errors = true` is set for `airflow.*` and `pipeline.dags.*` / `pipeline.operators.*` — Airflow has no public stubs and cannot be typed without vendoring the entire Airflow package.
- ML files (`ml/**`) suppress `N803`/`N806` (uppercase `X`, `X_train`, etc.) — standard numpy/sklearn convention.

---

## Troubleshooting

### Kafka is unhealthy — `UnknownHostException: zookeeper`

**Symptom:** `docker compose up -d` exits with `container kafka is unhealthy`. Kafka logs show `java.net.UnknownHostException: zookeeper`.

**Cause:** When Docker Desktop restarts between sessions and you run `docker compose up -d`, Docker restarts existing containers instead of recreating them. Docker's embedded DNS loses its hostname registrations during the restart, so Kafka can't resolve the `zookeeper` hostname even though the Zookeeper container is running and shows as healthy (its healthcheck tests `localhost:2181` inside its own container, not cross-container DNS).

**Fix:** Always use a full down + up after a Docker Desktop restart:

```bash
docker compose down
docker compose up -d
```

`docker compose down` removes containers and the network, then `up -d` recreates everything fresh with proper DNS registration. Never use `docker compose up -d` alone after Docker Desktop has been restarted — it will restart stale containers that may be missing from the network.

---

### `docker compose up -d` fails with "port 9101 not available"

Docker's internal backend process (`com.docker.backend`) sometimes holds port 9101 across container restarts on Windows. The Kafka JMX port is intentionally **not** exposed on the host (see `docker-compose.yml`) — it remains active inside the container network only. If you see this error after upgrading Docker Desktop, a full Docker Desktop restart (not just container restart) clears the reservation.

### `curl http://localhost:8000/health` — "Unable to connect"

`docker compose up -d` starts **infrastructure only** (Kafka, Postgres, Redis, Schema Registry). The FastAPI backend is a separate process — start it with:

```bash
uvicorn api.main:app --reload --port 8000
```

### `curl` in PowerShell returns a credential prompt or `ParameterBindingException`

In PowerShell, `curl` is an alias for `Invoke-WebRequest`, not `curl.exe`. Use `Invoke-RestMethod` instead for clean JSON output:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Or call `curl.exe` explicitly:

```powershell
curl.exe http://localhost:8000/health
```

### `mypy` reports errors in `ingestion/` or `pipeline/`

Run mypy against **all four** directories — `api/ ml/` alone misses the Kafka and Airflow layers:

```bash
mypy api/ ml/ ingestion/ pipeline/
```

### `npm run type-check` vs `npx tsc --noEmit`

They are equivalent. `npm run type-check` is the canonical project alias defined in `dashboard/package.json` and should be preferred in CI to pick up any future compiler flag changes automatically.

---

## Contributing

```bash
# Before committing — all must exit with 0 errors
ruff check . --fix                        # lint + auto-fix
ruff format .                             # format
mypy api/ ml/ ingestion/ pipeline/        # type check (all layers)
pytest tests/unit/                        # tests + coverage
cd dashboard && npm run type-check        # frontend types
```

Code style is enforced by `ruff` (replaces black + flake8). Type hints are mandatory on all public functions. See [CLAUDE.md](CLAUDE.md) for full coding conventions.

---

*OPB AI Mastery Lab · From pipeline to decision. — Octavio Pérez Bravo*
