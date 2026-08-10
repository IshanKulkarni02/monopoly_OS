from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app import auth, schemas
from app.connection_manager import manager
from app.db import get_db
from app.game_engine import trading
from app.models import Player, Trade
from app.serializers import serialize_game_state

router = APIRouter(prefix="/api/games/{code}/trades", tags=["trading"])


async def _broadcast_state(db: Session, game) -> schemas.GameStateOut:
    state = serialize_game_state(db, game)
    await manager.broadcast(game.code, {"type": "state", "game": state.model_dump(mode="json")})
    return state


def _get_trade(db: Session, game, trade_id: str) -> Trade:
    trade = db.get(Trade, trade_id)
    if not trade or trade.game_id != game.id:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade


@router.post("", response_model=schemas.TradeOut)
async def propose_trade(
    code: str,
    payload: schemas.ProposeTradeRequest,
    db: Session = Depends(get_db),
    x_player_id: str = Header(...),
    x_player_token: str = Header(...),
):
    game = auth.get_game_or_404(db, code)
    proposer = auth.require_player(db, game, x_player_id, x_player_token)
    recipient = db.get(Player, payload.recipient_id)
    if not recipient or recipient.game_id != game.id:
        raise HTTPException(status_code=404, detail="recipient_id not found in this game")

    try:
        trade = trading.propose_trade(
            db, game,
            proposer=proposer, recipient=recipient,
            offer_cash=payload.offer_cash, offer_property_ids=payload.offer_property_ids, offer_jail_cards=payload.offer_jail_cards,
            request_cash=payload.request_cash, request_property_ids=payload.request_property_ids, request_jail_cards=payload.request_jail_cards,
        )
        db.commit()
    except trading.GameEngineError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    state = serialize_game_state(db, game)
    await manager.broadcast(game.code, {"type": "state", "game": state.model_dump(mode="json")})
    return trade


@router.get("", response_model=list[schemas.TradeOut])
def list_trades(code: str, db: Session = Depends(get_db)):
    game = auth.get_game_or_404(db, code)
    return db.query(Trade).filter(Trade.game_id == game.id).order_by(Trade.created_at.desc()).all()


@router.post("/{trade_id}/accept", response_model=schemas.GameStateOut)
async def accept_trade(
    code: str,
    trade_id: str,
    db: Session = Depends(get_db),
    x_player_id: str = Header(...),
    x_player_token: str = Header(...),
):
    game = auth.get_game_or_404(db, code)
    player = auth.require_player(db, game, x_player_id, x_player_token)
    trade = _get_trade(db, game, trade_id)
    if trade.recipient_id != player.id:
        raise HTTPException(status_code=403, detail="Only the recipient can accept this trade")

    try:
        trading.respond_to_trade(db, game, trade=trade, accept=True)
        db.commit()
    except trading.GameEngineError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return await _broadcast_state(db, game)


@router.post("/{trade_id}/decline", response_model=schemas.GameStateOut)
async def decline_trade(
    code: str,
    trade_id: str,
    db: Session = Depends(get_db),
    x_player_id: str = Header(...),
    x_player_token: str = Header(...),
):
    game = auth.get_game_or_404(db, code)
    player = auth.require_player(db, game, x_player_id, x_player_token)
    trade = _get_trade(db, game, trade_id)
    if trade.recipient_id != player.id:
        raise HTTPException(status_code=403, detail="Only the recipient can decline this trade")

    try:
        trading.respond_to_trade(db, game, trade=trade, accept=False)
        db.commit()
    except trading.GameEngineError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return await _broadcast_state(db, game)


@router.post("/{trade_id}/cancel", response_model=schemas.GameStateOut)
async def cancel_trade(
    code: str,
    trade_id: str,
    db: Session = Depends(get_db),
    x_player_id: str = Header(...),
    x_player_token: str = Header(...),
):
    game = auth.get_game_or_404(db, code)
    player = auth.require_player(db, game, x_player_id, x_player_token)
    trade = _get_trade(db, game, trade_id)
    if trade.proposer_id != player.id and not player.is_host:
        raise HTTPException(status_code=403, detail="Only the proposer or the host can cancel this trade")

    try:
        trading.cancel_trade(db, game, trade=trade)
        db.commit()
    except trading.GameEngineError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return await _broadcast_state(db, game)
