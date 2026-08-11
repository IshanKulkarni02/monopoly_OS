from sqlalchemy.orm import Session

from app import logs
from app.game_engine import board_engine
from app.game_engine.events.base import EventOutcome
from app.game_engine.money_modes.banker_ledger import apply_auto_banker_landing, apply_pass_go, apply_transaction
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

    elif outcome.kind in ("move_forward", "move_backward", "move_to"):
        result["landing"] = _apply_move(db, game, player=player, outcome=outcome)

    elif outcome.kind == "lose_turn":
        player.skip_next_turn = True
        logs.write_event(db, game_id=game.id, kind="mystery_lose_turn", player_ids=[player.id], payload={"text": outcome.text})

    elif outcome.kind == "extra_turn":
        player.extra_turns += 1
        logs.write_event(db, game_id=game.id, kind="mystery_extra_turn", player_ids=[player.id], payload={"text": outcome.text})

    return result


def _apply_move(db: Session, game: Game, *, player: Player, outcome: EventOutcome) -> dict:
    """Shared by move_forward/move_backward/move_to — moves the player and
    resolves landing at the destination, same engine every other movement
    path uses. Doesn't chain into a second mystery draw if the destination
    is itself a mystery tile, to keep this from ever looping."""
    size = board_engine.board_size(db, game.board_id)
    old_position = player.position

    if outcome.kind == "move_forward":
        new_position = (old_position + outcome.amount) % size
        passed_go = old_position + outcome.amount >= size
    elif outcome.kind == "move_backward":
        new_position = (old_position - outcome.amount) % size
        passed_go = False
    else:  # move_to
        new_position = (outcome.target_position or 0) % size
        passed_go = new_position < old_position

    player.position = new_position
    if passed_go and new_position != 0:
        apply_pass_go(db, game, player=player)

    return apply_auto_banker_landing(db, game, player=player, space_index=new_position)
