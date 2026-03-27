"""Use case CRUD service with automatic versioning."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from akeso_soar.models.enums import EscalationPolicy, Severity, UseCaseStatus
from akeso_soar.models.use_case import UseCase, UseCaseVersion
from akeso_soar.services.audit_service import create_audit_entry


def _use_case_snapshot(uc: UseCase) -> dict:
    """Create a JSON-serializable snapshot of a use case for versioning."""
    return {
        "name": uc.name,
        "description": uc.description,
        "status": uc.status.value,
        "severity": uc.severity.value,
        "owner_id": str(uc.owner_id),
        "review_cadence_days": uc.review_cadence_days,
        "mitre_tactics": uc.mitre_tactics,
        "mitre_techniques": uc.mitre_techniques,
        "mitre_data_sources": uc.mitre_data_sources,
        "sigma_rule_ids": uc.sigma_rule_ids,
        "siem_alert_query": uc.siem_alert_query,
        "severity_threshold": uc.severity_threshold.value if uc.severity_threshold else None,
        "data_sources_required": uc.data_sources_required,
        "escalation_policy": uc.escalation_policy.value,
        "notification_channels": uc.notification_channels,
        "summary": uc.summary,
        "investigation_guide": uc.investigation_guide,
        "false_positive_guidance": uc.false_positive_guidance,
        "references": uc.references,
    }


async def create_use_case(
    db: AsyncSession,
    *,
    name: str,
    description: str,
    severity: Severity,
    owner_id: uuid.UUID,
    actor_id: uuid.UUID,
    mitre_tactics: list[str] | None = None,
    mitre_techniques: list[str] | None = None,
    mitre_data_sources: list[str] | None = None,
    sigma_rule_ids: list[str] | None = None,
    siem_alert_query: str | None = None,
    severity_threshold: Severity | None = None,
    data_sources_required: dict | None = None,
    escalation_policy: EscalationPolicy = EscalationPolicy.MANUAL,
    notification_channels: list[str] | None = None,
    summary: str = "",
    investigation_guide: str = "",
    false_positive_guidance: str = "",
    references: list[str] | None = None,
    review_cadence_days: int = 90,
) -> UseCase:
    uc = UseCase(
        name=name,
        description=description,
        severity=severity,
        owner_id=owner_id,
        version=1,
        status=UseCaseStatus.DRAFT,
        mitre_tactics=mitre_tactics or [],
        mitre_techniques=mitre_techniques or [],
        mitre_data_sources=mitre_data_sources or [],
        sigma_rule_ids=sigma_rule_ids or [],
        siem_alert_query=siem_alert_query,
        severity_threshold=severity_threshold,
        data_sources_required=data_sources_required,
        escalation_policy=escalation_policy,
        notification_channels=notification_channels or [],
        summary=summary,
        investigation_guide=investigation_guide,
        false_positive_guidance=false_positive_guidance,
        references=references or [],
        review_cadence_days=review_cadence_days,
    )
    db.add(uc)
    await db.flush()
    await db.refresh(uc)

    # Create initial version
    version = UseCaseVersion(
        use_case_id=uc.id,
        version=1,
        snapshot=_use_case_snapshot(uc),
        changed_by=actor_id,
        change_description="Initial creation",
    )
    db.add(version)
    await db.flush()

    # Audit
    await create_audit_entry(
        db,
        event_type="use_case.created",
        resource_type="use_case",
        resource_id=str(uc.id),
        user_id=actor_id,
        actor=str(actor_id),
        description=f"Use case '{name}' created",
        after_state=_use_case_snapshot(uc),
    )

    return uc


async def update_use_case(
    db: AsyncSession,
    uc: UseCase,
    *,
    actor_id: uuid.UUID,
    change_description: str = "",
    **fields,
) -> UseCase:
    before = _use_case_snapshot(uc)

    for key, value in fields.items():
        if value is not None and hasattr(uc, key):
            setattr(uc, key, value)

    uc.version += 1
    await db.flush()
    await db.refresh(uc)

    after = _use_case_snapshot(uc)

    # Create version
    version = UseCaseVersion(
        use_case_id=uc.id,
        version=uc.version,
        snapshot=after,
        changed_by=actor_id,
        change_description=change_description or "Updated",
    )
    db.add(version)
    await db.flush()

    # Audit
    await create_audit_entry(
        db,
        event_type="use_case.updated",
        resource_type="use_case",
        resource_id=str(uc.id),
        user_id=actor_id,
        actor=str(actor_id),
        description=f"Use case '{uc.name}' updated to v{uc.version}",
        before_state=before,
        after_state=after,
    )

    return uc


async def get_use_case(db: AsyncSession, use_case_id: uuid.UUID) -> UseCase | None:
    result = await db.execute(select(UseCase).where(UseCase.id == use_case_id))
    return result.scalar_one_or_none()


async def list_use_cases(
    db: AsyncSession,
    *,
    status: UseCaseStatus | None = None,
    severity: Severity | None = None,
    owner_id: uuid.UUID | None = None,
    mitre_tactic: str | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[UseCase], int]:
    query = select(UseCase)

    if status:
        query = query.where(UseCase.status == status)
    if severity:
        query = query.where(UseCase.severity == severity)
    if owner_id:
        query = query.where(UseCase.owner_id == owner_id)
    if mitre_tactic:
        query = query.where(UseCase.mitre_tactics.any(mitre_tactic))
    if search:
        query = query.where(UseCase.name.ilike(f"%{search}%"))

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    query = query.order_by(UseCase.updated_at.desc())
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)

    return list(result.scalars().all()), total


async def soft_delete_use_case(
    db: AsyncSession,
    uc: UseCase,
    *,
    actor_id: uuid.UUID,
    reason: str = "",
) -> None:
    before = _use_case_snapshot(uc)
    uc.status = UseCaseStatus.DEPRECATED
    await db.flush()

    await create_audit_entry(
        db,
        event_type="use_case.deleted",
        resource_type="use_case",
        resource_id=str(uc.id),
        user_id=actor_id,
        actor=str(actor_id),
        description=f"Use case '{uc.name}' soft-deleted (deprecated): {reason}",
        before_state=before,
        after_state=_use_case_snapshot(uc),
    )


async def get_versions(
    db: AsyncSession,
    use_case_id: uuid.UUID,
) -> list[UseCaseVersion]:
    result = await db.execute(
        select(UseCaseVersion)
        .where(UseCaseVersion.use_case_id == use_case_id)
        .order_by(UseCaseVersion.version.desc())
    )
    return list(result.scalars().all())
