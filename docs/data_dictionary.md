# Data Dictionary — features.team_daily

**Schema:** `features`  
**Table:** `team_daily`  
**Grain:** One row per `(team_id, workspace_id, date_utc)`  
**Idempotency key:** `UNIQUE (team_id, workspace_id, date_utc)` — re-running the DAG for the same date overwrites the row.

---

## Identity Columns

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | UUID | No | Surrogate primary key. Auto-generated (uuid4). |
| `team_id` | VARCHAR | No | Team unit identifier. Maps to a squad/team in the org chart. Never an individual user ID. |
| `workspace_id` | VARCHAR | No | Workspace/org identifier (e.g. Slack workspace ID or Jira org slug). |
| `date_utc` | DATE | No | Calendar date (UTC) for which the features are computed. |

---

## Feature Columns

All feature values are **normalized to [0.0, 1.0]** unless noted. Higher values indicate higher cognitive load / risk. `sprint_health_index` is the exception — higher = healthier.

### `calendar_density_score` (FLOAT, nullable)

**Definition:** Average share of the working day consumed by meetings, per team member.

**Formula:**
```
CDS = Σ(total_meeting_minutes across all CalendarActivityEvents) / (team_size × 480)
```
Clamped to [0.0, 1.0]. `480` = 8 hours (working day). Multiple CalendarActivityEvents for the same team-day are summed before dividing.

**Interpretation:**
| Range | Signal |
|---|---|
| 0.00–0.25 | Low meeting load — significant focus time available |
| 0.26–0.50 | Moderate — meetings take up to half the workday |
| 0.51–0.75 | High — limited focus time |
| 0.76–1.00 | Severe — near-total meeting saturation |

**Source topic:** `raw.calendar.events`  
**Null when:** No `CalendarActivityEvent` records exist for the team-day (e.g. data connector not yet set up or team has no calendar events).

---

### `after_hours_activity_index` (FLOAT, nullable)

**Definition:** Weighted proportion of Slack messages sent outside core hours (before 09:00 or after 18:00 UTC). Weekend messages are weighted 1.5× because they signal stronger boundary erosion.

**Formula:**
```
AHAI = Σ(message_count × weight) for after-hours events
       ─────────────────────────────────────────────────
       Σ(message_count × weight) for all events

where weight = 1.5 if day_of_week ∈ {5 (Sat), 6 (Sun)}, else 1.0
```
Clamped to [0.0, 1.0].

**Interpretation:**
| Range | Signal |
|---|---|
| 0.00–0.10 | Healthy — almost all communication within business hours |
| 0.11–0.30 | Moderate — some after-hours activity, monitor trend |
| 0.31–0.60 | High — significant after-hours volume |
| 0.61–1.00 | Severe — majority of communication outside work hours |

**Source topic:** `raw.slack.activity`  
**Null when:** No `SlackActivityEvent` records exist for the team-day.

---

### `context_switch_count` (FLOAT, nullable)

**Definition:** Normalized frequency of forced context switches per day. Each back-to-back meeting pair (< 5-minute gap) and each distinct GitHub repository touched counts as a context change.

**Formula:**
```
CSC_raw = Σ(back_to_back_count across CalendarActivityEvents) + |distinct repo_ids in GitHubActivityEvents|
CSC = min(CSC_raw / 20, 1.0)
```
`20` = the raw switch count that maps to maximum fragmentation (CSC = 1.0).

**Interpretation:**
| Range | Signal |
|---|---|
| 0.00–0.15 | Low fragmentation — focused work blocks likely |
| 0.16–0.40 | Moderate — some context switching, manageable |
| 0.41–0.70 | High — attention significantly fragmented |
| 0.71–1.00 | Severe — near-constant context switching |

**Source topics:** `raw.calendar.events`, `raw.github.activity`  
**Null when:** No calendar or GitHub events exist for the team-day.

---

### `sprint_health_index` (FLOAT, nullable)

**Definition:** Combined measure of sprint delivery health (Jira) and code review velocity (GitHub). Higher = healthier team workflow.

**Formula:**
```
delivery_ratio = min(Σ completed_points / Σ committed_points, 1.0)
               (defaults to 1.0 when no committed_points)

cycle_time_component = 1.0 - min(avg_pr_cycle_time_hours / 48, 1.0)
               (defaults to 1.0 when no GitHub events)

SHI = delivery_ratio × cycle_time_component
```
`48` hours = 2 working days; PRs taking longer than this map to `cycle_time_component = 0.0`.

**Interpretation:**
| Range | Signal |
|---|---|
| 0.80–1.00 | Healthy — strong delivery, fast code review |
| 0.50–0.79 | Moderate — some delivery shortfall or slow reviews |
| 0.25–0.49 | Degraded — significant sprint debt or long PR queues |
| 0.00–0.24 | Critical — severe underdelivery and/or blocked PRs |

**Source topics:** `raw.jira.sprint`, `raw.github.activity`  
**Null when:** No Jira sprint events AND no GitHub events exist for the team-day. When only one source is available, the missing component defaults to 1.0 (neutral).

---

## Operational Columns

| Column | Type | Nullable | Description |
|---|---|---|---|
| `team_size` | INTEGER | Yes | Number of people in the team unit at time of computation. Used as the denominator in `calendar_density_score`. Sourced from the team registry (`team_sizes` Airflow Variable). Defaults to 5 when registry is not configured. |
| `computed_at` | TIMESTAMP WITH TIME ZONE | No | UTC timestamp when this row was last written (inserted or upserted). |

---

## Lineage Columns

These columns store the last Kafka offset consumed per source topic for the execution window. They allow tracing a feature row back to its exact position in the raw event stream.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `kafka_slack_offset` | INTEGER | Yes | Last offset consumed from `raw.slack.activity` for this team-day. |
| `kafka_calendar_offset` | INTEGER | Yes | Last offset consumed from `raw.calendar.events` for this team-day. |
| `kafka_jira_offset` | INTEGER | Yes | Last offset consumed from `raw.jira.sprint` for this team-day. |
| `kafka_github_offset` | INTEGER | Yes | Last offset consumed from `raw.github.activity` for this team-day. |

---

## Downstream Usage

### Attention Fragmentation Score (AFS)

The four feature columns feed into the Sprint 4 ML feature engineering pipeline as inputs to the **Attention Fragmentation Score (AFS)** composite:

```
AFS = f(context_switch_count, calendar_density_score, after_hours_activity_index, 1 - sprint_health_index)
```

AFS is the primary input to the anomaly detection model (Sprint 5) and maps to a **Resilience Zone**:

| AFS Range | Zone | Meaning |
|---|---|---|
| 0–39 | 🟢 Green | Healthy — no intervention needed |
| 40–69 | 🟡 Yellow | Monitor — watch for trend deterioration |
| 70–100 | 🔴 Red | Intervene — HR action recommended |

### Data retention

Raw Kafka events: retained ≤ 7 days (per ADR-003).  
`features.team_daily`: retained ≤ 90 days (per ADR-003).
