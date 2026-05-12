"""Unit tests for RBAC dependency functions.

Tests verify that:
- require_authenticated rejects anonymous actors
- require_hr_admin rejects non-admin roles
- require_team_access enforces team_manager scope
"""

import pytest
from fastapi import HTTPException
from starlette.requests import Request

# ── Helpers ───────────────────────────────────────────────────────────────────

def _mock_request(
    user_id: str = "u1",
    user_name: str = "Alice",
    user_role: str = "hr_admin",
    team_id: str | None = None,
) -> Request:
    """Build a minimal ASGI Request with the auth headers the frontend sends."""
    headers: dict[str, str] = {
        "X-User-Id":   user_id,
        "X-User-Name": user_name,
        "X-User-Role": user_role,
    }
    if team_id is not None:
        headers["X-User-Team-Id"] = team_id

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/test",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "query_string": b"",
    }
    return Request(scope)


# ── require_authenticated ──────────────────────────────────────────────────────

def test_require_authenticated_passes_valid_user() -> None:
    from api.dependencies import require_authenticated
    actor = require_authenticated(_mock_request())
    assert actor["id"] == "u1"
    assert actor["name"] == "Alice"
    assert actor["role"] == "hr_admin"


def test_require_authenticated_raises_401_for_anonymous() -> None:
    from api.dependencies import require_authenticated
    with pytest.raises(HTTPException) as exc:
        require_authenticated(_mock_request(user_id="anonymous"))
    assert exc.value.status_code == 401


def test_require_authenticated_returns_team_id_for_manager() -> None:
    from api.dependencies import require_authenticated
    actor = require_authenticated(
        _mock_request(user_role="team_manager", team_id="team-eng")
    )
    assert actor["team_id"] == "team-eng"


def test_require_authenticated_team_id_none_when_header_absent() -> None:
    from api.dependencies import require_authenticated
    actor = require_authenticated(_mock_request(user_role="hr_admin"))
    assert actor["team_id"] is None


# ── require_hr_admin ──────────────────────────────────────────────────────────

def test_require_hr_admin_passes_for_hr_admin() -> None:
    from api.dependencies import require_hr_admin
    actor = {"id": "u1", "name": "Alice", "role": "hr_admin", "team_id": None}
    result = require_hr_admin(actor)
    assert result["role"] == "hr_admin"


def test_require_hr_admin_raises_403_for_team_manager() -> None:
    from api.dependencies import require_hr_admin
    actor = {"id": "u2", "name": "Bob", "role": "team_manager", "team_id": "T-1"}
    with pytest.raises(HTTPException) as exc:
        require_hr_admin(actor)
    assert exc.value.status_code == 403


def test_require_hr_admin_raises_403_for_viewer() -> None:
    from api.dependencies import require_hr_admin
    actor = {"id": "u3", "name": "Carol", "role": "viewer", "team_id": None}
    with pytest.raises(HTTPException) as exc:
        require_hr_admin(actor)
    assert exc.value.status_code == 403


# ── require_team_access ───────────────────────────────────────────────────────

def test_require_team_access_allows_hr_admin_any_team() -> None:
    from api.dependencies import require_team_access
    actor = {"id": "u1", "role": "hr_admin", "team_id": None}
    # Must not raise for any team_id
    require_team_access(actor, "team-frontend")
    require_team_access(actor, "team-infra")


def test_require_team_access_allows_viewer_any_team() -> None:
    from api.dependencies import require_team_access
    actor = {"id": "u3", "role": "viewer", "team_id": None}
    require_team_access(actor, "team-frontend")


def test_require_team_access_allows_manager_own_team() -> None:
    from api.dependencies import require_team_access
    actor = {"id": "u2", "role": "team_manager", "team_id": "team-eng"}
    require_team_access(actor, "team-eng")  # must not raise


def test_require_team_access_raises_403_for_manager_other_team() -> None:
    from api.dependencies import require_team_access
    actor = {"id": "u2", "role": "team_manager", "team_id": "team-eng"}
    with pytest.raises(HTTPException) as exc:
        require_team_access(actor, "team-frontend")
    assert exc.value.status_code == 403


def test_require_team_access_raises_403_when_manager_has_no_team_id() -> None:
    from api.dependencies import require_team_access
    # team_id missing from actor (header not sent) — should not grant access
    actor = {"id": "u2", "role": "team_manager", "team_id": None}
    with pytest.raises(HTTPException) as exc:
        require_team_access(actor, "team-frontend")
    assert exc.value.status_code == 403


def test_require_team_access_detail_contains_actor_and_team() -> None:
    from api.dependencies import require_team_access
    actor = {"id": "u2", "role": "team_manager", "team_id": "team-eng"}
    with pytest.raises(HTTPException) as exc:
        require_team_access(actor, "team-frontend")
    assert "u2" in str(exc.value.detail)
    assert "team-frontend" in str(exc.value.detail)
