"""AkesoSIEM connector — REST client for Akeso's SIEM product."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import httpx

from akeso_soar.connectors.base import ActionResult, AkesoConnector, HealthStatus


class AkesoSIEMConnector(AkesoConnector):
    """Connector for the AkesoSIEM REST API.

    Supports case management, alert search, and tagging operations.
    In mock mode every operation returns realistic fake data.
    """

    # Required params per operation
    _REQUIRED_PARAMS: dict[str, list[str]] = {
        "create_case": ["title", "severity"],
        "update_case": ["case_id"],
        "add_case_note": ["case_id", "note"],
        "search_alerts": [],
        "get_alert": ["alert_id"],
        "create_alert_tag": ["alert_id", "tag"],
    }

    @property
    def name(self) -> str:
        return "akeso_siem"

    @property
    def display_name(self) -> str:
        return "Akeso SIEM"

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

        # Validate operation name
        err = self._validate_operation(operation)
        if err:
            err.duration_ms = self._elapsed_ms(start)
            return err

        # Validate required params
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
        case_id = params.get("case_id", str(uuid.uuid4()))
        alert_id = params.get("alert_id", str(uuid.uuid4()))

        if operation == "create_case":
            return ActionResult(
                success=True,
                data={
                    "case_id": str(uuid.uuid4()),
                    "title": params["title"],
                    "severity": params["severity"],
                    "status": "open",
                    "created_at": now,
                    "assignee": None,
                    "alert_count": 0,
                },
            )

        if operation == "update_case":
            updates = {k: v for k, v in params.items() if k != "case_id"}
            return ActionResult(
                success=True,
                data={
                    "case_id": case_id,
                    "updated_fields": list(updates.keys()),
                    "updated_at": now,
                },
            )

        if operation == "add_case_note":
            return ActionResult(
                success=True,
                data={
                    "note_id": str(uuid.uuid4()),
                    "case_id": case_id,
                    "note": params["note"],
                    "author": "soar-automation",
                    "created_at": now,
                },
            )

        if operation == "search_alerts":
            return ActionResult(
                success=True,
                data={
                    "total": 3,
                    "alerts": [
                        {
                            "alert_id": str(uuid.uuid4()),
                            "title": "Suspicious login from new geography",
                            "severity": "high",
                            "source": "auth-logs",
                            "created_at": now,
                            "status": "open",
                        },
                        {
                            "alert_id": str(uuid.uuid4()),
                            "title": "Multiple failed SSH attempts",
                            "severity": "medium",
                            "source": "network-ids",
                            "created_at": now,
                            "status": "open",
                        },
                        {
                            "alert_id": str(uuid.uuid4()),
                            "title": "Anomalous outbound data transfer",
                            "severity": "critical",
                            "source": "dlp",
                            "created_at": now,
                            "status": "investigating",
                        },
                    ],
                },
            )

        if operation == "get_alert":
            return ActionResult(
                success=True,
                data={
                    "alert_id": alert_id,
                    "title": "Suspicious login from new geography",
                    "severity": "high",
                    "source": "auth-logs",
                    "created_at": now,
                    "status": "open",
                    "raw_event": {
                        "user": "jdoe",
                        "src_ip": "203.0.113.42",
                        "country": "RU",
                        "timestamp": now,
                    },
                    "tags": ["geo-anomaly", "auth"],
                },
            )

        if operation == "create_alert_tag":
            return ActionResult(
                success=True,
                data={
                    "alert_id": alert_id,
                    "tag": params["tag"],
                    "created_at": now,
                },
            )

        return ActionResult(success=False, error=f"Unhandled operation: {operation}")

    # ------------------------------------------------------------------
    # Live implementation (uses httpx)
    # ------------------------------------------------------------------

    async def _live_execute(self, operation: str, params: dict, start: float) -> ActionResult:
        base_url = self.config.get("base_url", "https://siem.akeso.local/api/v1")
        api_key = self.config.get("api_key", "")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(base_url=base_url, headers=headers, timeout=30.0) as client:
                if operation == "create_case":
                    resp = await client.post("/cases", json=params)
                elif operation == "update_case":
                    cid = params.pop("case_id")
                    resp = await client.patch(f"/cases/{cid}", json=params)
                elif operation == "add_case_note":
                    cid = params.pop("case_id")
                    resp = await client.post(f"/cases/{cid}/notes", json={"note": params["note"]})
                elif operation == "search_alerts":
                    resp = await client.get("/alerts", params=params)
                elif operation == "get_alert":
                    resp = await client.get(f"/alerts/{params['alert_id']}")
                elif operation == "create_alert_tag":
                    aid = params["alert_id"]
                    resp = await client.post(f"/alerts/{aid}/tags", json={"tag": params["tag"]})
                else:
                    return ActionResult(success=False, error=f"Unhandled operation: {operation}", duration_ms=self._elapsed_ms(start))

                resp.raise_for_status()
                return ActionResult(success=True, data=resp.json(), duration_ms=self._elapsed_ms(start))

        except httpx.HTTPStatusError as exc:
            return ActionResult(success=False, error=f"HTTP {exc.response.status_code}: {exc.response.text}", duration_ms=self._elapsed_ms(start))
        except httpx.RequestError as exc:
            return ActionResult(success=False, error=f"Request failed: {exc}", duration_ms=self._elapsed_ms(start))

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    async def health_check(self) -> HealthStatus:
        if self.mock:
            return HealthStatus(healthy=True, message="Mock mode — always healthy", latency_ms=0.1)

        base_url = self.config.get("base_url", "https://siem.akeso.local/api/v1")
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
