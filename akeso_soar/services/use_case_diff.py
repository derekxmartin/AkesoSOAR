"""Structured diffing between use case version snapshots."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from akeso_soar.models.use_case import UseCaseVersion


def diff_snapshots(v1_snapshot: dict, v2_snapshot: dict) -> list[dict]:
    """Compare two version snapshots and return a list of field-level changes."""
    changes = []
    all_keys = set(v1_snapshot.keys()) | set(v2_snapshot.keys())

    for key in sorted(all_keys):
        old_val = v1_snapshot.get(key)
        new_val = v2_snapshot.get(key)

        if old_val == new_val:
            continue

        change = {"field": key, "old": old_val, "new": new_val}

        # For list fields, show added/removed items
        if isinstance(old_val, list) and isinstance(new_val, list):
            old_set = set(old_val) if all(isinstance(x, str) for x in old_val) else None
            new_set = set(new_val) if all(isinstance(x, str) for x in new_val) else None
            if old_set is not None and new_set is not None:
                change["added"] = sorted(new_set - old_set)
                change["removed"] = sorted(old_set - new_set)

        # For dict fields, show nested key changes
        if isinstance(old_val, dict) and isinstance(new_val, dict):
            nested = []
            nested_keys = set(old_val.keys()) | set(new_val.keys())
            for nk in sorted(nested_keys):
                if old_val.get(nk) != new_val.get(nk):
                    nested.append({"key": nk, "old": old_val.get(nk), "new": new_val.get(nk)})
            if nested:
                change["nested_changes"] = nested

        changes.append(change)

    return changes


async def get_version_diff(
    db: AsyncSession,
    use_case_id: uuid.UUID,
    v1: int,
    v2: int,
) -> dict:
    """Return a structured diff between two versions of a use case."""
    result = await db.execute(
        select(UseCaseVersion)
        .where(UseCaseVersion.use_case_id == use_case_id)
        .where(UseCaseVersion.version.in_([v1, v2]))
    )
    versions = {v.version: v for v in result.scalars().all()}

    if v1 not in versions:
        return {"error": f"Version {v1} not found"}
    if v2 not in versions:
        return {"error": f"Version {v2} not found"}

    return {
        "use_case_id": str(use_case_id),
        "from_version": v1,
        "to_version": v2,
        "changes": diff_snapshots(versions[v1].snapshot, versions[v2].snapshot),
    }
