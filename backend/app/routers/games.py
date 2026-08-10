from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app import accounts, auth, schemas
from app.bots import run_bots_until_human
from app.connection_manager import manager
from app.db import get_db
from app.game_engine import board_engine, inflation, state as game_state
from app.models import Player
from app.serializers import serialize_game_state

router = APIRouter(prefix="/api/games", tags=["games"])


async def _broadcast_state(db: Session, game) -> schemas.GameStateOut:
    state = serialize_game_state(db, game)
    await manager.broadcast(game.code, {"type": "state", "game": state.model_dump(mode="json")})
    return state


@router.post("", response_model=schemas.GameCreateResponse)
def create_game(
    payload: schemas.GameCreateRequest,
    db: Session = Depends(get_db),
    x_session_token: str | None = Header(default=None),
):
    overrides: dict = {}
    if payload.starting_cash:
        overrides["starting_cash"] = payload.starting_cash
    overrides["free_parking_pot"] = payload.free_parking_pot
    overrides["event_system"] = payload.event_system
    overrides["challenge_before_buy"] = {"enabled": payload.challenge_before_buy}
    overrides["inflation"] = {
        "enabled": payload.inflation_enabled,
        "trigger": payload.inflation_trigger,
        "rate": payload.inflation_rate,
    }
    overrides["dice_count"] = payload.dice_count
    overrides["turn_order_mode"] = payload.turn_order_mode

    try:
        game, host = game_state.create_game(
            db, host_name=payload.host_name, name=payload.name, ruleset_overrides=overrides, board_key=payload.board_key
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    game.banker_mode = payload.banker_mode
    game.money_mode = payload.money_mode
    game.play_mode = payload.play_mode
    owner = accounts.get_current_user(db, x_session_token)
    if owner:
        game.owner_user_id = owner.id
    db.commit()
    db.refresh(game)
    return schemas.GameCreateResponse(
        game=serialize_game_state(db, game),
        host_player_id=host.id,
        host_token=game.host_token,
        player_token=host.token,
    )


@router.get("/{code}", response_model=schemas.GameStateOut)
def get_game(code: str, db: Session = Depends(get_db)):
    game = auth.get_game_or_404(db, code)
    return serialize_game_state(db, game)


@router.post("/{code}/join", response_model=schemas.JoinGameResponse)
async def join_game(code: str, payload: schemas.JoinGameRequest, db: Session = Depends(get_db)):
    game = auth.get_game_or_404(db, code)
    try:
        player = game_state.join_game(db, game, name=payload.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    state = await _broadcast_state(db, game)
    return schemas.JoinGameResponse(game=state, player_id=player.id, player_token=player.token)


@router.post("/{code}/players", response_model=schemas.JoinGameResponse)
async def add_player(
    code: str,
    payload: schemas.AddPlayerRequest,
    db: Session = Depends(get_db),
    x_host_token: str | None = Header(default=None),
):
    game = auth.get_game_or_404(db, code)
    auth.require_host(game, x_host_token)
    try:
        player = game_state.join_game(db, game, name=payload.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    state = await _broadcast_state(db, game)
    return schemas.JoinGameResponse(game=state, player_id=player.id, player_token=player.token)


@router.post("/{code}/start", response_model=schemas.GameStateOut)
async def start_game(
    code: str, db: Session = Depends(get_db), x_host_token: str | None = Header(default=None)
):
    game = auth.get_game_or_404(db, code)
    auth.require_host(game, x_host_token)
    try:
        game_state.start_game(db, game)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    await run_bots_until_human(db, game)
    return await _broadcast_state(db, game)


@router.post("/{code}/banker", response_model=schemas.GameStateOut)
async def set_banker(
    code: str,
    payload: schemas.PromoteBankerRequest,
    db: Session = Depends(get_db),
    x_host_token: str | None = Header(default=None),
):
    game = auth.get_game_or_404(db, code)
    auth.require_host(game, x_host_token)
    player = db.get(Player, payload.player_id)
    if not player or player.game_id != game.id:
        raise HTTPException(status_code=404, detail="Player not found")
    player.is_banker = payload.is_banker
    db.commit()

    return await _broadcast_state(db, game)


@router.post("/{code}/bots", response_model=schemas.GameStateOut)
async def add_bot(
    code: str,
    payload: schemas.AddBotRequest,
    db: Session = Depends(get_db),
    x_host_token: str | None = Header(default=None),
):
    game = auth.get_game_or_404(db, code)
    auth.require_host(game, x_host_token)
    try:
        game_state.add_bot(db, game, name=payload.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return await _broadcast_state(db, game)


@router.post("/{code}/save_board_template", response_model=schemas.BoardDetailOut)
def save_board_template(
    code: str,
    payload: schemas.SaveBoardTemplateRequest,
    db: Session = Depends(get_db),
    x_host_token: str | None = Header(default=None),
    x_session_token: str | None = Header(default=None),
):
    game = auth.get_game_or_404(db, code)
    auth.require_host(game, x_host_token)
    owner = accounts.require_user(db, x_session_token)

    try:
        clone = board_engine.clone_board(
            db, game.board, key=payload.key, name=payload.name, description=payload.description,
            owner_user_id=owner.id,
        )
    except board_engine.BoardEngineError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return schemas.BoardDetailOut.model_validate(clone)


@router.post("/{code}/advance_round", response_model=schemas.GameStateOut)
async def advance_round(
    code: str,
    db: Session = Depends(get_db),
    x_player_id: str = Header(...),
    x_player_token: str = Header(...),
):
    game = auth.get_game_or_404(db, code)
    auth.require_banker(db, game, x_player_id, x_player_token)
    inflation.advance_round(game)
    db.commit()

    return await _broadcast_state(db, game)
