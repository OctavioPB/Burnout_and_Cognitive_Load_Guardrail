# CLAUDE.md — Burnout & Cognitive Load Guardrail

> This file instructs Claude Code on how to navigate, build, and reason about this project.
> For all UI/UX and visual decisions, refer to **[BRAND.md](./BRAND.md)** before writing any frontend code.

---

## Project Overview

**The Burnout & Cognitive Load Guardrail** is a real-time digital exhaust monitoring system that predicts team burnout before it happens. It ingests collaboration metadata (calendar density, after-hours Slack activity, context-switching frequency), enriches it through an ML anomaly detection pipeline, and surfaces a **Team Resilience Dashboard** for HR teams.

**Core Promise:** Protect high-demand talent by detecting fatigue patterns weeks before attrition or medical leave occurs.

The Burnout & Cognitive Load Guardrail is a smart early-warning system designed to keep high-performing teams from hitting a wall. Instead of waiting for someone to quit or get sick from stress, this tool uses real-time data to spot "red zone" behaviors—like constant late-night messages or back-to-back meetings—well before they lead to a crisis. By giving leadership a clear view of team health, the project helps prevent costly turnover and keeps the workforce energized. It’s a straightforward move to protect your best people and ensure the company stays productive without burning anyone out.
---

## Repository Structure

```
burnout-guardrail/
├── ingestion/                  # Kafka producers & consumers (Digital Exhaust layer)
│   ├── connectors/             # Slack, Google Calendar, Jira, GitHub adapters
│   ├── schemas/                # Avro/Protobuf event schemas
│   └── config/                 # Kafka topic & broker configuration
│
├── pipeline/                   # Airflow DAGs (ETL enrichment layer)
│   ├── dags/                   # DAG definitions
│   ├── operators/              # Custom Airflow operators
│   └── transforms/             # Aggregation & enrichment logic
│
├── ml/                         # AI/ML anomaly detection
│   ├── models/                 # Trained model artifacts
│   ├── training/               # Feature engineering & training scripts
│   ├── inference/              # Real-time scoring service (FastAPI)
│   └── evaluation/             # Metrics, drift detection, notebooks
│
├── api/                        # Backend REST/GraphQL API
│   ├── routers/                # Endpoint definitions
│   ├── services/               # Business logic
│   └── schemas/                # Pydantic / GraphQL type definitions
│
├── dashboard/                  # Frontend Team Resilience Dashboard
│   ├── components/             # Reusable UI components
│   ├── pages/                  # Route-level views
│   ├── hooks/                  # Custom React hooks
│   └── styles/                 # Design tokens (see BRAND.md)
│
├── infra/                      # IaC (Terraform / Docker Compose)
├── tests/                      # Unit, integration, and E2E tests
├── docs/                       # Architecture diagrams, ADRs
├── CLAUDE.md                   # ← You are here
├── BRAND.md                    # UI/UX design system reference
└── PLAN.md                     # Sprint roadmap
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Event Streaming | Apache Kafka (Confluent Cloud or self-hosted) |
| Orchestration | Apache Airflow (MWAA or Astronomer) |
| Data Warehouse | Snowflake / BigQuery |
| ML Framework | scikit-learn, PyTorch (Isolation Forest, LSTM) |
| Inference API | FastAPI + Uvicorn |
| Backend API | FastAPI or NestJS |
| Frontend | React + TypeScript + Recharts |
| Auth | OAuth 2.0 (SSO via Okta/Auth0) |
| Infrastructure | Docker, Terraform, AWS/GCP |
| CI/CD | GitHub Actions |

---

## Privacy & Compliance Rules

> These are non-negotiable constraints. Never write code that violates them.

1. **No content capture.** Only metadata is collected — event timestamps, durations, counts. Message bodies, document contents, and video streams are never ingested.
2. **Team-level aggregation only.** Individual user data is aggregated into "team units" before surfacing in the dashboard. No individual-level burnout scores are displayed to HR.
3. **Consent-first.** All data collection requires explicit opt-in configured at the workspace/org level.
4. **Data minimization.** Retain raw events for ≤7 days. Aggregated features for ≤90 days.
5. **Audit logging.** Every API call that reads resilience data must be logged with actor identity and timestamp.

---

## Key Domain Concepts

- **Digital Exhaust:** Metadata signals emitted passively by collaboration tools (not content).
- **Attention Fragmentation Score (AFS):** The ML model's primary output. Measures how fragmented a team's focused work time is (0–100, higher = more fragmented).
- **Team Unit:** The atomic entity for all aggregations. Usually maps to a squad/team in the org chart.
- **Resilience Zone:** Color classification of a Team Unit's current risk level.
  - 🟢 Green: AFS 0–39 — Healthy
  - 🟡 Yellow: AFS 40–69 — Monitor
  - 🔴 Red: AFS 70–100 — Intervene
- **Sprint Health Index:** Correlated from Jira/GitHub — story points delivered vs. committed, PR cycle time, and incident frequency.
- **Suggested Intervention:** An automated HR recommendation triggered when a team enters Red Zone (e.g., "Meeting-Free Friday", "Load Redistribution").

---

## Coding Standards

### General
- All code must have docstrings / JSDoc comments for public interfaces.
- Use strict typing everywhere: `mypy` for Python, `strict` mode in `tsconfig.json`.
- Never hardcode credentials. Use environment variables via `.env` + a secrets manager.
- Every new module must include a corresponding test file.

### Python (Ingestion, Pipeline, ML, API)
- Python ≥ 3.11
- Use `ruff` for linting and formatting (replaces black + flake8).
- Follow the repository's `pyproject.toml` for tool configuration.
- Async-first for I/O bound services (`asyncio`, `httpx`).
- Pydantic v2 for all data models.

### TypeScript / React (Dashboard)
- React 18+ with functional components and hooks only. No class components.
- Use the design tokens defined in `dashboard/styles/tokens.ts` — sourced from **BRAND.md**.
- All chart colors, severity palettes, and typography must match **BRAND.md** exactly.
- State management: Zustand for global state, React Query for server state.
- No inline styles. Use CSS Modules or Tailwind utility classes as defined in **BRAND.md**.

### Kafka / Airflow
- All Kafka messages must use Avro schemas registered in the Schema Registry.
- Airflow DAGs must be idempotent. Never write a DAG that cannot be safely re-run.
- Use `task_groups` to organize complex DAGs visually.

---

## UI Decisions → See BRAND.md

> **Before writing any frontend component, style, color, chart configuration, or layout decision, open and read `BRAND.md`.**

BRAND.md defines:
- Color palette and severity zone colors (Green / Yellow / Red resilience zones)
- Typography scale and font families
- Component patterns (cards, badges, alert banners)
- Chart and data visualization conventions (Recharts configuration)
- Spacing and grid system
- Dark/light mode tokens
- Logo and icon usage guidelines

Deviating from BRAND.md without explicit user approval is not allowed.

---

## Environment Setup

```bash
# 1. Clone and enter the repo
git clone https://github.com/your-org/burnout-guardrail.git
cd burnout-guardrail

# 2. Copy environment template
cp .env.example .env

# 3. Start local infrastructure (Kafka, Postgres, Redis)
docker compose up -d

# 4. Install Python dependencies
pip install -e ".[dev]"

# 5. Install frontend dependencies
cd dashboard && npm install

# 6. Run all tests
pytest tests/ && npm test --prefix dashboard
```

---

## Running Services Locally

| Service | Command | Port |
|---|---|---|
| Kafka (via Docker) | `docker compose up kafka` | 9092 |
| Airflow Webserver | `airflow webserver` | 8080 |
| ML Inference API | `uvicorn ml.inference.main:app --reload` | 8001 |
| Backend API | `uvicorn api.main:app --reload` | 8000 |
| Dashboard (Vite) | `npm run dev --prefix dashboard` | 5173 |

---

## Testing Strategy

- **Unit tests:** All pure functions in `ml/`, `pipeline/transforms/`, and `api/services/` must have ≥80% coverage.
- **Integration tests:** Kafka producer→consumer round-trip tests live in `tests/integration/`.
- **E2E tests:** Playwright tests for the Dashboard cover the three main user flows (HR view, Team view, Alert drill-down).
- **ML tests:** Model evaluation scripts in `ml/evaluation/` must run on every PR to catch performance regressions.

Run with:
```bash
pytest tests/unit/
pytest tests/integration/
npx playwright test
```

---

## Common Tasks for Claude Code

### "Add a new data connector"
1. Create a new file in `ingestion/connectors/`.
2. Implement the `BaseConnector` interface defined in `ingestion/connectors/base.py`.
3. Register the new Kafka topic in `ingestion/config/topics.yaml`.
4. Add the Avro schema to `ingestion/schemas/`.
5. Write unit tests in `tests/unit/ingestion/`.

### "Add a new dashboard widget"
1. Read **BRAND.md** first.
2. Create the component in `dashboard/components/`.
3. Use tokens from `dashboard/styles/tokens.ts`.
4. Wire to the API via a custom hook in `dashboard/hooks/`.
5. Add a Playwright test.

### "Retrain the ML model"
1. Navigate to `ml/training/`.
2. Run `python train.py --config config/default.yaml`.
3. Evaluate with `python ml/evaluation/evaluate.py`.
4. If metrics pass thresholds, export to `ml/models/` and bump the model version in `ml/inference/config.py`.

---

## Architectural Decisions (ADR Index)

| # | Decision | Location |
|---|---|---|
| 001 | Use Kafka over SQS for event streaming | `docs/adr/001-kafka.md` |
| 002 | Isolation Forest for anomaly detection baseline | `docs/adr/002-isolation-forest.md` |
| 003 | Team-level aggregation to preserve privacy | `docs/adr/003-privacy-aggregation.md` |
| 004 | FastAPI for ML inference service | `docs/adr/004-fastapi-inference.md` |

---

## Contacts & Ownership

| Area | Owner |
|---|---|
| Ingestion / Kafka | Platform Engineering |
| ML Pipeline | Data Science Team |
| Backend API | Backend Team |
| Dashboard | Frontend Team |
| Privacy & Compliance | Legal / DPO |
