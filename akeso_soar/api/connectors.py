"""Connector list API — used by the dashboard for step autocomplete."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from akeso_soar.api.auth import require_user
from akeso_soar.db import get_session
from akeso_soar.models.connector import Connector

router = APIRouter(prefix="/api/v1/connectors", tags=["connectors"])


@router.get("")
async def list_connectors(
    _user=Depends(require_user),
    session: AsyncSession = Depends(get_session),
):
    """Return all connectors with their available operations."""
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
