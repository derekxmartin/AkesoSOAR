"""Use case ↔ playbook linking service."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from akeso_soar.models.playbook import Playbook, UseCasePlaybook
from akeso_soar.models.use_case import UseCase
from akeso_soar.services.audit_service import create_audit_entry


async def link_playbook(
    db: AsyncSession,
    use_case: UseCase,
    playbook_id: uuid.UUID,
    *,
    actor_id: uuid.UUID,
) -> UseCasePlaybook:
    # Verify playbook exists
    result = await db.execute(select(Playbook).where(Playbook.id == playbook_id))
    playbook = result.scalar_one_or_none()
    if playbook is None:
        raise ValueError("Playbook not found")

    # Check not already linked
    existing = await db.execute(
        select(UseCasePlaybook).where(
            UseCasePlaybook.use_case_id == use_case.id,
            UseCasePlaybook.playbook_id == playbook_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ValueError("Playbook already linked to this use case")

    link = UseCasePlaybook(use_case_id=use_case.id, playbook_id=playbook_id)
    db.add(link)
    await db.flush()

    await create_audit_entry(
        db,
        event_type="use_case.playbook_linked",
        resource_type="use_case",
        resource_id=str(use_case.id),
        user_id=actor_id,
        actor=str(actor_id),
        description=f"Playbook '{playbook.name}' linked to use case '{use_case.name}'",
        details={"playbook_id": str(playbook_id), "playbook_name": playbook.name},
    )

    return link


async def unlink_playbook(
    db: AsyncSession,
    use_case: UseCase,
    playbook_id: uuid.UUID,
    *,
    actor_id: uuid.UUID,
) -> None:
    result = await db.execute(
        select(UseCasePlaybook).where(
            UseCasePlaybook.use_case_id == use_case.id,
            UseCasePlaybook.playbook_id == playbook_id,
        )
    )
    link = result.scalar_one_or_none()
    if link is None:
        raise ValueError("Playbook not linked to this use case")

    await db.delete(link)
    await db.flush()

    await create_audit_entry(
        db,
        event_type="use_case.playbook_unlinked",
        resource_type="use_case",
        resource_id=str(use_case.id),
        user_id=actor_id,
        actor=str(actor_id),
        description=f"Playbook unlinked from use case '{use_case.name}'",
        details={"playbook_id": str(playbook_id)},
    )


async def get_linked_playbooks(db: AsyncSession, use_case_id: uuid.UUID) -> list[Playbook]:
    result = await db.execute(
        select(Playbook)
        .join(UseCasePlaybook, UseCasePlaybook.playbook_id == Playbook.id)
        .where(UseCasePlaybook.use_case_id == use_case_id)
    )
    return list(result.scalars().all())


async def get_linked_use_cases(db: AsyncSession, playbook_id: uuid.UUID) -> list[UseCase]:
    result = await db.execute(
        select(UseCase)
        .join(UseCasePlaybook, UseCasePlaybook.use_case_id == UseCase.id)
        .where(UseCasePlaybook.playbook_id == playbook_id)
    )
    return list(result.scalars().all())


async def disable_linked_playbooks(
    db: AsyncSession,
    use_case: UseCase,
    *,
    actor_id: uuid.UUID,
) -> list[Playbook]:
    """Disable all playbooks linked to a use case (called on deprecation)."""
    playbooks = await get_linked_playbooks(db, use_case.id)
    disabled = []
    for pb in playbooks:
        if pb.enabled:
            pb.enabled = False
            disabled.append(pb)
            await create_audit_entry(
                db,
                event_type="playbook.auto_disabled",
                resource_type="playbook",
                resource_id=str(pb.id),
                user_id=actor_id,
                actor=str(actor_id),
                description=f"Playbook '{pb.name}' auto-disabled: linked use case '{use_case.name}' deprecated",
                details={"use_case_id": str(use_case.id)},
            )
    await db.flush()
    return disabled
