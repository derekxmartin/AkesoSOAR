"""Background alert polling service — polls AkesoSIEM for new alerts at a configurable interval."""

from __future__ import annotations

import asyncio
import logging

from akeso_soar.db import async_session_factory
from akeso_soar.services.alert_ingestion import ingest_alert

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mock SIEM alert source (replaced by real SIEM connector in Phase 7)
# ---------------------------------------------------------------------------

_mock_alerts: list[dict] = []
_poll_interval: int = 30  # seconds


def set_poll_interval(seconds: int) -> None:
    global _poll_interval
    _poll_interval = seconds


def push_mock_alert(alert: dict) -> None:
    """Add an alert to the mock queue (simulates SIEM producing alerts)."""
    _mock_alerts.append(alert)


async def _fetch_alerts_from_siem() -> list[dict]:
    """Fetch new alerts from AkesoSIEM.

    In PoC mode, drains the mock queue.
    In production, this would call the SIEM connector's search_alerts operation.
    """
    alerts = list(_mock_alerts)
    _mock_alerts.clear()
    return alerts


# ---------------------------------------------------------------------------
# Poller loop
# ---------------------------------------------------------------------------

_running = False
_task: asyncio.Task | None = None


async def _poll_loop() -> None:
    """Background loop that polls for alerts and ingests them."""
    global _running
    _running = True
    logger.info("Alert poller started (interval=%ds)", _poll_interval)

    while _running:
        try:
            alerts = await _fetch_alerts_from_siem()
            if alerts:
                async with async_session_factory() as db:
                    for payload in alerts:
                        try:
                            await ingest_alert(db, payload)
                        except Exception:
                            logger.exception("Failed to ingest polled alert: %s", payload.get("external_id", "?"))
                    await db.commit()
                logger.info("Polled and ingested %d alert(s)", len(alerts))
        except Exception:
            logger.exception("Alert poller error")

        await asyncio.sleep(_poll_interval)


def start_poller() -> asyncio.Task:
    """Start the alert poller as a background asyncio task."""
    global _task
    if _task is not None and not _task.done():
        return _task
    _task = asyncio.create_task(_poll_loop())
    return _task


def stop_poller() -> None:
    """Stop the alert poller."""
    global _running, _task
    _running = False
    if _task is not None:
        _task.cancel()
        _task = None
