"""AkesoFW connector — REST client for Akeso's Firewall product."""

from __future__ import annotations

import ipaddress
import random
import uuid
from datetime import UTC, datetime

import httpx

from akeso_soar.connectors.base import ActionResult, AkesoConnector, HealthStatus


class AkesoFWConnector(AkesoConnector):
    """Connector for the AkesoFW REST API.

    Supports firewall rule management including IP/port blocking and
    rule CRUD operations.  In mock mode every operation returns
    realistic fake data.
    """

    _REQUIRED_PARAMS: dict[str, list[str]] = {
        "block_ip": ["ip_address"],
        "unblock_ip": ["ip_address"],
        "block_port": ["port", "protocol"],
        "add_rule": ["rule_name", "action", "direction"],
        "remove_rule": ["rule_id"],
        "get_rules": [],
    }

    @property
    def name(self) -> str:
        return "akeso_fw"

    @property
    def display_name(self) -> str:
        return "Akeso Firewall"

    @property
    def connector_type(self) -> str:
        return "rest"

    @property
    def operations(self) -> list[str]:
        return list(self._REQUIRED_PARAMS.keys())

    # ------------------------------------------------------------------
    # IP validation helper
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_ip(ip_str: str) -> str | None:
        """Return an error message if *ip_str* is not a valid IPv4/IPv6 address."""
        try:
            ipaddress.ip_address(ip_str)
        except ValueError:
            return f"Invalid IP address: '{ip_str}'. Must be a valid IPv4 or IPv6 address."
        return None

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

        # Extra validation: IP format for block/unblock
        if operation in ("block_ip", "unblock_ip"):
            ip_err = self._validate_ip(params["ip_address"])
            if ip_err:
                return ActionResult(success=False, error=ip_err, duration_ms=self._elapsed_ms(start))

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

        if operation == "block_ip":
            return ActionResult(
                success=True,
                data={
                    "rule_id": f"FW-BLK-{uuid.uuid4().hex[:8].upper()}",
                    "ip_address": params["ip_address"],
                    "action": "block",
                    "direction": params.get("direction", "inbound"),
                    "status": "active",
                    "created_at": now,
                    "expires_at": params.get("expires_at"),
                    "zone": params.get("zone", "untrusted"),
                },
            )

        if operation == "unblock_ip":
            return ActionResult(
                success=True,
                data={
                    "ip_address": params["ip_address"],
                    "rules_removed": random.randint(1, 3),
                    "status": "unblocked",
                    "removed_at": now,
                },
            )

        if operation == "block_port":
            return ActionResult(
                success=True,
                data={
                    "rule_id": f"FW-PORT-{uuid.uuid4().hex[:8].upper()}",
                    "port": params["port"],
                    "protocol": params["protocol"],
                    "action": "block",
                    "direction": params.get("direction", "inbound"),
                    "status": "active",
                    "created_at": now,
                },
            )

        if operation == "add_rule":
            return ActionResult(
                success=True,
                data={
                    "rule_id": f"FW-RULE-{uuid.uuid4().hex[:8].upper()}",
                    "rule_name": params["rule_name"],
                    "action": params["action"],
                    "direction": params["direction"],
                    "source": params.get("source", "any"),
                    "destination": params.get("destination", "any"),
                    "port": params.get("port", "any"),
                    "protocol": params.get("protocol", "any"),
                    "priority": params.get("priority", random.randint(100, 999)),
                    "status": "active",
                    "created_at": now,
                },
            )

        if operation == "remove_rule":
            return ActionResult(
                success=True,
                data={
                    "rule_id": params["rule_id"],
                    "status": "removed",
                    "removed_at": now,
                },
            )

        if operation == "get_rules":
            rules = [
                {
                    "rule_id": "FW-RULE-A1B2C3D4",
                    "rule_name": "Block known C2 IPs",
                    "action": "block",
                    "direction": "outbound",
                    "source": "any",
                    "destination": "198.51.100.0/24",
                    "protocol": "tcp",
                    "port": "443",
                    "priority": 100,
                    "status": "active",
                    "created_at": "2026-03-01T08:00:00+00:00",
                    "hit_count": random.randint(50, 5000),
                },
                {
                    "rule_id": "FW-RULE-E5F6G7H8",
                    "rule_name": "Allow internal DNS",
                    "action": "allow",
                    "direction": "outbound",
                    "source": "10.0.0.0/8",
                    "destination": "10.1.1.53",
                    "protocol": "udp",
                    "port": "53",
                    "priority": 50,
                    "status": "active",
                    "created_at": "2026-01-15T12:30:00+00:00",
                    "hit_count": random.randint(10000, 500000),
                },
                {
                    "rule_id": "FW-BLK-I9J0K1L2",
                    "rule_name": "Block SSH from external",
                    "action": "block",
                    "direction": "inbound",
                    "source": "any",
                    "destination": "any",
                    "protocol": "tcp",
                    "port": "22",
                    "priority": 200,
                    "status": "active",
                    "created_at": "2026-02-20T16:45:00+00:00",
                    "hit_count": random.randint(100, 10000),
                },
            ]
            return ActionResult(
                success=True,
                data={"total": len(rules), "rules": rules},
            )

        return ActionResult(success=False, error=f"Unhandled operation: {operation}")

    # ------------------------------------------------------------------
    # Live implementation (uses httpx)
    # ------------------------------------------------------------------

    async def _live_execute(self, operation: str, params: dict, start: float) -> ActionResult:
        base_url = self.config.get("base_url", "https://fw.akeso.local/api/v1")
        api_key = self.config.get("api_key", "")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(base_url=base_url, headers=headers, timeout=30.0) as client:
                if operation == "block_ip":
                    resp = await client.post("/rules/block-ip", json=params)
                elif operation == "unblock_ip":
                    resp = await client.post("/rules/unblock-ip", json=params)
                elif operation == "block_port":
                    resp = await client.post("/rules/block-port", json=params)
                elif operation == "add_rule":
                    resp = await client.post("/rules", json=params)
                elif operation == "remove_rule":
                    resp = await client.delete(f"/rules/{params['rule_id']}")
                elif operation == "get_rules":
                    resp = await client.get("/rules", params=params)
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

        base_url = self.config.get("base_url", "https://fw.akeso.local/api/v1")
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
