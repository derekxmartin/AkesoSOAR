"""Rollback handler — executes rollback actions in reverse order (best-effort)."""

from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from akeso_soar.engine.variable_resolver import resolve_params

logger = logging.getLogger(__name__)


async def execute_rollbacks(
    completed_steps: list[dict],
    context: dict,
    execute_action_fn: Callable[..., Coroutine[Any, Any, dict]],
) -> list[dict]:
    """Walk back completed steps in reverse order and execute their rollback actions.

    Args:
        completed_steps: List of step defs that completed successfully, in execution order.
        context: Variable context for resolving rollback params.
        execute_action_fn: The action executor function.

    Returns:
        List of rollback result dicts (step_id, status, output/error).
    """
    rollback_results = []

    # Reverse order
    for step_def in reversed(completed_steps):
        rollback_action = step_def.get("rollback_action")
        if not rollback_action:
            continue

        step_id = step_def.get("id", "?")
        connector = rollback_action.get("connector", "")
        operation = rollback_action.get("operation", "")
        raw_params = rollback_action.get("params", {})

        try:
            resolved = resolve_params(raw_params, context)
            output = await execute_action_fn(
                connector=connector,
                operation=operation,
                params=resolved,
            )
            rollback_results.append({
                "step_id": step_id,
                "status": "success",
                "connector": connector,
                "operation": operation,
                "output": output,
            })
            logger.info("Rollback succeeded for step %s: %s.%s", step_id, connector, operation)
        except Exception as exc:
            # Best-effort — log and continue
            rollback_results.append({
                "step_id": step_id,
                "status": "failed",
                "connector": connector,
                "operation": operation,
                "error": str(exc),
            })
            logger.warning("Rollback failed for step %s: %s", step_id, exc)

    return rollback_results
