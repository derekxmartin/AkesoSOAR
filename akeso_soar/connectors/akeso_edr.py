"""AkesoEDR connector — gRPC client for Akeso's EDR product.

In mock mode (default for POC) no actual gRPC channel is opened; all
operations return realistic fake data.  The live path is stubbed out
and will be wired to compiled protobuf stubs in a future phase.
"""

from __future__ import annotations

import random
import uuid
from datetime import UTC, datetime

from akeso_soar.connectors.base import ActionResult, AkesoConnector, HealthStatus


class AkesoEDRConnector(AkesoConnector):
    """Connector for the AkesoEDR gRPC service.

    Supports host isolation, artifact collection, process management,
    and alert listing.
    """

    _REQUIRED_PARAMS: dict[str, list[str]] = {
        "isolate_host": ["host_id"],
        "unisolate_host": ["host_id"],
        "collect_artifacts": ["host_id", "artifact_type"],
        "kill_process": ["host_id", "pid"],
        "get_host_info": ["host_id"],
        "list_alerts": [],
    }

    @property
    def name(self) -> str:
        return "akeso_edr"

    @property
    def display_name(self) -> str:
        return "Akeso EDR"

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
        host_id = params.get("host_id", str(uuid.uuid4()))

        if operation == "isolate_host":
            return ActionResult(
                success=True,
                data={
                    "host_id": host_id,
                    "hostname": f"ws-{host_id[:8]}",
                    "isolation_status": "isolated",
                    "isolated_at": now,
                    "network_acls_applied": True,
                },
            )

        if operation == "unisolate_host":
            return ActionResult(
                success=True,
                data={
                    "host_id": host_id,
                    "hostname": f"ws-{host_id[:8]}",
                    "isolation_status": "connected",
                    "unisolated_at": now,
                    "network_acls_removed": True,
                },
            )

        if operation == "collect_artifacts":
            artifact_type = params["artifact_type"]
            return ActionResult(
                success=True,
                data={
                    "collection_id": str(uuid.uuid4()),
                    "host_id": host_id,
                    "artifact_type": artifact_type,
                    "status": "collecting",
                    "started_at": now,
                    "estimated_size_mb": round(random.uniform(5.0, 250.0), 1),
                    "artifacts": [
                        f"/evidence/{host_id}/{artifact_type}/mem_dump.raw",
                        f"/evidence/{host_id}/{artifact_type}/registry_hive.dat",
                        f"/evidence/{host_id}/{artifact_type}/prefetch.zip",
                    ],
                },
            )

        if operation == "kill_process":
            pid = params["pid"]
            return ActionResult(
                success=True,
                data={
                    "host_id": host_id,
                    "pid": pid,
                    "process_name": "suspicious.exe",
                    "killed": True,
                    "killed_at": now,
                    "parent_pid": random.randint(100, 9999),
                },
            )

        if operation == "get_host_info":
            return ActionResult(
                success=True,
                data={
                    "host_id": host_id,
                    "hostname": f"ws-{host_id[:8]}",
                    "os": "Windows 11 Enterprise",
                    "os_version": "10.0.22631",
                    "agent_version": "3.14.2",
                    "last_seen": now,
                    "ip_addresses": ["10.1.42.107", "fe80::1"],
                    "isolation_status": "connected",
                    "policy_name": "SOC-Standard",
                    "tags": ["finance-dept", "vip-asset"],
                },
            )

        if operation == "list_alerts":
            return ActionResult(
                success=True,
                data={
                    "total": 2,
                    "alerts": [
                        {
                            "alert_id": str(uuid.uuid4()),
                            "host_id": str(uuid.uuid4()),
                            "hostname": "ws-a1b2c3d4",
                            "title": "Cobalt Strike beacon detected",
                            "severity": "critical",
                            "technique": "T1071.001",
                            "created_at": now,
                            "status": "new",
                        },
                        {
                            "alert_id": str(uuid.uuid4()),
                            "host_id": str(uuid.uuid4()),
                            "hostname": "srv-db-prod-01",
                            "title": "Credential dumping via LSASS",
                            "severity": "high",
                            "technique": "T1003.001",
                            "created_at": now,
                            "status": "investigating",
                        },
                    ],
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

        # In live mode we would open a gRPC channel and call a health RPC.
        grpc_target = self.config.get("grpc_target", "edr.akeso.local:443")
        timeout_seconds = self.config.get("connection_timeout", 5)
        start = self._timed()

        try:
            # Future: grpc.aio.insecure_channel / grpc.aio.secure_channel
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
