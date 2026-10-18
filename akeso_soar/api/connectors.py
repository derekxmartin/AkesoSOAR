"""Connector API — DB-backed CRUD plus live registry endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from akeso_soar.api.rbac import Permission, require_auth, require_permissions
from akeso_soar.connectors.registry import ConnectorRegistry
from akeso_soar.dependencies import get_db
from akeso_soar.models.connector import Connector

router = APIRouter(prefix="/api/v1/connectors", tags=["connectors"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_registry() -> ConnectorRegistry:
    return ConnectorRegistry.instance()


# ---------------------------------------------------------------------------
# DB-backed endpoints (original functionality)
# ---------------------------------------------------------------------------


@router.get("")
async def list_connectors(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_db),
):
    """Return all connectors from the DB with their available operations."""
    result = await session.execute(
        select(Connector).order_by(Connector.name)
    )
    connectors = result.scalars().all()
    return [
        {
            "name": c.name,
            "display_name": c.display_name,
            "connector_type": c.connector_type.value,
            "enabled": c.enabled,
            "operations": c.operations,
        }
        for c in connectors
    ]


# ---------------------------------------------------------------------------
# Registry-based endpoints
# ---------------------------------------------------------------------------


@router.get("/registry")
async def list_registered_connectors(
    _user=Depends(require_auth),
):
    """List all connectors discovered by the runtime registry, with health."""
    registry = _get_registry()
    connectors = registry.list_connectors()
    health_map = await registry.get_all_health()

    items = []
    for c in connectors:
        hs = health_map.get(c.name)
        items.append(
            {
                "name": c.name,
                "display_name": c.display_name,
                "connector_type": c.connector_type,
                "operations": c.operations,
                "mock_mode": c.mock,
                "health": {
                    "healthy": hs.healthy if hs else False,
                    "message": hs.message if hs else "Unknown",
                    "latency_ms": hs.latency_ms if hs else 0.0,
                },
            }
        )
    return items


@router.get("/registry/{name}/health")
async def connector_health(
    name: str,
    _user=Depends(require_auth),
):
    """Return detailed health for a single registered connector."""
    registry = _get_registry()
    connector = registry.get_connector(name)
    if connector is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connector '{name}' not found in registry",
        )
    hs = await connector.health_check()
    return {
        "name": connector.name,
        "display_name": connector.display_name,
        "connector_type": connector.connector_type,
        "mock_mode": connector.mock,
        "healthy": hs.healthy,
        "message": hs.message,
        "latency_ms": hs.latency_ms,
    }


class ExecuteRequest(BaseModel):
    operation: str
    params: dict = {}


@router.post("/registry/{name}/execute")
async def execute_connector_operation(
    name: str,
    body: ExecuteRequest,
    _user=Depends(require_permissions(Permission.MANAGE_CONNECTORS)),
):
    """Execute an operation on a registered connector (for testing / ad-hoc use)."""
    registry = _get_registry()
    connector = registry.get_connector(name)
    if connector is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Connector '{name}' not found in registry",
        )

    result = await connector.execute(body.operation, body.params)
    return {
        "connector": connector.name,
        "operation": body.operation,
        "success": result.success,
        "data": result.data,
        "error": result.error,
        "duration_ms": result.duration_ms,
    }
