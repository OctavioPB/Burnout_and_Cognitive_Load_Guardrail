"""FastAPI dependency functions for RBAC.

The staging auth contract: the frontend sends three headers on every request:
  X-User-Id      — unique user identifier
  X-User-Name    — display name
  X-User-Role    — one of: hr_admin | team_manager | viewer
  X-User-Team-Id — (team_manager only) the team_id this user can access

In production these headers would be validated against a signed JWT instead.
"""

from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, Request


def _actor_from_request(request: Request) -> dict[str, Any]:
    """Extract actor identity from request headers."""
    user_id   = request.headers.get("X-User-Id",   "anonymous")
    user_name = request.headers.get("X-User-Name",  "Anonymous User")
    user_role = request.headers.get("X-User-Role",  "viewer")
    team_id   = request.headers.get("X-User-Team-Id")
    return {
        "id":      user_id,
        "name":    user_name,
        "role":    user_role,
        "team_id": team_id,
    }


def require_authenticated(request: Request) -> dict[str, Any]:
    """Require any authenticated user (non-anonymous)."""
    actor = _actor_from_request(request)
    if actor["id"] == "anonymous":
        raise HTTPException(status_code=401, detail="Authentication required")
    return actor


def require_hr_admin(actor: dict[str, Any] = Depends(require_authenticated)) -> dict[str, Any]:
    """Require the HR Admin role."""
    if actor["role"] != "hr_admin":
        raise HTTPException(
            status_code=403,
            detail="HR Admin role required for this operation",
        )
    return actor


def require_team_access(actor: dict[str, Any], team_id: str) -> None:
    """Enforce that a team_manager can only access their own team.

    HR Admins and Viewers can access all teams.
    Raises HTTPException(403) if access is denied.
    """
    if actor["role"] == "team_manager" and actor.get("team_id") != team_id:
        raise HTTPException(
            status_code=403,
            detail=f"Team Manager '{actor['id']}' is not authorized to access team '{team_id}'",
        )
