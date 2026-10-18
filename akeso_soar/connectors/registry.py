"""Connector registry — auto-discovers and manages all AkesoConnector subclasses."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from akeso_soar.connectors.base import AkesoConnector, HealthStatus

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton registry
# ---------------------------------------------------------------------------


class ConnectorRegistry:
    """Central registry that discovers and holds connector instances.

    Usage::

        registry = ConnectorRegistry.instance()
        siem = registry.get_connector("akeso_siem")
    """

    _instance: ConnectorRegistry | None = None

    def __init__(self) -> None:
        self._connectors: dict[str, AkesoConnector] = {}

    @classmethod
    def instance(cls) -> ConnectorRegistry:
        """Return the singleton registry, creating it on first call."""
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._auto_discover()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Tear down the singleton (useful in tests)."""
        cls._instance = None

    # ------------------------------------------------------------------
    # Auto-discovery
    # ------------------------------------------------------------------

    def _auto_discover(self) -> None:
        """Import the connectors package so all subclasses register themselves."""
        # Importing the package triggers __init__.py which imports each
        # concrete connector module, causing their classes to exist.
        try:
            import akeso_soar.connectors  # noqa: F811
        except ImportError:
            logger.warning("Could not import akeso_soar.connectors for auto-discovery")
            return

        # Walk all subclasses of AkesoConnector
        for cls in AkesoConnector.__subclasses__():
            try:
                inst = cls()  # default: mock=True
                self.register(inst)
            except Exception:
                logger.exception("Failed to instantiate connector %s", cls.__name__)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(self, connector: AkesoConnector) -> None:
        """Register a connector instance (overwrites if name exists)."""
        self._connectors[connector.name] = connector
        logger.info("Registered connector: %s (%s)", connector.name, connector.display_name)

    def get_connector(self, name: str) -> AkesoConnector | None:
        """Return the connector with the given *name*, or ``None``."""
        return self._connectors.get(name)

    def list_connectors(self) -> list[AkesoConnector]:
        """Return all registered connectors sorted by name."""
        return sorted(self._connectors.values(), key=lambda c: c.name)

    async def get_all_health(self) -> dict[str, HealthStatus]:
        """Run health checks on every registered connector."""
        results: dict[str, HealthStatus] = {}
        for name, connector in self._connectors.items():
            try:
                results[name] = await connector.health_check()
            except Exception as exc:
                results[name] = HealthStatus(healthy=False, message=str(exc), latency_ms=0.0)
        return results
