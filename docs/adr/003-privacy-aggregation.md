# ADR-003 — Team-Level Aggregation to Preserve Privacy

**Status:** Accepted  
**Date:** 2026-05-06  
**Deciders:** Legal/DPO, Platform Engineering, Product

---

## Context

The system ingests collaboration metadata (timestamps, durations, counts) from employee-facing tools. Even without capturing content, metadata can be highly privacy-sensitive:

- Knowing that an individual sent Slack messages at 2am reveals behavioral patterns.
- Calendar metadata reveals meeting participants and one-on-one patterns.
- GitHub commit timestamps reveal when an engineer works, not just how much.

The product is aimed at HR teams making organizational decisions. HR does not need individual-level signals to take meaningful action — team-level trends are sufficient for interventions like "Meeting-Free Friday" or "Load Redistribution."

**Privacy-by-design alternatives evaluated:**
1. Individual-level scores with role-based access
2. Individual-level scores with differential privacy noise
3. Team-level aggregation only (no individual scores)
4. Anonymized individual scores (k-anonymity)

---

## Decision

All features are aggregated to the **team unit** grain before leaving the ETL pipeline. No individual-level scores, attributions, or identifiers appear in the `features.team_daily` table, the inference API, or the dashboard.

Raw individual events in Kafka are retained for ≤7 days and are accessible only to the ingestion service. The ETL pipeline aggregates and discards the individual records.

---

## Rationale

**Why not individual-level scores with RBAC:**
Even with access control, individual scores create a surveillance dynamic that undermines trust and could expose the organization to legal risk in GDPR, CCPA, or local labor law jurisdictions. HR managers should not be able to profile individual engineers.

**Why not differential privacy noise:**
DP noise calibration for small teams (< 10 members) requires very high noise levels to provide meaningful guarantees, making the scores inaccurate enough to be misleading. Team-level aggregation naturally provides a stronger privacy guarantee for small groups.

**Why not k-anonymity:**
k-anonymity prevents re-identification through quasi-identifiers but does not prevent HR from building accurate profiles of small teams where the "anonymous" individual is easily guessed from organizational context.

**Why team aggregation wins:**
- Simplest to implement and audit.
- Strongest privacy guarantee — individual signals are not stored, not transmitted, not scored.
- Legally defensible under GDPR Article 4(1): aggregated team metrics do not constitute personal data when the team size prevents re-identification.
- Consent is cleaner: workspace-level opt-in rather than per-user consent flows.

---

## Consequences

**Positive:**
- No individual burnout scores — eliminates the primary legal and ethical risk.
- Simplifies GDPR/CCPA compliance: the system processes personal data only in transit (raw events, ≤7 days), then replaces it with non-personal aggregates.
- HR stakeholders receive actionable team-level signals without surveillance capabilities.
- Audit surface is smaller: only the ETL aggregation pipeline touches raw individual data.

**Negative:**
- Cannot detect a single high-burnout individual on a healthy team (the individual's signal is averaged away).
- Team size heterogeneity matters: a 3-person team's metrics are more volatile and re-identifiable than a 20-person team's. Minimum team size threshold enforced at 5 members — teams smaller than 5 receive "Insufficient data" instead of a score.

**Constraints this enforces on the codebase:**
- The `features.team_daily` table schema must not include `user_id` or any individual identifier.
- The inference API must reject requests that include user-level fields in the input payload.
- Any Kafka consumer that writes to the feature store must aggregate before writing.
- Dashboard components are prohibited from rendering per-person breakdowns.
