"""AkesoNDR connector — gRPC client for Akeso's NDR product.

In mock mode (default for POC) no actual gRPC channel is opened; all
operations return realistic fake data.  The live path is stubbed out
and will be wired to compiled protobuf stubs in a future phase.
"""

from __future__ import annotations

import random
import uuid
from datetime import UTC, datetime

from akeso_soar.connectors.base import ActionResult, AkesoConnector, HealthStatus


class AkesoNDRConnector(AkesoConnector):
    """Connector for the AkesoNDR gRPC service.

    Supports network flow queries, connection info lookup, PCAP export,
    and anomaly detection retrieval.
    """

    _REQUIRED_PARAMS: dict[str, list[str]] = {
        "query_flows": [],
        "get_connection_info": ["connection_id"],
        "export_pcap": ["filter"],
        "get_anomalies": [],
    }

    @property
    def name(self) -> str:
        return "akeso_ndr"

    @property
    def display_name(self) -> str:
        return "Akeso NDR"

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

        if operation == "query_flows":
            flows = [
                {
                    "flow_id": str(uuid.uuid4()),
                    "src_ip": "10.1.42.107",
                    "src_port": random.randint(49152, 65535),
                    "dst_ip": "198.51.100.23",
                    "dst_port": 443,
                    "protocol": "tcp",
                    "bytes_sent": random.randint(500, 500000),
                    "bytes_received": random.randint(1000, 2000000),
                    "packets": random.randint(10, 5000),
                    "duration_seconds": round(random.uniform(0.5, 300.0), 2),
                    "application": "HTTPS",
                    "first_seen": now,
                    "last_seen": now,
                    "risk_score": round(random.uniform(0.0, 1.0), 2),
                },
                {
                    "flow_id": str(uuid.uuid4()),
                    "src_ip": "10.2.10.55",
                    "src_port": random.randint(49152, 65535),
                    "dst_ip": "203.0.113.42",
                    "dst_port": 8080,
                    "protocol": "tcp",
                    "bytes_sent": random.randint(100000, 5000000),
                    "bytes_received": random.randint(500, 5000),
                    "packets": random.randint(100, 10000),
                    "duration_seconds": round(random.uniform(10.0, 600.0), 2),
                    "application": "HTTP",
                    "first_seen": now,
                    "last_seen": now,
                    "risk_score": round(random.uniform(0.5, 1.0), 2),
                },
                {
                    "flow_id": str(uuid.uuid4()),
                    "src_ip": "10.1.42.107",
                    "src_port": random.randint(49152, 65535),
                    "dst_ip": "192.0.2.100",
                    "dst_port": 53,
                    "protocol": "udp",
                    "bytes_sent": random.randint(50, 500),
                    "bytes_received": random.randint(50, 2000),
                    "packets": random.randint(1, 50),
                    "duration_seconds": round(random.uniform(0.01, 2.0), 3),
                    "application": "DNS",
                    "first_seen": now,
                    "last_seen": now,
                    "risk_score": round(random.uniform(0.0, 0.3), 2),
                },
            ]
            return ActionResult(
                success=True,
                data={"total": len(flows), "flows": flows},
            )

        if operation == "get_connection_info":
            return ActionResult(
                success=True,
                data={
                    "connection_id": params["connection_id"],
                    "src_ip": "10.1.42.107",
                    "src_port": 52341,
                    "src_hostname": "ws-a1b2c3d4",
                    "dst_ip": "198.51.100.23",
                    "dst_port": 443,
                    "dst_hostname": "cdn.example.com",
                    "protocol": "tcp",
                    "tls_version": "TLS 1.3",
                    "tls_cipher": "TLS_AES_256_GCM_SHA384",
                    "server_certificate_cn": "*.example.com",
                    "ja3_hash": "e7d705a3286e19ea42f587b344ee6865",
                    "ja3s_hash": "eb1d94daa7e0344597e756a1fb6e7054",
                    "bytes_sent": random.randint(500, 500000),
                    "bytes_received": random.randint(1000, 2000000),
                    "packets": random.randint(10, 5000),
                    "duration_seconds": round(random.uniform(0.5, 300.0), 2),
                    "first_seen": now,
                    "last_seen": now,
                    "geo": {
                        "country": "US",
                        "city": "San Jose",
                        "asn": 13335,
                        "org": "Cloudflare Inc.",
                    },
                },
            )

        if operation == "export_pcap":
            pcap_id = uuid.uuid4().hex[:12]
            return ActionResult(
                success=True,
                data={
                    "pcap_id": pcap_id,
                    "filter": params["filter"],
                    "status": "generating",
                    "estimated_size_mb": round(random.uniform(1.0, 500.0), 1),
                    "packet_count": random.randint(100, 1000000),
                    "time_range_start": params.get("time_start", "2026-03-29T00:00:00+00:00"),
                    "time_range_end": params.get("time_end", now),
                    "file_path": f"/pcap/exports/{pcap_id}.pcap.gz",
                    "requested_at": now,
                },
            )

        if operation == "get_anomalies":
            anomalies = [
                {
                    "anomaly_id": str(uuid.uuid4()),
                    "type": "data_exfiltration",
                    "description": "Unusually large outbound transfer to external IP",
                    "src_ip": "10.2.10.55",
                    "dst_ip": "203.0.113.42",
                    "anomaly_score": round(random.uniform(0.85, 0.99), 2),
                    "baseline_bytes": 50000,
                    "observed_bytes": random.randint(5000000, 50000000),
                    "deviation_factor": round(random.uniform(10.0, 100.0), 1),
                    "detected_at": now,
                    "status": "new",
                },
                {
                    "anomaly_id": str(uuid.uuid4()),
                    "type": "beaconing",
                    "description": "Periodic callback pattern detected (60s intervals)",
                    "src_ip": "10.1.42.107",
                    "dst_ip": "198.51.100.23",
                    "anomaly_score": round(random.uniform(0.70, 0.95), 2),
                    "interval_seconds": 60,
                    "beacon_count": random.randint(50, 500),
                    "jitter_percent": round(random.uniform(0.5, 5.0), 1),
                    "detected_at": now,
                    "status": "investigating",
                },
                {
                    "anomaly_id": str(uuid.uuid4()),
                    "type": "dns_tunneling",
                    "description": "High entropy DNS queries to suspicious domain",
                    "src_ip": "10.3.5.22",
                    "dst_ip": "192.0.2.100",
                    "anomaly_score": round(random.uniform(0.60, 0.85), 2),
                    "suspicious_domain": "x7k2m.data.example.xyz",
                    "query_count": random.randint(200, 5000),
                    "avg_query_entropy": round(random.uniform(3.5, 4.5), 2),
                    "detected_at": now,
                    "status": "new",
                },
            ]
            return ActionResult(
                success=True,
                data={"total": len(anomalies), "anomalies": anomalies},
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

        grpc_target = self.config.get("grpc_target", "ndr.akeso.local:443")
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
