"""Pydantic v2 event models for all ingestion event types.

Privacy guarantee: none of these models contain user identifiers,
message content, document bodies, or any personal data. Only
metadata (timestamps, counts, durations) is represented.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field


def _now_utc() -> datetime:
    return datetime.now(tz=UTC)


class BaseEvent(BaseModel):
    """Common header for every ingestion event."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workspace_id: str
    team_id: str
    ingested_at: datetime = Field(default_factory=_now_utc)


class SlackActivityEvent(BaseEvent):
    """Channel-level message activity aggregated to a one-hour bucket.

    No user IDs, no message text, no reactions — only counts and timestamps.
    """

    channel_id: str
    hour_bucket_utc: datetime       # truncated to hour boundary, UTC
    message_count: int
    is_after_hours: bool            # true when hour < 9 or hour >= 18 (UTC)
    day_of_week: int                # 0 = Monday … 6 = Sunday


class CalendarActivityEvent(BaseEvent):
    """Team calendar load aggregated to a single calendar day.

    Attendee names and meeting titles are never captured.
    """

    date_utc: str                   # YYYY-MM-DD
    meeting_count: int
    total_meeting_minutes: int
    back_to_back_count: int         # adjacent meetings with < 5-minute gap
    after_hours_meeting_minutes: int  # minutes of meetings outside 09:00-18:00


class JiraSprintEvent(BaseEvent):
    """Sprint commitment vs. delivery ratio for a Jira board.

    Issue titles, descriptions, and assignees are never captured.
    """

    sprint_id: str
    board_id: str
    committed_points: int
    completed_points: int
    delivery_ratio: float           # completed / committed; 0.0 if committed == 0
    sprint_start_date: str          # YYYY-MM-DD
    sprint_end_date: str            # YYYY-MM-DD


class GitHubActivityEvent(BaseEvent):
    """PR cycle time and commit density aggregated to a calendar day.

    PR titles, commit messages, and author names are never captured.
    Repos are identified by numeric ID to avoid org/project name leakage.
    """

    date_utc: str                   # YYYY-MM-DD
    repo_id: str                    # GitHub numeric repo ID cast to string
    pr_count_opened: int
    pr_count_merged: int
    avg_pr_cycle_time_hours: float  # mean of (merged_at - created_at) for merged PRs
    avg_review_turnaround_hours: float  # mean time from PR open to first review
    commit_count_after_hours: int   # commits with author_date outside 09:00-18:00 UTC
    total_commit_count: int
