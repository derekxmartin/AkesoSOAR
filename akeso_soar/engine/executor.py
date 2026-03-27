"""DAG executor — runs playbook steps sequentially (linear path for Phase 5)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from akeso_soar.engine.variable_resolver import resolve_params
from akeso_soar.models.enums import ExecutionStatus, StepStatus
from akeso_soar.models.execution import Execution, StepResult

# ---------------------------------------------------------------------------
# Mock action registry — returns canned results per connector.operation
# In later phases, this is replaced by real connector calls.
# ---------------------------------------------------------------------------

_mock_results: dict[str, dict] = {}


def register_mock_action(connector: str, operation: str, result: dict) -> None:
    """Register a mock result for a connector.operation pair."""
    _mock_results[f"{connector}.{operation}"] = result


def clear_mock_actions() -> None:
    _mock_results.clear()


async def _execute_action(connector: str, operation: str, params: dict) -> dict:
    """Execute an action step. Uses mock registry, falls back to echo."""
    key = f"{connector}.{operation}"
    if key in _mock_results:
        return _mock_results[key]
    # Default mock: echo back the params
    return {"status": "ok", "connector": connector, "operation": operation, "params": params, "mock": True}


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------


async def execute_playbook(
    db: AsyncSession,
    *,
    playbook_id: uuid.UUID,
    playbook_version: int,
    definition: dict,
    alert_payload: dict | None = None,
    use_case_id: uuid.UUID | None = None,
    trigger_alert_id: str | None = None,
) -> Execution:
    """Execute a playbook definition (linear path: follows on_success chain).

    Creates an Execution record and StepResult records in the database.
    """
    # Create execution instance
    execution = Execution(
        playbook_id=playbook_id,
        playbook_version=playbook_version,
        trigger_alert_id=trigger_alert_id,
        use_case_id=use_case_id,
        status=ExecutionStatus.RUNNING,
        started_at=datetime.now(UTC),
    )
    db.add(execution)
    await db.flush()
    await db.refresh(execution)

    # Build variable context
    context: dict = {
        "alert": alert_payload or {},
        "config": definition.get("variables", {}),
        "steps": {},
    }

    steps = definition.get("steps", [])
    step_map = {s["id"]: s for s in steps}

    # Find the first step (first in the list)
    if not steps:
        execution.status = ExecutionStatus.COMPLETED
        execution.completed_at = datetime.now(UTC)
        execution.duration_ms = 0
        await db.flush()
        return execution

    current_step_id: str | None = steps[0]["id"]
    all_success = True
    cancelled = False

    while current_step_id and not cancelled:
        step_def = step_map.get(current_step_id)
        if step_def is None:
            break

        step_result = StepResult(
            execution_id=execution.id,
            step_id=current_step_id,
            status=StepStatus.RUNNING,
            started_at=datetime.now(UTC),
        )
        db.add(step_result)
        await db.flush()

        step_type = step_def.get("type", "action")
        next_step_id: str | None = step_def.get("on_success")

        try:
            if step_type == "action":
                action = step_def.get("action", {})
                raw_params = action.get("params", {})
                resolved = resolve_params(raw_params, context)
                step_result.input_data = resolved

                output = await _execute_action(
                    action.get("connector", ""),
                    action.get("operation", ""),
                    resolved,
                )
                step_result.output_data = output
                step_result.status = StepStatus.SUCCESS

                # Store result in context for downstream steps
                context["steps"][current_step_id] = {"result": output}

            elif step_type == "transform":
                transform = step_def.get("transform", {})
                expr = transform.get("expression", "")
                transform.get("output_var", current_step_id)
                # Simple eval of Jinja2 expression
                from akeso_soar.engine.variable_resolver import resolve_string

                resolved_val = resolve_string(expr, context)
                context["steps"][current_step_id] = {"result": resolved_val}
                step_result.output_data = {"value": resolved_val}
                step_result.status = StepStatus.SUCCESS

            elif step_type == "condition":
                # Condition evaluation is Phase 6 — mark as skipped for now
                step_result.status = StepStatus.SKIPPED
                step_result.output_data = {"note": "Condition evaluation requires Phase 6"}
                next_step_id = None

            elif step_type == "human_task":
                # Human task pausing is Phase 11 — mark as waiting
                step_result.status = StepStatus.WAITING
                step_result.output_data = {"note": "Human approval gates require Phase 11"}
                next_step_id = None

            elif step_type == "parallel":
                # Parallel execution is Phase 6 — mark as skipped
                step_result.status = StepStatus.SKIPPED
                step_result.output_data = {"note": "Parallel execution requires Phase 6"}
                next_step_id = None

            else:
                step_result.status = StepStatus.FAILED
                step_result.error = f"Unknown step type: {step_type}"
                all_success = False
                next_step_id = step_def.get("on_failure")

        except Exception as exc:
            step_result.status = StepStatus.FAILED
            step_result.error = str(exc)
            all_success = False
            next_step_id = step_def.get("on_failure")

        # Finalize step timing
        step_result.completed_at = datetime.now(UTC)
        step_result.duration_ms = int(
            (step_result.completed_at - step_result.started_at).total_seconds() * 1000
        )
        await db.flush()

        # Check for cancellation
        await db.refresh(execution)
        if execution.status == ExecutionStatus.CANCELLED:
            cancelled = True
            break

        # Advance to next step
        if next_step_id == "abort":
            break
        current_step_id = next_step_id

    # Finalize execution
    now = datetime.now(UTC)
    execution.completed_at = now
    execution.duration_ms = int((now - execution.started_at).total_seconds() * 1000)

    if cancelled:
        execution.status = ExecutionStatus.CANCELLED
    elif all_success:
        execution.status = ExecutionStatus.COMPLETED
    else:
        execution.status = ExecutionStatus.FAILED

    await db.flush()
    await db.refresh(execution)
    return execution
