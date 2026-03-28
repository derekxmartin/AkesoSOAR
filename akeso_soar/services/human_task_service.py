"""Human task service — create, list, approve/reject tasks and resume executions."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from akeso_soar.models.enums import ExecutionStatus, HumanTaskStatus, StepStatus
from akeso_soar.models.execution import Execution, StepResult
from akeso_soar.models.human_task import HumanTask
from akeso_soar.services.ws_manager import ROOM_GLOBAL, execution_room, ws_manager


async def create_human_task(
    db: AsyncSession,
    *,
    execution_id: uuid.UUID,
    step_id: str,
    prompt: str,
    assignee_role: str,
    timeout_hours: int = 4,
) -> HumanTask:
    """Create a pending human task and pause the execution."""
    task = HumanTask(
        execution_id=execution_id,
        step_id=step_id,
        prompt=prompt,
        assignee_role=assignee_role,
        timeout_hours=timeout_hours,
        status=HumanTaskStatus.PENDING,
    )
    db.add(task)

    # Mark execution as paused
    result = await db.execute(select(Execution).where(Execution.id == execution_id))
    execution = result.scalar_one_or_none()
    if execution:
        execution.status = ExecutionStatus.PAUSED

    await db.flush()
    await db.refresh(task)

    # Broadcast via WebSocket
    await ws_manager.broadcast_global({
        "type": "human_task.created",
        "task_id": str(task.id),
        "execution_id": str(execution_id),
        "step_id": step_id,
        "prompt": prompt,
        "assignee_role": assignee_role,
    })
    await ws_manager.broadcast(execution_room(str(execution_id)), {
        "type": "execution.paused",
        "execution_id": str(execution_id),
        "step_id": step_id,
        "reason": "human_task",
    })

    return task


async def list_pending_tasks(
    db: AsyncSession,
    *,
    assignee_role: str | None = None,
) -> list[HumanTask]:
    """List pending human tasks, optionally filtered by assignee role."""
    stmt = select(HumanTask).where(HumanTask.status == HumanTaskStatus.PENDING).order_by(HumanTask.created_at.desc())
    if assignee_role:
        stmt = stmt.where(HumanTask.assignee_role == assignee_role)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_all_tasks(
    db: AsyncSession,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[HumanTask], int]:
    """List all human tasks with pagination."""
    count_stmt = select(HumanTask)
    count_result = await db.execute(count_stmt)
    total = len(count_result.scalars().all())

    stmt = (
        select(HumanTask)
        .order_by(HumanTask.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all()), total


async def resolve_task(
    db: AsyncSession,
    *,
    task_id: uuid.UUID,
    approved: bool,
    resolved_by: uuid.UUID,
    resolution_note: str = "",
) -> HumanTask:
    """Approve or reject a human task, then resume or fail the execution."""
    result = await db.execute(select(HumanTask).where(HumanTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise ValueError("Human task not found")
    if task.status != HumanTaskStatus.PENDING:
        raise ValueError(f"Task already resolved: {task.status.value}")

    task.status = HumanTaskStatus.APPROVED if approved else HumanTaskStatus.REJECTED
    task.resolved_by = resolved_by
    task.resolution_note = resolution_note

    # Update the step result
    sr_result = await db.execute(
        select(StepResult).where(
            StepResult.execution_id == task.execution_id,
            StepResult.step_id == task.step_id,
        )
    )
    step_result = sr_result.scalar_one_or_none()
    if step_result:
        step_result.status = StepStatus.SUCCESS if approved else StepStatus.FAILED
        step_result.completed_at = datetime.now(UTC)
        step_result.duration_ms = int((step_result.completed_at - step_result.started_at).total_seconds() * 1000) if step_result.started_at else 0
        step_result.output_data = {
            "decision": "approved" if approved else "rejected",
            "resolved_by": str(resolved_by),
            "note": resolution_note,
        }

    # Resume or fail execution
    exec_result = await db.execute(select(Execution).where(Execution.id == task.execution_id))
    execution = exec_result.scalar_one_or_none()
    if execution and execution.status == ExecutionStatus.PAUSED:
        if approved:
            # Resume — mark as completed (in a real system we'd continue the DAG)
            execution.status = ExecutionStatus.COMPLETED
            execution.completed_at = datetime.now(UTC)
            execution.duration_ms = int((execution.completed_at - execution.started_at).total_seconds() * 1000) if execution.started_at else 0
        else:
            execution.status = ExecutionStatus.FAILED
            execution.completed_at = datetime.now(UTC)
            execution.duration_ms = int((execution.completed_at - execution.started_at).total_seconds() * 1000) if execution.started_at else 0

    await db.flush()
    await db.refresh(task)

    # Broadcast resolution
    action = "approved" if approved else "rejected"
    await ws_manager.broadcast_global({
        "type": f"human_task.{action}",
        "task_id": str(task.id),
        "execution_id": str(task.execution_id),
        "step_id": task.step_id,
    })
    await ws_manager.broadcast(execution_room(str(task.execution_id)), {
        "type": f"execution.{'completed' if approved else 'failed'}",
        "execution_id": str(task.execution_id),
        "reason": f"human_task_{action}",
    })

    return task


async def timeout_overdue_tasks(db: AsyncSession) -> list[HumanTask]:
    """Find and timeout pending tasks past their deadline."""
    stmt = select(HumanTask).where(HumanTask.status == HumanTaskStatus.PENDING)
    result = await db.execute(stmt)
    tasks = result.scalars().all()
    timed_out = []
    now = datetime.now(UTC)

    for task in tasks:
        deadline = task.created_at.replace(tzinfo=UTC) if task.created_at.tzinfo is None else task.created_at
        hours_elapsed = (now - deadline).total_seconds() / 3600
        if hours_elapsed >= task.timeout_hours:
            task.status = HumanTaskStatus.TIMED_OUT
            task.resolution_note = f"Timed out after {task.timeout_hours}h"

            # Fail execution
            exec_result = await db.execute(select(Execution).where(Execution.id == task.execution_id))
            execution = exec_result.scalar_one_or_none()
            if execution and execution.status == ExecutionStatus.PAUSED:
                execution.status = ExecutionStatus.FAILED
                execution.completed_at = now
                execution.duration_ms = int((now - execution.started_at).total_seconds() * 1000) if execution.started_at else 0

            timed_out.append(task)

            await ws_manager.broadcast_global({
                "type": "human_task.timed_out",
                "task_id": str(task.id),
                "execution_id": str(task.execution_id),
                "step_id": task.step_id,
            })

    if timed_out:
        await db.flush()

    return timed_out
