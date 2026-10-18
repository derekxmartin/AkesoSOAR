"""AkesoDLP connector — gRPC client for Akeso's DLP product.

In mock mode (default for POC) no actual gRPC channel is opened; all
operations return realistic fake data.  The live path is stubbed out
and will be wired to compiled protobuf stubs in a future phase.
"""

from __future__ import annotations

import random
import uuid
from datetime import UTC, datetime

from akeso_soar.connectors.base import ActionResult, AkesoConnector, HealthStatus


class AkesoDLPConnector(AkesoConnector):
    """Connector for the AkesoDLP gRPC service.

    Supports file quarantine, policy management, incident retrieval,
    and file release operations.
    """

    _REQUIRED_PARAMS: dict[str, list[str]] = {
        "quarantine_file": ["file_path"],
        "update_policy": ["policy_id"],
        "get_incidents": [],
        "release_file": ["quarantine_id"],
    }

    @property
    def name(self) -> str:
        return "akeso_dlp"

    @property
    def display_name(self) -> str:
        return "Akeso DLP"

    @property
    def connector_type(self) -> str:
        return "grpc"

    @property
    def operations(self) -> list[str]:
        return list(self._REQUIRED_PARAMS.keys())

    # ------------------------------------------------------------------
    # Execute
    # ------------------------------------------------------------------

    async def execute(self, operation: str, params: dict) -> ActionResult:
        start = self._timed()

        err = self._validate_operation(operation)
        if err:
            err.duration_ms = self._elapsed_ms(start)
            return err

        err = self._validate_required_params(params, self._REQUIRED_PARAMS[operation], operation)
        if err:
            err.duration_ms = self._elapsed_ms(start)
            return err

        if self.mock:
            result = self._mock_execute(operation, params)
            result.duration_ms = self._elapsed_ms(start)
            return result

        return await self._live_execute(operation, params, start)

    # ------------------------------------------------------------------
    # Mock implementation
    # ------------------------------------------------------------------

    def _mock_execute(self, operation: str, params: dict) -> ActionResult:
        now = datetime.now(UTC).isoformat()

        if operation == "quarantine_file":
            return ActionResult(
                success=True,
                data={
                    "quarantine_id": f"DLP-Q-{uuid.uuid4().hex[:8].upper()}",
                    "file_path": params["file_path"],
                    "file_hash_sha256": uuid.uuid4().hex + uuid.uuid4().hex[:32],
                    "file_size_bytes": random.randint(1024, 52428800),
                    "original_owner": params.get("owner", "jdoe"),
                    "policy_violated": params.get("policy", "PII-External-Transfer"),
                    "status": "quarantined",
                    "quarantined_at": now,
                    "quarantine_path": f"/dlp/quarantine/{uuid.uuid4().hex[:12]}",
                },
            )

        if operation == "update_policy":
            policy_id = params["policy_id"]
            updates = {k: v for k, v in params.items() if k != "policy_id"}
            return ActionResult(
                success=True,
                data={
                    "policy_id": policy_id,
                    "policy_name": params.get("policy_name", "PII-External-Transfer"),
                    "updated_fields": list(updates.keys()),
                    "status": "active",
                    "updated_at": now,
                    "enforcement_mode": params.get("enforcement_mode", "block"),
                    "applied_to_endpoints": random.randint(50, 5000),
                },
            )

        if operation == "get_incidents":
            incidents = [
                {
                    "incident_id": f"DLP-INC-{uuid.uuid4().hex[:8].upper()}",
                    "policy_name": "PII-External-Transfer",
                    "file_path": "/home/jdoe/Documents/customer_export.xlsx",
                    "file_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "user": "jdoe",
                    "action_taken": "blocked",
                    "destination": "personal-email@gmail.com",
                    "data_types_detected": ["SSN", "credit_card"],
                    "severity": "critical",
                    "created_at": now,
                    "status": "open",
                },
                {
                    "incident_id": f"DLP-INC-{uuid.uuid4().hex[:8].upper()}",
                    "policy_name": "Source-Code-Protection",
                    "file_path": "/repos/internal-api/src/auth.py",
                    "file_type": "text/x-python",
                    "user": "dev-contractor",
                    "action_taken": "quarantined",
                    "destination": "usb-drive-E:",
                    "data_types_detected": ["source_code", "api_key"],
                    "severity": "high",
                    "created_at": now,
                    "status": "investigating",
                },
                {
                    "incident_id": f"DLP-INC-{uuid.uuid4().hex[:8].upper()}",
                    "policy_name": "HIPAA-PHI-Controls",
                    "file_path": "/shared/medical_records_q1.pdf",
                    "file_type": "application/pdf",
                    "user": "nurse.smith",
                    "action_taken": "alerted",
                    "destination": "cloud-sync",
                    "data_types_detected": ["PHI", "medical_record_number"],
                    "severity": "medium",
                    "created_at": now,
                    "status": "open",
                },
            ]
            return ActionResult(
                success=True,
                data={"total": len(incidents), "incidents": incidents},
            )

        if operation == "release_file":
            return ActionResult(
                success=True,
                data={
                    "quarantine_id": params["quarantine_id"],
                    "status": "released",
                    "released_at": now,
                    "released_by": params.get("released_by", "soar-automation"),
                    "reason": params.get("reason", "False positive — approved by analyst"),
                    "restored_path": params.get("restore_path", "/home/jdoe/Documents/customer_export.xlsx"),
                },
            )

        return ActionResult(success=False, error=f"Unhandled operation: {operation}")

    # ------------------------------------------------------------------
    # Live implementation (gRPC — stubbed for future use)
    # ------------------------------------------------------------------

    async def _live_execute(self, operation: str, params: dict, start: float) -> ActionResult:
        """Placeholder for real gRPC calls.  Requires compiled protobuf stubs."""
        return ActionResult(
            success=False,
            error="Live gRPC mode is not yet implemented. Use mock=True.",
            duration_ms=self._elapsed_ms(start),
        )

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    async def health_check(self) -> HealthStatus:
        if self.mock:
            return HealthStatus(healthy=True, message="Mock mode — always healthy", latency_ms=0.1)

        grpc_target = self.config.get("grpc_target", "dlp.akeso.local:443")
        timeout_seconds = self.config.get("connection_timeout", 5)
        start = self._timed()

        try:
            return HealthStatus(
                healthy=False,
                message=f"Live gRPC health check not implemented (target={grpc_target}, timeout={timeout_seconds}s)",
                latency_ms=self._elapsed_ms(start),
            )
        except Exception as exc:
            return HealthStatus(
                healthy=False,
                message=str(exc),
                latency_ms=self._elapsed_ms(start),
            )
