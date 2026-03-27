"""Use case matching engine — evaluates alerts against active use cases."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from akeso_soar.models.alert import Alert
from akeso_soar.models.enums import Severity, UseCaseStatus
from akeso_soar.models.use_case import UseCase

logger = logging.getLogger(__name__)

# Severity ranking for threshold comparison
_SEVERITY_RANK = {
    Severity.INFORMATIONAL: 0,
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}


def _severity_meets_threshold(alert_severity: Severity, threshold: Severity | None) -> bool:
    """Check if alert severity meets or exceeds the use case threshold."""
    if threshold is None:
        return True
    return _SEVERITY_RANK.get(alert_severity, 0) >= _SEVERITY_RANK.get(threshold, 0)


def _matches_sigma_rule(alert: Alert, use_case: UseCase) -> bool:
    """Check if the alert's sigma_rule_id matches any of the use case's sigma_rule_ids."""
    if not use_case.sigma_rule_ids:
        return False
    return alert.sigma_rule_id is not None and alert.sigma_rule_id in use_case.sigma_rule_ids


def _matches_mitre_technique(alert_payload: dict, use_case: UseCase) -> bool:
    """Check if the alert's MITRE techniques overlap with the use case's techniques."""
    if not use_case.mitre_techniques:
        return False
    alert_techniques = set()
    # Check common ECS-like locations for technique IDs
    threat = alert_payload.get("threat", {})
    if isinstance(threat, dict):
        technique = threat.get("technique", {})
        if isinstance(technique, dict):
            tid = technique.get("id")
            if tid:
                alert_techniques.add(tid)
        elif isinstance(technique, list):
            for t in technique:
                if isinstance(t, dict) and "id" in t:
                    alert_techniques.add(t["id"])

    # Also check top-level mitre_technique_ids if present
    for tid in alert_payload.get("mitre_technique_ids", []):
        alert_techniques.add(tid)

    return bool(alert_techniques & set(use_case.mitre_techniques))


def evaluate_match(alert: Alert, use_case: UseCase) -> dict | None:
    """Evaluate whether an alert matches a use case.

    Returns a match details dict if matched, None otherwise.
    A match requires at least one of:
    - Sigma rule ID match
    - MITRE technique overlap
    AND the alert severity must meet the use case's threshold.
    """
    # Severity threshold gate
    if not _severity_meets_threshold(alert.severity, use_case.severity_threshold):
        return None

    match_reasons = []

    if _matches_sigma_rule(alert, use_case):
        match_reasons.append("sigma_rule_id")

    if _matches_mitre_technique(alert.raw_payload, use_case):
        match_reasons.append("mitre_technique")

    if not match_reasons:
        return None

    return {
        "use_case_id": str(use_case.id),
        "use_case_name": use_case.name,
        "match_reasons": match_reasons,
        "alert_severity": alert.severity.value,
        "threshold": use_case.severity_threshold.value if use_case.severity_threshold else None,
    }


async def match_alert(db: AsyncSession, alert: Alert) -> list[dict]:
    """Evaluate an alert against all active (Production) use cases.

    Returns a list of match dicts for each matched use case.
    """
    result = await db.execute(
        select(UseCase).where(UseCase.status == UseCaseStatus.PRODUCTION)
    )
    use_cases = result.scalars().all()

    matches = []
    for uc in use_cases:
        match = evaluate_match(alert, uc)
        if match:
            matches.append(match)
            logger.info(
                "Alert %s matched use case %s (%s)",
                alert.external_id,
                uc.name,
                ", ".join(match["match_reasons"]),
            )

    return matches
