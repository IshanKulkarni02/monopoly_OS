from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app import auth, schemas
from app.bots import run_bots_until_human
from app.connection_manager import manager
from app.db import get_db
from app.game_engine import turn_engine
from app.game_engine.money_modes.banker_ledger import GameEngineError
from app.serializers import serialize_game_state

router = APIRouter(prefix="/api/games/{code}", tags=["virtual"])


async def _broadcast_state(db: Session, game) -> schemas.GameStateOut:
    state = serialize_game_state(db, game)
    await manager.broadcast(game.code, {"type": "state", "game": state.model_dump(mode="json")})
    return state


@router.post("/roll")
async def roll(
    code: str,
    payload: schemas.RollRequest,
    db: Session = Depends(get_db),
    x_player_id: str = Header(...),
    x_player_token: str = Header(...),
):
    game = auth.get_game_or_404(db, code)
    player = auth.require_player(db, game, x_player_id, x_player_token)

    try:
        result = turn_engine.roll_dice(
            db, game, player=player, use_jail_free_card=payload.use_jail_free_card, pay_fine=payload.pay_fine
        )
        db.commit()
    except GameEngineError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    state = await _broadcast_state(db, game)
    return {"result": result, "game": state}


@router.post("/end_turn", response_model=schemas.GameStateOut)
async def end_turn(
    code: str,
    db: Session = Depends(get_db),
    x_player_id: str = Header(...),
    x_player_token: str = Header(...),
):
    game = auth.get_game_or_404(db, code)
    player = auth.require_player(db, game, x_player_id, x_player_token)

    try:
        turn_engine.end_turn(db, game, player=player)
        db.commit()
    except GameEngineError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await run_bots_until_human(db, game)
    return await _broadcast_state(db, game)
