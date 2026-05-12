"""Persistence layer for features.team_daily.

All writes use PostgreSQL INSERT … ON CONFLICT DO UPDATE so every re-run of the
DAG for the same (team_id, workspace_id, date_utc) overwrites the previous row
rather than inserting a duplicate.  This is the primary idempotency guarantee.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from pipeline.models import TeamDailyFeature

logger = logging.getLogger(__name__)


async def upsert_team_daily_features(
    engine: AsyncEngine,
    records: list[dict[str, Any]],
) -> int:
    """Upsert a batch of feature dicts into features.team_daily.

    Args:
        engine: Async SQLAlchemy engine pointed at the data warehouse.
        records: List of dicts, each keyed by TeamDailyFeature column names.
                 Must contain team_id, workspace_id, date_utc, and computed_at.

    Returns:
        Number of rows inserted or updated.
    """
    if not records:
        return 0

    # Stamp computed_at if caller didn't supply it
    now = datetime.now(tz=UTC)
    for rec in records:
        rec.setdefault("computed_at", now)

    async with AsyncSession(engine) as session:
        stmt = pg_insert(TeamDailyFeature).values(records)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_team_daily_team_date",
            set_={
                "calendar_density_score": stmt.excluded.calendar_density_score,
                "after_hours_activity_index": stmt.excluded.after_hours_activity_index,
                "context_switch_count": stmt.excluded.context_switch_count,
                "sprint_health_index": stmt.excluded.sprint_health_index,
                "team_size": stmt.excluded.team_size,
                "computed_at": stmt.excluded.computed_at,
                "kafka_slack_offset": stmt.excluded.kafka_slack_offset,
                "kafka_calendar_offset": stmt.excluded.kafka_calendar_offset,
                "kafka_jira_offset": stmt.excluded.kafka_jira_offset,
                "kafka_github_offset": stmt.excluded.kafka_github_offset,
            },
        )
        result = await session.execute(stmt)
        await session.commit()
        rowcount: int = getattr(result, "rowcount", 0) or 0
        logger.info("upserted %d feature rows", rowcount)
        return rowcount
