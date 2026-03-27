"""Execution API: trigger, list, detail, cancel."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from akeso_soar.api.rbac import Permission, require_permissions
from akeso_soar.dependencies import get_db
from akeso_soar.engine.executor import execute_playbook
from akeso_soar.models.enums import ExecutionStatus, StepStatus
from akeso_soar.models.execution import Execution
from akeso_soar.services.playbook_service import get_playbook

router = APIRouter(prefix="/api/v1", tags=["executions"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ExecuteRequest(BaseModel):
    alert_payload: dict = {}
    use_case_id: uuid.UUID | None = None
    trigger_alert_id: str | None = None


class StepResultOut(BaseModel):
    id: uuid.UUID
    step_id: str
    status: StepStatus
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    input_data: dict | None
    output_data: dict | None
    error: str | None
    retry_count: int

    model_config = {"from_attributes": True}


class ExecutionOut(BaseModel):
    id: uuid.UUID
    playbook_id: uuid.UUID
    playbook_version: int
    trigger_alert_id: str | None
    use_case_id: uuid.UUID | None
    status: ExecutionStatus
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ExecutionDetailOut(ExecutionOut):
    step_results: list[StepResultOut]


class PaginatedExecutionResponse(BaseModel):
    items: list[ExecutionOut]
    total: int
    page: int
    limit: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/playbooks/{playbook_id}/execute", response_model=ExecutionDetailOut, status_code=status.HTTP_201_CREATED)
async def trigger_execution(
    playbook_id: uuid.UUID,
    body: ExecuteRequest,
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(require_permissions(Permission.TRIGGER_PLAYBOOKS)),
):
    pb = await get_playbook(db, playbook_id)
    if pb is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playbook not found")
    if not pb.enabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Playbook is disabled")

    execution = await execute_playbook(
        db,
        playbook_id=pb.id,
        playbook_version=pb.version,
        definition=pb.definition,
        alert_payload=body.alert_payload,
        use_case_id=body.use_case_id,
        trigger_alert_id=body.trigger_alert_id,
    )

    # Reload with step results
    await db.refresh(execution)
    return execution


@router.get("/executions", response_model=PaginatedExecutionResponse)
async def list_executions(
    playbook_id: uuid.UUID | None = Query(None),
    use_case_id: uuid.UUID | None = Query(None),
    status_filter: ExecutionStatus | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permissions(Permission.VIEW_EXECUTIONS)),
):
    query = select(Execution)

    if playbook_id:
        query = query.where(Execution.playbook_id == playbook_id)
    if use_case_id:
        query = query.where(Execution.use_case_id == use_case_id)
    if status_filter:
        query = query.where(Execution.status == status_filter)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    query = query.order_by(Execution.created_at.desc())
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    return PaginatedExecutionResponse(items=items, total=total, page=page, limit=limit)


@router.get("/executions/{execution_id}", response_model=ExecutionDetailOut)
async def get_execution(
    execution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permissions(Permission.VIEW_EXECUTIONS)),
):
    result = await db.execute(select(Execution).where(Execution.id == execution_id))
    execution = result.scalar_one_or_none()
    if execution is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
    return execution


@router.post("/executions/{execution_id}/cancel", response_model=ExecutionOut)
async def cancel_execution(
    execution_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permissions(Permission.TRIGGER_PLAYBOOKS)),
):
    result = await db.execute(select(Execution).where(Execution.id == execution_id))
    execution = result.scalar_one_or_none()
    if execution is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

    if execution.status not in (ExecutionStatus.RUNNING, ExecutionStatus.QUEUED, ExecutionStatus.PAUSED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel execution in '{execution.status.value}' state",
        )

    execution.status = ExecutionStatus.CANCELLED
    execution.completed_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(execution)
    return execution
