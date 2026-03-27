"""MITRE ATT&CK coverage matrix derived from use case mappings."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from akeso_soar.models.enums import UseCaseStatus
from akeso_soar.models.use_case import UseCase

# ---------------------------------------------------------------------------
# MITRE ATT&CK reference data (subset for PoC — the full matrix is 200+ techniques)
# ---------------------------------------------------------------------------

TACTICS = {
    "TA0001": "Initial Access",
    "TA0002": "Execution",
    "TA0003": "Persistence",
    "TA0004": "Privilege Escalation",
    "TA0005": "Defense Evasion",
    "TA0006": "Credential Access",
    "TA0007": "Discovery",
    "TA0008": "Lateral Movement",
    "TA0009": "Collection",
    "TA0010": "Exfiltration",
    "TA0011": "Command and Control",
    "TA0040": "Impact",
    "TA0042": "Resource Development",
    "TA0043": "Reconnaissance",
}

# technique_id → (name, [parent_tactic_ids])
TECHNIQUES: dict[str, tuple[str, list[str]]] = {
    "T1059": ("Command and Scripting Interpreter", ["TA0002"]),
    "T1059.001": ("PowerShell", ["TA0002"]),
    "T1059.003": ("Windows Command Shell", ["TA0002"]),
    "T1078": ("Valid Accounts", ["TA0001", "TA0003", "TA0004", "TA0005"]),
    "T1078.002": ("Domain Accounts", ["TA0001", "TA0003", "TA0004", "TA0005"]),
    "T1110": ("Brute Force", ["TA0006"]),
    "T1110.001": ("Password Guessing", ["TA0006"]),
    "T1110.003": ("Password Spraying", ["TA0006"]),
    "T1003": ("OS Credential Dumping", ["TA0006"]),
    "T1003.001": ("LSASS Memory", ["TA0006"]),
    "T1021": ("Remote Services", ["TA0008"]),
    "T1021.001": ("Remote Desktop Protocol", ["TA0008"]),
    "T1021.002": ("SMB/Windows Admin Shares", ["TA0008"]),
    "T1053": ("Scheduled Task/Job", ["TA0002", "TA0003", "TA0004"]),
    "T1053.005": ("Scheduled Task", ["TA0002", "TA0003", "TA0004"]),
    "T1071": ("Application Layer Protocol", ["TA0011"]),
    "T1071.001": ("Web Protocols", ["TA0011"]),
    "T1486": ("Data Encrypted for Impact", ["TA0040"]),
    "T1566": ("Phishing", ["TA0001"]),
    "T1566.001": ("Spearphishing Attachment", ["TA0001"]),
    "T1566.002": ("Spearphishing Link", ["TA0001"]),
    "T1547": ("Boot or Logon Autostart Execution", ["TA0003", "TA0004"]),
    "T1547.001": ("Registry Run Keys / Startup Folder", ["TA0003", "TA0004"]),
    "T1048": ("Exfiltration Over Alternative Protocol", ["TA0010"]),
    "T1082": ("System Information Discovery", ["TA0007"]),
    "T1083": ("File and Directory Discovery", ["TA0007"]),
    "T1005": ("Data from Local System", ["TA0009"]),
    "T1595": ("Active Scanning", ["TA0043"]),
    "T1583": ("Acquire Infrastructure", ["TA0042"]),
}


async def build_coverage_matrix(db: AsyncSession) -> dict:
    """Build the full MITRE coverage matrix from active use cases.

    Returns a tactic-keyed structure suitable for heatmap rendering.
    """
    # Get all non-deprecated use cases
    result = await db.execute(
        select(UseCase).where(UseCase.status != UseCaseStatus.DEPRECATED)
    )
    use_cases = result.scalars().all()

    # Build technique → use case mapping
    technique_coverage: dict[str, list[dict]] = {}
    for uc in use_cases:
        for tech_id in uc.mitre_techniques:
            if tech_id not in technique_coverage:
                technique_coverage[tech_id] = []
            technique_coverage[tech_id].append({
                "use_case_id": str(uc.id),
                "use_case_name": uc.name,
                "status": uc.status.value,
            })

    # Build tactic → techniques structure
    matrix = {}
    for tactic_id, tactic_name in TACTICS.items():
        techniques = []
        for tech_id, (tech_name, parent_tactics) in TECHNIQUES.items():
            if tactic_id not in parent_tactics:
                continue

            coverage_entries = technique_coverage.get(tech_id, [])
            production_count = sum(1 for e in coverage_entries if e["status"] == "production")
            total_count = len(coverage_entries)

            if production_count > 0:
                coverage_status = "covered"
            elif total_count > 0:
                coverage_status = "partial"
            else:
                coverage_status = "gap"

            techniques.append({
                "technique_id": tech_id,
                "technique_name": tech_name,
                "coverage": coverage_status,
                "use_cases": coverage_entries,
                "count": total_count,
            })

        matrix[tactic_id] = {
            "tactic_name": tactic_name,
            "techniques": techniques,
            "covered": sum(1 for t in techniques if t["coverage"] == "covered"),
            "partial": sum(1 for t in techniques if t["coverage"] == "partial"),
            "gaps": sum(1 for t in techniques if t["coverage"] == "gap"),
        }

    return {
        "matrix": matrix,
        "summary": {
            "total_techniques": len(TECHNIQUES),
            "covered": sum(1 for t in TECHNIQUES if technique_coverage.get(t) and any(e["status"] == "production" for e in technique_coverage[t])),
            "partial": sum(1 for t in TECHNIQUES if technique_coverage.get(t) and not any(e["status"] == "production" for e in technique_coverage[t])),
            "gaps": sum(1 for t in TECHNIQUES if t not in technique_coverage),
        },
    }
