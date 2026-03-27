"""Alert ingestion webhook endpoint with rate limiting."""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from akeso_soar.dependencies import get_db
from akeso_soar.models.alert import Alert
from akeso_soar.models.enums import Severity
from akeso_soar.services.alert_ingestion import AlertValidationError, ingest_alert
from akeso_soar.services.playbook_trigger import process_alert

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])

# ---------------------------------------------------------------------------
# Simple in-memory rate limiter (per source IP)
# ---------------------------------------------------------------------------

_rate_limit_window = 60  # seconds
_rate_limit_max = 100  # max requests per window
_request_counts: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(client_ip: str) -> bool:
    """Returns True if the request should be allowed."""
    now = time.monotonic()
    window_start = now - _rate_limit_window

    # Prune old entries
    timestamps = _request_counts[client_ip]
    _request_counts[client_ip] = [t for t in timestamps if t > window_start]

    if len(_request_counts[client_ip]) >= _rate_limit_max:
        return False

    _request_counts[client_ip].append(now)
    return True


def set_rate_limit(max_requests: int, window_seconds: int = 60) -> None:
    """Override rate limit settings (for testing)."""
    global _rate_limit_max, _rate_limit_window
    _rate_limit_max = max_requests
    _rate_limit_window = window_seconds


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class AlertOut(BaseModel):
    id: uuid.UUID
    external_id: str
    title: str
    description: str
    severity: Severity
    sigma_rule_id: str | None
    source: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedAlertResponse(BaseModel):
    items: list[AlertOut]
    total: int
    page: int
    limit: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/ingest", status_code=status.HTTP_202_ACCEPTED)
async def ingest_alert_endpoint(
    request: Request,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """Ingest an alert from AkesoSIEM. No auth required (webhook endpoint)."""
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: max {_rate_limit_max} requests per {_rate_limit_window}s",
        )

    try:
        alert = await ingest_alert(db, body)
    except AlertValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Alert validation failed", "errors": e.errors},
        ) from e

    # Run use case matching + playbook triggering pipeline
    trigger_results = await process_alert(db, alert)

    return {
        "alert": AlertOut.model_validate(alert),
        "triggers": trigger_results,
    }


@router.get("", response_model=PaginatedAlertResponse)
async def list_alerts(
    severity: Severity | None = Query(None),
    source: str | None = Query(None),
    sigma_rule_id: str | None = Query(None),
    alert_status: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    query = select(Alert)

    if severity:
        query = query.where(Alert.severity == severity)
    if source:
        query = query.where(Alert.source == source)
    if sigma_rule_id:
        query = query.where(Alert.sigma_rule_id == sigma_rule_id)
    if alert_status:
        query = query.where(Alert.status == alert_status)

    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar_one()

    query = query.order_by(Alert.created_at.desc())
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)

    return PaginatedAlertResponse(items=result.scalars().all(), total=total, page=page, limit=limit)


@router.get("/{alert_id}", response_model=AlertOut)
async def get_alert(
    alert_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return alert
