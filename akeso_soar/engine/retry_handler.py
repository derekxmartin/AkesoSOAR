"""Retry handler — exponential backoff retry for failed action steps."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any


async def execute_with_retry(
    action_fn: Callable[..., Coroutine[Any, Any, dict]],
    *,
    max_attempts: int = 1,
    backoff_seconds: int = 1,
    **action_kwargs,
) -> tuple[dict, int, str | None]:
    """Execute an async action with exponential backoff retry.

    Returns:
        (result, retry_count, error) — the action result (or empty dict on failure),
        the number of retries attempted, and the final error message (or None on success).
    """
    last_error: str | None = None

    for attempt in range(max_attempts):
        try:
            result = await action_fn(**action_kwargs)
            return result, attempt, None
        except Exception as exc:
            last_error = str(exc)
            if attempt < max_attempts - 1:
                wait = backoff_seconds * (2 ** attempt)
                await asyncio.sleep(wait)

    return {}, max_attempts - 1, last_error
