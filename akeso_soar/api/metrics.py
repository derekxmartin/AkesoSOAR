"""Metrics API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from akeso_soar.api.rbac import require_auth
from akeso_soar.dependencies import get_db
from akeso_soar.services.metrics_service import (
    get_alerts_by_severity,
    get_overview_metrics,
    get_playbook_metrics,
    get_use_case_metrics,
)

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


@router.get("/overview")
async def overview(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    return await get_overview_metrics(db)


@router.get("/playbooks")
async def playbooks(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    return await get_playbook_metrics(db, days=days)


@router.get("/use-cases")
async def use_cases(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    return await get_use_case_metrics(db)


@router.get("/alerts-by-severity")
async def alerts_by_severity(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_auth),
):
    return await get_alerts_by_severity(db)
