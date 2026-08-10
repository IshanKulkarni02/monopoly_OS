import asyncio

from fastapi import WebSocket


class ConnectionManager:
    """Per-game-code websocket room registry used only for broadcasting state
    updates. Game state itself lives in the database, not here — so a server
    restart never loses game progress, only open sockets (which clients
    reconnect automatically).
    """

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, code: str, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.setdefault(code, set()).add(ws)

    async def disconnect(self, code: str, ws: WebSocket) -> None:
        async with self._lock:
            conns = self._connections.get(code)
            if conns and ws in conns:
                conns.discard(ws)
                if not conns:
                    self._connections.pop(code, None)

    async def broadcast(self, code: str, message: dict) -> None:
        conns = list(self._connections.get(code, set()))
        stale = []
        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception:
                stale.append(ws)
        for ws in stale:
            await self.disconnect(code, ws)


manager = ConnectionManager()
