from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.connection_manager import manager
from app.db import SessionLocal
from app.models import Game
from app.serializers import serialize_game_state

router = APIRouter(tags=["ws"])


@router.websocket("/ws/games/{code}")
async def game_ws(websocket: WebSocket, code: str):
    db = SessionLocal()
    game = db.query(Game).filter(Game.code == code.upper()).first()
    if not game:
        await websocket.close(code=4404)
        db.close()
        return

    await manager.connect(game.code, websocket)
    try:
        state = serialize_game_state(db, game)
        await websocket.send_json({"type": "state", "game": state.model_dump(mode="json")})
        while True:
            # Clients don't need to send anything meaningful; this just keeps
            # the socket open and lets us detect disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(game.code, websocket)
        db.close()
