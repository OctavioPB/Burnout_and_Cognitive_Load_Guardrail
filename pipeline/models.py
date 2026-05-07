"""SQLAlchemy ORM model for the features.team_daily table.

The UNIQUE constraint on (team_id, workspace_id, date_utc) is the idempotency key —
every upsert targeting the same team-day overwrites the previous values rather than
inserting a duplicate row.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TeamDailyFeature(Base):
    """One row per (team_id, workspace_id, date_utc) — daily aggregate features."""

    __tablename__ = "team_daily"
    __table_args__ = (
        UniqueConstraint(
            "team_id", "workspace_id", "date_utc", name="uq_team_daily_team_date"
        ),
        {"schema": "features"},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    team_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(String, nullable=False)
    date_utc: Mapped[date] = mapped_column(Date, nullable=False)

    # ── Feature columns ──────────────────────────────────────────────────────
    calendar_density_score: Mapped[Optional[float]] = mapped_column(Float)
    after_hours_activity_index: Mapped[Optional[float]] = mapped_column(Float)
    context_switch_count: Mapped[Optional[float]] = mapped_column(Float)
    sprint_health_index: Mapped[Optional[float]] = mapped_column(Float)
    team_size: Mapped[Optional[int]] = mapped_column(Integer)

    # ── Lineage — last Kafka offset consumed per source topic ────────────────
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    kafka_slack_offset: Mapped[Optional[int]] = mapped_column(Integer)
    kafka_calendar_offset: Mapped[Optional[int]] = mapped_column(Integer)
    kafka_jira_offset: Mapped[Optional[int]] = mapped_column(Integer)
    kafka_github_offset: Mapped[Optional[int]] = mapped_column(Integer)
