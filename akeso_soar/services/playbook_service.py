"""Playbook CRUD service with versioning."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from akeso_soar.models.enums import PlaybookTriggerType
from akeso_soar.models.playbook import Playbook, PlaybookVersion
from akeso_soar.services.audit_service import create_audit_entry


async def create_playbook(
    db: AsyncSession,
    *,
    name: str,
    description: str,
    definition: dict,
    trigger_type: PlaybookTriggerType = PlaybookTriggerType.MANUAL,
    trigger_conditions: dict | None = None,
    enabled: bool = True,
    actor_id: uuid.UUID,
) -> Playbook:
    pb = Playbook(
        name=name,
        description=description,
        version=1,
        enabled=enabled,
        trigger_type=trigger_type,
        trigger_conditions=trigger_conditions,
        definition=definition,
    )
    db.add(pb)
    await db.flush()
    await db.refresh(pb)

    ver = PlaybookVersion(
        playbook_id=pb.id,
        version=1,
        definition=definition,
        changed_by=actor_id,
        change_description="Initial creation",
    )
    db.add(ver)
    await db.flush()

    await create_audit_entry(
        db,
        event_type="playbook.created",
        resource_type="playbook",
        resource_id=str(pb.id),
        user_id=actor_id,
        actor=str(actor_id),
        description=f"Playbook '{name}' created",
        after_state={"name": name, "version": 1, "enabled": enabled},
    )

    return pb


async def update_playbook(
    db: AsyncSession,
    pb: Playbook,
    *,
    actor_id: uuid.UUID,
    change_description: str = "",
    **fields,
) -> Playbook:
    before = {"name": pb.name, "version": pb.version, "enabled": pb.enabled}

    definition_changed = False
    for key, value in fields.items():
        if value is not None and hasattr(pb, key):
            if key == "definition":
                definition_changed = True
            setattr(pb, key, value)

    # Only bump version if definition changed
    if definition_changed:
        pb.version += 1

    await db.flush()
    await db.refresh(pb)

    if definition_changed:
        ver = PlaybookVersion(
            playbook_id=pb.id,
            version=pb.version,
            definition=pb.definition,
            changed_by=actor_id,
            change_description=change_description or "Updated",
        )
        db.add(ver)
        await db.flush()

    after = {"name": pb.name, "version": pb.version, "enabled": pb.enabled}
    await create_audit_entry(
        db,
        event_type="playbook.updated",
        resource_type="playbook",
        resource_id=str(pb.id),
        user_id=actor_id,
        actor=str(actor_id),
        description=f"Playbook '{pb.name}' updated to v{pb.version}",
        before_state=before,
        after_state=after,
    )

    return pb


async def get_playbook(db: AsyncSession, playbook_id: uuid.UUID) -> Playbook | None:
    result = await db.execute(select(Playbook).where(Playbook.id == playbook_id))
    return result.scalar_one_or_none()


async def list_playbooks(
    db: AsyncSession,
    *,
    enabled: bool | None = None,
    trigger_type: PlaybookTriggerType | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[Playbook], int]:
    query = select(Playbook)

    if enabled is not None:
        query = query.where(Playbook.enabled == enabled)
    if trigger_type:
        query = query.where(Playbook.trigger_type == trigger_type)
    if search:
        query = query.where(Playbook.name.ilike(f"%{search}%"))

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    query = query.order_by(Playbook.updated_at.desc())
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)

    return list(result.scalars().all()), total


async def delete_playbook(
    db: AsyncSession,
    pb: Playbook,
    *,
    actor_id: uuid.UUID,
) -> None:
    await create_audit_entry(
        db,
        event_type="playbook.deleted",
        resource_type="playbook",
        resource_id=str(pb.id),
        user_id=actor_id,
        actor=str(actor_id),
        description=f"Playbook '{pb.name}' deleted",
    )
    await db.delete(pb)
    await db.flush()
