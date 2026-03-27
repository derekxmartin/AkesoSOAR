"""Use case lifecycle state machine with promotion gates."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from akeso_soar.models.enums import UseCaseStatus
from akeso_soar.models.playbook import UseCasePlaybook
from akeso_soar.models.use_case import UseCase
from akeso_soar.services.audit_service import create_audit_entry
from akeso_soar.services.use_case_service import _use_case_snapshot

# ---------------------------------------------------------------------------
# Legal transitions (from_status → set of allowed to_statuses)
# ---------------------------------------------------------------------------

TRANSITIONS: dict[UseCaseStatus, set[UseCaseStatus]] = {
    UseCaseStatus.DRAFT: {UseCaseStatus.TESTING, UseCaseStatus.DEPRECATED},
    UseCaseStatus.TESTING: {UseCaseStatus.PRODUCTION},
    UseCaseStatus.PRODUCTION: {UseCaseStatus.TESTING, UseCaseStatus.DEPRECATED},
    UseCaseStatus.DEPRECATED: set(),
}


class TransitionError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


# ---------------------------------------------------------------------------
# Promotion gate checks
# ---------------------------------------------------------------------------


async def _check_draft_to_testing(db: AsyncSession, uc: UseCase) -> list[str]:
    """Draft → Testing requires: data sources documented, playbook linked, investigation guide."""
    errors = []
    if not uc.sigma_rule_ids:
        errors.append("At least one sigma_rule_id is required")

    # Check playbook linked
    result = await db.execute(
        select(UseCasePlaybook).where(UseCasePlaybook.use_case_id == uc.id).limit(1)
    )
    if result.scalar_one_or_none() is None:
        errors.append("At least one playbook must be linked")

    if not uc.investigation_guide.strip():
        errors.append("Investigation guide must be written")

    return errors


async def _check_testing_to_production(db: AsyncSession, uc: UseCase) -> list[str]:
    """Testing → Production requires: successful execution, FP guidance, review cadence."""
    from akeso_soar.models.enums import ExecutionStatus
    from akeso_soar.models.execution import Execution
    from akeso_soar.models.playbook import UseCasePlaybook

    errors = []

    if not uc.false_positive_guidance.strip():
        errors.append("False positive guidance must be documented")

    if not uc.review_cadence_days or uc.review_cadence_days <= 0:
        errors.append("Review cadence must be set")

    # Check for at least one successful playbook execution linked to this use case
    linked_playbooks = await db.execute(
        select(UseCasePlaybook.playbook_id).where(UseCasePlaybook.use_case_id == uc.id)
    )
    playbook_ids = [row[0] for row in linked_playbooks.all()]

    if playbook_ids:
        success_exec = await db.execute(
            select(Execution)
            .where(Execution.playbook_id.in_(playbook_ids))
            .where(Execution.status == ExecutionStatus.COMPLETED)
            .limit(1)
        )
        if success_exec.scalar_one_or_none() is None:
            errors.append("At least one linked playbook must have a completed execution")
    else:
        errors.append("At least one playbook must be linked")

    return errors


GATE_CHECKS = {
    (UseCaseStatus.DRAFT, UseCaseStatus.TESTING): _check_draft_to_testing,
    (UseCaseStatus.TESTING, UseCaseStatus.PRODUCTION): _check_testing_to_production,
}


# ---------------------------------------------------------------------------
# Transition executor
# ---------------------------------------------------------------------------


async def transition_use_case(
    db: AsyncSession,
    uc: UseCase,
    *,
    to_status: UseCaseStatus,
    reason: str,
    actor_id: uuid.UUID,
) -> UseCase:
    from_status = uc.status

    # Check transition is legal
    allowed = TRANSITIONS.get(from_status, set())
    if to_status not in allowed:
        raise TransitionError(
            f"Cannot transition from '{from_status.value}' to '{to_status.value}'. "
            f"Allowed transitions: {', '.join(s.value for s in allowed) or 'none'}"
        )

    # Check promotion gates
    gate_check = GATE_CHECKS.get((from_status, to_status))
    if gate_check:
        errors = await gate_check(db, uc)
        if errors:
            raise TransitionError(
                f"Promotion gate failed for {from_status.value} → {to_status.value}: "
                + "; ".join(errors)
            )

    before = _use_case_snapshot(uc)
    uc.status = to_status
    uc.version += 1
    await db.flush()
    await db.refresh(uc)
    after = _use_case_snapshot(uc)

    # Version snapshot
    from akeso_soar.models.use_case import UseCaseVersion

    version = UseCaseVersion(
        use_case_id=uc.id,
        version=uc.version,
        snapshot=after,
        changed_by=actor_id,
        change_description=f"Status transition: {from_status.value} → {to_status.value}. Reason: {reason}",
    )
    db.add(version)
    await db.flush()

    # Audit
    await create_audit_entry(
        db,
        event_type="use_case.transition",
        resource_type="use_case",
        resource_id=str(uc.id),
        user_id=actor_id,
        actor=str(actor_id),
        description=f"Status: {from_status.value} → {to_status.value}",
        details={"from": from_status.value, "to": to_status.value, "reason": reason},
        before_state=before,
        after_state=after,
    )

    return uc
