import asyncio

from app.realtime.manager import MAX_CONNECTIONS_PER_IP, ConnectionManager


class FakeWebSocket:
    """Minimal stand-in for fastapi.WebSocket, for unit-testing the
    connection manager's fan-out/cap logic without a real socket."""

    def __init__(self) -> None:
        self.sent: list[dict] = []
        self.accepted = False

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, data: dict) -> None:
        self.sent.append(data)


def test_broadcast_fans_out_to_all_connections():
    manager = ConnectionManager()

    async def scenario():
        ws1, ws2 = FakeWebSocket(), FakeWebSocket()
        assert await manager.connect(ws1, "1.1.1.1") is True
        assert await manager.connect(ws2, "2.2.2.2") is True

        await manager.broadcast({"ip_hash": "abc", "risk_score": 42.0})

        assert ws1.sent == [{"ip_hash": "abc", "risk_score": 42.0}]
        assert ws2.sent == [{"ip_hash": "abc", "risk_score": 42.0}]

    asyncio.run(scenario())


def test_broadcast_handles_missing_risk_score_gracefully():
    """The ML model may not exist yet (Phase 2 artifact pending) or the
    /check quota guard may have been hit — either way risk_score can be
    None, and the broadcast path must not choke on it.
    """
    manager = ConnectionManager()

    async def scenario():
        ws = FakeWebSocket()
        await manager.connect(ws, "3.3.3.3")

        await manager.broadcast({"ip_hash": "not-yet-scored", "risk_score": None, "lat": 1.0, "lon": 2.0})

        assert len(ws.sent) == 1
        assert ws.sent[0]["risk_score"] is None
        assert ws.sent[0]["ip_hash"] == "not-yet-scored"

    asyncio.run(scenario())


def test_per_ip_connection_cap_rejects_over_limit():
    manager = ConnectionManager()

    async def scenario():
        sockets = [FakeWebSocket() for _ in range(MAX_CONNECTIONS_PER_IP + 1)]
        results = [await manager.connect(ws, "4.4.4.4") for ws in sockets]

        assert results.count(True) == MAX_CONNECTIONS_PER_IP
        assert results.count(False) == 1

    asyncio.run(scenario())


def test_disconnect_removes_from_broadcast_targets():
    manager = ConnectionManager()

    async def scenario():
        ws1, ws2 = FakeWebSocket(), FakeWebSocket()
        await manager.connect(ws1, "5.5.5.5")
        await manager.connect(ws2, "6.6.6.6")

        manager.disconnect(ws1, "5.5.5.5")
        await manager.broadcast({"ip_hash": "xyz", "risk_score": None})

        assert ws1.sent == []
        assert ws2.sent == [{"ip_hash": "xyz", "risk_score": None}]

    asyncio.run(scenario())


def test_ws_endpoint_accepts_connection(client):
    with client.websocket_connect("/ws/events"):
        pass  # if the handshake fails, this raises
