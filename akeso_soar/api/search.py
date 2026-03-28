"""Global search API endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from akeso_soar.api.rbac import require_auth
from akeso_soar.dependencies import get_db
from akeso_soar.services.search_service import global_search

router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.get("")
async def search(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    """Search across use cases, playbooks, alerts, executions, and connectors."""
    return await global_search(db, q, limit=limit)
