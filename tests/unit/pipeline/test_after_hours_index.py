"""Unit tests for After-Hours Activity Index transform."""

from __future__ import annotations

from pipeline.transforms.after_hours_index import (
    _WEEKEND_WEIGHT,
    compute_after_hours_activity_index,
)
from tests.unit.pipeline.conftest import make_slack


# ── Edge cases ────────────────────────────────────────────────────────────────


def test_ahai_empty_events_returns_zero() -> None:
    assert compute_after_hours_activity_index([]) == 0.0


def test_ahai_all_zero_message_counts_returns_zero() -> None:
    events = [make_slack(message_count=0, is_after_hours=True)]
    assert compute_after_hours_activity_index(events) == 0.0


def test_ahai_no_after_hours_returns_zero() -> None:
    events = [make_slack(message_count=50, is_after_hours=False)]
    assert compute_after_hours_activity_index(events) == 0.0


# ── Normal computation ─────────────────────────────────────────────────────────


def test_ahai_all_after_hours_returns_one() -> None:
    events = [make_slack(message_count=10, is_after_hours=True)]
    assert compute_after_hours_activity_index(events) == 1.0


def test_ahai_half_and_half() -> None:
    # 50 after-hours, 50 business-hours → ratio = 0.5
    events = [
        make_slack(message_count=50, is_after_hours=True, day_of_week=0),
        make_slack(message_count=50, is_after_hours=False, day_of_week=0),
    ]
    result = compute_after_hours_activity_index(events)
    assert abs(result - 0.5) < 1e-9


def test_ahai_weekend_weight_increases_after_hours_proportion() -> None:
    # Without weekend weight: 10 after-hours / 20 total = 0.5
    # With weekend weight on the after-hours event (day=5):
    #   weighted_after = 10 × 1.5 = 15
    #   weighted_total = 10 × 1.5 + 10 × 1.0 = 25
    #   ratio = 15/25 = 0.6
    events = [
        make_slack(message_count=10, is_after_hours=True, day_of_week=5),
        make_slack(message_count=10, is_after_hours=False, day_of_week=0),
    ]
    result = compute_after_hours_activity_index(events)
    expected = (10 * _WEEKEND_WEIGHT) / (10 * _WEEKEND_WEIGHT + 10 * 1.0)
    assert abs(result - expected) < 1e-9


def test_ahai_sunday_also_applies_weekend_weight() -> None:
    events = [
        make_slack(message_count=10, is_after_hours=True, day_of_week=6),
        make_slack(message_count=10, is_after_hours=False, day_of_week=0),
    ]
    result = compute_after_hours_activity_index(events)
    expected = (10 * _WEEKEND_WEIGHT) / (10 * _WEEKEND_WEIGHT + 10 * 1.0)
    assert abs(result - expected) < 1e-9


def test_ahai_multiple_events_aggregated_correctly() -> None:
    events = [
        make_slack(message_count=30, is_after_hours=True, day_of_week=0),
        make_slack(message_count=20, is_after_hours=False, day_of_week=0),
        make_slack(message_count=10, is_after_hours=True, day_of_week=0),
    ]
    # after-hours: 40, total: 60 → 0.6667
    result = compute_after_hours_activity_index(events)
    assert abs(result - 40 / 60) < 1e-9


# ── Clamping ──────────────────────────────────────────────────────────────────


def test_ahai_never_exceeds_one() -> None:
    events = [make_slack(message_count=9999, is_after_hours=True, day_of_week=6)]
    assert compute_after_hours_activity_index(events) <= 1.0


def test_ahai_never_below_zero() -> None:
    result = compute_after_hours_activity_index([make_slack(is_after_hours=False)])
    assert result >= 0.0
