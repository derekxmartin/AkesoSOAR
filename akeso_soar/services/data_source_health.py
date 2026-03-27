"""Data source health tracking — checks use case dependencies against SIEM ingestion sources."""

from __future__ import annotations

from akeso_soar.models.use_case import UseCase

# Mock of active SIEM ingestion sources.
# In production, this would call AkesoSIEM's API via the connector.
_MOCK_ACTIVE_SOURCES: set[str] = {
    "windows_security",
    "akeso_edr",
    "syslog",
    "dns_logs",
    "firewall_logs",
}


def set_mock_active_sources(sources: set[str]) -> None:
    """Override the mock source list (for testing)."""
    global _MOCK_ACTIVE_SOURCES
    _MOCK_ACTIVE_SOURCES = sources


async def get_active_siem_sources() -> set[str]:
    """Return the set of currently active ingestion sources from AkesoSIEM.

    TODO: Replace with actual SIEM connector call when available.
    """
    return _MOCK_ACTIVE_SOURCES


async def check_use_case_health(uc: UseCase) -> dict:
    """Check a use case's data source dependencies against active SIEM sources.

    Returns:
        {
            "status": "operational" | "partial" | "non_operational",
            "required_sources": [...],
            "active_sources": [...],
            "missing_sources": [...],
            "details": [...]
        }
    """
    active = await get_active_siem_sources()

    if not uc.data_sources_required:
        return {
            "status": "operational",
            "required_sources": [],
            "active_sources": sorted(active),
            "missing_sources": [],
            "details": "No data sources declared — health check not applicable.",
        }

    # Extract source names from the data_sources_required JSONB
    # Expected format: [{"source": "windows_security", ...}, {"source": "akeso_edr", ...}]
    required_entries = uc.data_sources_required if isinstance(uc.data_sources_required, list) else []
    required_names = set()
    details = []

    for entry in required_entries:
        src = entry.get("source", "")
        required_names.add(src)
        is_active = src in active
        details.append({
            "source": src,
            "description": entry.get("description", ""),
            "active": is_active,
        })

    missing = required_names - active

    if not missing:
        health_status = "operational"
    elif missing == required_names:
        health_status = "non_operational"
    else:
        health_status = "partial"

    return {
        "status": health_status,
        "required_sources": sorted(required_names),
        "active_sources": sorted(active & required_names),
        "missing_sources": sorted(missing),
        "details": details,
    }
