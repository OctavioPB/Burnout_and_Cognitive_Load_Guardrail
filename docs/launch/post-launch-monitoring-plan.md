# Post-Launch Monitoring Plan — First 30 Days

> **Purpose:** Define what "good" looks like in production during the initial pilot period,
> who watches it, and what triggers an escalation vs a normal learning curve.

---

## Monitoring cadence

| Frequency | Activity | Owner |
|---|---|---|
| Real-time | Grafana/Datadog dashboards + Alertmanager pages | On-call rotation |
| Daily (09:00) | Automated health digest (Slack #guardrail-ops) | Platform Engineering |
| Weekly (Monday) | KPI review with HR Admin lead | Product + HR |
| Day 7 | First check-in: data quality + HR feedback | Product + Platform |
| Day 14 | Mid-pilot review: intervention usage + AFS accuracy | Product + ML + HR |
| Day 30 | Full pilot retrospective | All stakeholders |

---

## Service-level objectives (SLOs) — pilot period

| Metric | SLO | Alert threshold |
|---|---|---|
| API availability | ≥ 99.0% (relaxed from 99.5% for pilot) | < 99.0% over any 24h window |
| API p99 latency | < 500ms (relaxed during pilot) | > 500ms for > 10 min |
| AFS data freshness | Updated within 30h of midnight UTC | Missing update for 2 consecutive days |
| Kafka consumer lag | < 50,000 messages | > 100,000 for > 30 min |
| Error rate | < 2% | > 5% for > 5 min |

*SLOs tighten to production targets (99.5% / 300ms p99) at the end of the pilot.*

---

## Day-1 checklist (launch day)

Run immediately after the production deployment completes:

- [ ] Grafana dashboard green — all services `up{} == 1`
- [ ] `/health` returns `200 OK` from at least 2 geographic locations
- [ ] At least one team shows AFS data for today
- [ ] Alert feed loads without errors
- [ ] HR Admin can log in and reach the Audit Log
- [ ] Team Manager can see only their own team
- [ ] Apply a test intervention (on a designated test team) — confirm Jira/Calendar/Slack receipts
- [ ] Audit log shows the test intervention entry
- [ ] Prometheus is scraping `/metrics` — confirm at least 5 metrics are populated
- [ ] PagerDuty test alert fires and routes to on-call engineer correctly

---

## Day 7 check-in

**Data quality gates:**
- Kafka consumer lag < 1,000 messages during business hours every day
- All pilot teams have ≥ 6 of 7 daily AFS readings
- No team showing `zone = "unknown"` (would indicate a scoring failure)

**HR feedback gates:**
- HR Admin lead confirms dashboard is loading correctly
- At least 1 genuine intervention has been triggered (or HR confirms no Red Zone teams — valid result)
- 0 critical data accuracy complaints from HR

**Escalation:** If any data quality gate fails, convene a 30-minute incident call same day.

---

## Day 14 mid-pilot review

**Metrics to review:**

| Metric | Target | Source |
|---|---|---|
| Teams with ≥ 12 days of AFS data | 100% of pilot teams | Airflow DAG run history |
| Intervention accept rate | > 0 (at least 1 accepted) | Audit log |
| Avg AFS across pilot teams | Baseline established | Dashboard summary |
| Drift alert fires | 0 false positives | Prometheus `MLScoreDistributionDrift` |
| HR Admin satisfaction (1–5) | ≥ 4 | Quick survey |

**Agenda for mid-pilot review:**
1. Walk through AFS trend for each pilot team with HR Admin lead
2. Review any dismissed interventions — understand why
3. Discuss AFS accuracy: do scores align with HR's qualitative read?
4. Identify any missing data (teams with gaps) and root-cause
5. Prioritise top 3 feedback items for the hardening sprint

---

## Day 30 pilot retrospective

**Success criteria for pilot graduation:**

| Criterion | Target |
|---|---|
| SLO compliance | All SLOs met for final 14 days |
| Data completeness | ≥ 95% of team-days have AFS readings |
| HR Admin satisfaction | ≥ 4/5 on exit survey |
| At least 1 efficacy view available | ≥ 1 intervention with ≥ 14 post-intervention days |
| Zero open Critical/High security findings | Security review completed |
| Privacy sign-off | DPO confirms DPA is in effect and data practices match it |

**Retrospective outputs:**
1. Go / No-go decision for full rollout
2. Prioritised backlog of feedback items (file as GitHub issues)
3. Updated SLOs for full production
4. Onboarding guide updated with lessons from the pilot

---

## Escalation matrix

| Situation | Immediate action | Escalate to |
|---|---|---|
| Service down > 15 min | On-call restores or rolls back | Backend lead |
| Data breach suspected | Isolate, notify DPO within 1h | DPO + Legal |
| HR reports incorrect data | Do not dismiss — investigate immediately | ML lead + HR lead |
| Kafka lag > 100k messages | Scale consumers, notify HR of delay | Platform lead |
| Intervention integration failure (e.g. Jira API down) | HR notified manually; track in ops log | Backend lead |
| User access concern (e.g. manager seeing wrong team) | Immediately revoke session, audit log review | Security + Legal |

---

## Feedback collection

During the pilot, collect feedback through:

1. **Slack channel `#guardrail-pilot-feedback`** — asynchronous quick reactions
2. **Weekly 15-min HR Admin check-in** — structured questions each Monday
3. **In-app feedback button** (Phase 2 roadmap item — file as issue if not built)
4. **Day 14 and Day 30 surveys** — Google Form, 5 questions, < 5 min

Feedback is triaged weekly by Product and filed as GitHub issues with labels: `ux`, `data-quality`, `feature-request`, `bug`.
