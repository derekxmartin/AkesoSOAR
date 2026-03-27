"""Playbook CRUD API endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from akeso_soar.api.rbac import Permission, require_permissions
from akeso_soar.dependencies import get_db
from akeso_soar.engine.parser import parse_playbook_yaml
from akeso_soar.models.enums import PlaybookTriggerType
from akeso_soar.services import playbook_service

router = APIRouter(prefix="/api/v1/playbooks", tags=["playbooks"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class PlaybookCreate(BaseModel):
    name: str
    description: str = ""
    yaml_definition: str  # Raw YAML string
    trigger_type: PlaybookTriggerType = PlaybookTriggerType.MANUAL
    trigger_conditions: dict | None = None
    enabled: bool = True


class PlaybookUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    yaml_definition: str | None = None
    trigger_type: PlaybookTriggerType | None = None
    trigger_conditions: dict | None = None
    enabled: bool | None = None
    change_description: str = ""


class PlaybookOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    version: int
    enabled: bool
    trigger_type: PlaybookTriggerType
    trigger_conditions: dict | None
    definition: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaginatedPlaybookResponse(BaseModel):
    items: list[PlaybookOut]
    total: int
    page: int
    limit: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", response_model=PlaybookOut, status_code=status.HTTP_201_CREATED)
async def create_playbook(
    body: PlaybookCreate,
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(require_permissions(Permission.MANAGE_PLAYBOOKS)),
):
    # Parse and validate YAML
    result = parse_playbook_yaml(body.yaml_definition)
    if not result.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Playbook YAML validation failed", "errors": result.error_dicts()},
        )

    actor_id = uuid.UUID(payload["sub"])
    pb = await playbook_service.create_playbook(
        db,
        name=body.name,
        description=body.description,
        definition=result.data,
        trigger_type=body.trigger_type,
        trigger_conditions=body.trigger_conditions,
        enabled=body.enabled,
        actor_id=actor_id,
    )
    return pb


@router.get("", response_model=PaginatedPlaybookResponse)
async def list_playbooks(
    enabled: bool | None = Query(None),
    trigger_type: PlaybookTriggerType | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permissions(Permission.VIEW_PLAYBOOKS)),
):
    items, total = await playbook_service.list_playbooks(
        db,
        enabled=enabled,
        trigger_type=trigger_type,
        search=search,
        page=page,
        limit=limit,
    )
    return PaginatedPlaybookResponse(items=items, total=total, page=page, limit=limit)


@router.get("/{playbook_id}", response_model=PlaybookOut)
async def get_playbook(
    playbook_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(require_permissions(Permission.VIEW_PLAYBOOKS)),
):
    pb = await playbook_service.get_playbook(db, playbook_id)
    if pb is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playbook not found")
    return pb


@router.patch("/{playbook_id}", response_model=PlaybookOut)
async def update_playbook(
    playbook_id: uuid.UUID,
    body: PlaybookUpdate,
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(require_permissions(Permission.EDIT_PLAYBOOKS)),
):
    pb = await playbook_service.get_playbook(db, playbook_id)
    if pb is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playbook not found")

    fields = body.model_dump(exclude_unset=True, exclude={"yaml_definition", "change_description"})

    # If YAML provided, parse and validate
    if body.yaml_definition is not None:
        result = parse_playbook_yaml(body.yaml_definition)
        if not result.is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Playbook YAML validation failed", "errors": result.error_dicts()},
            )
        fields["definition"] = result.data

    actor_id = uuid.UUID(payload["sub"])
    pb = await playbook_service.update_playbook(
        db, pb, actor_id=actor_id, change_description=body.change_description, **fields
    )
    return pb


@router.delete("/{playbook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_playbook(
    playbook_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    payload: dict = Depends(require_permissions(Permission.MANAGE_PLAYBOOKS)),
):
    pb = await playbook_service.get_playbook(db, playbook_id)
    if pb is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playbook not found")

    actor_id = uuid.UUID(payload["sub"])
    await playbook_service.delete_playbook(db, pb, actor_id=actor_id)
