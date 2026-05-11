# On-Call Runbook — Burnout Guardrail

> **Audience:** On-call engineers responding to PagerDuty/Alertmanager pages.
> Keep this document short and actionable. If a fix requires > 30 min, escalate.

---

## Escalation path

| Tier | Who | When |
|---|---|---|
| L1 On-call | Any platform engineer in the rotation | First responder for all alerts |
| L2 Backend | Backend team lead | API/intervention failures, data issues |
| L2 ML | ML team lead | Model drift, inference failures |
| L3 Privacy/Legal | DPO | Any suspected data breach or privacy incident |

PagerDuty schedule: `burnout-guardrail-oncall` (auto-escalates after 15 min)

---

## SLA targets (production)

| Metric | Target |
|---|---|
| API p99 latency | < 300ms |
| API error rate (5xx) | < 1% |
| Kafka consumer lag | < 10,000 messages |
| AFS data freshness | Updated within 26 hours of midnight UTC |
| Dashboard availability | ≥ 99.5% monthly |

---

## Runbook index

| Alert | Section |
|---|---|
| `APIDown` | [API is down](#api-is-down) |
| `APIHighErrorRate` | [High API error rate](#high-api-error-rate) |
| `APIHighLatencyP99` | [High API latency](#high-api-latency) |
| `KafkaConsumerLagHigh` | [Kafka consumer lag](#kafka-consumer-lag) |
| `MLInferenceServiceDown` | [ML inference down](#ml-inference-down) |
| `MLScoreDistributionDrift` | [Model drift](#model-score-distribution-drift) |
| `MLHighAlertFireRate` | [High alert fire rate](#high-alert-fire-rate) |
| Data freshness stale | [Stale AFS data](#stale-afs-data) |

---

## API is down

**Symptoms:** `APIDown` page; dashboard shows all grey; `/health` returns connection refused.

1. Check pod status: `kubectl get pods -n guardrail -l app=burnout-api`
2. Read recent logs: `kubectl logs -n guardrail -l app=burnout-api --tail=100`
3. If pods are in `CrashLoopBackOff`:
   - Check for OOM: `kubectl describe pod <pod> -n guardrail | grep -A5 OOMKilled`
   - If OOM: increase memory limit in `infra/terraform/modules/eks/variables.tf` → PR → deploy
   - If application error: check logs for `Exception` or `Error` and file incident
4. If pods are running but unreachable:
   - Check Service: `kubectl get svc -n guardrail burnout-api`
   - Check nginx: `kubectl logs -n ingress-nginx <ingress-pod> --tail=50`
5. Rollback if a recent deploy caused this: `kubectl rollout undo deployment/burnout-api -n guardrail`

**Resolution target:** 15 minutes.

---

## High API error rate

**Symptoms:** `APIHighErrorRate` page; > 5% of requests returning 5xx.

1. Check which endpoints are failing: query Prometheus
   ```promql
   topk(5, sum by (path_template) (rate(http_requests_total{status_code=~"5.."}[5m])))
   ```
2. If `/interventions/*/apply` is the source: check integration adapter logs (Calendar/Jira/Slack credentials may have expired).
3. If `/dashboard/summary` or `/teams/*` are the source: check if mock_data or DB connection is broken.
4. If all endpoints: likely a dependency failure (DB, Redis). Check those services.
5. For transient spikes (< 5 min): monitor and close if it self-resolves.

---

## High API latency

**Symptoms:** `APIHighLatencyP99` page; p99 > 300ms on one or more paths.

1. Identify the slow path:
   ```promql
   topk(5, histogram_quantile(0.99, sum by (le, path_template) (rate(http_request_duration_seconds_bucket[5m]))))
   ```
2. If `/interventions/*/apply`: external integration calls are synchronous. Calendar/Jira/Slack APIs may be slow. Check their status pages.
3. If dashboard read paths: check DB connection pool utilisation.
4. If the ML inference service is slow: `APIHighLatencyP99` on `/teams/*/history` path indicates model scoring backlog.
5. If widespread: check if a traffic spike is occurring (check `http_requests_in_flight`). Consider scaling: `kubectl scale deployment/burnout-api -n guardrail --replicas=4`.

---

## Kafka consumer lag

**Symptoms:** `KafkaConsumerLagHigh` or `KafkaConsumerLagCritical`.

1. Check consumer group status: `kafka-consumer-groups.sh --bootstrap-server $KAFKA_BROKER --describe --group burnout-ingestion`
2. If lag is growing:
   - Check consumer pod logs: `kubectl logs -n guardrail -l app=burnout-consumer --tail=100`
   - Check for deserialization errors (schema mismatch) — common after connector deploys
   - Scale up consumers: `kubectl scale deployment/burnout-consumer -n guardrail --replicas=6`
3. If consumer is healthy but lagging: check upstream producers for burst traffic. Consider increasing topic partitions (requires coordination).
4. If Critical (> 50k): AFS data is going stale. Notify HR lead that today's scores may be delayed. Set ETA.

---

## ML inference down

**Symptoms:** `MLInferenceServiceDown`; AFS scores not updating.

1. Check inference pods: `kubectl get pods -n guardrail -l app=burnout-ml-inference`
2. Check logs for model load errors: `kubectl logs -n guardrail -l app=burnout-ml-inference --tail=50`
3. If model artifact is missing: `aws s3 ls s3://burnout-models/production/` — confirm artifact exists. Re-trigger model download: `kubectl rollout restart deployment/burnout-ml-inference -n guardrail`
4. If OOM: inference requires minimum 2GB RAM. Check resource limits.
5. Manual fallback: if inference is down > 2h, run batch scoring script: `python scripts/batch_score.py --date today`. This updates the DB directly.

---

## Model score distribution drift

**Symptoms:** `MLScoreDistributionDrift`; AFS mean shifted > 10 points vs 24h ago.

1. Check if a new model version was deployed in the last 24h: `kubectl rollout history deployment/burnout-ml-inference -n guardrail`
2. If yes: compare new vs old model on the evaluation dataset: `make evaluate-model`. If regression, roll back.
3. If no new deploy: check feature pipeline for data quality issues (null values, out-of-range inputs). Run: `python scripts/feature_quality_report.py --date today`
4. Check if there's a genuine org-wide event (Monday after a company retreat, product launch crunch, etc.). Consult HR lead before alerting as a model issue.
5. If no clear cause after 1h investigation: escalate to ML team lead.

---

## High alert fire rate

**Symptoms:** `MLHighAlertFireRate`; > 5 Red Zone alerts/hour.

1. First: check if this is a real event. Pull up the dashboard — how many teams are actually Red?
2. If multiple teams genuinely Red: this may be a real org stress event. Notify HR lead immediately. Do not suppress the alerts.
3. If all teams showing Red simultaneously: likely a data pipeline bug producing inflated AFS values. Check: `python scripts/feature_quality_report.py --date today` for anomalous features.
4. Silence the alerting rule for 2h while investigating: `amtool silence add alertname=MLHighAlertFireRate --duration=2h --comment="investigating data quality"`

---

## Stale AFS data

**Symptoms:** Dashboard shows no data for today, or data is > 26 hours old; no active alert (silent failure).

1. Check Airflow DAG status: `http://airflow.internal:8080/dags/burnout_daily_scoring`
2. If the DAG failed: read the task logs in Airflow UI. Common causes: DB connection timeout, Kafka consumer not drained.
3. Manually trigger the DAG: `airflow dags trigger burnout_daily_scoring`
4. Monitor DAG run to completion (typically 8–12 min).
5. If the DAG succeeds but dashboard still stale: check Redis cache TTL. Flush if needed: `redis-cli FLUSHDB` (staging only — coordinate with backend lead in production).
