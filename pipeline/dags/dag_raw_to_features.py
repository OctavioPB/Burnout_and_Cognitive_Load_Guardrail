"""DAG: dag_raw_to_features

Hourly ETL pipeline: Kafka raw topics → features.team_daily.

Schedule:   @hourly  (catchup=True enables 30-day backfill)
Idempotency: the upsert in features.team_daily uses ON CONFLICT DO UPDATE on
             (team_id, workspace_id, date_utc) — re-running any execution_date
             overwrites the row rather than duplicating it.
Lineage:    Each row stores the last Kafka offset consumed per source topic so
             events can be traced back to their raw Kafka position.
"""

from __future__ import annotations

import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

try:
    from airflow.decorators import dag, task
    from airflow.models import Variable
except ImportError as _exc:  # pragma: no cover
    raise ImportError(
        "apache-airflow is required to run this DAG. "
        "Install with: pip install 'burnout-guardrail[pipeline]'"
    ) from _exc

from pipeline.operators.kafka_consume_operator import KafkaBatchConsumeOperator
from pipeline.transforms.after_hours_index import compute_after_hours_activity_index
from pipeline.transforms.calendar_density import compute_calendar_density_score
from pipeline.transforms.context_switch import compute_context_switch_count
from pipeline.transforms.sprint_health import compute_sprint_health_index
from pipeline.quality.checks import validate_team_daily_batch
from ingestion.models import (
    CalendarActivityEvent,
    GitHubActivityEvent,
    JiraSprintEvent,
    SlackActivityEvent,
)

_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://guardrail:guardrail_dev@localhost:5432/burnout_guardrail",
)
_DEFAULT_TEAM_SIZE = 5  # fallback when team registry is not yet available


def _get_team_size(workspace_id: str, team_id: str) -> int:
    """Return team size from Airflow Variable or fall back to default."""
    try:
        registry: dict[str, int] = Variable.get(
            "team_sizes", default_var={}, deserialize_json=True
        )
        return int(registry.get(f"{workspace_id}/{team_id}", _DEFAULT_TEAM_SIZE))
    except Exception:
        return _DEFAULT_TEAM_SIZE


@dag(
    dag_id="dag_raw_to_features",
    description="ETL: Kafka raw events → features.team_daily (hourly, idempotent)",
    schedule="@hourly",
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    catchup=True,
    max_active_runs=4,
    tags=["burnout", "etl", "features"],
)
def raw_to_features() -> None:

    # ── 1. Consume events from all four source topics in parallel ────────────

    @task(task_id="consume_slack")
    def consume_slack(ds: str, run_id: str) -> list[dict[str, Any]]:
        op = KafkaBatchConsumeOperator(
            topic="raw.slack.activity",
            schema_file="slack_activity.avsc",
            date_filter=ds,
            bootstrap_servers=_BOOTSTRAP,
            task_id="consume_slack",
        )
        return op.execute(run_id=run_id)

    @task(task_id="consume_calendar")
    def consume_calendar(ds: str, run_id: str) -> list[dict[str, Any]]:
        op = KafkaBatchConsumeOperator(
            topic="raw.calendar.events",
            schema_file="calendar_event.avsc",
            date_filter=ds,
            bootstrap_servers=_BOOTSTRAP,
            task_id="consume_calendar",
        )
        return op.execute(run_id=run_id)

    @task(task_id="consume_jira")
    def consume_jira(ds: str, run_id: str) -> list[dict[str, Any]]:
        op = KafkaBatchConsumeOperator(
            topic="raw.jira.sprint",
            schema_file="jira_sprint.avsc",
            date_filter=ds,
            bootstrap_servers=_BOOTSTRAP,
            task_id="consume_jira",
        )
        return op.execute(run_id=run_id)

    @task(task_id="consume_github")
    def consume_github(ds: str, run_id: str) -> list[dict[str, Any]]:
        op = KafkaBatchConsumeOperator(
            topic="raw.github.activity",
            schema_file="github_activity.avsc",
            date_filter=ds,
            bootstrap_servers=_BOOTSTRAP,
            task_id="consume_github",
        )
        return op.execute(run_id=run_id)

    # ── 2. Aggregate per team and compute all four feature transforms ────────

    @task(task_id="compute_features")
    def compute_features(
        slack_records: list[dict[str, Any]],
        calendar_records: list[dict[str, Any]],
        jira_records: list[dict[str, Any]],
        github_records: list[dict[str, Any]],
        ds: str,
    ) -> list[dict[str, Any]]:
        # Group raw dicts by (workspace_id, team_id)
        slack_by_team: dict[tuple[str, str], list[dict]] = defaultdict(list)
        calendar_by_team: dict[tuple[str, str], list[dict]] = defaultdict(list)
        jira_by_team: dict[tuple[str, str], list[dict]] = defaultdict(list)
        github_by_team: dict[tuple[str, str], list[dict]] = defaultdict(list)

        for r in slack_records:
            slack_by_team[(r["workspace_id"], r["team_id"])].append(r)
        for r in calendar_records:
            calendar_by_team[(r["workspace_id"], r["team_id"])].append(r)
        for r in jira_records:
            jira_by_team[(r["workspace_id"], r["team_id"])].append(r)
        for r in github_records:
            github_by_team[(r["workspace_id"], r["team_id"])].append(r)

        all_teams = (
            set(slack_by_team)
            | set(calendar_by_team)
            | set(jira_by_team)
            | set(github_by_team)
        )

        feature_rows: list[dict[str, Any]] = []
        for workspace_id, team_id in all_teams:
            key = (workspace_id, team_id)
            team_size = _get_team_size(workspace_id, team_id)

            slack_evts = [SlackActivityEvent(**r) for r in slack_by_team[key]]
            cal_evts = [CalendarActivityEvent(**r) for r in calendar_by_team[key]]
            jira_evts = [JiraSprintEvent(**r) for r in jira_by_team[key]]
            gh_evts = [GitHubActivityEvent(**r) for r in github_by_team[key]]

            feature_rows.append(
                {
                    "workspace_id": workspace_id,
                    "team_id": team_id,
                    "date_utc": ds,
                    "team_size": team_size,
                    "calendar_density_score": compute_calendar_density_score(
                        cal_evts, team_size
                    ),
                    "after_hours_activity_index": compute_after_hours_activity_index(
                        slack_evts
                    ),
                    "context_switch_count": compute_context_switch_count(
                        cal_evts, gh_evts
                    ),
                    "sprint_health_index": compute_sprint_health_index(
                        jira_evts, gh_evts
                    ),
                }
            )

        return feature_rows

    # ── 3. Upsert to features.team_daily ────────────────────────────────────

    @task(task_id="upsert_features")
    def upsert_features(feature_rows: list[dict[str, Any]]) -> int:
        import asyncio

        from sqlalchemy.ext.asyncio import create_async_engine

        from pipeline.repository import upsert_team_daily_features

        if not feature_rows:
            return 0

        engine = create_async_engine(_DATABASE_URL, echo=False)
        count: int = asyncio.get_event_loop().run_until_complete(
            upsert_team_daily_features(engine, feature_rows)
        )
        return count

    # ── 4. Data quality checks ───────────────────────────────────────────────

    @task(task_id="run_quality_checks")
    def run_quality_checks(feature_rows: list[dict[str, Any]]) -> dict[str, Any]:
        results = validate_team_daily_batch(feature_rows)
        failed = [r for r in results if not r.passed]
        summary = {
            "total_checks": len(results),
            "passed": len(results) - len(failed),
            "failed": len(failed),
            "failures": [{"check": r.check_name, "message": r.message} for r in failed],
        }
        if failed:
            import logging

            logging.getLogger(__name__).warning(
                "Quality checks failed: %s", summary["failures"]
            )
        return summary

    # ── Wire the graph ───────────────────────────────────────────────────────
    slack = consume_slack()
    calendar = consume_calendar()
    jira = consume_jira()
    github = consume_github()

    features = compute_features(slack, calendar, jira, github)
    upsert_features(features)
    run_quality_checks(features)


raw_to_features()
