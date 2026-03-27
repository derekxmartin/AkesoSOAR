"""Automatic playbook triggering — fires linked playbooks when use cases match, with cooldown dedup."""

from __future__ import annotations

import logging
import time
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from akeso_soar.engine.executor import execute_playbook
from akeso_soar.engine.use_case_matcher import match_alert
from akeso_soar.models.alert import Alert
from akeso_soar.models.playbook import Playbook, UseCasePlaybook

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cooldown tracking (alert_id + playbook_id → last trigger time)
# ---------------------------------------------------------------------------

_cooldown_seconds: int = 300  # 5 minutes default
_trigger_history: dict[str, float] = {}


def set_cooldown(seconds: int) -> None:
    global _cooldown_seconds
    _cooldown_seconds = seconds


def clear_cooldown_history() -> None:
    _trigger_history.clear()


def _cooldown_key(alert_external_id: str, playbook_id: uuid.UUID) -> str:
    return f"{alert_external_id}:{playbook_id}"


def _is_in_cooldown(alert_external_id: str, playbook_id: uuid.UUID) -> bool:
    key = _cooldown_key(alert_external_id, playbook_id)
    last = _trigger_history.get(key)
    if last is None:
        return False
    return (time.monotonic() - last) < _cooldown_seconds


def _record_trigger(alert_external_id: str, playbook_id: uuid.UUID) -> None:
    key = _cooldown_key(alert_external_id, playbook_id)
    _trigger_history[key] = time.monotonic()


# ---------------------------------------------------------------------------
# Pipeline: alert → match → trigger
# ---------------------------------------------------------------------------


async def process_alert(db: AsyncSession, alert: Alert) -> list[dict]:
    """Full pipeline: match alert against use cases and trigger linked playbooks.

    Returns a list of trigger results with execution IDs.
    """
    matches = await match_alert(db, alert)
    if not matches:
        return []

    trigger_results = []

    for match in matches:
        uc_id = uuid.UUID(match["use_case_id"])

        # Get linked playbooks for this use case
        result = await db.execute(
            select(Playbook)
            .join(UseCasePlaybook, UseCasePlaybook.playbook_id == Playbook.id)
            .where(UseCasePlaybook.use_case_id == uc_id)
            .where(Playbook.enabled.is_(True))
        )
        playbooks = result.scalars().all()

        for pb in playbooks:
            # Cooldown check
            if _is_in_cooldown(alert.external_id, pb.id):
                logger.info(
                    "Skipping playbook %s for alert %s (cooldown)",
                    pb.name,
                    alert.external_id,
                )
                trigger_results.append({
                    "use_case_id": str(uc_id),
                    "use_case_name": match["use_case_name"],
                    "playbook_id": str(pb.id),
                    "playbook_name": pb.name,
                    "status": "cooldown",
                    "execution_id": None,
                })
                continue

            # Execute playbook
            logger.info(
                "Triggering playbook %s for alert %s (use case: %s)",
                pb.name,
                alert.external_id,
                match["use_case_name"],
            )

            execution = await execute_playbook(
                db,
                playbook_id=pb.id,
                playbook_version=pb.version,
                definition=pb.definition,
                alert_payload=alert.raw_payload,
                use_case_id=uc_id,
                trigger_alert_id=alert.external_id,
            )

            _record_trigger(alert.external_id, pb.id)

            trigger_results.append({
                "use_case_id": str(uc_id),
                "use_case_name": match["use_case_name"],
                "playbook_id": str(pb.id),
                "playbook_name": pb.name,
                "status": "triggered",
                "execution_id": str(execution.id),
                "execution_status": execution.status.value,
            })

    return trigger_results
