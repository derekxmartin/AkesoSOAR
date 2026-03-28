"""DAG executor — runs playbook steps with conditions, parallelism, retry, timeouts, and rollback."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from akeso_soar.engine.condition_evaluator import resolve_branch
from akeso_soar.engine.retry_handler import execute_with_retry
from akeso_soar.engine.rollback_handler import execute_rollbacks
from akeso_soar.engine.variable_resolver import resolve_params, resolve_string
from akeso_soar.models.enums import ExecutionStatus, StepStatus
from akeso_soar.models.execution import Execution, StepResult
from akeso_soar.services.human_task_service import create_human_task

# ---------------------------------------------------------------------------
# Mock action registry
# ---------------------------------------------------------------------------

_mock_results: dict[str, dict] = {}
_mock_errors: dict[str, str] = {}
_mock_delays: dict[str, float] = {}


def register_mock_action(connector: str, operation: str, result: dict) -> None:
    _mock_results[f"{connector}.{operation}"] = result


def register_mock_error(connector: str, operation: str, error_msg: str) -> None:
    _mock_errors[f"{connector}.{operation}"] = error_msg


def register_mock_delay(connector: str, operation: str, delay_seconds: float) -> None:
    _mock_delays[f"{connector}.{operation}"] = delay_seconds


def clear_mock_actions() -> None:
    _mock_results.clear()
    _mock_errors.clear()
    _mock_delays.clear()


async def _execute_action(connector: str, operation: str, params: dict) -> dict:
    key = f"{connector}.{operation}"
    if key in _mock_errors:
        raise RuntimeError(_mock_errors[key])
    if key in _mock_delays:
        await asyncio.sleep(_mock_delays[key])
    if key in _mock_results:
        return _mock_results[key]
    return {"status": "ok", "connector": connector, "operation": operation, "params": params, "mock": True}


# ---------------------------------------------------------------------------
# Step result data (in-memory, written to DB after parallel completes)
# ---------------------------------------------------------------------------


class StepResultData:
    """In-memory representation of a step result, written to DB later."""

    def __init__(self, step_id: str):
        self.step_id = step_id
        self.status = StepStatus.RUNNING
        self.started_at = datetime.now(UTC)
        self.completed_at: datetime | None = None
        self.duration_ms: int | None = None
        self.input_data: dict | None = None
        self.output_data: dict | None = None
        self.error: str | None = None
        self.retry_count: int = 0

    def finalize(self) -> None:
        self.completed_at = datetime.now(UTC)
        self.duration_ms = int((self.completed_at - self.started_at).total_seconds() * 1000)

    def to_db_model(self, execution_id: uuid.UUID) -> StepResult:
        return StepResult(
            execution_id=execution_id,
            step_id=self.step_id,
            status=self.status,
            started_at=self.started_at,
            completed_at=self.completed_at,
            duration_ms=self.duration_ms,
            input_data=self.input_data,
            output_data=self.output_data,
            error=self.error,
            retry_count=self.retry_count,
        )


# ---------------------------------------------------------------------------
# Execute a single step (no DB writes — returns StepResultData)
# ---------------------------------------------------------------------------


async def _run_step_logic(
    step_id: str,
    step_def: dict,
    context: dict,
) -> StepResultData:
    """Execute a single action/transform step and return result data (no DB)."""
    sr = StepResultData(step_id)
    step_type = step_def.get("type", "action")
    retry_config = step_def.get("retry", {})
    max_attempts = retry_config.get("max_attempts", 1)
    backoff = retry_config.get("backoff_seconds", 1)
    timeout = step_def.get("timeout_seconds")

    try:
        if step_type == "action":
            action = step_def.get("action", {})
            raw_params = action.get("params", {})
            resolved = resolve_params(raw_params, context)
            sr.input_data = resolved

            async def _do_action() -> dict:
                return await _execute_action(
                    action.get("connector", ""),
                    action.get("operation", ""),
                    resolved,
                )

            action_coro = execute_with_retry(
                _do_action, max_attempts=max_attempts, backoff_seconds=backoff
            )

            if timeout:
                try:
                    result, retries, error = await asyncio.wait_for(action_coro, timeout=timeout)
                except TimeoutError:
                    sr.status = StepStatus.FAILED
                    sr.error = f"Timeout after {timeout}s"
                    sr.finalize()
                    return sr
            else:
                result, retries, error = await action_coro

            sr.retry_count = retries
            if error:
                sr.status = StepStatus.FAILED
                sr.error = error
            else:
                sr.output_data = result
                sr.status = StepStatus.SUCCESS
                context["steps"][step_id] = {"result": result}

        elif step_type == "transform":
            transform = step_def.get("transform", {})
            expr = transform.get("expression", "")
            resolved_val = resolve_string(expr, context)
            context["steps"][step_id] = {"result": resolved_val}
            sr.output_data = {"value": resolved_val}
            sr.status = StepStatus.SUCCESS

        else:
            sr.status = StepStatus.FAILED
            sr.error = f"Unsupported step type: {step_type}"

    except Exception as exc:
        sr.status = StepStatus.FAILED
        sr.error = str(exc)

    sr.finalize()
    return sr


# ---------------------------------------------------------------------------
# Parallel branch runner (no DB — collects StepResultData)
# ---------------------------------------------------------------------------


async def _run_parallel_branches(
    step_def: dict,
    step_map: dict[str, dict],
    context: dict,
) -> tuple[list[StepResultData], bool]:
    """Run parallel branches concurrently. Returns (all_step_results, all_success)."""
    parallel_config = step_def.get("parallel", {})
    branches = parallel_config.get("branches", [])
    join_mode = parallel_config.get("join", "all")

    async def _run_branch(branch_steps: list[str]) -> list[StepResultData]:
        results = []
        for sid in branch_steps:
            s_def = step_map.get(sid)
            if s_def is None:
                sr = StepResultData(sid)
                sr.status = StepStatus.FAILED
                sr.error = f"Unknown step ID: {sid}"
                sr.finalize()
                results.append(sr)
                break
            sr = await _run_step_logic(sid, s_def, context)
            results.append(sr)
            if sr.status == StepStatus.FAILED:
                break
        return results

    branch_step_lists = [b.get("steps", []) for b in branches]
    all_results: list[StepResultData] = []
    all_success = True

    if join_mode == "any":
        import contextlib

        tasks = [asyncio.create_task(_run_branch(bs)) for bs in branch_step_lists]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for t in pending:
            t.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await t
        for task in done:
            for sr in task.result():
                all_results.append(sr)
                if sr.status == StepStatus.FAILED:
                    all_success = False
    else:
        branch_results = await asyncio.gather(*[_run_branch(bs) for bs in branch_step_lists])
        for branch in branch_results:
            for sr in branch:
                all_results.append(sr)
                if sr.status == StepStatus.FAILED:
                    all_success = False

    return all_results, all_success


# ---------------------------------------------------------------------------
# Main executor
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
    """Execute a playbook with conditions, parallelism, retry, timeouts, and rollback."""

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

    context: dict = {
        "alert": alert_payload or {},
        "config": definition.get("variables", {}),
        "steps": {},
    }

    steps = definition.get("steps", [])
    step_map = {s["id"]: s for s in steps}
    rollback_on_failure = definition.get("rollback_on_failure", False)

    if not steps:
        execution.status = ExecutionStatus.COMPLETED
        execution.completed_at = datetime.now(UTC)
        execution.duration_ms = 0
        await db.flush()
        return execution

    current_step_id: str | None = steps[0]["id"]
    all_success = True
    cancelled = False
    completed_steps: list[dict] = []

    while current_step_id and not cancelled:
        step_def = step_map.get(current_step_id)
        if step_def is None:
            break

        step_type = step_def.get("type", "action")
        next_step_id: str | None = step_def.get("on_success")

        # --- Condition ---
        if step_type == "condition":
            condition = step_def.get("condition", {})
            expression = condition.get("expression", "false")
            branches = condition.get("branches", {})

            branch_target = resolve_branch(expression, branches, context)

            sr = StepResult(
                execution_id=execution.id,
                step_id=current_step_id,
                status=StepStatus.SUCCESS,
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
                duration_ms=0,
                output_data={"expression": expression, "branch": branch_target},
            )
            db.add(sr)
            await db.flush()

            current_step_id = branch_target
            continue

        # --- Parallel ---
        if step_type == "parallel":
            par_start = datetime.now(UTC)
            branch_results, branch_success = await _run_parallel_branches(step_def, step_map, context)

            # Write all branch step results to DB
            for sr_data in branch_results:
                db.add(sr_data.to_db_model(execution.id))

            # Write the parallel step itself
            par_sr = StepResult(
                execution_id=execution.id,
                step_id=current_step_id,
                status=StepStatus.SUCCESS if branch_success else StepStatus.FAILED,
                started_at=par_start,
                completed_at=datetime.now(UTC),
                duration_ms=int((datetime.now(UTC) - par_start).total_seconds() * 1000),
                output_data={"branches": len(step_def.get("parallel", {}).get("branches", []))},
            )
            db.add(par_sr)
            await db.flush()

            if not branch_success:
                all_success = False
                next_step_id = step_def.get("on_failure")
            current_step_id = next_step_id
            continue

        # --- Human task ---
        if step_type == "human_task":
            ht_config = step_def.get("human_task", {})
            prompt = ht_config.get("prompt", "Approval required")
            assignee_role = ht_config.get("assignee_role", "soc_l2")
            timeout_hours = ht_config.get("timeout_hours", 4)

            # Resolve Jinja2 in the prompt
            try:
                prompt = resolve_string(prompt, context)
            except Exception:
                pass

            sr = StepResult(
                execution_id=execution.id,
                step_id=current_step_id,
                status=StepStatus.WAITING,
                started_at=datetime.now(UTC),
                output_data={"prompt": prompt, "assignee_role": assignee_role},
            )
            db.add(sr)
            await db.flush()

            # Create the human task record and pause execution
            await create_human_task(
                db,
                execution_id=execution.id,
                step_id=current_step_id,
                prompt=prompt,
                assignee_role=assignee_role,
                timeout_hours=timeout_hours,
            )

            # Stop DAG traversal — execution is paused until approve/reject
            execution.status = ExecutionStatus.PAUSED
            await db.flush()
            return execution

        # --- Action / Transform (with retry + timeout) ---
        sr_data = await _run_step_logic(current_step_id, step_def, context)
        db.add(sr_data.to_db_model(execution.id))
        await db.flush()

        if sr_data.status == StepStatus.SUCCESS:
            completed_steps.append(step_def)
        else:
            all_success = False
            next_step_id = step_def.get("on_failure")

        # Check cancellation
        await db.refresh(execution)
        if execution.status == ExecutionStatus.CANCELLED:
            cancelled = True
            break

        if next_step_id == "abort":
            all_success = False
            break
        current_step_id = next_step_id

    # --- Rollback ---
    if not all_success and rollback_on_failure and completed_steps:
        await execute_rollbacks(
            completed_steps,
            context,
            lambda connector, operation, params: _execute_action(connector, operation, params),
        )

    # Finalize
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
