"""Unit tests for Calendar Density Score transform."""

from __future__ import annotations

from pipeline.transforms.calendar_density import (
    _WORK_MINUTES_PER_DAY,
    compute_calendar_density_score,
)
from tests.unit.pipeline.conftest import make_calendar


# ── Edge cases ────────────────────────────────────────────────────────────────


def test_cds_empty_events_returns_zero() -> None:
    assert compute_calendar_density_score([], team_size=5) == 0.0


def test_cds_zero_team_size_returns_zero() -> None:
    assert compute_calendar_density_score([make_calendar()], team_size=0) == 0.0


def test_cds_negative_team_size_returns_zero() -> None:
    assert compute_calendar_density_score([make_calendar()], team_size=-1) == 0.0


# ── Normal computation ─────────────────────────────────────────────────────────


def test_cds_exact_half_day() -> None:
    # 240 min out of 480 for 1 person = 0.5
    event = make_calendar(total_meeting_minutes=240)
    result = compute_calendar_density_score([event], team_size=1)
    assert abs(result - 0.5) < 1e-9


def test_cds_aggregates_multiple_events() -> None:
    # Two events: 120 min each → 240 min total, team_size=1 → 0.5
    events = [make_calendar(total_meeting_minutes=120), make_calendar(total_meeting_minutes=120)]
    result = compute_calendar_density_score(events, team_size=1)
    assert abs(result - 0.5) < 1e-9


def test_cds_normalises_by_team_size() -> None:
    # 480 min total, team_size=2 → 240 min per person → CDS = 0.5
    event = make_calendar(total_meeting_minutes=480)
    result = compute_calendar_density_score([event], team_size=2)
    assert abs(result - 0.5) < 1e-9


def test_cds_formula_matches_manual_calculation() -> None:
    minutes = 300
    team_size = 5
    expected = minutes / (team_size * _WORK_MINUTES_PER_DAY)
    event = make_calendar(total_meeting_minutes=minutes)
    assert abs(compute_calendar_density_score([event], team_size=team_size) - expected) < 1e-9


# ── Clamping ──────────────────────────────────────────────────────────────────


def test_cds_clamped_to_one_when_meetings_exceed_full_day() -> None:
    # 1000 min far exceeds 480 → must be clamped to 1.0
    event = make_calendar(total_meeting_minutes=1000)
    assert compute_calendar_density_score([event], team_size=1) == 1.0


def test_cds_never_exceeds_one() -> None:
    event = make_calendar(total_meeting_minutes=_WORK_MINUTES_PER_DAY + 1)
    result = compute_calendar_density_score([event], team_size=1)
    assert result <= 1.0


def test_cds_never_below_zero() -> None:
    result = compute_calendar_density_score([make_calendar(total_meeting_minutes=0)], team_size=5)
    assert result >= 0.0
