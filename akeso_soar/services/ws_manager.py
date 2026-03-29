"""WebSocket connection manager — rooms for per-execution and global broadcasts."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime

from fastapi import WebSocket

from akeso_soar.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Room types
# ---------------------------------------------------------------------------

ROOM_GLOBAL = "global"  # new alerts, new human tasks, execution status changes


def execution_room(execution_id: str) -> str:
    return f"execution:{execution_id}"


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------


class ConnectionManager:
    """Track active WebSocket connections by room."""

    def __init__(self) -> None:
        # room_name → set of WebSocket connections
        self._rooms: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket, rooms: list[str]) -> None:
        """Accept a WebSocket and subscribe it to the given rooms."""
        await ws.accept()
        async with self._lock:
            for room in rooms:
                self._rooms.setdefault(room, set()).add(ws)
        logger.debug("ws.connect", rooms=rooms)

    async def disconnect(self, ws: WebSocket) -> None:
        """Remove a WebSocket from all rooms."""
        async with self._lock:
            empty_rooms = []
            for room, connections in self._rooms.items():
                connections.discard(ws)
                if not connections:
                    empty_rooms.append(room)
            for room in empty_rooms:
                del self._rooms[room]
        logger.debug("ws.disconnect")

    async def subscribe(self, ws: WebSocket, room: str) -> None:
        """Add a WebSocket to an additional room after initial connect."""
        async with self._lock:
            self._rooms.setdefault(room, set()).add(ws)

    async def broadcast(self, room: str, message: dict) -> None:
        """Send a JSON message to all connections in a room."""
        async with self._lock:
            connections = list(self._rooms.get(room, set()))

        if not connections:
            return

        payload = json.dumps({**message, "timestamp": datetime.now(UTC).isoformat()})
        dead: list[WebSocket] = []
        for ws in connections:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    for conns in self._rooms.values():
                        conns.discard(ws)

    async def broadcast_global(self, message: dict) -> None:
        """Broadcast to the global room."""
        await self.broadcast(ROOM_GLOBAL, message)

    @property
    def active_connections(self) -> int:
        """Total unique active connections."""
        all_ws: set[WebSocket] = set()
        for conns in self._rooms.values():
            all_ws.update(conns)
        return len(all_ws)


# Singleton instance
ws_manager = ConnectionManager()
