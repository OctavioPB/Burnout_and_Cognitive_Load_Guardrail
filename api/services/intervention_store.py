"""In-memory store for intervention records and audit log.

Both stores are module-level singletons.  In production, back them with
PostgreSQL (intervention_records table) and a structured log sink (audit_log).
The interface is designed so that swapping to a DB just means replacing the
two store classes without touching the router layer.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone

from api.schemas.interventions import (
    AuditAction,
    AuditLogEntry,
    IntegrationResult,
    InterventionRecord,
)

# ── Intervention record store ─────────────────────────────────────────────────

_INTERVENTION_TITLES: dict[str, str] = {
    "meeting_free_friday": "Meeting-Free Friday",
    "async_first_week":    "Async-First Week",
    "load_redistribution": "Load Redistribution Review",
    "focus_blocks":        "Deep Work Blocks",
}


class InterventionStore:
    """Tracks accepted / dismissed intervention actions per team."""

    def __init__(self) -> None:
        # team_id → list[InterventionRecord]
        self._records: dict[str, list[InterventionRecord]] = defaultdict(list)

    def apply(
        self,
        team_id: str,
        intervention_id: str,
        actor_id: str,
        actor_name: str,
        integration: IntegrationResult,
        customization: str | None = None,
    ) -> InterventionRecord:
        record = InterventionRecord(
            record_id=str(uuid.uuid4()),
            team_id=team_id,
            intervention_id=intervention_id,
            intervention_title=_INTERVENTION_TITLES.get(intervention_id, intervention_id),
            action="customized" if customization else "accepted",
            actor_id=actor_id,
            actor_name=actor_name,
            applied_at=_now(),
            customization=customization,
            integration=integration,
        )
        self._records[team_id].append(record)
        return record

    def dismiss(
        self,
        team_id: str,
        intervention_id: str,
        actor_id: str,
        actor_name: str,
    ) -> InterventionRecord:
        record = InterventionRecord(
            record_id=str(uuid.uuid4()),
            team_id=team_id,
            intervention_id=intervention_id,
            intervention_title=_INTERVENTION_TITLES.get(intervention_id, intervention_id),
            action="dismissed",
            actor_id=actor_id,
            actor_name=actor_name,
            applied_at=_now(),
            integration=IntegrationResult(integration="none", status="skipped"),
        )
        self._records[team_id].append(record)
        return record

    def records_for_team(self, team_id: str) -> list[InterventionRecord]:
        return list(self._records[team_id])

    def latest_for_intervention(
        self, team_id: str, intervention_id: str
    ) -> InterventionRecord | None:
        matches = [
            r for r in self._records[team_id]
            if r.intervention_id == intervention_id
        ]
        return matches[-1] if matches else None

    def all_records(self) -> list[InterventionRecord]:
        result: list[InterventionRecord] = []
        for records in self._records.values():
            result.extend(records)
        return sorted(result, key=lambda r: r.applied_at, reverse=True)


# ── Audit log store ───────────────────────────────────────────────────────────

class AuditStore:
    """Append-only audit log of dashboard read and write events."""

    def __init__(self) -> None:
        self._log: list[AuditLogEntry] = []

    def record(
        self,
        actor_id: str,
        actor_name: str,
        actor_role: str,
        action: AuditAction,
        resource: str,
        detail: str = "",
    ) -> None:
        entry = AuditLogEntry(
            log_id=str(uuid.uuid4()),
            actor_id=actor_id,
            actor_name=actor_name,
            actor_role=actor_role,
            action=action,
            resource=resource,
            timestamp=_now(),
            detail=detail,
        )
        self._log.append(entry)

    def entries(self, limit: int = 200) -> list[AuditLogEntry]:
        return list(reversed(self._log))[:limit]


# ── Module-level singletons ───────────────────────────────────────────────────

intervention_store = InterventionStore()
audit_store        = AuditStore()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
