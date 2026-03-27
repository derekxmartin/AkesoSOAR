"""seed_data

Revision ID: dc8490cca28f
Revises: b9cc93673767
Create Date: 2026-03-27 14:27:11.682010

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "dc8490cca28f"
down_revision: str | Sequence[str] | None = "b9cc93673767"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ADMIN_ID = uuid.UUID("00000000-0000-4000-a000-000000000001")

# bcrypt hash of "admin" — MUST be changed on first login in production
ADMIN_PASSWORD_HASH = "$2b$12$abL7X.xZ2hkIEYfMadBq6./5A0hHUm8igaJavx5sblfPrlYNt2lX2"

CONNECTORS = [
    {
        "id": uuid.UUID("00000000-0000-4000-b000-000000000001"),
        "name": "akeso_siem",
        "display_name": "AkesoSIEM",
        "description": "Alert ingestion and case management",
        "connector_type": "rest",
        "operations": {
            "create_case": {"method": "POST", "path": "/api/v1/cases"},
            "update_case": {"method": "PATCH", "path": "/api/v1/cases/{id}"},
            "add_case_note": {"method": "POST", "path": "/api/v1/cases/{id}/notes"},
            "search_alerts": {"method": "GET", "path": "/api/v1/alerts"},
            "get_alert": {"method": "GET", "path": "/api/v1/alerts/{id}"},
            "create_alert_tag": {"method": "POST", "path": "/api/v1/alerts/{id}/tags"},
        },
    },
    {
        "id": uuid.UUID("00000000-0000-4000-b000-000000000002"),
        "name": "akeso_edr",
        "display_name": "AkesoEDR",
        "description": "Endpoint detection and response — isolate, collect, kill",
        "connector_type": "grpc",
        "operations": {
            "isolate_host": {"service": "EDRService", "method": "IsolateHost"},
            "unisolate_host": {"service": "EDRService", "method": "UnisolateHost"},
            "collect_artifacts": {"service": "EDRService", "method": "CollectArtifacts"},
            "kill_process": {"service": "EDRService", "method": "KillProcess"},
            "get_host_info": {"service": "EDRService", "method": "GetHostInfo"},
            "list_alerts": {"service": "EDRService", "method": "ListAlerts"},
        },
    },
    {
        "id": uuid.UUID("00000000-0000-4000-b000-000000000003"),
        "name": "akeso_av",
        "display_name": "AkesoAV",
        "description": "Antivirus scanning and quarantine (via EDR)",
        "connector_type": "grpc",
        "operations": {
            "scan_file": {"service": "AVService", "method": "ScanFile"},
            "scan_host": {"service": "AVService", "method": "ScanHost"},
            "quarantine_file": {"service": "AVService", "method": "QuarantineFile"},
            "get_scan_result": {"service": "AVService", "method": "GetScanResult"},
        },
    },
    {
        "id": uuid.UUID("00000000-0000-4000-b000-000000000004"),
        "name": "akeso_dlp",
        "display_name": "AkesoDLP",
        "description": "Data loss prevention — quarantine files, update policies",
        "connector_type": "grpc",
        "operations": {
            "quarantine_file": {"service": "DLPService", "method": "QuarantineFile"},
            "update_policy": {"service": "DLPService", "method": "UpdatePolicy"},
            "get_incidents": {"service": "DLPService", "method": "GetIncidents"},
            "release_file": {"service": "DLPService", "method": "ReleaseFile"},
        },
    },
    {
        "id": uuid.UUID("00000000-0000-4000-b000-000000000005"),
        "name": "akeso_ndr",
        "display_name": "AkesoNDR",
        "description": "Network detection and response — flow queries, PCAP export",
        "connector_type": "grpc",
        "operations": {
            "query_flows": {"service": "NDRService", "method": "QueryFlows"},
            "get_connection_info": {"service": "NDRService", "method": "GetConnectionInfo"},
            "export_pcap": {"service": "NDRService", "method": "ExportPcap"},
            "get_anomalies": {"service": "NDRService", "method": "GetAnomalies"},
        },
    },
    {
        "id": uuid.UUID("00000000-0000-4000-b000-000000000006"),
        "name": "akeso_fw",
        "display_name": "AkesoFW",
        "description": "Firewall — block/unblock IPs, manage rules",
        "connector_type": "rest",
        "operations": {
            "block_ip": {"method": "POST", "path": "/api/v1/rules/block"},
            "unblock_ip": {"method": "DELETE", "path": "/api/v1/rules/block/{ip}"},
            "block_port": {"method": "POST", "path": "/api/v1/rules/block-port"},
            "add_rule": {"method": "POST", "path": "/api/v1/rules"},
            "remove_rule": {"method": "DELETE", "path": "/api/v1/rules/{id}"},
            "get_rules": {"method": "GET", "path": "/api/v1/rules"},
        },
    },
    {
        "id": uuid.UUID("00000000-0000-4000-b000-000000000007"),
        "name": "akeso_c2",
        "display_name": "AkesoC2",
        "description": "Red team C2 simulation",
        "connector_type": "rest",
        "operations": {
            "list_implants": {"method": "GET", "path": "/api/v1/implants"},
            "task_implant": {"method": "POST", "path": "/api/v1/implants/{id}/tasks"},
            "get_task_result": {"method": "GET", "path": "/api/v1/tasks/{id}"},
        },
    },
    {
        "id": uuid.UUID("00000000-0000-4000-b000-000000000008"),
        "name": "generic_http",
        "display_name": "Generic HTTP",
        "description": "Generic REST connector for external APIs (VirusTotal, AbuseIPDB, etc.)",
        "connector_type": "rest",
        "operations": {
            "get": {"method": "GET"},
            "post": {"method": "POST"},
            "put": {"method": "PUT"},
            "delete": {"method": "DELETE"},
        },
    },
]


def upgrade() -> None:
    users = sa.table(
        "users",
        sa.column("id", UUID(as_uuid=True)),
        sa.column("username", sa.String),
        sa.column("email", sa.String),
        sa.column("password_hash", sa.String),
        sa.column("full_name", sa.String),
        sa.column("role", sa.Enum("admin", name="userrole", create_constraint=False, native_enum=True)),
        sa.column("is_active", sa.Boolean),
        sa.column("mfa_enabled", sa.Boolean),
    )
    op.bulk_insert(
        users,
        [
            {
                "id": ADMIN_ID,
                "username": "admin",
                "email": "admin@akeso.local",
                "password_hash": ADMIN_PASSWORD_HASH,
                "full_name": "System Administrator",
                "role": "admin",
                "is_active": True,
                "mfa_enabled": False,
            },
        ],
    )

    connectors = sa.table(
        "connectors",
        sa.column("id", UUID(as_uuid=True)),
        sa.column("name", sa.String),
        sa.column("display_name", sa.String),
        sa.column("description", sa.String),
        sa.column("connector_type", sa.Enum("rest", "grpc", name="connectortype", create_constraint=False, native_enum=True)),
        sa.column("enabled", sa.Boolean),
        sa.column("config", sa.JSON),
        sa.column("operations", sa.JSON),
    )
    rows = []
    for c in CONNECTORS:
        rows.append(
            {
                "id": c["id"],
                "name": c["name"],
                "display_name": c["display_name"],
                "description": c["description"],
                "connector_type": c["connector_type"],
                "enabled": True,
                "config": {},
                "operations": c["operations"],
            }
        )
    op.bulk_insert(connectors, rows)


def downgrade() -> None:
    op.execute("DELETE FROM connectors WHERE name LIKE 'akeso_%' OR name = 'generic_http'")
    op.execute(f"DELETE FROM users WHERE id = '{ADMIN_ID}'")
