from sqlalchemy.orm import Session

from app import logs
from app.game_engine.events.base import EventOutcome
from app.game_engine.money_modes.banker_ledger import apply_pass_go, apply_transaction
from app.models import Game, Player


def apply_event_outcome(db: Session, game: Game, *, player: Player, outcome: EventOutcome) -> dict:
    other_players = [p for p in game.players if p.id != player.id and p.status == "active"]
    result = {"kind": outcome.kind, "text": outcome.text, "amount": outcome.amount, "transaction_ids": []}

    if outcome.kind == "bank_pays":
        txn = apply_transaction(
            db, game, from_player=None, to_player=player, amount=outcome.amount, reason=outcome.text, created_by_player_id=player.id
        )
        result["transaction_ids"] = [txn.id]

    elif outcome.kind == "pay_bank":
        txn = apply_transaction(
            db, game, from_player=player, to_player=None, amount=outcome.amount, reason=outcome.text,
            created_by_player_id=player.id, feeds_free_parking_pot=True,
        )
        result["transaction_ids"] = [txn.id]

    elif outcome.kind == "pay_each_player":
        for other in other_players:
            txn = apply_transaction(
                db, game, from_player=player, to_player=other, amount=outcome.amount, reason=outcome.text, created_by_player_id=player.id
            )
            result["transaction_ids"].append(txn.id)

    elif outcome.kind == "collect_each_player":
        for other in other_players:
            txn = apply_transaction(
                db, game, from_player=other, to_player=player, amount=outcome.amount, reason=outcome.text, created_by_player_id=player.id
            )
            result["transaction_ids"].append(txn.id)

    elif outcome.kind == "jail_free":
        player.jail_free_cards += 1
        logs.write_event(db, game_id=game.id, kind="jail_free_card", player_ids=[player.id], payload={"text": outcome.text})

    elif outcome.kind == "pass_go":
        txn = apply_pass_go(db, game, player=player)
        result["amount"] = txn.amount
        result["transaction_ids"] = [txn.id]

    return result
