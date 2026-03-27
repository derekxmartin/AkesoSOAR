"""MITRE ATT&CK coverage API."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from akeso_soar.api.rbac import Permission, require_permissions
from akeso_soar.dependencies import get_db
from akeso_soar.services.mitre_coverage import build_coverage_matrix

router = APIRouter(prefix="/api/v1/coverage", tags=["coverage"])


@router.get("/mitre")
async def mitre_coverage(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permissions(Permission.VIEW_USE_CASES)),
):
    return await build_coverage_matrix(db)
