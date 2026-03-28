"""Human task API endpoints — list, approve, reject."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from akeso_soar.api.rbac import require_permissions, Permission
from akeso_soar.dependencies import get_db
from akeso_soar.services.human_task_service import list_all_tasks, list_pending_tasks, resolve_task

router = APIRouter(prefix="/api/v1/human-tasks", tags=["human-tasks"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class HumanTaskOut(BaseModel):
    id: str
    execution_id: str
    step_id: str
    prompt: str
    assignee_role: str
    status: str
    timeout_hours: int
    resolved_by: str | None = None
    resolution_note: str | None = None
    created_at: str
    updated_at: str


class ResolveRequest(BaseModel):
    note: str = ""


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


def _task_to_out(task) -> dict:
    return {
        "id": str(task.id),
        "execution_id": str(task.execution_id),
        "step_id": task.step_id,
        "prompt": task.prompt,
        "assignee_role": task.assignee_role,
        "status": task.status.value,
        "timeout_hours": task.timeout_hours,
        "resolved_by": str(task.resolved_by) if task.resolved_by else None,
        "resolution_note": task.resolution_note,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    }


@router.get("")
async def list_tasks(
    role: str | None = Query(None, description="Filter by assignee role"),
    pending_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permissions(Permission.VIEW_EXECUTIONS)),
):
    """List human tasks. Optionally filter by assignee role or pending status."""
    if pending_only:
        tasks = await list_pending_tasks(db, assignee_role=role)
        return {"items": [_task_to_out(t) for t in tasks], "total": len(tasks)}

    tasks, total = await list_all_tasks(db, limit=limit, offset=offset)
    return {"items": [_task_to_out(t) for t in tasks], "total": total}


@router.post("/{task_id}/approve")
async def approve_task(
    task_id: uuid.UUID,
    body: ResolveRequest = ResolveRequest(),
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(require_permissions(Permission.APPROVE_HUMAN_TASKS)),
):
    """Approve a pending human task, resuming the paused execution."""
    try:
        task = await resolve_task(
            db,
            task_id=task_id,
            approved=True,
            resolved_by=uuid.UUID(payload["sub"]),
            resolution_note=body.note,
        )
        return _task_to_out(task)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{task_id}/reject")
async def reject_task(
    task_id: uuid.UUID,
    body: ResolveRequest = ResolveRequest(),
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(require_permissions(Permission.APPROVE_HUMAN_TASKS)),
):
    """Reject a pending human task, failing the paused execution."""
    try:
        task = await resolve_task(
            db,
            task_id=task_id,
            approved=False,
            resolved_by=uuid.UUID(payload["sub"]),
            resolution_note=body.note,
        )
        return _task_to_out(task)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
