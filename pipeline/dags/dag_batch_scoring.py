"""Airflow DAG: daily batch scoring of all team units.

Reads team feature records from the warehouse (``features.team_daily`` table),
calls the inference predictor for each team, and writes results to
``predictions.team_daily``.

Idempotency
-----------
The upsert uses ``ON CONFLICT (team_id, workspace_id, date_utc) DO UPDATE``
so re-running for the same date overwrites the previous prediction without
creating duplicates.

Schedule: @daily at 02:00 UTC (after the previous day's ETL enrichment DAG
has completed its nightly run).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta

from airflow.decorators import dag, task
from airflow.providers.postgres.hooks.postgres import PostgresHook

logger = logging.getLogger(__name__)

_POSTGRES_CONN_ID: str = "postgres_default"
_FEATURES_TABLE: str = "features.team_daily"
_PREDICTIONS_TABLE: str = "predictions.team_daily"
_MAX_TEAMS_PER_RUN: int = 500


@dag(
    dag_id="batch_scoring",
    description="Daily batch inference: score all team units and write to predictions table.",
    schedule="0 2 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args={
        "owner": "data-science",
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
    },
    tags=["ml", "inference", "batch"],
)
def batch_scoring_dag() -> None:

    @task()
    def fetch_team_features(ds: str | None = None) -> list[dict]:
        """Read yesterday's enriched features from the feature table.

        Args:
            ds: Airflow execution date string (YYYY-MM-DD).

        Returns:
            List of dicts with team_id, workspace_id, and feature columns.
        """
        hook = PostgresHook(postgres_conn_id=_POSTGRES_CONN_ID)
        rows = hook.get_records(
            f"""
            SELECT
                team_id,
                workspace_id,
                date_utc::text,
                calendar_density_score,
                after_hours_activity_index,
                context_switch_count,
                sprint_health_index
            FROM {_FEATURES_TABLE}
            WHERE date_utc = %(ds)s
            ORDER BY team_id
            LIMIT %(limit)s
            """,
            parameters={"ds": ds, "limit": _MAX_TEAMS_PER_RUN},
        )
        logger.info("Fetched %d team records for %s", len(rows), ds)
        cols = [
            "team_id", "workspace_id", "date_utc",
            "calendar_density_score", "after_hours_activity_index",
            "context_switch_count", "sprint_health_index",
        ]
        return [dict(zip(cols, row, strict=False)) for row in rows]

    @task()
    def score_teams(records: list[dict]) -> list[dict]:
        """Run the inference predictor on each team record.

        Cold-start mode is used (no LSTM history) for batch scoring since
        building per-team sequence history at DAG runtime is out of scope
        for the current sprint.

        Args:
            records: List of feature dicts from fetch_team_features.

        Returns:
            List of prediction result dicts ready for upsert.
        """
        # Import here so Airflow workers don't need the full ML stack at parse time
        from ml.inference.model_loader import load_models
        from ml.inference.predictor import BurnoutPredictor

        bundle = load_models()
        predictor = BurnoutPredictor(bundle)

        results: list[dict] = []
        for rec in records:
            try:
                features = {
                    k: rec[k]
                    for k in [
                        "calendar_density_score",
                        "after_hours_activity_index",
                        "context_switch_count",
                        "sprint_health_index",
                    ]
                }
                pred = predictor.predict(features)
                results.append(
                    {
                        "team_id": rec["team_id"],
                        "workspace_id": rec["workspace_id"],
                        "date_utc": rec["date_utc"],
                        "afs": pred.afs,
                        "resilience_zone": pred.resilience_zone,
                        "zone_label": pred.zone_label,
                        "probabilities": json.dumps(pred.probabilities),
                        "cold_start": pred.cold_start,
                        "model_version": pred.model_version,
                    }
                )
            except Exception as exc:
                logger.error("Scoring failed for team %s: %s", rec.get("team_id"), exc)

        logger.info("Scored %d / %d teams", len(results), len(records))
        return results

    @task()
    def upsert_predictions(predictions: list[dict]) -> None:
        """Write predictions to the warehouse with ON CONFLICT upsert.

        Args:
            predictions: List of prediction dicts from score_teams.
        """
        if not predictions:
            logger.info("No predictions to write")
            return

        hook = PostgresHook(postgres_conn_id=_POSTGRES_CONN_ID)
        conn = hook.get_conn()
        cursor = conn.cursor()

        upsert_sql = f"""
            INSERT INTO {_PREDICTIONS_TABLE} (
                team_id, workspace_id, date_utc,
                afs, resilience_zone, zone_label,
                probabilities, cold_start, model_version
            ) VALUES (
                %(team_id)s, %(workspace_id)s, %(date_utc)s,
                %(afs)s, %(resilience_zone)s, %(zone_label)s,
                %(probabilities)s, %(cold_start)s, %(model_version)s
            )
            ON CONFLICT (team_id, workspace_id, date_utc)
            DO UPDATE SET
                afs = EXCLUDED.afs,
                resilience_zone = EXCLUDED.resilience_zone,
                zone_label = EXCLUDED.zone_label,
                probabilities = EXCLUDED.probabilities,
                cold_start = EXCLUDED.cold_start,
                model_version = EXCLUDED.model_version
        """

        cursor.executemany(upsert_sql, predictions)
        conn.commit()
        cursor.close()
        logger.info("Upserted %d predictions into %s", len(predictions), _PREDICTIONS_TABLE)

    # ── DAG wiring ────────────────────────────────────────────────────────────
    records = fetch_team_features()
    predictions = score_teams(records)
    upsert_predictions(predictions)


batch_scoring_dag()
