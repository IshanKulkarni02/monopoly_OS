from sqlalchemy.orm import Session

from app import schemas
from app.models import EventLogEntry, Game, Trade, Transaction


def serialize_game_state(db: Session, game: Game) -> schemas.GameStateOut:
    recent = (
        db.query(EventLogEntry)
        .filter(EventLogEntry.game_id == game.id)
        .order_by(EventLogEntry.created_at.desc())
        .limit(100)
        .all()
    )
    recent.reverse()

    pending_transfers = (
        db.query(Transaction)
        .filter(Transaction.game_id == game.id, Transaction.status == "pending")
        .order_by(Transaction.created_at.asc())
        .all()
    )

    pending_trades = (
        db.query(Trade)
        .filter(Trade.game_id == game.id, Trade.status == "pending")
        .order_by(Trade.created_at.asc())
        .all()
    )

    return schemas.GameStateOut(
        id=game.id,
        code=game.code,
        name=game.name,
        status=game.status,
        money_mode=game.money_mode,
        banker_mode=game.banker_mode,
        play_mode=game.play_mode,
        board=schemas.BoardDetailOut.model_validate(game.board),
        ruleset=game.ruleset_json,
        inflation_multiplier=game.inflation_multiplier,
        round_number=game.round_number,
        free_parking_pot_amount=game.free_parking_pot_amount,
        turn_order=game.turn_order,
        current_turn_player_id=game.current_turn_player_id,
        pending_turn_order_rolls=game.pending_turn_order_rolls,
        players=[schemas.PlayerOut.model_validate(p) for p in sorted(game.players, key=lambda p: p.joined_at)],
        properties=[schemas.PropertyOut.model_validate(p) for p in sorted(game.properties, key=lambda p: p.space_index)],
        recent_log=[schemas.EventLogOut.model_validate(e) for e in recent],
        pending_transfers=[schemas.TransactionOut.model_validate(t) for t in pending_transfers],
        active_auction=game.active_auction,
        pending_trades=[schemas.TradeOut.model_validate(t) for t in pending_trades],
    )
