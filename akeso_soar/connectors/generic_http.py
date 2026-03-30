"""Generic HTTP connector — configurable REST client for third-party APIs.

Supports arbitrary HTTP requests as well as pre-built threat-intel
lookup operations (IP, hash, domain).  In mock mode, returns realistic
VirusTotal-style threat intelligence data.
"""

from __future__ import annotations

import random
import uuid
from datetime import UTC, datetime

import httpx

from akeso_soar.connectors.base import ActionResult, AkesoConnector, HealthStatus


class GenericHTTPConnector(AkesoConnector):
    """Configurable REST client for arbitrary third-party integrations.

    Supports a generic ``http_request`` operation as well as
    purpose-built threat-intel lookups (IP, hash, domain) that return
    VirusTotal-style enrichment data in mock mode.

    Config keys
    -----------
    base_url : str
        Default base URL for all requests.
    auth_header : str
        Header name for authentication (default: ``x-apikey``).
    auth_value : str
        Authentication token/key value.
    default_headers : dict
        Additional headers to include on every request.
    """

    _REQUIRED_PARAMS: dict[str, list[str]] = {
        "http_request": ["method", "url"],
        "lookup_ip": ["ip"],
        "lookup_hash": ["hash"],
        "lookup_domain": ["domain"],
    }

    @property
    def name(self) -> str:
        return "generic_http"

    @property
    def display_name(self) -> str:
        return "Generic HTTP"

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
        now = datetime.now(UTC).isoformat()

        if operation == "http_request":
            return ActionResult(
                success=True,
                data={
                    "status_code": 200,
                    "headers": {
                        "content-type": "application/json",
                        "x-request-id": str(uuid.uuid4()),
                    },
                    "body": {"message": "Mock response", "timestamp": now},
                    "elapsed_ms": round(random.uniform(50, 500), 1),
                },
            )

        if operation == "lookup_ip":
            ip = params["ip"]
            malicious = random.randint(0, 25)
            suspicious = random.randint(0, 10)
            harmless = random.randint(50, 70)
            undetected = 90 - malicious - suspicious - harmless
            return ActionResult(
                success=True,
                data={
                    "ip": ip,
                    "risk_score": round(random.uniform(0.0, 100.0), 1),
                    "reputation": random.choice(["malicious", "suspicious", "clean", "clean"]),
                    "analysis_stats": {
                        "malicious": malicious,
                        "suspicious": suspicious,
                        "harmless": max(0, harmless),
                        "undetected": max(0, undetected),
                    },
                    "geo": {
                        "country": random.choice(["US", "CN", "RU", "DE", "BR", "IN"]),
                        "city": random.choice(["Beijing", "Moscow", "San Jose", "Berlin", "Sao Paulo"]),
                        "latitude": round(random.uniform(-90, 90), 4),
                        "longitude": round(random.uniform(-180, 180), 4),
                    },
                    "asn": {
                        "number": random.randint(1000, 60000),
                        "org": random.choice([
                            "Cloudflare Inc.",
                            "Amazon.com Inc.",
                            "DigitalOcean LLC",
                            "Hetzner Online GmbH",
                            "OVH SAS",
                        ]),
                    },
                    "whois": {
                        "network": f"{ip.rsplit('.', 1)[0]}.0/24" if "." in ip else f"{ip}/48",
                        "registrar": "ARIN",
                        "last_updated": "2025-11-15",
                    },
                    "last_analysis_date": now,
                    "tags": random.sample(
                        ["proxy", "vpn", "tor-exit", "scanner", "botnet", "spam", "c2"],
                        k=random.randint(0, 3),
                    ),
                },
            )

        if operation == "lookup_hash":
            file_hash = params["hash"]
            malicious = random.randint(0, 40)
            suspicious = random.randint(0, 5)
            harmless = random.randint(30, 50)
            undetected = 72 - malicious - suspicious - harmless
            return ActionResult(
                success=True,
                data={
                    "hash": file_hash,
                    "hash_type": "sha256" if len(file_hash) == 64 else "md5" if len(file_hash) == 32 else "sha1",
                    "risk_score": round(random.uniform(0.0, 100.0), 1),
                    "verdict": random.choice(["malicious", "malicious", "suspicious", "clean"]),
                    "analysis_stats": {
                        "malicious": malicious,
                        "suspicious": suspicious,
                        "harmless": max(0, harmless),
                        "undetected": max(0, undetected),
                    },
                    "file_info": {
                        "file_name": random.choice([
                            "invoice_2026.pdf.exe",
                            "update.dll",
                            "readme.txt",
                            "payload.bin",
                        ]),
                        "file_type": random.choice(["PE32 executable", "PDF document", "DLL", "ELF"]),
                        "file_size_bytes": random.randint(1024, 10485760),
                        "magic": "PE32 executable (GUI) Intel 80386 Mono/.Net assembly",
                    },
                    "signature_info": {
                        "signed": random.choice([True, False]),
                        "signer": random.choice(["Unknown", "Microsoft Corporation", "Self-signed"]),
                        "verified": random.choice([True, False, False]),
                    },
                    "sandbox_verdicts": {
                        "CrowdStrike Falcon": random.choice(["malicious", "suspicious", "clean"]),
                        "VMRay": random.choice(["malicious", "suspicious", "clean"]),
                        "Joe Sandbox": random.choice(["malicious", "suspicious", "clean"]),
                    },
                    "first_seen": "2026-01-15T08:30:00+00:00",
                    "last_analysis_date": now,
                    "tags": random.sample(
                        ["trojan", "ransomware", "dropper", "packed", "adware", "miner", "rat"],
                        k=random.randint(0, 3),
                    ),
                },
            )

        if operation == "lookup_domain":
            domain = params["domain"]
            malicious = random.randint(0, 15)
            suspicious = random.randint(0, 8)
            harmless = random.randint(55, 75)
            undetected = 90 - malicious - suspicious - harmless
            return ActionResult(
                success=True,
                data={
                    "domain": domain,
                    "risk_score": round(random.uniform(0.0, 100.0), 1),
                    "reputation": random.choice(["malicious", "suspicious", "clean", "clean", "clean"]),
                    "analysis_stats": {
                        "malicious": malicious,
                        "suspicious": suspicious,
                        "harmless": max(0, harmless),
                        "undetected": max(0, undetected),
                    },
                    "categories": random.sample(
                        ["phishing", "malware", "business", "technology", "education", "news"],
                        k=random.randint(1, 3),
                    ),
                    "dns_records": {
                        "A": [f"198.51.100.{random.randint(1, 254)}"],
                        "AAAA": [f"2001:db8::{random.randint(1, 9999):x}"],
                        "MX": [f"mail.{domain}"],
                        "NS": [f"ns1.{domain}", f"ns2.{domain}"],
                        "TXT": [f"v=spf1 include:_spf.{domain} ~all"],
                    },
                    "whois": {
                        "registrar": random.choice([
                            "GoDaddy", "Namecheap", "Cloudflare", "Google Domains"
                        ]),
                        "creation_date": "2020-03-15",
                        "expiration_date": "2027-03-15",
                        "registrant_country": random.choice(["US", "CN", "RU", "DE"]),
                    },
                    "ssl_certificate": {
                        "issuer": random.choice(["Let's Encrypt", "DigiCert", "Sectigo", "Self-signed"]),
                        "valid_from": "2026-01-01",
                        "valid_to": "2027-01-01",
                        "subject_cn": domain,
                    },
                    "last_analysis_date": now,
                    "subdomains_found": random.randint(0, 25),
                    "tags": random.sample(
                        ["dga", "fast-flux", "parked", "newly-registered", "phishing", "c2"],
                        k=random.randint(0, 2),
                    ),
                },
            )

        return ActionResult(success=False, error=f"Unhandled operation: {operation}")

    # ------------------------------------------------------------------
    # Live implementation (uses httpx)
    # ------------------------------------------------------------------

    async def _live_execute(self, operation: str, params: dict, start: float) -> ActionResult:
        base_url = self.config.get("base_url", "")
        auth_header = self.config.get("auth_header", "x-apikey")
        auth_value = self.config.get("auth_value", "")
        default_headers: dict = self.config.get("default_headers", {})

        headers = {**default_headers}
        if auth_value:
            headers[auth_header] = auth_value

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if operation == "http_request":
                    method = params["method"].upper()
                    url = params["url"]
                    if not url.startswith("http") and base_url:
                        url = f"{base_url.rstrip('/')}/{url.lstrip('/')}"
                    req_headers = {**headers, **params.get("headers", {})}
                    resp = await client.request(
                        method,
                        url,
                        headers=req_headers,
                        json=params.get("body"),
                        params=params.get("query_params"),
                    )
                    resp.raise_for_status()
                    try:
                        body = resp.json()
                    except Exception:
                        body = resp.text
                    return ActionResult(
                        success=True,
                        data={
                            "status_code": resp.status_code,
                            "headers": dict(resp.headers),
                            "body": body,
                        },
                        duration_ms=self._elapsed_ms(start),
                    )

                if operation == "lookup_ip":
                    url = f"{base_url.rstrip('/')}/ip-addresses/{params['ip']}"
                    resp = await client.get(url, headers=headers)
                    resp.raise_for_status()
                    return ActionResult(success=True, data=resp.json(), duration_ms=self._elapsed_ms(start))

                if operation == "lookup_hash":
                    url = f"{base_url.rstrip('/')}/files/{params['hash']}"
                    resp = await client.get(url, headers=headers)
                    resp.raise_for_status()
                    return ActionResult(success=True, data=resp.json(), duration_ms=self._elapsed_ms(start))

                if operation == "lookup_domain":
                    url = f"{base_url.rstrip('/')}/domains/{params['domain']}"
                    resp = await client.get(url, headers=headers)
                    resp.raise_for_status()
                    return ActionResult(success=True, data=resp.json(), duration_ms=self._elapsed_ms(start))

                return ActionResult(
                    success=False,
                    error=f"Unhandled operation: {operation}",
                    duration_ms=self._elapsed_ms(start),
                )

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

        base_url = self.config.get("base_url", "")
        if not base_url:
            return HealthStatus(healthy=False, message="No base_url configured", latency_ms=0.0)

        auth_header = self.config.get("auth_header", "x-apikey")
        auth_value = self.config.get("auth_value", "")
        health_endpoint = self.config.get("health_endpoint", "/health")
        start = self._timed()

        headers: dict = {}
        if auth_value:
            headers[auth_header] = auth_value

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{base_url.rstrip('/')}{health_endpoint}", headers=headers)
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
