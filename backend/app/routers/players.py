from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app import auth, schemas
from app.connection_manager import manager
from app.db import get_db
from app.game_engine.money_modes import banker_ledger
from app.models import EventLogEntry
from app.serializers import serialize_game_state

router = APIRouter(prefix="/api/games/{code}", tags=["players"])


@router.post("/land")
async def declare_landing(
    code: str,
    payload: schemas.LandRequest,
    db: Session = Depends(get_db),
    x_player_token: str = Header(...),
):
    game = auth.get_game_or_404(db, code)
    player = auth.require_player(db, game, payload.player_id, x_player_token)
    if game.banker_mode != "auto":
        raise HTTPException(status_code=400, detail="This game is not in auto banker mode")

    try:
        outcome = banker_ledger.apply_auto_banker_landing(
            db, game, player=player, space_index=payload.space_index, dice_roll=payload.dice_roll
        )
        db.commit()
    except banker_ledger.GameEngineError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    state = serialize_game_state(db, game)
    await manager.broadcast(game.code, {"type": "state", "game": state.model_dump(mode="json")})
    return {"outcome": outcome, "game": state}


@router.get("/players/{player_id}/log", response_model=list[schemas.EventLogOut])
def player_log(code: str, player_id: str, db: Session = Depends(get_db)):
    game = auth.get_game_or_404(db, code)
    entries = (
        db.query(EventLogEntry)
        .filter(EventLogEntry.game_id == game.id)
        .order_by(EventLogEntry.created_at.desc())
        .all()
    )
    personal = [e for e in entries if player_id in (e.player_ids or [])]
    return list(reversed(personal))
