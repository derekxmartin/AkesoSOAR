"""Use case CRUD API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from akeso_soar.api.rbac import Permission, require_permissions
from akeso_soar.dependencies import get_db
from akeso_soar.models.enums import EscalationPolicy, Severity, UseCaseStatus
from akeso_soar.services import use_case_service
from akeso_soar.services.data_source_health import check_use_case_health
from akeso_soar.services.review_scheduler import get_overdue_use_cases, record_review
from akeso_soar.services.use_case_diff import get_version_diff
from akeso_soar.services.use_case_lifecycle import TransitionError, transition_use_case
from akeso_soar.services.use_case_playbook_link import get_linked_playbooks, link_playbook, unlink_playbook

router = APIRouter(prefix="/api/v1/use-cases", tags=["use-cases"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class UseCaseCreate(BaseModel):
    name: str
    description: str
    severity: Severity = Severity.MEDIUM
    owner_id: uuid.UUID
    mitre_tactics: list[str] = []
    mitre_techniques: list[str] = []
    mitre_data_sources: list[str] = []
    sigma_rule_ids: list[str] = []
    siem_alert_query: str | None = None
    severity_threshold: Severity | None = None
    data_sources_required: list | dict | None = None
    escalation_policy: EscalationPolicy = EscalationPolicy.MANUAL
    notification_channels: list[str] = []
    summary: str = ""
    investigation_guide: str = ""
    false_positive_guidance: str = ""
    references: list[str] = []
    review_cadence_days: int = 90


class UseCaseUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    severity: Severity | None = None
    owner_id: uuid.UUID | None = None
    mitre_tactics: list[str] | None = None
    mitre_techniques: list[str] | None = None
    mitre_data_sources: list[str] | None = None
    sigma_rule_ids: list[str] | None = None
    siem_alert_query: str | None = None
    severity_threshold: Severity | None = None
    data_sources_required: list | dict | None = None
    escalation_policy: EscalationPolicy | None = None
    notification_channels: list[str] | None = None
    summary: str | None = None
    investigation_guide: str | None = None
    false_positive_guidance: str | None = None
    references: list[str] | None = None
    review_cadence_days: int | None = None
    change_description: str = ""


class UseCaseOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    version: int
    status: UseCaseStatus
    severity: Severity
    owner_id: uuid.UUID
    review_cadence_days: int
    last_reviewed_at: datetime | None
    next_review_at: datetime | None
    mitre_tactics: list[str]
    mitre_techniques: list[str]
    mitre_data_sources: list[str]
    sigma_rule_ids: list[str]
    siem_alert_query: str | None
    severity_threshold: Severity | None
    data_sources_required: list | dict | None
    escalation_policy: EscalationPolicy
    notification_channels: list[str]
    summary: str
    investigation_guide: str
    false_positive_guidance: str
    references: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UseCaseVersionOut(BaseModel):
    id: uuid.UUID
    use_case_id: uuid.UUID
    version: int
    snapshot: dict
    changed_by: uuid.UUID
    change_description: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedUseCaseResponse(BaseModel):
    items: list[UseCaseOut]
    total: int
    page: int
    limit: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", response_model=UseCaseOut, status_code=status.HTTP_201_CREATED)
async def create_use_case(
    body: UseCaseCreate,
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(require_permissions(Permission.MANAGE_USE_CASES)),
):
    actor_id = uuid.UUID(payload["sub"])
    uc = await use_case_service.create_use_case(
        db,
        actor_id=actor_id,
        **body.model_dump(),
    )
    return uc


@router.get("", response_model=PaginatedUseCaseResponse)
async def list_use_cases(
    status_filter: UseCaseStatus | None = Query(None, alias="status"),
    severity: Severity | None = Query(None),
    owner_id: uuid.UUID | None = Query(None),
    mitre_tactic: str | None = Query(None),
    search: str | None = Query(None),
    overdue: bool = Query(False),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permissions(Permission.VIEW_USE_CASES)),
):
    if overdue:
        items = await get_overdue_use_cases(db)
        return PaginatedUseCaseResponse(items=items, total=len(items), page=1, limit=len(items) or 1)

    items, total = await use_case_service.list_use_cases(
        db,
        status=status_filter,
        severity=severity,
        owner_id=owner_id,
        mitre_tactic=mitre_tactic,
        search=search,
        page=page,
        limit=limit,
    )
    return PaginatedUseCaseResponse(items=items, total=total, page=page, limit=limit)


@router.get("/{use_case_id}", response_model=UseCaseOut)
async def get_use_case(
    use_case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permissions(Permission.VIEW_USE_CASES)),
):
    uc = await use_case_service.get_use_case(db, use_case_id)
    if uc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Use case not found")
    return uc


@router.patch("/{use_case_id}", response_model=UseCaseOut)
async def update_use_case(
    use_case_id: uuid.UUID,
    body: UseCaseUpdate,
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(require_permissions(Permission.EDIT_USE_CASES)),
):
    uc = await use_case_service.get_use_case(db, use_case_id)
    if uc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Use case not found")

    actor_id = uuid.UUID(payload["sub"])
    fields = body.model_dump(exclude_unset=True, exclude={"change_description"})
    uc = await use_case_service.update_use_case(
        db, uc, actor_id=actor_id, change_description=body.change_description, **fields
    )
    return uc


@router.delete("/{use_case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_use_case(
    use_case_id: uuid.UUID,
    reason: str = Query("", description="Reason for deletion"),
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(require_permissions(Permission.MANAGE_USE_CASES)),
):
    uc = await use_case_service.get_use_case(db, use_case_id)
    if uc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Use case not found")

    actor_id = uuid.UUID(payload["sub"])
    await use_case_service.soft_delete_use_case(db, uc, actor_id=actor_id, reason=reason)


class TransitionRequest(BaseModel):
    to_status: UseCaseStatus
    reason: str


@router.post("/{use_case_id}/transition", response_model=UseCaseOut)
async def transition(
    use_case_id: uuid.UUID,
    body: TransitionRequest,
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(require_permissions(Permission.MANAGE_USE_CASES)),
):
    uc = await use_case_service.get_use_case(db, use_case_id)
    if uc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Use case not found")

    actor_id = uuid.UUID(payload["sub"])
    try:
        uc = await transition_use_case(db, uc, to_status=body.to_status, reason=body.reason, actor_id=actor_id)
    except TransitionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message) from e
    return uc


@router.get("/{use_case_id}/versions", response_model=list[UseCaseVersionOut])
async def list_versions(
    use_case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permissions(Permission.VIEW_USE_CASES)),
):
    uc = await use_case_service.get_use_case(db, use_case_id)
    if uc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Use case not found")
    return await use_case_service.get_versions(db, use_case_id)


@router.get("/{use_case_id}/diff")
async def diff_versions(
    use_case_id: uuid.UUID,
    v1: int = Query(..., description="First version number"),
    v2: int = Query(..., description="Second version number"),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permissions(Permission.VIEW_USE_CASES)),
):
    uc = await use_case_service.get_use_case(db, use_case_id)
    if uc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Use case not found")

    result = await get_version_diff(db, use_case_id, v1, v2)
    if "error" in result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])
    return result


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@router.get("/{use_case_id}/health")
async def use_case_health(
    use_case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permissions(Permission.VIEW_USE_CASES)),
):
    uc = await use_case_service.get_use_case(db, use_case_id)
    if uc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Use case not found")
    return await check_use_case_health(uc)


# ---------------------------------------------------------------------------
# Review
# ---------------------------------------------------------------------------


class ReviewRequest(BaseModel):
    notes: str = ""


@router.post("/{use_case_id}/review", response_model=UseCaseOut)
async def review_use_case(
    use_case_id: uuid.UUID,
    body: ReviewRequest,
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(require_permissions(Permission.MANAGE_USE_CASES)),
):
    uc = await use_case_service.get_use_case(db, use_case_id)
    if uc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Use case not found")

    actor_id = uuid.UUID(payload["sub"])
    uc = await record_review(db, uc, actor_id=actor_id, notes=body.notes)
    return uc


# ---------------------------------------------------------------------------
# Playbook linking
# ---------------------------------------------------------------------------


class PlaybookLinkRequest(BaseModel):
    playbook_id: uuid.UUID


class LinkedPlaybookOut(BaseModel):
    id: uuid.UUID
    name: str
    version: int
    enabled: bool

    model_config = {"from_attributes": True}


@router.get("/{use_case_id}/playbooks", response_model=list[LinkedPlaybookOut])
async def list_linked_playbooks(
    use_case_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permissions(Permission.VIEW_USE_CASES)),
):
    uc = await use_case_service.get_use_case(db, use_case_id)
    if uc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Use case not found")
    return await get_linked_playbooks(db, use_case_id)


@router.post("/{use_case_id}/playbooks", status_code=status.HTTP_201_CREATED)
async def link_playbook_to_use_case(
    use_case_id: uuid.UUID,
    body: PlaybookLinkRequest,
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(require_permissions(Permission.MANAGE_USE_CASES)),
):
    uc = await use_case_service.get_use_case(db, use_case_id)
    if uc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Use case not found")

    actor_id = uuid.UUID(payload["sub"])
    try:
        await link_playbook(db, uc, body.playbook_id, actor_id=actor_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return {"status": "linked"}


@router.delete("/{use_case_id}/playbooks/{playbook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_playbook_from_use_case(
    use_case_id: uuid.UUID,
    playbook_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(require_permissions(Permission.MANAGE_USE_CASES)),
):
    uc = await use_case_service.get_use_case(db, use_case_id)
    if uc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Use case not found")

    actor_id = uuid.UUID(payload["sub"])
    try:
        await unlink_playbook(db, uc, playbook_id, actor_id=actor_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
