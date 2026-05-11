# OWASP Top 10 Security Checklist — Burnout Guardrail API

> **Date:** 2026-05-11  
> **Scope:** `api/` FastAPI backend + React dashboard frontend  
> **Standard:** OWASP Top 10 (2021)

Legend: ✅ Mitigated | ⚠️ Partial | ❌ Not mitigated | N/A Not applicable

---

## A01 — Broken Access Control ✅

| Control | Status | Implementation |
|---|---|---|
| Unauthenticated access blocked on sensitive endpoints | ✅ | `require_authenticated` dependency; 401 on missing/anonymous headers |
| HR Admin-only endpoints protected | ✅ | `require_hr_admin` dependency on `/audit`; 403 for other roles |
| Team Manager scope enforced | ✅ | `require_team_access()` blocks cross-team access; verified by `test_rbac.py` |
| IDOR prevention on team data | ✅ | `team_id` validated against actor's `team_id` for managers |
| Directory traversal blocked | ✅ | FastAPI path parameters are validated; no filesystem paths in routes |
| Missing function-level access control | ✅ | All POST routes check `require_authenticated` via `Depends()` |

**Residual risk:** Auth header trust model is staging-only. Production must validate signed JWTs — swap `_actor_from_request()` in `api/dependencies.py`.

---

## A02 — Cryptographic Failures ✅ / ⚠️

| Control | Status | Implementation |
|---|---|---|
| HTTPS enforced | ✅ | nginx `return 301 https://...` redirect + HSTS header |
| TLS 1.2+ only | ✅ | `ssl_protocols TLSv1.2 TLSv1.3` in nginx.conf |
| Weak ciphers disabled | ✅ | Only ECDHE+AES-GCM and CHACHA20 cipher suites |
| Sensitive data not logged | ✅ | Logging middleware logs actor_id and path only; no request bodies |
| Secrets not in source code | ✅ | All secrets via env vars / Secrets Manager; `.env` in `.gitignore` |
| Data at rest encryption | ⚠️ | Postgres volume encryption depends on AWS RDS/EBS config — not code-level |

**Action:** Enable AWS RDS encryption at rest (`StorageEncrypted: true` in Terraform) before production launch.

---

## A03 — Injection ✅

| Control | Status | Implementation |
|---|---|---|
| SQL injection | N/A | No raw SQL in Sprint 7–8; in-memory store. Pydantic v2 validates all inputs |
| NoSQL injection | N/A | Redis used for caching only; keys are deterministic slugs |
| Command injection | ✅ | No `subprocess` calls with user input anywhere in `api/` |
| LDAP injection | N/A | No LDAP used |
| Path traversal via `team_id` | ✅ | `team_id` used only as dict key, not in filesystem paths |
| Template injection | ✅ | No server-side templating; all responses are Pydantic-serialised JSON |

---

## A04 — Insecure Design ✅

| Control | Status | Implementation |
|---|---|---|
| Privacy by design — no individual-level data | ✅ | Aggregation at team level enforced in `api/services/mock_data.py` and documented in ADR-003 |
| Consent-first data collection | ✅ | Onboarding checklist requires consent activation before any connector runs |
| Audit logging of all data access | ✅ | `audit_middleware` in `api/main.py` logs every GET by authenticated actors |
| Threat model documented | ✅ | This document covers the API surface |

---

## A05 — Security Misconfiguration ✅

| Control | Status | Implementation |
|---|---|---|
| Security headers present | ✅ | `SecurityHeadersMiddleware`: CSP, HSTS, X-Frame-Options, nosniff, Referrer-Policy, Permissions-Policy |
| Server header removed | ✅ | `SecurityHeadersMiddleware` strips `Server` and `X-Powered-By` |
| Debug mode disabled in production | ✅ | `uvicorn --no-access-log` in prod; `ENVIRONMENT=production` guard |
| CORS restricted | ✅ | Only `localhost:5173`, `localhost:4173`, and `ALLOWED_ORIGINS` env var are permitted |
| `/metrics` not publicly accessible | ✅ | nginx blocks `/api/metrics` for external traffic |
| Default credentials changed | ✅ | All secrets via Secrets Manager; no hardcoded defaults |
| Stack traces not exposed | ✅ | `_unhandled` exception handler returns generic `{"detail": "Internal server error"}` |

---

## A06 — Vulnerable and Outdated Components ⚠️

| Control | Status | Implementation |
|---|---|---|
| Python dependencies pinned | ⚠️ | `pyproject.toml` uses `>=` floor pins; no lockfile checked in |
| Automated dependency scanning | ⚠️ | GitHub Dependabot not yet configured |
| Frontend dependencies | ⚠️ | `npm audit` not in CI pipeline yet |

**Action items:**
1. Add `pip-audit` to CI: `pip-audit --requirement requirements.txt`
2. Add `npm audit --audit-level=high` to the frontend CI job
3. Enable Dependabot in `.github/dependabot.yml`

---

## A07 — Identification and Authentication Failures ⚠️

| Control | Status | Implementation |
|---|---|---|
| Unauthenticated access rejected | ✅ | 401 on missing `X-User-Id` header |
| Brute force protection | ⚠️ | nginx rate-limiting (10 req/s per IP) mitigates but doesn't prevent credential stuffing |
| Session fixation | N/A | Stateless API; no server-side sessions |
| JWT expiry enforced | ⚠️ | JWT validation not yet implemented (staging uses header trust) |

**Action:** Implement JWT validation in `api/dependencies.py` (`_actor_from_request`) before production launch using `python-jose` (already in dependencies).

---

## A08 — Software and Data Integrity Failures ✅

| Control | Status | Implementation |
|---|---|---|
| Input validation on all API bodies | ✅ | Pydantic v2 models on all request bodies with strict types |
| Intervention ID validated | ✅ | Unknown `intervention_id` falls through to `case _` with no external call |
| CI pipeline integrity | ✅ | GitHub Actions with pinned action versions (to be verified in CI setup) |

---

## A09 — Security Logging and Monitoring Failures ✅

| Control | Status | Implementation |
|---|---|---|
| All authenticated reads logged | ✅ | `audit_middleware` + `AuditStore` with actor identity + timestamp |
| All intervention write actions logged | ✅ | Explicit `audit_store.record()` in intervention router |
| Structured JSON logs | ✅ | `CorrelationLoggingMiddleware` with structlog JSON renderer |
| Correlation IDs on all requests | ✅ | `X-Request-Id` generated/propagated per request |
| Alerting on anomalous patterns | ✅ | Prometheus alerting rules in `infra/monitoring/prometheus/alerts.yaml` |

---

## A10 — Server-Side Request Forgery (SSRF) ✅ / N/A

| Control | Status | Implementation |
|---|---|---|
| Integration adapter URLs hardcoded | ✅ | Calendar/Jira/Slack URLs come from env vars, not user input |
| No URL parameters passed to outbound requests | ✅ | `team_id` is used only as a data key in integration calls, never as a URL |

---

## Summary

| Category | Status |
|---|---|
| Broken Access Control | ✅ Mitigated |
| Cryptographic Failures | ✅ / ⚠️ At-rest encryption depends on infra config |
| Injection | ✅ Mitigated |
| Insecure Design | ✅ Mitigated |
| Security Misconfiguration | ✅ Mitigated |
| Vulnerable Components | ⚠️ Automated scanning not yet in CI |
| Auth Failures | ⚠️ JWT validation needed before production |
| Data Integrity | ✅ Mitigated |
| Logging & Monitoring | ✅ Mitigated |
| SSRF | ✅ / N/A |

**Pre-launch blockers:** A02 (DB encryption at rest), A07 (JWT validation)
**Post-launch hardening:** A06 (Dependabot + pip-audit in CI)
