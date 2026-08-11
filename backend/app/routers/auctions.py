from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app import auth, schemas
from app.connection_manager import manager
from app.db import get_db
from app.game_engine import auctions
from app.models import Property
from app.serializers import serialize_game_state

router = APIRouter(prefix="/api/games/{code}/auctions", tags=["auctions"])


async def _broadcast_state(db: Session, game) -> schemas.GameStateOut:
    state = serialize_game_state(db, game)
    await manager.broadcast(game.code, {"type": "state", "game": state.model_dump(mode="json")})
    return state


@router.post("/start", response_model=schemas.GameStateOut)
async def start_auction(
    code: str,
    payload: schemas.StartAuctionRequest,
    db: Session = Depends(get_db),
    x_player_id: str = Header(...),
    x_player_token: str = Header(...),
):
    game = auth.get_game_or_404(db, code)
    player = auth.require_player(db, game, x_player_id, x_player_token)
    prop = db.get(Property, payload.property_id)
    if not prop or prop.game_id != game.id:
        raise HTTPException(status_code=404, detail="Property not found")

    try:
        auctions.start_auction(db, game, property_=prop, started_by=player)
        db.commit()
    except auctions.GameEngineError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return await _broadcast_state(db, game)


@router.post("/bid", response_model=schemas.GameStateOut)
async def bid(
    code: str,
    payload: schemas.BidRequest,
    db: Session = Depends(get_db),
    x_player_id: str = Header(...),
    x_player_token: str = Header(...),
):
    game = auth.get_game_or_404(db, code)
    player = auth.require_player(db, game, x_player_id, x_player_token)

    try:
        auctions.place_bid(db, game, player=player, amount=payload.amount)
        db.commit()
    except auctions.GameEngineError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return await _broadcast_state(db, game)


@router.post("/pass", response_model=schemas.GameStateOut)
async def pass_bid(
    code: str,
    db: Session = Depends(get_db),
    x_player_id: str = Header(...),
    x_player_token: str = Header(...),
):
    game = auth.get_game_or_404(db, code)
    player = auth.require_player(db, game, x_player_id, x_player_token)

    try:
        auctions.pass_auction(db, game, player=player)
        db.commit()
    except auctions.GameEngineError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return await _broadcast_state(db, game)


@router.post("/cancel", response_model=schemas.GameStateOut)
async def cancel_auction(
    code: str,
    db: Session = Depends(get_db),
    x_host_token: str = Header(...),
):
    game = auth.get_game_or_404(db, code)
    auth.require_host(game, x_host_token)
    host = next((p for p in game.players if p.is_host), None)
    if not host:
        raise HTTPException(status_code=404, detail="Host player not found")

    try:
        auctions.cancel_auction(db, game, actor=host)
        db.commit()
    except auctions.GameEngineError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return await _broadcast_state(db, game)
