"""WebSocket endpoint — /ws?token=<jwt>&rooms=global,execution:<id>"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError

from akeso_soar.logging import get_logger
from akeso_soar.services.auth import decode_token
from akeso_soar.services.ws_manager import ROOM_GLOBAL, ws_manager

logger = get_logger(__name__)
router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    ws: WebSocket,
    token: str = Query(...),
    rooms: str = Query(default=ROOM_GLOBAL),
):
    # Authenticate before accepting
    try:
        payload = decode_token(token)
    except (JWTError, Exception):
        await ws.accept()
        await ws.close(code=4001, reason="Invalid or expired token")
        return

    # Parse rooms
    room_list = [r.strip() for r in rooms.split(",") if r.strip()]
    if ROOM_GLOBAL not in room_list:
        room_list.append(ROOM_GLOBAL)

    await ws_manager.connect(ws, room_list)

    try:
        while True:
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
                if "subscribe" in msg:
                    await ws_manager.subscribe(ws, msg["subscribe"])
                    await ws.send_text(json.dumps({"type": "subscribed", "room": msg["subscribe"]}))
                elif msg.get("type") == "ping":
                    await ws.send_text(json.dumps({"type": "pong"}))
            except (json.JSONDecodeError, KeyError):
                pass
    except WebSocketDisconnect:
        pass
    except asyncio.CancelledError:
        pass
    except Exception as exc:
        logger.warning("ws.error", error=str(exc))
    finally:
        await ws_manager.disconnect(ws)
