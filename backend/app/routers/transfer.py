from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app import auth, schemas
from app.connection_manager import manager
from app.db import get_db
from app.game_engine.money_modes import banker_ledger, digital_transfer
from app.models import Player, Transaction
from app.serializers import serialize_game_state

router = APIRouter(prefix="/api/games/{code}/transfer", tags=["transfer"])


async def _broadcast_state(db: Session, game) -> schemas.GameStateOut:
    state = serialize_game_state(db, game)
    await manager.broadcast(game.code, {"type": "state", "game": state.model_dump(mode="json")})
    return state


def _require_digital_transfer_mode(game) -> None:
    if game.money_mode != "digital_transfer":
        raise HTTPException(status_code=400, detail="This game is not in digital transfer money mode")


def _get_other_player(db: Session, game, other_player_id: str) -> Player:
    other = db.get(Player, other_player_id)
    if not other or other.game_id != game.id:
        raise HTTPException(status_code=404, detail="Player not found")
    return other


@router.post("/send", response_model=schemas.GameStateOut)
async def send_transfer(
    code: str,
    payload: schemas.TransferRequest,
    db: Session = Depends(get_db),
    x_player_id: str = Header(...),
    x_player_token: str = Header(...),
):
    game = auth.get_game_or_404(db, code)
    _require_digital_transfer_mode(game)
    sender = auth.require_player(db, game, x_player_id, x_player_token)
    to_player = _get_other_player(db, game, payload.other_player_id)

    try:
        digital_transfer.send(db, game, sender=sender, to_player=to_player, amount=payload.amount, reason=payload.reason)
        db.commit()
    except banker_ledger.GameEngineError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return await _broadcast_state(db, game)


@router.post("/request", response_model=schemas.GameStateOut)
async def request_transfer(
    code: str,
    payload: schemas.TransferRequest,
    db: Session = Depends(get_db),
    x_player_id: str = Header(...),
    x_player_token: str = Header(...),
):
    game = auth.get_game_or_404(db, code)
    _require_digital_transfer_mode(game)
    requester = auth.require_player(db, game, x_player_id, x_player_token)
    from_player = _get_other_player(db, game, payload.other_player_id)

    try:
        digital_transfer.request(db, game, requester=requester, from_player=from_player, amount=payload.amount, reason=payload.reason)
        db.commit()
    except banker_ledger.GameEngineError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return await _broadcast_state(db, game)


def _get_pending_request(db: Session, game, transaction_id: str, requesting_player: Player) -> Transaction:
    txn = db.get(Transaction, transaction_id)
    if not txn or txn.game_id != game.id:
        raise HTTPException(status_code=404, detail="Request not found")
    if txn.from_player_id != requesting_player.id:
        raise HTTPException(status_code=403, detail="Only the paying player can respond to this request")
    return txn


@router.post("/{transaction_id}/confirm", response_model=schemas.GameStateOut)
async def confirm_transfer(
    code: str,
    transaction_id: str,
    db: Session = Depends(get_db),
    x_player_id: str = Header(...),
    x_player_token: str = Header(...),
):
    game = auth.get_game_or_404(db, code)
    player = auth.require_player(db, game, x_player_id, x_player_token)
    txn = _get_pending_request(db, game, transaction_id, player)

    try:
        digital_transfer.confirm(db, game, txn=txn)
        db.commit()
    except banker_ledger.GameEngineError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return await _broadcast_state(db, game)


@router.post("/{transaction_id}/decline", response_model=schemas.GameStateOut)
async def decline_transfer(
    code: str,
    transaction_id: str,
    db: Session = Depends(get_db),
    x_player_id: str = Header(...),
    x_player_token: str = Header(...),
):
    game = auth.get_game_or_404(db, code)
    player = auth.require_player(db, game, x_player_id, x_player_token)
    txn = _get_pending_request(db, game, transaction_id, player)

    try:
        digital_transfer.decline(db, game, txn=txn)
        db.commit()
    except banker_ledger.GameEngineError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return await _broadcast_state(db, game)
