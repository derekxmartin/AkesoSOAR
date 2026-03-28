"""WebSocket endpoint — /ws?token=<jwt>&rooms=global,execution:<id>"""

from __future__ import annotations

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError

from akeso_soar.services.auth import decode_token
from akeso_soar.services.ws_manager import ROOM_GLOBAL, ws_manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    ws: WebSocket,
    token: str = Query(...),
    rooms: str = Query(default=ROOM_GLOBAL),
):
    """WebSocket endpoint with JWT auth via query param.

    Query params:
      token  — valid access JWT
      rooms  — comma-separated room names (default: "global")
    """
    # Authenticate
    try:
        payload = decode_token(token)
    except (JWTError, Exception):
        await ws.close(code=4001, reason="Invalid or expired token")
        return

    # Parse rooms
    room_list = [r.strip() for r in rooms.split(",") if r.strip()]
    if ROOM_GLOBAL not in room_list:
        room_list.append(ROOM_GLOBAL)

    await ws_manager.connect(ws, room_list)

    try:
        while True:
            # Keep connection alive; handle client messages if needed
            data = await ws.receive_text()
            # Client can send {"subscribe": "execution:<id>"} to join a room
            try:
                import json
                msg = json.loads(data)
                if "subscribe" in msg:
                    await ws_manager.subscribe(ws, msg["subscribe"])
                    await ws.send_text(json.dumps({"type": "subscribed", "room": msg["subscribe"]}))
            except Exception:
                pass
    except WebSocketDisconnect:
        await ws_manager.disconnect(ws)
    except Exception:
        await ws_manager.disconnect(ws)
