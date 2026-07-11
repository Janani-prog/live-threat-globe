import asyncio
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)

# Cap concurrent connections per client IP so a single client can't exhaust
# connection slots on a free-tier instance (Security & Access doc section 4).
MAX_CONNECTIONS_PER_IP = 5


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, websocket: WebSocket, client_ip: str) -> bool:
        existing = self._connections.get(client_ip, set())
        if len(existing) >= MAX_CONNECTIONS_PER_IP:
            return False
        await websocket.accept()
        self._connections.setdefault(client_ip, set()).add(websocket)
        return True

    def disconnect(self, websocket: WebSocket, client_ip: str) -> None:
        conns = self._connections.get(client_ip)
        if conns and websocket in conns:
            conns.discard(websocket)
            if not conns:
                self._connections.pop(client_ip, None)

    async def broadcast(self, event: dict) -> None:
        dead: list[tuple[str, WebSocket]] = []
        for client_ip, sockets in list(self._connections.items()):
            for ws in list(sockets):
                try:
                    await ws.send_json(event)
                except Exception:
                    dead.append((client_ip, ws))
        for client_ip, ws in dead:
            self.disconnect(ws, client_ip)

    def broadcast_from_thread(self, event: dict) -> None:
        """Thread-safe entrypoint for callers running outside the main event
        loop — the ingestion cycle runs as a sync APScheduler job in a
        worker thread, not on the loop that owns the WebSocket connections.
        """
        if self._loop is None:
            logger.warning("No event loop registered with ConnectionManager — dropping broadcast")
            return
        asyncio.run_coroutine_threadsafe(self.broadcast(event), self._loop)


manager = ConnectionManager()
