"""Unit tests for Sprint Health Index transform."""

from __future__ import annotations

from pipeline.transforms.sprint_health import (
    _MAX_CYCLE_TIME_HOURS,
    compute_sprint_health_index,
)
from tests.unit.pipeline.conftest import make_github, make_jira


# ── Edge cases ────────────────────────────────────────────────────────────────


def test_shi_both_empty_returns_none() -> None:
    assert compute_sprint_health_index([], []) is None


def test_shi_only_jira_data_cycle_time_defaults_to_one() -> None:
    jira = [make_jira(committed_points=10, completed_points=10)]
    result = compute_sprint_health_index(jira, [])
    # delivery=1.0, cycle_time_component=1.0 → SHI=1.0
    assert result is not None
    assert abs(result - 1.0) < 1e-9


def test_shi_only_github_data_delivery_defaults_to_one() -> None:
    gh = [make_github(avg_pr_cycle_time_hours=0.0)]
    result = compute_sprint_health_index([], gh)
    # delivery=1.0, cycle_time=1-(0/48)=1.0 → SHI=1.0
    assert result is not None
    assert abs(result - 1.0) < 1e-9


def test_shi_zero_committed_points_delivery_defaults_to_one() -> None:
    jira = [make_jira(committed_points=0, completed_points=5)]
    gh = [make_github(avg_pr_cycle_time_hours=0.0)]
    result = compute_sprint_health_index(jira, gh)
    assert result is not None
    assert abs(result - 1.0) < 1e-9


# ── Delivery component ────────────────────────────────────────────────────────


def test_shi_partial_delivery_reduces_score() -> None:
    # 80 % delivery, 0 cycle time → SHI = 0.8
    jira = [make_jira(committed_points=10, completed_points=8)]
    gh = [make_github(avg_pr_cycle_time_hours=0.0)]
    result = compute_sprint_health_index(jira, gh)
    assert result is not None
    assert abs(result - 0.8) < 1e-9


def test_shi_delivery_ratio_clamped_to_one_when_over_committed() -> None:
    # Completed > committed (heroic sprint) — delivery capped at 1.0
    jira = [make_jira(committed_points=10, completed_points=15)]
    result = compute_sprint_health_index(jira, [])
    assert result is not None
    assert result <= 1.0


def test_shi_aggregates_multiple_jira_events() -> None:
    jira = [
        make_jira(committed_points=10, completed_points=8),
        make_jira(committed_points=10, completed_points=6),
    ]
    # total: 14/20 = 0.7
    result = compute_sprint_health_index(jira, [])
    assert result is not None
    assert abs(result - 0.7) < 1e-9


# ── Cycle-time component ──────────────────────────────────────────────────────


def test_shi_max_cycle_time_zeroes_cycle_component() -> None:
    gh = [make_github(avg_pr_cycle_time_hours=_MAX_CYCLE_TIME_HOURS)]
    result = compute_sprint_health_index([], gh)
    # cycle_component = 1 - (48/48) = 0.0 → SHI = 0.0
    assert result is not None
    assert abs(result - 0.0) < 1e-9


def test_shi_cycle_time_beyond_max_clamped() -> None:
    gh = [make_github(avg_pr_cycle_time_hours=_MAX_CYCLE_TIME_HOURS * 2)]
    result = compute_sprint_health_index([], gh)
    assert result is not None
    assert result >= 0.0


def test_shi_four_hour_cycle_time_expected_value() -> None:
    # delivery=1.0, cycle=1-(4/48)=11/12 ≈ 0.9167
    gh = [make_github(avg_pr_cycle_time_hours=4.0)]
    result = compute_sprint_health_index([], gh)
    expected = 1.0 - (4.0 / _MAX_CYCLE_TIME_HOURS)
    assert result is not None
    assert abs(result - expected) < 1e-9


def test_shi_combined_partial_delivery_and_moderate_cycle() -> None:
    # delivery = 0.8, cycle_component = 1 - (24/48) = 0.5 → SHI = 0.4
    jira = [make_jira(committed_points=10, completed_points=8)]
    gh = [make_github(avg_pr_cycle_time_hours=24.0)]
    result = compute_sprint_health_index(jira, gh)
    assert result is not None
    assert abs(result - 0.4) < 1e-9


# ── Output range ──────────────────────────────────────────────────────────────


def test_shi_never_exceeds_one() -> None:
    jira = [make_jira(committed_points=1, completed_points=1)]
    gh = [make_github(avg_pr_cycle_time_hours=0.0)]
    result = compute_sprint_health_index(jira, gh)
    assert result is not None
    assert result <= 1.0


def test_shi_never_below_zero() -> None:
    jira = [make_jira(committed_points=10, completed_points=0)]
    gh = [make_github(avg_pr_cycle_time_hours=_MAX_CYCLE_TIME_HOURS)]
    result = compute_sprint_health_index(jira, gh)
    assert result is not None
    assert result >= 0.0
