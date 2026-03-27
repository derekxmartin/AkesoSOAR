"""Alert ingestion service — validates, deduplicates, and stores incoming alerts."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from akeso_soar.models.alert import Alert
from akeso_soar.models.enums import Severity

# Required fields in an alert payload
REQUIRED_FIELDS = {"external_id", "title"}
VALID_SEVERITIES = {s.value for s in Severity}


class AlertValidationError(Exception):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def validate_alert_payload(payload: dict) -> list[str]:
    """Validate an incoming alert payload. Returns list of error strings."""
    errors = []
    for field in REQUIRED_FIELDS:
        if not payload.get(field):
            errors.append(f"Missing required field: {field}")

    sev = payload.get("severity")
    if sev and sev not in VALID_SEVERITIES:
        errors.append(f"Invalid severity: {sev}. Must be one of: {', '.join(VALID_SEVERITIES)}")

    return errors


async def ingest_alert(db: AsyncSession, payload: dict) -> Alert:
    """Validate, deduplicate, and store an alert.

    Raises AlertValidationError if payload is invalid.
    Returns existing alert if duplicate (by external_id).
    """
    errors = validate_alert_payload(payload)
    if errors:
        raise AlertValidationError(errors)

    external_id = payload["external_id"]

    # Deduplicate by external_id
    result = await db.execute(select(Alert).where(Alert.external_id == external_id))
    existing = result.scalar_one_or_none()
    if existing is not None:
        return existing

    alert = Alert(
        external_id=external_id,
        title=payload["title"],
        description=payload.get("description", ""),
        severity=Severity(payload.get("severity", "medium")),
        sigma_rule_id=payload.get("sigma_rule_id"),
        source=payload.get("source", "akeso_siem"),
        raw_payload=payload,
        status="new",
    )
    db.add(alert)
    await db.flush()
    await db.refresh(alert)
    return alert
