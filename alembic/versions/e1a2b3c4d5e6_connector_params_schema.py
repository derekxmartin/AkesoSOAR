"""add params_schema to connector operations

Revision ID: e1a2b3c4d5e6
Revises: dc8490cca28f
Create Date: 2026-03-27 20:00:00.000000

"""

import json
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e1a2b3c4d5e6"
down_revision: str | Sequence[str] | None = "dc8490cca28f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Enhanced operations with params_schema and descriptions
OPERATIONS_UPDATE = {
    "akeso_siem": {
        "create_case": {
            "method": "POST", "path": "/api/v1/cases",
            "description": "Create a new SIEM case",
            "params_schema": {
                "title": {"description": "Case title"},
                "severity": {"description": "low | medium | high | critical"},
                "description": {"description": "Case description"},
                "source_alert_id": {"description": "Originating alert ID"},
            },
        },
        "update_case": {
            "method": "PATCH", "path": "/api/v1/cases/{id}",
            "description": "Update an existing case",
            "params_schema": {
                "case_id": {"description": "Case UUID"},
                "status": {"description": "open | investigating | resolved | closed"},
                "assignee": {"description": "Username to assign"},
            },
        },
        "add_case_note": {
            "method": "POST", "path": "/api/v1/cases/{id}/notes",
            "description": "Add a note to a case",
            "params_schema": {
                "case_id": {"description": "Case UUID"},
                "note": {"description": "Note content (supports markdown)"},
            },
        },
        "search_alerts": {
            "method": "GET", "path": "/api/v1/alerts",
            "description": "Search SIEM alerts",
            "params_schema": {
                "query": {"description": "Search query string"},
                "severity": {"description": "Filter by severity"},
                "time_range": {"description": "e.g. 1h, 24h, 7d"},
            },
        },
        "get_alert": {
            "method": "GET", "path": "/api/v1/alerts/{id}",
            "description": "Get a single alert by ID",
            "params_schema": {
                "alert_id": {"description": "Alert ID"},
            },
        },
        "create_alert_tag": {
            "method": "POST", "path": "/api/v1/alerts/{id}/tags",
            "description": "Tag an alert",
            "params_schema": {
                "alert_id": {"description": "Alert ID"},
                "tag": {"description": "Tag name"},
            },
        },
        "lookup_ip": {
            "method": "GET", "path": "/api/v1/enrich/ip/{ip}",
            "description": "Enrich an IP address via SIEM intelligence",
            "params_schema": {
                "ip": {"description": "IP address to look up"},
            },
        },
    },
    "akeso_edr": {
        "isolate_host": {
            "service": "EDRService", "method": "IsolateHost",
            "description": "Network-isolate an endpoint",
            "params_schema": {
                "hostname": {"description": "Target hostname"},
                "reason": {"description": "Isolation reason"},
            },
        },
        "unisolate_host": {
            "service": "EDRService", "method": "UnisolateHost",
            "description": "Remove network isolation",
            "params_schema": {
                "hostname": {"description": "Target hostname"},
            },
        },
        "collect_artifacts": {
            "service": "EDRService", "method": "CollectArtifacts",
            "description": "Collect forensic artifacts from endpoint",
            "params_schema": {
                "hostname": {"description": "Target hostname"},
                "artifact_types": {"description": "Comma-separated: memory, disk, registry, logs"},
            },
        },
        "kill_process": {
            "service": "EDRService", "method": "KillProcess",
            "description": "Kill a process on an endpoint",
            "params_schema": {
                "hostname": {"description": "Target hostname"},
                "pid": {"description": "Process ID"},
                "process_name": {"description": "Process name (alternative to PID)"},
            },
        },
        "get_host_info": {
            "service": "EDRService", "method": "GetHostInfo",
            "description": "Get endpoint details and status",
            "params_schema": {
                "hostname": {"description": "Target hostname"},
            },
        },
        "list_alerts": {
            "service": "EDRService", "method": "ListAlerts",
            "description": "List EDR alerts for a host",
            "params_schema": {
                "hostname": {"description": "Filter by hostname (optional)"},
                "severity": {"description": "Filter by severity"},
            },
        },
    },
    "akeso_av": {
        "scan_file": {
            "service": "AVService", "method": "ScanFile",
            "description": "Scan a file for malware",
            "params_schema": {
                "file_hash": {"description": "SHA256 hash of the file"},
                "file_path": {"description": "Path on endpoint (optional)"},
            },
        },
        "scan_host": {
            "service": "AVService", "method": "ScanHost",
            "description": "Initiate a full AV scan on a host",
            "params_schema": {
                "hostname": {"description": "Target hostname"},
                "scan_type": {"description": "quick | full"},
            },
        },
        "quarantine_file": {
            "service": "AVService", "method": "QuarantineFile",
            "description": "Quarantine a file",
            "params_schema": {
                "hostname": {"description": "Host where file resides"},
                "file_path": {"description": "File path to quarantine"},
            },
        },
        "get_scan_result": {
            "service": "AVService", "method": "GetScanResult",
            "description": "Get result of a previous scan",
            "params_schema": {
                "scan_id": {"description": "Scan job ID"},
            },
        },
    },
    "akeso_dlp": {
        "quarantine_file": {
            "service": "DLPService", "method": "QuarantineFile",
            "description": "DLP quarantine a file violating policy",
            "params_schema": {
                "file_path": {"description": "File path"},
                "policy_id": {"description": "Violated policy ID"},
            },
        },
        "update_policy": {
            "service": "DLPService", "method": "UpdatePolicy",
            "description": "Update a DLP policy",
            "params_schema": {
                "policy_id": {"description": "Policy ID"},
                "action": {"description": "block | alert | encrypt"},
            },
        },
        "get_incidents": {
            "service": "DLPService", "method": "GetIncidents",
            "description": "List DLP incidents",
            "params_schema": {
                "policy_id": {"description": "Filter by policy (optional)"},
                "time_range": {"description": "e.g. 1h, 24h, 7d"},
            },
        },
        "release_file": {
            "service": "DLPService", "method": "ReleaseFile",
            "description": "Release a quarantined file",
            "params_schema": {
                "file_id": {"description": "Quarantined file ID"},
                "reason": {"description": "Release justification"},
            },
        },
    },
    "akeso_ndr": {
        "query_flows": {
            "service": "NDRService", "method": "QueryFlows",
            "description": "Query network flow data",
            "params_schema": {
                "src_ip": {"description": "Source IP filter"},
                "dst_ip": {"description": "Destination IP filter"},
                "time_range": {"description": "e.g. 1h, 24h"},
            },
        },
        "get_connection_info": {
            "service": "NDRService", "method": "GetConnectionInfo",
            "description": "Get details about a specific connection",
            "params_schema": {
                "connection_id": {"description": "Connection/flow ID"},
            },
        },
        "export_pcap": {
            "service": "NDRService", "method": "ExportPcap",
            "description": "Export packet capture for a flow",
            "params_schema": {
                "connection_id": {"description": "Connection/flow ID"},
                "duration_seconds": {"description": "Capture duration"},
            },
        },
        "get_anomalies": {
            "service": "NDRService", "method": "GetAnomalies",
            "description": "List detected network anomalies",
            "params_schema": {
                "time_range": {"description": "e.g. 1h, 24h"},
                "severity": {"description": "Filter by severity"},
            },
        },
    },
    "akeso_fw": {
        "block_ip": {
            "method": "POST", "path": "/api/v1/rules/block",
            "description": "Block an IP address at the firewall",
            "params_schema": {
                "ip": {"description": "IP address to block"},
                "reason": {"description": "Block reason"},
                "duration": {"description": "Block duration (e.g. 1h, 24h, permanent)"},
            },
        },
        "unblock_ip": {
            "method": "DELETE", "path": "/api/v1/rules/block/{ip}",
            "description": "Remove an IP block rule",
            "params_schema": {
                "ip": {"description": "IP address to unblock"},
            },
        },
        "block_port": {
            "method": "POST", "path": "/api/v1/rules/block-port",
            "description": "Block a port",
            "params_schema": {
                "port": {"description": "Port number"},
                "protocol": {"description": "tcp | udp"},
                "direction": {"description": "inbound | outbound | both"},
            },
        },
        "add_rule": {
            "method": "POST", "path": "/api/v1/rules",
            "description": "Add a custom firewall rule",
            "params_schema": {
                "name": {"description": "Rule name"},
                "action": {"description": "allow | deny"},
                "src": {"description": "Source CIDR"},
                "dst": {"description": "Destination CIDR"},
                "port": {"description": "Port or port range"},
            },
        },
        "remove_rule": {
            "method": "DELETE", "path": "/api/v1/rules/{id}",
            "description": "Remove a firewall rule",
            "params_schema": {
                "rule_id": {"description": "Rule ID"},
            },
        },
        "get_rules": {
            "method": "GET", "path": "/api/v1/rules",
            "description": "List all firewall rules",
            "params_schema": {},
        },
    },
    "akeso_c2": {
        "list_implants": {
            "method": "GET", "path": "/api/v1/implants",
            "description": "List active C2 implants",
            "params_schema": {},
        },
        "task_implant": {
            "method": "POST", "path": "/api/v1/implants/{id}/tasks",
            "description": "Task an implant with a command",
            "params_schema": {
                "implant_id": {"description": "Implant UUID"},
                "command": {"description": "Command to execute"},
            },
        },
        "get_task_result": {
            "method": "GET", "path": "/api/v1/tasks/{id}",
            "description": "Get task execution result",
            "params_schema": {
                "task_id": {"description": "Task UUID"},
            },
        },
    },
    "generic_http": {
        "get": {
            "method": "GET",
            "description": "HTTP GET request",
            "params_schema": {
                "url": {"description": "Full URL to request"},
                "headers": {"description": "Custom headers (JSON)"},
            },
        },
        "post": {
            "method": "POST",
            "description": "HTTP POST request",
            "params_schema": {
                "url": {"description": "Full URL to request"},
                "body": {"description": "Request body (JSON)"},
                "headers": {"description": "Custom headers (JSON)"},
            },
        },
        "put": {
            "method": "PUT",
            "description": "HTTP PUT request",
            "params_schema": {
                "url": {"description": "Full URL to request"},
                "body": {"description": "Request body (JSON)"},
            },
        },
        "delete": {
            "method": "DELETE",
            "description": "HTTP DELETE request",
            "params_schema": {
                "url": {"description": "Full URL to request"},
            },
        },
    },
}


def upgrade() -> None:
    conn = op.get_bind()
    for connector_name, operations in OPERATIONS_UPDATE.items():
        conn.execute(
            sa.text("UPDATE connectors SET operations = :ops WHERE name = :name"),
            {"ops": json.dumps(operations), "name": connector_name},
        )


def downgrade() -> None:
    # Revert to original operations without params_schema
    pass
