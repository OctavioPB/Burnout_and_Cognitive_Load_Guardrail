"""Shared fixtures for pipeline unit tests."""

from __future__ import annotations

from datetime import UTC, datetime

from ingestion.models import (
    CalendarActivityEvent,
    GitHubActivityEvent,
    JiraSprintEvent,
    SlackActivityEvent,
)

_DATE = "2024-01-15"
_WORKSPACE = "W001"
_TEAM = "T001"


def make_slack(
    message_count: int = 10,
    is_after_hours: bool = False,
    day_of_week: int = 0,
) -> SlackActivityEvent:
    return SlackActivityEvent(
        workspace_id=_WORKSPACE,
        team_id=_TEAM,
        channel_id="C001",
        hour_bucket_utc=datetime(2024, 1, 15, 10, 0, tzinfo=UTC),
        message_count=message_count,
        is_after_hours=is_after_hours,
        day_of_week=day_of_week,
    )


def make_calendar(
    total_meeting_minutes: int = 120,
    back_to_back_count: int = 2,
    meeting_count: int = 3,
    after_hours_meeting_minutes: int = 0,
) -> CalendarActivityEvent:
    return CalendarActivityEvent(
        workspace_id=_WORKSPACE,
        team_id=_TEAM,
        date_utc=_DATE,
        meeting_count=meeting_count,
        total_meeting_minutes=total_meeting_minutes,
        back_to_back_count=back_to_back_count,
        after_hours_meeting_minutes=after_hours_meeting_minutes,
    )


def make_jira(
    committed_points: int = 20,
    completed_points: int = 16,
    delivery_ratio: float = 0.8,
) -> JiraSprintEvent:
    return JiraSprintEvent(
        workspace_id=_WORKSPACE,
        team_id=_TEAM,
        sprint_id="SP-1",
        board_id="B-1",
        committed_points=committed_points,
        completed_points=completed_points,
        delivery_ratio=delivery_ratio,
        sprint_start_date="2024-01-08",
        sprint_end_date="2024-01-22",
    )


def make_github(
    avg_pr_cycle_time_hours: float = 4.0,
    repo_id: str = "123456",
    commit_count_after_hours: int = 1,
    total_commit_count: int = 5,
) -> GitHubActivityEvent:
    return GitHubActivityEvent(
        workspace_id=_WORKSPACE,
        team_id=_TEAM,
        date_utc=_DATE,
        repo_id=repo_id,
        pr_count_opened=1,
        pr_count_merged=1,
        avg_pr_cycle_time_hours=avg_pr_cycle_time_hours,
        avg_review_turnaround_hours=2.0,
        commit_count_after_hours=commit_count_after_hours,
        total_commit_count=total_commit_count,
    )
