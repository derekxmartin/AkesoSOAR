"""Cross-entity search using PostgreSQL ILIKE for broad matching."""

from __future__ import annotations

from sqlalchemy import or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from akeso_soar.models.alert import Alert
from akeso_soar.models.connector import Connector
from akeso_soar.models.execution import Execution
from akeso_soar.models.playbook import Playbook
from akeso_soar.models.use_case import UseCase


async def global_search(db: AsyncSession, query: str, limit: int = 20) -> list[dict]:
    """Search across use cases, playbooks, executions, alerts, and connectors."""
    if not query or len(query.strip()) < 2:
        return []

    q = f"%{query.strip()}%"
    results: list[dict] = []

    # Use cases — name, description, summary
    uc_stmt = (
        select(UseCase)
        .where(or_(
            UseCase.name.ilike(q),
            UseCase.description.ilike(q),
            UseCase.summary.ilike(q),
        ))
        .order_by(UseCase.updated_at.desc())
        .limit(limit)
    )
    uc_rows = await db.execute(uc_stmt)
    for uc in uc_rows.scalars():
        snippet = _snippet(uc.description or uc.summary or "", query)
        results.append({
            "type": "use_case",
            "id": str(uc.id),
            "name": uc.name,
            "snippet": snippet,
            "status": uc.status.value,
            "url": f"/use-cases/{uc.id}",
        })

    # Playbooks — name, description
    pb_stmt = (
        select(Playbook)
        .where(or_(
            Playbook.name.ilike(q),
            Playbook.description.ilike(q),
        ))
        .order_by(Playbook.updated_at.desc())
        .limit(limit)
    )
    pb_rows = await db.execute(pb_stmt)
    for pb in pb_rows.scalars():
        results.append({
            "type": "playbook",
            "id": str(pb.id),
            "name": pb.name,
            "snippet": pb.description[:100] if pb.description else "",
            "status": "enabled" if pb.enabled else "disabled",
            "url": f"/playbooks/{pb.id}",
        })

    # Alerts — title, external_id
    alert_stmt = (
        select(Alert)
        .where(or_(
            Alert.title.ilike(q),
            Alert.external_id.ilike(q),
        ))
        .order_by(Alert.created_at.desc())
        .limit(limit)
    )
    alert_rows = await db.execute(alert_stmt)
    for a in alert_rows.scalars():
        results.append({
            "type": "alert",
            "id": str(a.id),
            "name": a.title,
            "snippet": f"{a.external_id} · {a.severity.value}",
            "status": a.status,
            "url": f"/alerts",
        })

    # Executions — trigger_alert_id
    exec_stmt = (
        select(Execution)
        .where(Execution.trigger_alert_id.ilike(q))
        .order_by(Execution.created_at.desc())
        .limit(limit)
    )
    exec_rows = await db.execute(exec_stmt)
    for ex in exec_rows.scalars():
        results.append({
            "type": "execution",
            "id": str(ex.id),
            "name": f"Execution {str(ex.id)[:8]}",
            "snippet": f"Alert: {ex.trigger_alert_id} · {ex.status.value}",
            "status": ex.status.value,
            "url": f"/executions/{ex.id}",
        })

    # Connectors — name, display_name
    conn_stmt = (
        select(Connector)
        .where(or_(
            Connector.name.ilike(q),
            Connector.display_name.ilike(q),
        ))
        .limit(limit)
    )
    conn_rows = await db.execute(conn_stmt)
    for c in conn_rows.scalars():
        results.append({
            "type": "connector",
            "id": str(c.id),
            "name": c.display_name,
            "snippet": c.connector_type.value,
            "status": "enabled" if c.enabled else "disabled",
            "url": f"/connectors",
        })

    return results[:limit]


def _snippet(text: str, query: str, window: int = 60) -> str:
    """Extract a short snippet around the first match."""
    lower = text.lower()
    idx = lower.find(query.lower())
    if idx == -1:
        return text[:window] + ("..." if len(text) > window else "")
    start = max(0, idx - window // 2)
    end = min(len(text), idx + len(query) + window // 2)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    return f"{prefix}{text[start:end]}{suffix}"
