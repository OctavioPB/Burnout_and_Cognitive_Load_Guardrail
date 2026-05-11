# Onboarding Checklist — New Organisation Setup

> **Audience:** Platform Engineering / IT Administrator setting up a new customer organisation.
> Complete every item in order. Each section has an owner and estimated time.

---

## Phase 1 — Prerequisites (IT / Legal) · ~2 days

- [ ] **Legal sign-off on DPA** — the Data Processing Agreement must be countersigned before any data flows. File in the contract management system.
- [ ] **Privacy notice reviewed** — confirm the organisation's employee privacy notice covers collection of collaboration metadata. Legal team to advise.
- [ ] **Consent mechanism activated** — set `CONSENT_REQUIRED=true` in the workspace config and enable the opt-in flow in the admin portal. No data is collected until this is confirmed.
- [ ] **Scope confirmed** — agree which teams (squads / departments) are in scope for the pilot. Minimum viable pilot: 3–5 teams.

---

## Phase 2 — Infrastructure (Platform Engineering) · ~4 hours

- [ ] **Tenant provisioned** in the Burnout Guardrail SaaS or self-hosted cluster. Record the `WORKSPACE_ID` here: ___________
- [ ] **Secrets created** in the secrets manager (AWS Secrets Manager / Vault):
  - `ANTHROPIC_API_KEY` (if ML explanations enabled)
  - `KAFKA_SASL_PASSWORD`
  - `POSTGRES_PASSWORD`
  - `REDIS_PASSWORD`
  - Integration credentials (see Phase 3)
- [ ] **Network connectivity verified** — confirm the ingestion pods can reach:
  - Google Workspace API (`admin.googleapis.com`, `calendar.googleapis.com`)
  - Jira Cloud (`https://<org>.atlassian.net`)
  - Slack API (`slack.com`)
- [ ] **Terraform apply executed** — `cd infra/terraform && terraform apply -var-file=production.tfvars`
- [ ] **Database migrations run** — `alembic upgrade head`

---

## Phase 3 — Connector Configuration (Platform Engineering) · ~2 hours per connector

### Google Workspace (Calendar + Directory)
- [ ] Google Cloud project created with OAuth consent screen configured (internal app type)
- [ ] APIs enabled: Calendar API, Admin SDK Directory API
- [ ] Service account created with domain-wide delegation granted
- [ ] P12 key downloaded and stored as `GOOGLE_SERVICE_ACCOUNT_KEY` in secrets manager
- [ ] `GOOGLE_ADMIN_DELEGATED_EMAIL` set to a super-admin email
- [ ] Connector smoke test: `python scripts/test_connector.py --connector google_calendar`

### Jira
- [ ] API token created in Jira for the service account user `burnout-guardrail@<org>.atlassian.net`
- [ ] `JIRA_URL`, `JIRA_USER`, `JIRA_API_TOKEN` set in secrets manager
- [ ] Target project key confirmed (for Load Redistribution epics): `JIRA_PROJECT_KEY=___`
- [ ] Connector smoke test: `python scripts/test_connector.py --connector jira`

### Slack
- [ ] Slack app created at https://api.slack.com/apps
- [ ] OAuth scopes granted: `channels:join`, `chat:write`, `pins:write`, `users:read`
- [ ] App installed to workspace; Bot token stored as `SLACK_BOT_TOKEN` in secrets manager
- [ ] Channel naming convention confirmed (e.g., `#team-<slug>`): ___________
- [ ] Connector smoke test: `python scripts/test_connector.py --connector slack`

### GitHub (optional — for Sprint Health Index)
- [ ] GitHub App created with read access to all target repos
- [ ] App ID and private key stored as `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY`
- [ ] Repos mapped to team units in `config/team_github_map.yaml`
- [ ] Connector smoke test: `python scripts/test_connector.py --connector github`

---

## Phase 4 — Team Unit Mapping (Platform Engineering + HR) · ~1 hour

- [ ] Team unit definitions confirmed with HR — each team needs:
  - `team_id` (URL-safe slug, e.g. `frontend-engineering`)
  - `team_name` (display name)
  - `department`
  - `slack_channel` (e.g. `#frontend-eng`)
  - `jira_team_label` or `jira_squad_filter`
  - Google group email for calendar access
- [ ] Team mapping file written to `config/teams.yaml` and committed to the config repo
- [ ] Kafka topic `digital-exhaust-events` partitioned to `max(12, 2×team_count)` partitions
- [ ] First ingestion run triggered: `python scripts/backfill.py --days 30`
- [ ] Backfill verified: `python scripts/verify_backfill.py` — all teams should have ≥ 25 of 30 days

---

## Phase 5 — User Access (HR + IT) · ~30 minutes

- [ ] HR Admin accounts provisioned in the identity provider (Okta/Auth0)
- [ ] Team Manager accounts provisioned and mapped to their `team_id`
- [ ] Viewer accounts provisioned for any read-only stakeholders
- [ ] SSO connection tested: log in as each role and confirm correct dashboard access
- [ ] HR Admins given a walkthrough of the HR Admin Guide (`docs/user-guides/hr-admin-guide.md`)

---

## Phase 6 — Go-Live Verification · ~1 hour

- [ ] Grafana/Datadog dashboard green — all services `up{} == 1`
- [ ] At least 3 teams show AFS data for today in the Dashboard Home
- [ ] Alert feed loads without errors
- [ ] Apply a test intervention on a non-production team and confirm Jira/Calendar/Slack receipts
- [ ] Audit log shows the test intervention entry
- [ ] Revert the test intervention (delete the calendar event, close the Jira epic, unpin the Slack message)
- [ ] Sign-off from HR Admin lead: ___________  Date: ___________

---

## Post go-live (Day 7 check-in)

- [ ] Confirm Kafka consumer lag is < 1,000 messages during business hours
- [ ] Confirm model scoring is running daily (check Airflow DAG `burnout_daily_scoring`)
- [ ] Confirm at least one genuine Red Zone alert has fired (or confirm no teams are in Red)
- [ ] Collect initial feedback from HR Admins — file in the pilot feedback log
