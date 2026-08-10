"""Mortgage / unmortgage — the `mortgaged` field and its blocking logic
(rent disabled, group-wide house-building blocked) have existed since
Phase 1, but nothing ever set it until now."""

from sqlalchemy.orm import Session

from app import logs
from app.game_engine import board_engine
from app.game_engine.money_modes.banker_ledger import GameEngineError, apply_transaction
from app.models import Game, Player, Property, Transaction


class MortgageError(GameEngineError):
    pass


def mortgage_property(db: Session, game: Game, *, player: Player, property_: Property) -> Transaction:
    if property_.owner_id != player.id:
        raise MortgageError(f"{player.name} does not own {property_.name}")
    if property_.mortgaged:
        raise MortgageError(f"{property_.name} is already mortgaged")
    if property_.houses > 0:
        raise MortgageError(f"Sell the upgrades on {property_.name} before mortgaging it")

    tile = board_engine.tile_at(db, game.board_id, property_.space_index)
    value = board_engine.mortgage_value_for(tile, game.ruleset_json)

    txn = apply_transaction(
        db, game, from_player=None, to_player=player, amount=value,
        reason=f"mortgage:{property_.name}", created_by_player_id=player.id,
    )
    property_.mortgaged = True
    db.flush()
    logs.write_event(
        db, game_id=game.id, kind="property_mortgaged", player_ids=[player.id],
        payload={"property_id": property_.id, "property_name": property_.name, "value": value},
    )
    return txn


def unmortgage_property(db: Session, game: Game, *, player: Player, property_: Property) -> Transaction:
    if property_.owner_id != player.id:
        raise MortgageError(f"{player.name} does not own {property_.name}")
    if not property_.mortgaged:
        raise MortgageError(f"{property_.name} is not mortgaged")

    tile = board_engine.tile_at(db, game.board_id, property_.space_index)
    value = board_engine.mortgage_value_for(tile, game.ruleset_json)
    interest = game.ruleset_json.get("mortgage_interest", 0.1)
    payoff = round(value * (1 + interest))

    if player.balance < payoff:
        raise MortgageError(f"{player.name} cannot afford the payoff ({payoff})")

    txn = apply_transaction(
        db, game, from_player=player, to_player=None, amount=payoff,
        reason=f"unmortgage:{property_.name}", created_by_player_id=player.id,
    )
    property_.mortgaged = False
    db.flush()
    logs.write_event(
        db, game_id=game.id, kind="property_unmortgaged", player_ids=[player.id],
        payload={"property_id": property_.id, "property_name": property_.name, "payoff": payoff},
    )
    return txn
