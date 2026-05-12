"""Unit tests for Context-Switch Count transform."""

from __future__ import annotations

from pipeline.transforms.context_switch import (
    _MAX_DAILY_SWITCHES,
    compute_context_switch_count,
)
from tests.unit.pipeline.conftest import make_calendar, make_github

# ── Edge cases ────────────────────────────────────────────────────────────────


def test_csc_empty_both_returns_zero() -> None:
    assert compute_context_switch_count([], []) == 0.0


def test_csc_empty_calendar_uses_only_github() -> None:
    gh = [make_github(repo_id="111")]
    result = compute_context_switch_count([], gh)
    assert result == 1 / _MAX_DAILY_SWITCHES


def test_csc_empty_github_uses_only_calendar() -> None:
    cal = [make_calendar(back_to_back_count=4)]
    result = compute_context_switch_count(cal, [])
    assert result == 4 / _MAX_DAILY_SWITCHES


# ── Normal computation ─────────────────────────────────────────────────────────


def test_csc_combines_back_to_back_and_repos() -> None:
    # 3 back-to-back + 2 distinct repos = 5 raw switches
    cal = [make_calendar(back_to_back_count=3)]
    gh = [make_github(repo_id="A"), make_github(repo_id="B")]
    expected = 5 / _MAX_DAILY_SWITCHES
    assert abs(compute_context_switch_count(cal, gh) - expected) < 1e-9


def test_csc_deduplicates_repos() -> None:
    # Same repo_id in two events → only 1 distinct repo
    gh = [make_github(repo_id="SAME"), make_github(repo_id="SAME")]
    result = compute_context_switch_count([], gh)
    assert result == 1 / _MAX_DAILY_SWITCHES


def test_csc_aggregates_back_to_back_across_events() -> None:
    cal = [make_calendar(back_to_back_count=2), make_calendar(back_to_back_count=3)]
    result = compute_context_switch_count(cal, [])
    assert result == 5 / _MAX_DAILY_SWITCHES


def test_csc_ignores_empty_repo_id() -> None:
    gh = [make_github(repo_id=""), make_github(repo_id="123")]
    result = compute_context_switch_count([], gh)
    # empty string filtered out → 1 distinct repo
    assert result == 1 / _MAX_DAILY_SWITCHES


# ── Clamping ──────────────────────────────────────────────────────────────────


def test_csc_clamped_to_one_when_switches_exceed_max() -> None:
    cal = [make_calendar(back_to_back_count=_MAX_DAILY_SWITCHES + 10)]
    assert compute_context_switch_count(cal, []) == 1.0


def test_csc_never_exceeds_one() -> None:
    cal = [make_calendar(back_to_back_count=100)]
    assert compute_context_switch_count(cal, []) <= 1.0


def test_csc_never_below_zero() -> None:
    assert compute_context_switch_count([], []) >= 0.0
