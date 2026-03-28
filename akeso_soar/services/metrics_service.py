"""Metrics aggregation — MTTR, success rates, execution trends, coverage."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import case, cast, func, select, Float
from sqlalchemy.ext.asyncio import AsyncSession

from akeso_soar.models.enums import (
    ExecutionStatus,
    HumanTaskStatus,
    UseCaseStatus,
)
from akeso_soar.models.execution import Execution
from akeso_soar.models.human_task import HumanTask
from akeso_soar.models.use_case import UseCase


async def get_overview_metrics(db: AsyncSession) -> dict:
    """High-level SOC overview numbers."""
    now = datetime.now(UTC)

    # Active executions (running or paused)
    active_exec = await db.execute(
        select(func.count()).select_from(Execution).where(
            Execution.status.in_([ExecutionStatus.RUNNING, ExecutionStatus.PAUSED])
        )
    )
    active_executions = active_exec.scalar() or 0

    # Total executions
    total_exec = await db.execute(select(func.count()).select_from(Execution))
    total_executions = total_exec.scalar() or 0

    # Pending human tasks
    pending_ht = await db.execute(
        select(func.count()).select_from(HumanTask).where(
            HumanTask.status == HumanTaskStatus.PENDING
        )
    )
    pending_human_tasks = pending_ht.scalar() or 0

    # MTTR (mean time to resolve) — avg duration_ms of completed executions in last 30 days
    mttr_result = await db.execute(
        select(func.avg(Execution.duration_ms)).where(
            Execution.status == ExecutionStatus.COMPLETED,
            Execution.completed_at >= now - timedelta(days=30),
        )
    )
    mttr_ms = mttr_result.scalar()
    mttr_seconds = round(mttr_ms / 1000, 1) if mttr_ms else 0

    # Use case coverage (production use cases / total)
    total_uc = await db.execute(select(func.count()).select_from(UseCase))
    total_use_cases = total_uc.scalar() or 0
    prod_uc = await db.execute(
        select(func.count()).select_from(UseCase).where(UseCase.status == UseCaseStatus.PRODUCTION)
    )
    production_use_cases = prod_uc.scalar() or 0
    coverage_pct = round((production_use_cases / total_use_cases * 100), 1) if total_use_cases else 0

    # Overdue reviews
    overdue = await db.execute(
        select(func.count()).select_from(UseCase).where(
            UseCase.status == UseCaseStatus.PRODUCTION,
            UseCase.next_review_at != None,  # noqa: E711
            UseCase.next_review_at < now,
        )
    )
    overdue_reviews = overdue.scalar() or 0

    # Alerts (total from executions with trigger_alert_id)
    alert_count = await db.execute(
        select(func.count(func.distinct(Execution.trigger_alert_id))).where(
            Execution.trigger_alert_id != None  # noqa: E711
        )
    )
    total_alerts = alert_count.scalar() or 0

    return {
        "active_executions": active_executions,
        "total_executions": total_executions,
        "pending_human_tasks": pending_human_tasks,
        "mttr_seconds": mttr_seconds,
        "coverage_percent": coverage_pct,
        "total_use_cases": total_use_cases,
        "production_use_cases": production_use_cases,
        "overdue_reviews": overdue_reviews,
        "total_alerts": total_alerts,
    }


async def get_playbook_metrics(db: AsyncSession, days: int = 30) -> dict:
    """Playbook execution success/failure rates and trends."""
    now = datetime.now(UTC)
    since = now - timedelta(days=days)

    # Success rate
    total_r = await db.execute(
        select(func.count()).select_from(Execution).where(
            Execution.completed_at >= since,
            Execution.status.in_([ExecutionStatus.COMPLETED, ExecutionStatus.FAILED]),
        )
    )
    total = total_r.scalar() or 0

    success_r = await db.execute(
        select(func.count()).select_from(Execution).where(
            Execution.completed_at >= since,
            Execution.status == ExecutionStatus.COMPLETED,
        )
    )
    successes = success_r.scalar() or 0
    success_rate = round((successes / total * 100), 1) if total else 0

    # Daily execution counts (last N days)
    daily = await db.execute(
        select(
            func.date_trunc("day", Execution.started_at).label("day"),
            func.count().label("total"),
            func.sum(case((Execution.status == ExecutionStatus.COMPLETED, 1), else_=0)).label("completed"),
            func.sum(case((Execution.status == ExecutionStatus.FAILED, 1), else_=0)).label("failed"),
        )
        .where(Execution.started_at >= since)
        .group_by("day")
        .order_by("day")
    )
    trend = [
        {
            "date": row.day.isoformat()[:10] if row.day else None,
            "total": row.total,
            "completed": row.completed or 0,
            "failed": row.failed or 0,
        }
        for row in daily
    ]

    # Average duration by status
    avg_duration = await db.execute(
        select(func.avg(Execution.duration_ms)).where(
            Execution.completed_at >= since,
            Execution.status == ExecutionStatus.COMPLETED,
        )
    )
    avg_ms = avg_duration.scalar()

    return {
        "period_days": days,
        "total_executions": total,
        "successes": successes,
        "failures": total - successes,
        "success_rate": success_rate,
        "avg_duration_ms": round(avg_ms) if avg_ms else 0,
        "daily_trend": trend,
    }


async def get_use_case_metrics(db: AsyncSession) -> dict:
    """Use case status distribution and health."""
    # Status distribution
    dist = await db.execute(
        select(
            UseCase.status,
            func.count().label("count"),
        )
        .group_by(UseCase.status)
    )
    status_counts = {row.status.value: row.count for row in dist}

    # Severity distribution
    sev_dist = await db.execute(
        select(
            UseCase.severity,
            func.count().label("count"),
        )
        .group_by(UseCase.severity)
    )
    severity_counts = {row.severity.value: row.count for row in sev_dist}

    # Overdue reviews detail
    now = datetime.now(UTC)
    overdue_r = await db.execute(
        select(UseCase.id, UseCase.name, UseCase.next_review_at).where(
            UseCase.status == UseCaseStatus.PRODUCTION,
            UseCase.next_review_at != None,  # noqa: E711
            UseCase.next_review_at < now,
        )
        .order_by(UseCase.next_review_at)
        .limit(10)
    )
    overdue_reviews = [
        {"id": str(row.id), "name": row.name, "next_review_at": row.next_review_at.isoformat() if row.next_review_at else None}
        for row in overdue_r
    ]

    return {
        "status_distribution": status_counts,
        "severity_distribution": severity_counts,
        "overdue_reviews": overdue_reviews,
    }


async def get_alerts_by_severity(db: AsyncSession) -> list[dict]:
    """Alert count grouped by severity — reads from the alerts table if it exists, else from executions."""
    try:
        from akeso_soar.models.alert import Alert
        result = await db.execute(
            select(Alert.severity, func.count().label("count"))
            .group_by(Alert.severity)
        )
        return [{"severity": row.severity, "count": row.count} for row in result]
    except Exception:
        return []
