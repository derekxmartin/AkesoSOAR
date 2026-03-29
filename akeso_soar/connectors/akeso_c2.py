"""AkesoC2 connector — REST client for Akeso's C2 simulation/tracking product.

In mock mode (default for POC) every operation returns realistic fake
data.  The live path uses httpx for actual API calls.
"""

from __future__ import annotations

import random
import uuid
from datetime import UTC, datetime, timedelta

import httpx

from akeso_soar.connectors.base import ActionResult, AkesoConnector, HealthStatus


class AkesoC2Connector(AkesoConnector):
    """Connector for the AkesoC2 REST API.

    Supports implant management, tasking, and result retrieval for
    adversary-simulation and C2-tracking operations.
    """

    _REQUIRED_PARAMS: dict[str, list[str]] = {
        "list_implants": [],
        "task_implant": ["implant_id", "command"],
        "get_task_result": ["task_id"],
    }

    @property
    def name(self) -> str:
        return "akeso_c2"

    @property
    def display_name(self) -> str:
        return "Akeso C2"

    @property
    def connector_type(self) -> str:
        return "rest"

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
        now = datetime.now(UTC)
        now_iso = now.isoformat()

        if operation == "list_implants":
            implants = [
                {
                    "implant_id": f"IMP-{uuid.uuid4().hex[:8].upper()}",
                    "hostname": "ws-a1b2c3d4",
                    "internal_ip": "10.1.42.107",
                    "external_ip": "203.0.113.10",
                    "os": "Windows 11 Enterprise 10.0.22631",
                    "arch": "x86_64",
                    "process_name": "svchost.exe",
                    "pid": random.randint(1000, 9999),
                    "user": "CORP\\jdoe",
                    "integrity_level": "medium",
                    "last_callback": now_iso,
                    "callback_interval_seconds": 60,
                    "jitter_percent": 10,
                    "status": "active",
                    "first_seen": (now - timedelta(hours=random.randint(1, 72))).isoformat(),
                },
                {
                    "implant_id": f"IMP-{uuid.uuid4().hex[:8].upper()}",
                    "hostname": "srv-db-prod-01",
                    "internal_ip": "10.3.5.22",
                    "external_ip": "203.0.113.10",
                    "os": "Ubuntu 22.04.3 LTS",
                    "arch": "x86_64",
                    "process_name": "python3",
                    "pid": random.randint(1000, 9999),
                    "user": "www-data",
                    "integrity_level": "low",
                    "last_callback": (now - timedelta(minutes=random.randint(1, 30))).isoformat(),
                    "callback_interval_seconds": 300,
                    "jitter_percent": 20,
                    "status": "active",
                    "first_seen": (now - timedelta(hours=random.randint(12, 168))).isoformat(),
                },
                {
                    "implant_id": f"IMP-{uuid.uuid4().hex[:8].upper()}",
                    "hostname": "ws-e5f6g7h8",
                    "internal_ip": "10.1.42.205",
                    "external_ip": "203.0.113.10",
                    "os": "macOS 14.3 Sonoma",
                    "arch": "arm64",
                    "process_name": "com.apple.Safari",
                    "pid": random.randint(100, 9999),
                    "user": "admin",
                    "integrity_level": "high",
                    "last_callback": (now - timedelta(hours=random.randint(2, 48))).isoformat(),
                    "callback_interval_seconds": 120,
                    "jitter_percent": 15,
                    "status": "dormant",
                    "first_seen": (now - timedelta(days=random.randint(1, 14))).isoformat(),
                },
            ]
            return ActionResult(
                success=True,
                data={"total": len(implants), "implants": implants},
            )

        if operation == "task_implant":
            return ActionResult(
                success=True,
                data={
                    "task_id": f"TASK-{uuid.uuid4().hex[:8].upper()}",
                    "implant_id": params["implant_id"],
                    "command": params["command"],
                    "args": params.get("args", []),
                    "status": "queued",
                    "queued_at": now_iso,
                    "estimated_callback": (now + timedelta(seconds=random.randint(30, 300))).isoformat(),
                },
            )

        if operation == "get_task_result":
            status = random.choice(["completed", "completed", "completed", "pending", "failed"])
            result_data: dict = {
                "task_id": params["task_id"],
                "status": status,
                "queued_at": (now - timedelta(minutes=random.randint(5, 60))).isoformat(),
            }
            if status == "completed":
                result_data.update(
                    {
                        "completed_at": now_iso,
                        "output": "uid=1000(www-data) gid=1000(www-data) groups=1000(www-data),33(www-data)",
                        "exit_code": 0,
                    }
                )
            elif status == "failed":
                result_data.update(
                    {
                        "completed_at": now_iso,
                        "error": "Implant lost connectivity during execution",
                        "exit_code": -1,
                    }
                )
            else:
                result_data["estimated_callback"] = (
                    now + timedelta(seconds=random.randint(10, 120))
                ).isoformat()

            return ActionResult(success=True, data=result_data)

        return ActionResult(success=False, error=f"Unhandled operation: {operation}")

    # ------------------------------------------------------------------
    # Live implementation (uses httpx)
    # ------------------------------------------------------------------

    async def _live_execute(self, operation: str, params: dict, start: float) -> ActionResult:
        base_url = self.config.get("base_url", "https://c2.akeso.local/api/v1")
        api_key = self.config.get("api_key", "")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(base_url=base_url, headers=headers, timeout=30.0) as client:
                if operation == "list_implants":
                    resp = await client.get("/implants", params=params)
                elif operation == "task_implant":
                    implant_id = params["implant_id"]
                    resp = await client.post(f"/implants/{implant_id}/tasks", json=params)
                elif operation == "get_task_result":
                    resp = await client.get(f"/tasks/{params['task_id']}")
                else:
                    return ActionResult(
                        success=False,
                        error=f"Unhandled operation: {operation}",
                        duration_ms=self._elapsed_ms(start),
                    )

                resp.raise_for_status()
                return ActionResult(success=True, data=resp.json(), duration_ms=self._elapsed_ms(start))

        except httpx.HTTPStatusError as exc:
            return ActionResult(
                success=False,
                error=f"HTTP {exc.response.status_code}: {exc.response.text}",
                duration_ms=self._elapsed_ms(start),
            )
        except httpx.RequestError as exc:
            return ActionResult(success=False, error=f"Request failed: {exc}", duration_ms=self._elapsed_ms(start))

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    async def health_check(self) -> HealthStatus:
        if self.mock:
            return HealthStatus(healthy=True, message="Mock mode — always healthy", latency_ms=0.1)

        base_url = self.config.get("base_url", "https://c2.akeso.local/api/v1")
        api_key = self.config.get("api_key", "")
        start = self._timed()

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{base_url}/health",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                resp.raise_for_status()
                return HealthStatus(
                    healthy=True,
                    message="Connected",
                    latency_ms=self._elapsed_ms(start),
                )
        except Exception as exc:
            return HealthStatus(
                healthy=False,
                message=str(exc),
                latency_ms=self._elapsed_ms(start),
            )
