"""Upgrade building — houses/hotels in the classic ruleset, or whatever a
board's own `upgrade_costs` / `rent_table` define for its property tiles.

Generic over any board: eligibility, cost, and the upgrade cap all come from
the landed-on tile's own group and `upgrade_costs`, not a hardcoded
color-to-cost map — the validation shape (own it, not mortgaged, group
complete, even build-out, can afford it) is what stayed constant when this
stopped being classic-Monopoly-only.
"""

from sqlalchemy.orm import Session

from app import logs
from app.game_engine import board_engine
from app.game_engine.money_modes.banker_ledger import GameEngineError, apply_transaction
from app.models import Game, Player, Property, Transaction


class HouseError(GameEngineError):
    pass


def _group_properties(db: Session, game_id: str, group_id: str | None) -> list[Property]:
    if group_id is None:
        return []
    positions = board_engine.group_tile_positions(db, group_id)
    return db.query(Property).filter(Property.game_id == game_id, Property.space_index.in_(positions)).all()


def owns_full_group(db: Session, game_id: str, player_id: str, group_id: str | None) -> bool:
    return board_engine.owns_full_group(db, game_id, player_id, group_id)


def _property_tile(db: Session, game: Game, property_: Property):
    tile = board_engine.tile_at(db, game.board_id, property_.space_index)
    if tile.kind != "property" or not tile.upgrade_costs:
        raise HouseError(f"{property_.name} cannot have upgrades built on it")
    return tile


def build_house(db: Session, game: Game, *, player: Player, property_: Property) -> Transaction:
    tile = _property_tile(db, game, property_)
    if property_.owner_id != player.id:
        raise HouseError(f"{player.name} does not own {property_.name}")
    if property_.mortgaged:
        raise HouseError(f"{property_.name} is mortgaged")

    max_level = board_engine.max_upgrade_level(tile)
    if property_.houses >= max_level:
        raise HouseError(f"{property_.name} is already fully upgraded")

    if game.ruleset_json.get("upgrade_requires_full_group", True) and not owns_full_group(db, game.id, player.id, tile.group_id):
        group_name = tile.group.name if tile.group else "this group"
        raise HouseError(f"{player.name} must own the entire {group_name} group to build here")

    group = _group_properties(db, game.id, tile.group_id) or [property_]
    if any(p.mortgaged for p in group):
        raise HouseError("Cannot build while any property in this group is mortgaged")
    if property_.houses > min(p.houses for p in group):
        raise HouseError("Upgrades must be built evenly across the group")

    cost = tile.upgrade_costs[property_.houses]
    if player.balance < cost:
        raise HouseError(f"{player.name} cannot afford an upgrade here ({cost})")

    label = "hotel" if property_.houses == max_level - 1 else "house"
    txn = apply_transaction(
        db, game,
        from_player=player, to_player=None,
        amount=cost, reason=f"build {label}:{property_.name}",
        created_by_player_id=player.id,
    )
    property_.houses += 1
    db.flush()
    logs.write_event(
        db, game_id=game.id, kind="house_built", player_ids=[player.id],
        payload={"property_id": property_.id, "property_name": property_.name, "houses": property_.houses, "cost": cost},
    )
    return txn


def sell_house(db: Session, game: Game, *, player: Player, property_: Property) -> Transaction:
    tile = _property_tile(db, game, property_)
    if property_.owner_id != player.id:
        raise HouseError(f"{player.name} does not own {property_.name}")
    if property_.houses <= 0:
        raise HouseError(f"{property_.name} has no upgrades to sell")

    group = _group_properties(db, game.id, tile.group_id) or [property_]
    if property_.houses < max(p.houses for p in group):
        raise HouseError("Upgrades must be sold evenly across the group")

    refund = tile.upgrade_costs[property_.houses - 1] // 2
    txn = apply_transaction(
        db, game,
        from_player=None, to_player=player,
        amount=refund, reason=f"sell house:{property_.name}",
        created_by_player_id=player.id,
    )
    property_.houses -= 1
    db.flush()
    logs.write_event(
        db, game_id=game.id, kind="house_sold", player_ids=[player.id],
        payload={"property_id": property_.id, "property_name": property_.name, "houses": property_.houses, "refund": refund},
    )
    return txn
