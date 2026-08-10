"""Host-driven IRL live-play: the turn-order dice ceremony, tracked
positions from manually-entered physical dice rolls, and GM correction
tools (move/swap). Complements — doesn't replace — the original
declare-your-landing `/land` flow in `players.py`, which still works for
IRL games that don't want position tracking."""

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app import auth, schemas
from app.connection_manager import manager
from app.db import get_db
from app.game_engine import turn_engine
from app.game_engine.money_modes.banker_ledger import GameEngineError
from app.models import Player
from app.serializers import serialize_game_state

router = APIRouter(prefix="/api/games/{code}", tags=["irl_live"])


async def _broadcast_state(db: Session, game) -> schemas.GameStateOut:
    state = serialize_game_state(db, game)
    await manager.broadcast(game.code, {"type": "state", "game": state.model_dump(mode="json")})
    return state


@router.post("/roll_for_order")
async def roll_for_order(
    code: str,
    payload: schemas.RollForOrderRequest,
    db: Session = Depends(get_db),
    x_host_token: str | None = Header(default=None),
    x_player_id: str | None = Header(default=None),
    x_player_token: str | None = Header(default=None),
):
    game = auth.get_game_or_404(db, code)
    player = auth.require_host_or_target_player(
        db, game, payload.player_id, host_token=x_host_token, player_id=x_player_id, player_token=x_player_token
    )

    try:
        outcome = turn_engine.record_order_roll(db, game, player=player, roll=payload.roll)
        db.commit()
    except GameEngineError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    state = await _broadcast_state(db, game)
    return {"outcome": outcome, "game": state}


@router.post("/roll_for_player")
async def roll_for_player(
    code: str,
    payload: schemas.RollForPlayerRequest,
    db: Session = Depends(get_db),
    x_host_token: str | None = Header(default=None),
    x_player_id: str | None = Header(default=None),
    x_player_token: str | None = Header(default=None),
):
    game = auth.get_game_or_404(db, code)
    player = auth.require_host_or_target_player(
        db, game, payload.player_id, host_token=x_host_token, player_id=x_player_id, player_token=x_player_token
    )

    try:
        result = turn_engine.roll_dice(
            db, game, player=player, use_jail_free_card=payload.use_jail_free_card,
            pay_fine=payload.pay_fine, manual_dice=payload.dice,
        )
        db.commit()
    except GameEngineError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    state = await _broadcast_state(db, game)
    return {"result": result, "game": state}


@router.post("/players/{player_id}/move", response_model=schemas.GameStateOut)
async def move_player(
    code: str,
    player_id: str,
    payload: schemas.MovePlayerRequest,
    db: Session = Depends(get_db),
    x_host_token: str | None = Header(default=None),
):
    game = auth.get_game_or_404(db, code)
    auth.require_host(game, x_host_token)
    player = db.get(Player, player_id)
    if not player or player.game_id != game.id:
        raise HTTPException(status_code=404, detail="Player not found")

    try:
        turn_engine.move_player(db, game, player=player, position=payload.position, resolve_landing=payload.resolve_landing)
        db.commit()
    except GameEngineError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return await _broadcast_state(db, game)


@router.post("/players/swap", response_model=schemas.GameStateOut)
async def swap_players(
    code: str,
    payload: schemas.SwapPlayersRequest,
    db: Session = Depends(get_db),
    x_host_token: str | None = Header(default=None),
):
    game = auth.get_game_or_404(db, code)
    auth.require_host(game, x_host_token)
    player_a = db.get(Player, payload.player_a_id)
    player_b = db.get(Player, payload.player_b_id)
    if not player_a or player_a.game_id != game.id or not player_b or player_b.game_id != game.id:
        raise HTTPException(status_code=404, detail="Player not found")
    if player_a.id == player_b.id:
        raise HTTPException(status_code=400, detail="Can't swap a player with themselves")

    turn_engine.swap_players(db, game, player_a=player_a, player_b=player_b)
    db.commit()
    return await _broadcast_state(db, game)


@router.get("/player_tokens")
def player_tokens(code: str, db: Session = Depends(get_db), x_host_token: str | None = Header(default=None)):
    """Lets the host's device act on behalf of any player who hasn't
    connected their own phone — e.g. purchasing property or ending a turn
    using that player's existing token, without a duplicate host-authorized
    endpoint for every single player action."""
    game = auth.get_game_or_404(db, code)
    auth.require_host(game, x_host_token)
    return {p.id: p.token for p in game.players}
