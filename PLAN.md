# PLAN.md — Burnout & Cognitive Load Guardrail
## Sprint Roadmap

> **Methodology:** 2-week sprints. Each sprint has a single north-star goal, a defined set of deliverables, explicit acceptance criteria, and known dependencies.
> Definition of Done: Code reviewed, tests passing (≥80% coverage), deployed to staging, and documented.

---

## Roadmap at a Glance

```
Phase 1 — Foundation          Phase 2 — Intelligence        Phase 3 — Product
─────────────────────         ──────────────────────         ─────────────────
Sprint 1: Infra Skeleton       Sprint 4: Feature Eng.         Sprint 7: Dashboard V1
Sprint 2: Data Ingestion       Sprint 5: ML Model             Sprint 8: Interventions
Sprint 3: ETL Pipeline         Sprint 6: Inference API        Sprint 9: Hardening & Launch
```

---

## Phase 1 — Foundation

### Sprint 1 — Infrastructure Skeleton
**Goal:** Every engineer can run the full local stack with a single command.
**Dates:** Weeks 1–2

#### Deliverables
- [x] `docker-compose.yml` with Kafka, Zookeeper, Postgres, Redis, and Schema Registry
- [x] Terraform modules for staging environment (VPC, EKS/ECS cluster, managed Kafka)
- [x] GitHub Actions CI pipeline: lint → test → build → push image
- [x] Base Python project scaffold (`pyproject.toml`, `ruff`, `mypy`, `pytest` configured)
- [x] Base TypeScript project scaffold (Vite + React 18 + Tailwind + strict tsconfig)
- [x] `BRAND.md` authored and merged — design tokens committed to `dashboard/styles/tokens.ts`
- [x] `.env.example` with all required environment variable keys documented
- [x] `docs/adr/` folder seeded with ADR-001 through ADR-004

#### Acceptance Criteria
- `docker compose up -d && pytest tests/ && npm test` all pass on a fresh clone
- Staging environment is reachable and healthy in AWS/GCP
- CI pipeline runs on every PR and blocks merge on failure

#### Dependencies
- Cloud provider accounts and IAM roles provisioned
- Design system decisions finalized (feeds into `BRAND.md`)

---

### Sprint 2 — Digital Exhaust Ingestion
**Goal:** Raw collaboration metadata flows from source systems into Kafka topics in real time.
**Dates:** Weeks 3–4

#### Deliverables
- [ ] `BaseConnector` abstract interface defined in `ingestion/connectors/base.py`
- [ ] **Slack connector** — captures: message timestamp, channel activity count, after-hours message flag (no message content)
- [ ] **Google Calendar connector** — captures: meeting count per day, total meeting hours, back-to-back meeting flag
- [ ] **Jira connector** — captures: ticket creation/closure rates, sprint commitment vs. delivery ratio
- [ ] **GitHub connector** — captures: PR cycle time, review turnaround, commit frequency by hour
- [ ] Avro schemas for all event types registered in Schema Registry
- [ ] Kafka topics created: `raw.slack.activity`, `raw.calendar.events`, `raw.jira.sprint`, `raw.github.activity`
- [ ] Kafka producer with retry logic, dead-letter queue (DLQ), and schema validation
- [ ] Unit tests for each connector (mocked API responses)
- [ ] Integration test: producer → Kafka → consumer round-trip

#### Acceptance Criteria
- All four connectors produce valid Avro messages consumed without schema errors
- DLQ captures and logs malformed events without crashing producers
- No PII (names, message content, email bodies) appears in any Kafka message
- Privacy review signed off by DPO

#### Dependencies
- OAuth apps registered in Slack, Google Workspace, Jira, and GitHub (org-level)
- Sprint 1 Kafka infrastructure live

---

### Sprint 3 — ETL Enrichment Pipeline
**Goal:** Raw events are cleaned, aggregated into team-level features, and written to the data warehouse.
**Dates:** Weeks 5–6

#### Deliverables
- [ ] Airflow DAG: `dag_raw_to_features` — triggered on Kafka offset checkpoints, runs hourly
- [ ] Transform: **Calendar Density Score** — meetings per day normalized by team size
- [ ] Transform: **After-Hours Activity Index** — weighted ratio of Slack events outside 9–6 local time
- [ ] Transform: **Context-Switch Count** — number of distinct task/meeting context changes per day per team unit
- [ ] Transform: **Sprint Health Index** — Jira/GitHub delivery ratio × PR cycle time
- [ ] Aggregation: all transforms roll up to the `team_unit` grain, written to `features.team_daily` table
- [ ] Data quality checks with Great Expectations (null rates, range checks, schema drift alerts)
- [ ] Airflow DAG is idempotent — safe to backfill without duplicating records
- [ ] `docs/` data dictionary for all feature columns

#### Acceptance Criteria
- `features.team_daily` table is populated with 30 days of backfilled data on staging
- All Great Expectations checks pass for the backfilled dataset
- DAG re-run produces identical output (idempotency verified by row count + checksum)
- Data lineage traceable from raw Kafka offset → feature row

#### Dependencies
- Sprint 2 connectors producing data to Kafka
- Data warehouse (Snowflake/BigQuery) provisioned with correct IAM permissions

---

## Phase 2 — Intelligence

### Sprint 4 — Feature Engineering & Training Dataset
**Goal:** A clean, labeled-ready ML dataset is available and the feature pipeline is reproducible.
**Dates:** Weeks 7–8

#### Deliverables
- [ ] Feature store schema finalized (`ml/training/features.py`)
- [ ] Exploratory Data Analysis (EDA) notebook: distribution analysis, correlation heatmap, outlier inspection
- [ ] **Attention Fragmentation Score (AFS)** composite feature engineered:
  - `AFS = f(context_switch_count, calendar_density, after_hours_index, sprint_health_inverse)`
- [ ] Train/validation/test split logic with temporal holdout (no data leakage)
- [ ] Synthetic data generator for local development and CI (`ml/training/synthetic.py`)
- [ ] Feature pipeline unit tests with synthetic data
- [ ] Baseline model (rule-based thresholds) for benchmarking ML model against

#### Acceptance Criteria
- AFS values for the 30-day backfill land in the [0, 100] range with expected distribution
- EDA notebook reviewed and approved by Data Science lead
- Synthetic data generator produces statistically plausible signals
- Baseline model metrics documented as the benchmark floor

#### Dependencies
- Sprint 3 `features.team_daily` table populated

---

### Sprint 5 — Anomaly Detection Model
**Goal:** A trained ML model flags teams at risk of burnout with acceptable precision and recall.
**Dates:** Weeks 9–10

#### Deliverables
- [ ] **Isolation Forest** model trained on AFS composite feature + individual components
- [ ] **LSTM sequence model** trained on 14-day rolling windows (detects trend deterioration, not just point anomalies)
- [ ] Ensemble scorer: IF for point anomalies + LSTM for trend anomalies → final risk score
- [ ] Resilience Zone classifier: risk score → Green / Yellow / Red label
- [ ] Model evaluation report: precision, recall, F1, false positive rate on holdout set
- [ ] Drift detection baseline (feature distribution fingerprint saved for monitoring)
- [ ] Model artifacts versioned and stored in `ml/models/v1.0/`
- [ ] `ml/evaluation/evaluate.py` script runs in CI on every PR to `ml/` folder

#### Acceptance Criteria
- Red Zone precision ≥ 0.80 (fewer false alarms for HR)
- Red Zone recall ≥ 0.75 (catching real at-risk teams)
- False positive rate on Green Zone ≤ 0.10
- Evaluation script runs in < 3 minutes in CI
- Model card documented (`ml/models/v1.0/MODEL_CARD.md`)

#### Dependencies
- Sprint 4 feature dataset ready
- GPU-capable training instance available (or cloud training job configured)

---

### Sprint 6 — ML Inference API & Alerting
**Goal:** The model serves real-time predictions accessible to the backend, and HR alerts are triggered automatically.
**Dates:** Weeks 11–12

#### Deliverables
- [ ] FastAPI inference service (`ml/inference/main.py`):
  - `POST /predict` — accepts team features, returns AFS score + Resilience Zone
  - `GET /health` — liveness + model version
- [ ] Batch scoring Airflow DAG: runs daily, scores all team units, writes to `predictions.team_daily`
- [ ] Alert engine: when a team transitions into Red Zone for ≥3 consecutive days, trigger an HR notification
- [ ] Notification adapters: Slack DM to HR channel, email via SendGrid
- [ ] Suggested intervention logic: rule-based recommendations per Red Zone trigger
  - 10+ micro-meetings/day → "Meeting-Free Friday" suggestion
  - After-hours index > 0.6 → "Async-first week" suggestion
  - Sprint health < 0.5 → "Load redistribution review" suggestion
- [ ] Inference API deployed to staging with load testing (k6 or Locust)
- [ ] API response time p99 < 200ms under 50 RPS

#### Acceptance Criteria
- Inference API returns predictions in < 200ms at p99 under load test
- Batch scoring DAG completes for 100 team units in < 10 minutes
- Alert fires correctly in staging when a team is injected with Red Zone signals for 3 days
- Intervention suggestions appear in the HR notification payload

#### Dependencies
- Sprint 5 model artifacts available at `ml/models/v1.0/`
- Slack and SendGrid credentials configured in secrets manager

---

## Phase 3 — Product

### Sprint 7 — Team Resilience Dashboard V1
**Goal:** HR users can log in and see their organization's Resilience Zones in a clear, actionable dashboard.
**Dates:** Weeks 13–14

#### Deliverables

> ⚠️ All UI decisions in this sprint are governed by **BRAND.md**. Read it before writing any component.

- [ ] Authentication flow: SSO via Okta/Auth0, role-based access (HR Admin, Team Manager, Viewer)
- [ ] **Dashboard Home** — org-wide heatmap of Resilience Zones by department
- [ ] **Team Drill-Down** — 30-day AFS trend chart, component breakdown (calendar density, after-hours, context switches, sprint health)
- [ ] **Alert Feed** — chronological list of Red Zone entries with timestamps and triggered interventions
- [ ] **Zone Badge Component** — reusable Green/Yellow/Red indicator (colors from BRAND.md severity palette)
- [ ] **Resilience Trend Chart** — Recharts `<LineChart>` with zone threshold bands (styled per BRAND.md)
- [ ] **Department Heatmap** — grid of team cards color-coded by zone
- [ ] Empty states, loading skeletons, and error boundaries for all views
- [ ] Responsive layout: desktop (1280px+) and tablet (768px+)
- [ ] Accessibility: WCAG 2.1 AA compliance (keyboard navigation, ARIA labels, color contrast)

#### Acceptance Criteria
- Dashboard loads with real staging data for at least 10 seeded team units
- All chart colors and component styles match BRAND.md exactly (design review sign-off required)
- Lighthouse accessibility score ≥ 90
- Auth flow tested with at least 2 roles (HR Admin and Team Manager)
- Zero hardcoded colors or styles — all values from design tokens

#### Dependencies
- Sprint 6 Inference API and `predictions.team_daily` table available
- Backend API endpoints for dashboard data wired up (can be done in parallel)
- BRAND.md finalized (Sprint 1 dependency)

---

### Sprint 8 — Automated Interventions & HR Workflows
**Goal:** HR can act on burnout signals directly from the dashboard, and interventions are tracked for efficacy.
**Dates:** Weeks 15–16

#### Deliverables
- [ ] **Intervention Panel** — HR can accept, dismiss, or customize a suggested intervention per team
- [ ] Intervention actions wired to integrations:
  - "Meeting-Free Friday" → creates a recurring calendar block via Google Calendar API for the team
  - "Load Redistribution" → creates a Jira epic with a checklist template
  - "Async-first week" → posts a pinned Slack message to the team channel (no content generated by system — HR writes the message, system delivers it)
- [ ] Intervention tracking: record which interventions were applied, by whom, and when
- [ ] **Efficacy view:** AFS trend before/after each intervention (14-day window)
- [ ] Audit log UI: HR Admins can view a full log of who viewed which team data and when
- [ ] Manager self-service view: Team Managers see only their own team's data (RBAC enforced at API layer)

#### Acceptance Criteria
- Intervention actions execute correctly in staging (calendar blocks created, Jira epics created, Slack messages delivered)
- Efficacy chart renders correctly for interventions with ≥14 days of post-intervention data
- Audit log captures all dashboard read events with actor + timestamp
- RBAC: a Team Manager cannot access another team's data (verified by automated test)

#### Dependencies
- Sprint 7 Dashboard V1 live
- Google Calendar API, Jira API, Slack API write permissions configured

---

### Sprint 9 — Hardening, Observability & Launch
**Goal:** The system is production-ready: observable, secure, performant, and documented for end users.
**Dates:** Weeks 17–18

#### Deliverables

**Observability**
- [ ] Structured logging (JSON) with correlation IDs across all services
- [ ] Metrics exported to Prometheus / Datadog: API latency, Kafka consumer lag, model score distribution, alert fire rate
- [ ] Dashboards in Grafana/Datadog: service health, pipeline health, ML drift indicators
- [ ] Alerting rules: Kafka lag > 5min → PagerDuty; model score distribution drift → Slack #ml-alerts

**Security**
- [ ] Penetration test on the API surface (or third-party security review)
- [ ] Secrets rotation runbook documented
- [ ] OWASP Top 10 checklist completed for the backend API
- [ ] All data encrypted at rest (AES-256) and in transit (TLS 1.3)

**Performance**
- [ ] Load test: 500 concurrent users on Dashboard, 200 RPS on Inference API — p99 < 300ms
- [ ] Database query optimization: all queries with EXPLAIN ANALYZE reviewed
- [ ] CDN configured for dashboard static assets

**Documentation & Launch**
- [ ] End-user guide for HR Admins (how to read zones, trigger interventions, read the audit log)
- [ ] Onboarding checklist for new organizations (connector setup, consent configuration, team unit mapping)
- [ ] Runbook for on-call engineers (common failure modes and recovery steps)
- [ ] Data Processing Agreement (DPA) template reviewed by legal
- [ ] Production deployment executed with zero-downtime blue-green strategy
- [ ] Post-launch monitoring plan (first 30 days SLA targets)

#### Acceptance Criteria
- All load test scenarios pass within p99 thresholds
- Zero Critical or High findings open from security review
- Grafana/Datadog dashboards green on production deploy
- End-user guide reviewed and approved by at least 2 HR stakeholders
- Production environment live and serving at least 1 pilot customer organization

#### Dependencies
- Sprints 7 and 8 fully complete and stable on staging
- Legal review of DPA complete
- Production cloud environment provisioned (mirrors staging Terraform config)

---

## Backlog / Post-Launch Candidates

These items are scoped but deferred to future sprints based on pilot feedback:

| Item | Priority | Notes |
|---|---|---|
| Mobile-responsive dashboard (< 768px) | Medium | Phase 3 covers tablet only |
| HRIS integrations (Workday, BambooHR) | High | Enriches team unit definitions |
| Multi-tenant SaaS architecture | High | Required for commercial scaling |
| Predictive attrition risk score | Medium | Extend ML model with turnover signals |
| Anonymous team member pulse survey trigger | Low | Self-reported data to validate AFS |
| SCIM provisioning for user management | Medium | Reduces onboarding friction |
| Microsoft 365 / Teams connector | High | Parallel to Google/Slack stack |
| Exportable PDF resilience report for board decks | Low | HR stakeholder request |

---

## Sprint Velocity & Risk Log

| Sprint | Risk | Mitigation |
|---|---|---|
| Sprint 2 | OAuth app approvals delayed by IT/legal | Start approval requests in Sprint 1; use synthetic data as fallback |
| Sprint 3 | Airflow DAG idempotency bugs cause duplicate features | Enforce upsert logic with composite primary keys; add Great Expectations checks |
| Sprint 5 | ML model underperforms on small teams (< 5 people) | Add team-size as a covariate; flag small teams with "insufficient data" instead of a score |
| Sprint 7 | BRAND.md not finalized before UI work begins | BRAND.md is a Sprint 1 hard exit criterion — do not start Sprint 7 without it |
| Sprint 8 | Calendar API write permissions blocked by org IT policy | Offer "copy suggestion" fallback (HR copies text, no API write required) |
| Sprint 9 | Security review findings delay launch | Schedule security review at end of Sprint 8 to allow Sprint 9 remediation buffer |
