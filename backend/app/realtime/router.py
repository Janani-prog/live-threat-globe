import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.realtime.manager import manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/events")
async def ws_events(websocket: WebSocket):
    client_ip = websocket.client.host if websocket.client else "unknown"
    accepted = await manager.connect(websocket, client_ip)
    if not accepted:
        # 1013 = "Try Again Later", the closest standard WS close code for
        # a capacity-based rejection.
        await websocket.close(code=1013)
        return

    try:
        while True:
            # Clients don't send anything meaningful; this just lets us
            # detect disconnects promptly.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, client_ip)
