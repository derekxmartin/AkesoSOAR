"""Base connector framework for AkesoSOAR product integrations."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ActionResult:
    """Result from executing a connector operation."""

    success: bool
    data: dict = field(default_factory=dict)
    error: str | None = None
    duration_ms: float = 0.0


@dataclass
class HealthStatus:
    """Health check result for a connector."""

    healthy: bool
    message: str
    latency_ms: float = 0.0


class AkesoConnector(ABC):
    """Abstract base class for all AkesoSOAR connectors.

    Each connector wraps a single product integration (SIEM, EDR, etc.)
    and exposes a uniform interface for executing operations.

    Set ``mock=True`` (the default for POC) to use built-in fake
    responses instead of making real API calls.
    """

    def __init__(self, *, mock: bool = True, config: dict | None = None) -> None:
        self.mock = mock
        self.config = config or {}

    # ------------------------------------------------------------------
    # Abstract properties & methods — subclasses MUST implement
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique machine-readable name, e.g. ``akeso_siem``."""

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable label shown in the UI."""

    @property
    @abstractmethod
    def connector_type(self) -> str:
        """Transport type — ``rest`` or ``grpc``."""

    @property
    @abstractmethod
    def operations(self) -> list[str]:
        """List of supported operation names."""

    @abstractmethod
    async def execute(self, operation: str, params: dict) -> ActionResult:
        """Run *operation* with the given *params* and return an ``ActionResult``."""

    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """Return the current health of the connector."""

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def _validate_operation(self, operation: str) -> ActionResult | None:
        """Return an error ``ActionResult`` if *operation* is unknown, else ``None``."""
        if operation not in self.operations:
            return ActionResult(
                success=False,
                error=f"Unknown operation '{operation}'. Supported: {', '.join(self.operations)}",
            )
        return None

    @staticmethod
    def _timed() -> float:
        """Return a high-resolution timestamp (use pairs for duration)."""
        return time.perf_counter()

    @staticmethod
    def _elapsed_ms(start: float) -> float:
        return round((time.perf_counter() - start) * 1000, 2)

    def _validate_required_params(
        self, params: dict, required: list[str], operation: str
    ) -> ActionResult | None:
        """Return an error ``ActionResult`` if any required key is missing."""
        missing = [k for k in required if k not in params]
        if missing:
            return ActionResult(
                success=False,
                error=f"Operation '{operation}' requires params: {', '.join(missing)}",
            )
        return None
