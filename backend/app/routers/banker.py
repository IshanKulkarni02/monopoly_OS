from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app import auth, schemas
from app.connection_manager import manager
from app.db import get_db
from app.game_engine import houses, mortgages
from app.game_engine.money_modes import banker_ledger
from app.models import Player, Property, Transaction
from app.serializers import serialize_game_state

router = APIRouter(prefix="/api/games/{code}", tags=["banker"])


async def _broadcast_state(db: Session, game) -> schemas.GameStateOut:
    state = serialize_game_state(db, game)
    await manager.broadcast(game.code, {"type": "state", "game": state.model_dump(mode="json")})
    return state


@router.post("/transactions", response_model=schemas.GameStateOut)
async def log_transaction(
    code: str,
    payload: schemas.ManualTransactionRequest,
    db: Session = Depends(get_db),
    x_player_id: str = Header(...),
    x_player_token: str = Header(...),
):
    game = auth.get_game_or_404(db, code)
    banker = auth.require_banker(db, game, x_player_id, x_player_token)

    from_player = db.get(Player, payload.from_player_id) if payload.from_player_id else None
    to_player = db.get(Player, payload.to_player_id) if payload.to_player_id else None
    if payload.from_player_id and (not from_player or from_player.game_id != game.id):
        raise HTTPException(status_code=404, detail="from_player not found")
    if payload.to_player_id and (not to_player or to_player.game_id != game.id):
        raise HTTPException(status_code=404, detail="to_player not found")

    try:
        banker_ledger.apply_transaction(
            db,
            game,
            from_player=from_player,
            to_player=to_player,
            amount=payload.amount,
            reason=payload.reason or "manual",
            created_by_player_id=banker.id,
        )
        db.commit()
    except banker_ledger.GameEngineError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return await _broadcast_state(db, game)


@router.post("/properties/{property_id}/purchase")
async def purchase_property(
    code: str,
    property_id: str,
    db: Session = Depends(get_db),
    x_player_id: str = Header(...),
    x_player_token: str = Header(...),
):
    game = auth.get_game_or_404(db, code)
    player = auth.require_player(db, game, x_player_id, x_player_token)
    prop = db.get(Property, property_id)
    if not prop or prop.game_id != game.id:
        raise HTTPException(status_code=404, detail="Property not found")

    try:
        result = banker_ledger.apply_purchase(db, game, player=player, property_=prop)
        db.commit()
    except banker_ledger.GameEngineError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    state = await _broadcast_state(db, game)
    return {"purchased": result["purchased"], "challenge": result["challenge"], "game": state}


@router.post("/properties/{property_id}/build_house", response_model=schemas.GameStateOut)
async def build_house(
    code: str,
    property_id: str,
    db: Session = Depends(get_db),
    x_player_id: str = Header(...),
    x_player_token: str = Header(...),
):
    game = auth.get_game_or_404(db, code)
    player = auth.require_player(db, game, x_player_id, x_player_token)
    prop = db.get(Property, property_id)
    if not prop or prop.game_id != game.id:
        raise HTTPException(status_code=404, detail="Property not found")

    try:
        houses.build_house(db, game, player=player, property_=prop)
        db.commit()
    except houses.HouseError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return await _broadcast_state(db, game)


@router.post("/properties/{property_id}/sell_house", response_model=schemas.GameStateOut)
async def sell_house(
    code: str,
    property_id: str,
    db: Session = Depends(get_db),
    x_player_id: str = Header(...),
    x_player_token: str = Header(...),
):
    game = auth.get_game_or_404(db, code)
    player = auth.require_player(db, game, x_player_id, x_player_token)
    prop = db.get(Property, property_id)
    if not prop or prop.game_id != game.id:
        raise HTTPException(status_code=404, detail="Property not found")

    try:
        houses.sell_house(db, game, player=player, property_=prop)
        db.commit()
    except houses.HouseError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return await _broadcast_state(db, game)


@router.post("/properties/{property_id}/mortgage", response_model=schemas.GameStateOut)
async def mortgage_property(
    code: str,
    property_id: str,
    db: Session = Depends(get_db),
    x_player_id: str = Header(...),
    x_player_token: str = Header(...),
):
    game = auth.get_game_or_404(db, code)
    player = auth.require_player(db, game, x_player_id, x_player_token)
    prop = db.get(Property, property_id)
    if not prop or prop.game_id != game.id:
        raise HTTPException(status_code=404, detail="Property not found")

    try:
        mortgages.mortgage_property(db, game, player=player, property_=prop)
        db.commit()
    except banker_ledger.GameEngineError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return await _broadcast_state(db, game)


@router.post("/properties/{property_id}/unmortgage", response_model=schemas.GameStateOut)
async def unmortgage_property(
    code: str,
    property_id: str,
    db: Session = Depends(get_db),
    x_player_id: str = Header(...),
    x_player_token: str = Header(...),
):
    game = auth.get_game_or_404(db, code)
    player = auth.require_player(db, game, x_player_id, x_player_token)
    prop = db.get(Property, property_id)
    if not prop or prop.game_id != game.id:
        raise HTTPException(status_code=404, detail="Property not found")

    try:
        mortgages.unmortgage_property(db, game, player=player, property_=prop)
        db.commit()
    except banker_ledger.GameEngineError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return await _broadcast_state(db, game)


@router.post("/transactions/{transaction_id}/reverse", response_model=schemas.GameStateOut)
async def reverse_transaction(
    code: str,
    transaction_id: str,
    db: Session = Depends(get_db),
    x_player_id: str = Header(...),
    x_player_token: str = Header(...),
):
    game = auth.get_game_or_404(db, code)
    banker = auth.require_banker(db, game, x_player_id, x_player_token)
    txn = db.get(Transaction, transaction_id)
    if not txn or txn.game_id != game.id:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if txn.reversed:
        raise HTTPException(status_code=400, detail="Transaction already reversed")

    from_player = db.get(Player, txn.from_player_id) if txn.from_player_id else None
    to_player = db.get(Player, txn.to_player_id) if txn.to_player_id else None

    try:
        # Reversing means replaying the same amount in the opposite direction.
        banker_ledger.apply_transaction(
            db,
            game,
            from_player=to_player,
            to_player=from_player,
            amount=txn.amount,
            reason=f"reversal of: {txn.reason}",
            created_by_player_id=banker.id,
        )
        txn.reversed = True
        db.commit()
    except banker_ledger.GameEngineError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return await _broadcast_state(db, game)
