"""Review cadence tracking for use cases in Production."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from akeso_soar.models.enums import UseCaseStatus
from akeso_soar.models.use_case import UseCase
from akeso_soar.services.audit_service import create_audit_entry


async def record_review(
    db: AsyncSession,
    uc: UseCase,
    *,
    actor_id: uuid.UUID,
    notes: str = "",
) -> UseCase:
    """Record a review of a use case and reset its next_review_at."""
    now = datetime.now(UTC)
    uc.last_reviewed_at = now
    uc.next_review_at = now + timedelta(days=uc.review_cadence_days)
    await db.flush()
    await db.refresh(uc)

    await create_audit_entry(
        db,
        event_type="use_case.reviewed",
        resource_type="use_case",
        resource_id=str(uc.id),
        user_id=actor_id,
        actor=str(actor_id),
        description=f"Use case '{uc.name}' reviewed",
        details={"notes": notes, "next_review_at": uc.next_review_at.isoformat()},
    )

    return uc


async def get_overdue_use_cases(db: AsyncSession) -> list[UseCase]:
    """Return all Production use cases past their review date."""
    now = datetime.now(UTC)
    result = await db.execute(
        select(UseCase).where(
            UseCase.status == UseCaseStatus.PRODUCTION,
            UseCase.next_review_at < now,
        )
    )
    return list(result.scalars().all())


async def initialize_review_dates(db: AsyncSession) -> int:
    """Set next_review_at for Production use cases that don't have one yet.

    Returns the number of use cases updated.
    """
    now = datetime.now(UTC)
    stmt = (
        update(UseCase)
        .where(
            UseCase.status == UseCaseStatus.PRODUCTION,
            UseCase.next_review_at.is_(None),
        )
        .values(next_review_at=now + timedelta(days=90))
    )
    result = await db.execute(stmt)
    await db.flush()
    return result.rowcount
