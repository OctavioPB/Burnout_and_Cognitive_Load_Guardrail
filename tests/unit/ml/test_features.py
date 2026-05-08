"""Unit tests for ml.training.features — AFS computation and zone mapping."""

from __future__ import annotations

import pytest

from ml.training.features import (
    AFS_WEIGHTS,
    ResilienceZone,
    TeamDayFeatureRecord,
    afs_to_zone,
    compute_afs,
    compute_afs_from_row,
)


# ── ResilienceZone ─────────────────────────────────────────────────────────────


def test_zone_labels_are_ordered() -> None:
    assert ResilienceZone.GREEN.label == 0
    assert ResilienceZone.YELLOW.label == 1
    assert ResilienceZone.RED.label == 2


def test_afs_to_zone_green_boundary() -> None:
    assert afs_to_zone(0.0) == ResilienceZone.GREEN
    assert afs_to_zone(39.9) == ResilienceZone.GREEN


def test_afs_to_zone_yellow_boundary() -> None:
    assert afs_to_zone(40.0) == ResilienceZone.YELLOW
    assert afs_to_zone(69.9) == ResilienceZone.YELLOW


def test_afs_to_zone_red_boundary() -> None:
    assert afs_to_zone(70.0) == ResilienceZone.RED
    assert afs_to_zone(100.0) == ResilienceZone.RED


# ── AFS weights ────────────────────────────────────────────────────────────────


def test_afs_weights_sum_to_one() -> None:
    assert abs(sum(AFS_WEIGHTS.values()) - 1.0) < 1e-9


# ── compute_afs ────────────────────────────────────────────────────────────────


def test_afs_zero_stress_returns_near_zero() -> None:
    # All features at min stress: switches=0, density=0, after_hours=0, health=1
    afs = compute_afs(0.0, 0.0, 0.0, 1.0)
    assert afs == pytest.approx(0.0, abs=1.0)


def test_afs_max_stress_returns_near_hundred() -> None:
    # All features at max stress
    afs = compute_afs(1.0, 1.0, 1.0, 0.0)
    assert afs == pytest.approx(100.0, abs=1.0)


def test_afs_range_always_0_to_100() -> None:
    for _ in range(50):
        import random
        afs = compute_afs(
            random.random(), random.random(), random.random(), random.random()
        )
        assert 0.0 <= afs <= 100.0


def test_afs_sprint_health_none_uses_neutral() -> None:
    afs_with_none = compute_afs(0.3, 0.3, 0.3, None)
    afs_with_half = compute_afs(0.3, 0.3, 0.3, 0.5)
    assert abs(afs_with_none - afs_with_half) < 1e-6


def test_afs_sprint_health_inverted() -> None:
    # Lower SHI → higher AFS (worse health = more fragmentation)
    afs_low_health = compute_afs(0.5, 0.5, 0.5, 0.1)
    afs_high_health = compute_afs(0.5, 0.5, 0.5, 0.9)
    assert afs_low_health > afs_high_health


def test_afs_each_component_increases_score() -> None:
    base = compute_afs(0.2, 0.2, 0.2, 0.8)
    assert compute_afs(0.8, 0.2, 0.2, 0.8) > base  # higher context switch
    assert compute_afs(0.2, 0.8, 0.2, 0.8) > base  # higher density
    assert compute_afs(0.2, 0.2, 0.8, 0.8) > base  # higher after-hours
    assert compute_afs(0.2, 0.2, 0.2, 0.1) > base  # lower health → higher AFS


def test_afs_formula_matches_manual_calculation() -> None:
    csc, cds, ahai, shi = 0.4, 0.3, 0.2, 0.6
    expected_raw = (
        AFS_WEIGHTS["context_switch_count"] * csc
        + AFS_WEIGHTS["calendar_density_score"] * cds
        + AFS_WEIGHTS["after_hours_activity_index"] * ahai
        + AFS_WEIGHTS["sprint_health_index"] * (1.0 - shi)
    ) * 100.0
    assert compute_afs(csc, cds, ahai, shi) == pytest.approx(expected_raw, abs=1e-6)


# ── compute_afs_from_row ──────────────────────────────────────────────────────


def test_afs_from_row_equivalent_to_direct() -> None:
    row = {
        "context_switch_count": 0.4,
        "calendar_density_score": 0.3,
        "after_hours_activity_index": 0.2,
        "sprint_health_index": 0.7,
    }
    direct = compute_afs(0.4, 0.3, 0.2, 0.7)
    from_row = compute_afs_from_row(row)
    assert abs(direct - from_row) < 1e-6


def test_afs_from_row_handles_missing_keys() -> None:
    row: dict = {}
    afs = compute_afs_from_row(row)
    # All defaults: stress=0 except SHI=0.5 (neutral)
    assert 0.0 <= afs <= 100.0


# ── TeamDayFeatureRecord ──────────────────────────────────────────────────────


def test_feature_record_computes_afs_on_init() -> None:
    rec = TeamDayFeatureRecord(
        team_id="T1",
        workspace_id="W1",
        date_utc="2024-01-15",
        calendar_density_score=0.3,
        after_hours_activity_index=0.1,
        context_switch_count=0.2,
        sprint_health_index=0.8,
    )
    assert 0.0 <= rec.afs <= 100.0


def test_feature_record_zone_matches_afs() -> None:
    rec = TeamDayFeatureRecord(
        team_id="T1",
        workspace_id="W1",
        date_utc="2024-01-15",
        calendar_density_score=0.9,
        after_hours_activity_index=0.8,
        context_switch_count=0.9,
        sprint_health_index=0.1,
    )
    assert rec.resilience_zone == ResilienceZone.RED
    assert rec.afs >= 70.0


def test_feature_record_to_dict_has_all_keys() -> None:
    rec = TeamDayFeatureRecord(
        team_id="T1",
        workspace_id="W1",
        date_utc="2024-01-15",
        calendar_density_score=0.2,
        after_hours_activity_index=0.05,
        context_switch_count=0.1,
        sprint_health_index=0.9,
    )
    d = rec.to_dict()
    expected_keys = {
        "team_id", "workspace_id", "date_utc",
        "calendar_density_score", "after_hours_activity_index",
        "context_switch_count", "sprint_health_index",
        "afs", "resilience_zone",
    }
    assert set(d.keys()) == expected_keys
