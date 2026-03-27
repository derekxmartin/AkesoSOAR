"""Generic audit logging service for all entity changes."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from akeso_soar.models.audit import AuditLog


async def create_audit_entry(
    db: AsyncSession,
    *,
    event_type: str,
    resource_type: str,
    resource_id: str,
    actor: str = "system",
    user_id: uuid.UUID | None = None,
    description: str = "",
    details: dict | None = None,
    before_state: dict | None = None,
    after_state: dict | None = None,
) -> AuditLog:
    entry = AuditLog(
        event_type=event_type,
        resource_type=resource_type,
        resource_id=str(resource_id),
        actor=actor,
        user_id=user_id,
        description=description,
        details=details,
        before_state=before_state,
        after_state=after_state,
    )
    db.add(entry)
    await db.flush()
    return entry


async def query_audit_log(
    db: AsyncSession,
    *,
    resource_type: str | None = None,
    resource_id: str | None = None,
    event_type: str | None = None,
    user_id: uuid.UUID | None = None,
    after: datetime | None = None,
    before: datetime | None = None,
    page: int = 1,
    limit: int = 50,
) -> tuple[list[AuditLog], int]:
    """Return paginated, filtered audit log entries and total count."""
    query = select(AuditLog)

    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    if resource_id:
        query = query.where(AuditLog.resource_id == resource_id)
    if event_type:
        query = query.where(AuditLog.event_type == event_type)
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if after:
        query = query.where(AuditLog.created_at >= after)
    if before:
        query = query.where(AuditLog.created_at <= before)

    # Total count (without pagination)
    from sqlalchemy import func

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    # Paginated results
    query = query.order_by(AuditLog.created_at.desc())
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)

    return list(result.scalars().all()), total
