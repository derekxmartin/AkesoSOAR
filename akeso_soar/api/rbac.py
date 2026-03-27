"""Role-based access control middleware and dependency guards."""

from __future__ import annotations

from enum import StrEnum

from fastapi import Depends, HTTPException, status

from akeso_soar.api.auth import get_current_user_payload
from akeso_soar.models.enums import UserRole

# ---------------------------------------------------------------------------
# Permission definitions
# ---------------------------------------------------------------------------


class Permission(StrEnum):
    # Use cases
    VIEW_USE_CASES = "view_use_cases"
    EDIT_USE_CASES = "edit_use_cases"
    MANAGE_USE_CASES = "manage_use_cases"  # create, delete, lifecycle transitions

    # Playbooks
    VIEW_PLAYBOOKS = "view_playbooks"
    EDIT_PLAYBOOKS = "edit_playbooks"
    MANAGE_PLAYBOOKS = "manage_playbooks"
    TRIGGER_PLAYBOOKS = "trigger_playbooks"

    # Executions
    VIEW_EXECUTIONS = "view_executions"

    # Human tasks
    APPROVE_HUMAN_TASKS = "approve_human_tasks"

    # Users
    VIEW_USERS = "view_users"
    MANAGE_USERS = "manage_users"  # create, delete

    # Connectors
    VIEW_CONNECTORS = "view_connectors"
    MANAGE_CONNECTORS = "manage_connectors"

    # Admin
    ADMIN = "admin"


# Role → permissions mapping
ROLE_PERMISSIONS: dict[UserRole, set[Permission]] = {
    UserRole.ADMIN: set(Permission),  # all permissions
    UserRole.SOC_MANAGER: {
        Permission.VIEW_USE_CASES,
        Permission.EDIT_USE_CASES,
        Permission.MANAGE_USE_CASES,
        Permission.VIEW_PLAYBOOKS,
        Permission.EDIT_PLAYBOOKS,
        Permission.MANAGE_PLAYBOOKS,
        Permission.TRIGGER_PLAYBOOKS,
        Permission.VIEW_EXECUTIONS,
        Permission.APPROVE_HUMAN_TASKS,
        Permission.VIEW_USERS,
        Permission.VIEW_CONNECTORS,
        Permission.MANAGE_CONNECTORS,
    },
    UserRole.SOC_L3: {
        Permission.VIEW_USE_CASES,
        Permission.EDIT_USE_CASES,
        Permission.MANAGE_USE_CASES,
        Permission.VIEW_PLAYBOOKS,
        Permission.EDIT_PLAYBOOKS,
        Permission.MANAGE_PLAYBOOKS,
        Permission.TRIGGER_PLAYBOOKS,
        Permission.VIEW_EXECUTIONS,
        Permission.APPROVE_HUMAN_TASKS,
        Permission.VIEW_USERS,
        Permission.VIEW_CONNECTORS,
    },
    UserRole.SOC_L2: {
        Permission.VIEW_USE_CASES,
        Permission.VIEW_PLAYBOOKS,
        Permission.EDIT_PLAYBOOKS,
        Permission.TRIGGER_PLAYBOOKS,
        Permission.VIEW_EXECUTIONS,
        Permission.APPROVE_HUMAN_TASKS,
        Permission.VIEW_USERS,
        Permission.VIEW_CONNECTORS,
    },
    UserRole.SOC_L1: {
        Permission.VIEW_USE_CASES,
        Permission.VIEW_PLAYBOOKS,
        Permission.TRIGGER_PLAYBOOKS,
        Permission.VIEW_EXECUTIONS,
        Permission.VIEW_USERS,
        Permission.VIEW_CONNECTORS,
    },
    UserRole.READ_ONLY: {
        Permission.VIEW_USE_CASES,
        Permission.VIEW_PLAYBOOKS,
        Permission.VIEW_EXECUTIONS,
        Permission.VIEW_USERS,
        Permission.VIEW_CONNECTORS,
    },
}


# ---------------------------------------------------------------------------
# Dependency factories
# ---------------------------------------------------------------------------


def require_auth(payload: dict = Depends(get_current_user_payload)) -> dict:
    """Dependency that ensures the request has a valid JWT. Returns the token payload."""
    return payload


def require_permissions(*permissions: Permission):
    """Return a FastAPI dependency that checks the caller has ALL listed permissions."""

    async def _check(payload: dict = Depends(get_current_user_payload)) -> dict:
        role_str = payload.get("role")
        try:
            role = UserRole(role_str)
        except (ValueError, KeyError) as err:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unknown role") from err

        granted = ROLE_PERMISSIONS.get(role, set())
        missing = set(permissions) - granted
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Missing: {', '.join(m.value for m in missing)}",
            )
        return payload

    return _check


def require_role(*roles: UserRole):
    """Return a FastAPI dependency that checks the caller has one of the listed roles."""

    async def _check(payload: dict = Depends(get_current_user_payload)) -> dict:
        role_str = payload.get("role")
        try:
            role = UserRole(role_str)
        except (ValueError, KeyError) as err:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unknown role") from err

        if role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role.value}' not authorized. Required: {', '.join(r.value for r in roles)}",
            )
        return payload

    return _check
