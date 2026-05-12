"""Unit tests for InterventionStore and AuditStore."""

import pytest

from api.schemas.interventions import IntegrationResult
from api.services.intervention_store import AuditStore, InterventionStore

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def store() -> InterventionStore:
    """Fresh store per test — isolates state."""
    return InterventionStore()


@pytest.fixture
def audit() -> AuditStore:
    return AuditStore()


def _integration(name: str = "none") -> IntegrationResult:
    return IntegrationResult(integration=name, status="success")


# ── InterventionStore: apply ───────────────────────────────────────────────────

def test_apply_returns_record(store: InterventionStore) -> None:
    r = store.apply("T-1", "meeting_free_friday", "u1", "Alice", _integration("google_calendar"))
    assert r.team_id == "T-1"
    assert r.intervention_id == "meeting_free_friday"
    assert r.action == "accepted"
    assert r.actor_name == "Alice"


def test_apply_resolves_known_title(store: InterventionStore) -> None:
    r = store.apply("T-1", "load_redistribution", "u1", "Alice", _integration())
    assert r.intervention_title == "Load Redistribution Review"


def test_apply_unknown_id_uses_id_as_title(store: InterventionStore) -> None:
    r = store.apply("T-1", "custom_intervention_xyz", "u1", "Alice", _integration())
    assert r.intervention_title == "custom_intervention_xyz"


def test_apply_with_customization_sets_customized_action(store: InterventionStore) -> None:
    r = store.apply(
        "T-1", "async_first_week", "u1", "Alice",
        _integration("slack"), customization="Async week is on."
    )
    assert r.action == "customized"
    assert r.customization == "Async week is on."


def test_apply_without_customization_sets_accepted_action(store: InterventionStore) -> None:
    r = store.apply("T-1", "meeting_free_friday", "u1", "Alice", _integration(), customization=None)
    assert r.action == "accepted"
    assert r.customization is None


def test_apply_record_id_is_unique(store: InterventionStore) -> None:
    r1 = store.apply("T-1", "focus_blocks", "u1", "Alice", _integration())
    r2 = store.apply("T-1", "focus_blocks", "u1", "Alice", _integration())
    assert r1.record_id != r2.record_id


def test_apply_record_has_iso_timestamp(store: InterventionStore) -> None:
    r = store.apply("T-1", "focus_blocks", "u1", "Alice", _integration())
    # ISO 8601 UTC — must end with +00:00 or Z
    assert "T" in r.applied_at


# ── InterventionStore: dismiss ────────────────────────────────────────────────

def test_dismiss_returns_dismissed_record(store: InterventionStore) -> None:
    r = store.dismiss("T-1", "meeting_free_friday", "u1", "Alice")
    assert r.action == "dismissed"
    assert r.team_id == "T-1"


def test_dismiss_integration_is_none_skipped(store: InterventionStore) -> None:
    r = store.dismiss("T-1", "focus_blocks", "u1", "Alice")
    assert r.integration.integration == "none"
    assert r.integration.status == "skipped"


# ── InterventionStore: records_for_team ───────────────────────────────────────

def test_records_for_team_empty_by_default(store: InterventionStore) -> None:
    assert store.records_for_team("T-unknown") == []


def test_records_for_team_returns_only_that_team(store: InterventionStore) -> None:
    store.apply("T-1", "focus_blocks",        "u1", "Alice", _integration())
    store.apply("T-2", "meeting_free_friday",  "u2", "Bob",   _integration())
    store.dismiss("T-1", "async_first_week",   "u1", "Alice")

    t1 = store.records_for_team("T-1")
    t2 = store.records_for_team("T-2")

    assert len(t1) == 2
    assert len(t2) == 1
    assert all(r.team_id == "T-1" for r in t1)


def test_records_for_team_preserves_insertion_order(store: InterventionStore) -> None:
    store.apply("T-1",   "focus_blocks",        "u1", "Alice", _integration())
    store.dismiss("T-1", "meeting_free_friday", "u1", "Alice")
    records = store.records_for_team("T-1")
    assert records[0].intervention_id == "focus_blocks"
    assert records[1].intervention_id == "meeting_free_friday"


# ── InterventionStore: latest_for_intervention ────────────────────────────────

def test_latest_for_intervention_returns_none_when_absent(store: InterventionStore) -> None:
    assert store.latest_for_intervention("T-1", "focus_blocks") is None


def test_latest_for_intervention_returns_last_record(store: InterventionStore) -> None:
    store.apply("T-1",   "focus_blocks", "u1", "Alice", _integration())
    store.dismiss("T-1", "focus_blocks", "u1", "Alice")
    latest = store.latest_for_intervention("T-1", "focus_blocks")
    assert latest is not None
    assert latest.action == "dismissed"


def test_latest_for_intervention_ignores_other_interventions(store: InterventionStore) -> None:
    store.apply("T-1", "focus_blocks",        "u1", "Alice", _integration())
    store.apply("T-1", "meeting_free_friday",  "u1", "Alice", _integration())
    latest = store.latest_for_intervention("T-1", "meeting_free_friday")
    assert latest is not None
    assert latest.intervention_id == "meeting_free_friday"


# ── InterventionStore: all_records ────────────────────────────────────────────

def test_all_records_empty_initially(store: InterventionStore) -> None:
    assert store.all_records() == []


def test_all_records_aggregates_all_teams(store: InterventionStore) -> None:
    store.apply("T-1", "focus_blocks",       "u1", "Alice", _integration())
    store.apply("T-2", "load_redistribution", "u2", "Bob",   _integration())
    store.dismiss("T-3", "async_first_week", "u3", "Carol")
    assert len(store.all_records()) == 3


def test_all_records_sorted_descending_by_timestamp(store: InterventionStore) -> None:
    store.apply("T-1", "focus_blocks",        "u1", "Alice", _integration())
    store.apply("T-2", "meeting_free_friday",  "u2", "Bob",   _integration())
    records = store.all_records()
    # Later records appear first
    timestamps = [r.applied_at for r in records]
    assert timestamps == sorted(timestamps, reverse=True)


# ── AuditStore ────────────────────────────────────────────────────────────────

def test_audit_entries_empty_initially(audit: AuditStore) -> None:
    assert audit.entries() == []


def test_audit_record_appends_entry(audit: AuditStore) -> None:
    audit.record("u1", "Alice", "hr_admin", "view_dashboard", "/dashboard/summary")
    entries = audit.entries()
    assert len(entries) == 1
    assert entries[0].actor_id == "u1"
    assert entries[0].action == "view_dashboard"


def test_audit_entries_are_newest_first(audit: AuditStore) -> None:
    audit.record("u1", "Alice", "hr_admin", "view_dashboard",  "/dashboard/summary")
    audit.record("u1", "Alice", "hr_admin", "view_alerts",     "/alerts")
    entries = audit.entries()
    assert entries[0].action == "view_alerts"
    assert entries[1].action == "view_dashboard"


def test_audit_entries_limit_respected(audit: AuditStore) -> None:
    for i in range(20):
        audit.record("u1", "Alice", "hr_admin", "view_dashboard", f"/path/{i}")
    assert len(audit.entries(limit=5)) == 5


def test_audit_entry_log_id_is_unique(audit: AuditStore) -> None:
    audit.record("u1", "Alice", "hr_admin", "view_dashboard", "/dashboard/summary")
    audit.record("u1", "Alice", "hr_admin", "view_alerts",    "/alerts")
    ids = [e.log_id for e in audit.entries()]
    assert ids[0] != ids[1]


def test_audit_detail_stored_correctly(audit: AuditStore) -> None:
    audit.record("u1", "Alice", "hr_admin", "apply_intervention", "/interventions/T-1/apply",
                 detail="meeting_free_friday")
    assert audit.entries()[0].detail == "meeting_free_friday"
