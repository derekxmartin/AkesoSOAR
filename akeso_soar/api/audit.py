"""Audit log query endpoint."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from akeso_soar.api.rbac import Permission, require_permissions
from akeso_soar.dependencies import get_db
from akeso_soar.services.audit_service import query_audit_log

router = APIRouter(prefix="/api/v1/audit-log", tags=["audit"])


class AuditLogOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None
    actor: str
    event_type: str
    resource_type: str
    resource_id: str
    description: str
    details: dict | None
    before_state: dict | None
    after_state: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedAuditResponse(BaseModel):
    items: list[AuditLogOut]
    total: int
    page: int
    limit: int


@router.get("", response_model=PaginatedAuditResponse)
async def list_audit_logs(
    resource_type: str | None = Query(None),
    resource_id: str | None = Query(None),
    event_type: str | None = Query(None),
    user_id: uuid.UUID | None = Query(None),
    after: datetime | None = Query(None),
    before: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permissions(Permission.VIEW_USE_CASES)),
):
    items, total = await query_audit_log(
        db,
        resource_type=resource_type,
        resource_id=resource_id,
        event_type=event_type,
        user_id=user_id,
        after=after,
        before=before,
        page=page,
        limit=limit,
    )
    return PaginatedAuditResponse(items=items, total=total, page=page, limit=limit)
