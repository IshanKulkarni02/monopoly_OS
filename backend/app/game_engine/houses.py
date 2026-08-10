"""House/hotel building on monopolized color groups.

`Property.houses` and the six-entry rent tables in `board_data.py` have
existed since Phase 1 (rent already looks up `rent[houses]`) — this module
is what actually lets a player move that number, honoring the standard
rules: must own the whole color group, houses go on evenly, and a
mortgaged property anywhere in the group blocks building.
"""

from sqlalchemy.orm import Session

from app import logs
from app.game_engine import board_data
from app.game_engine.money_modes.banker_ledger import apply_transaction
from app.models import Game, Player, Property, Transaction


class HouseError(Exception):
    pass


def _group_properties(db: Session, game_id: str, color: str) -> list[Property]:
    space_indices = [s["index"] for s in board_data.spaces_in_color_group(color)]
    return db.query(Property).filter(Property.game_id == game_id, Property.space_index.in_(space_indices)).all()


def owns_full_color_group(db: Session, game_id: str, player_id: str, color: str) -> bool:
    group = _group_properties(db, game_id, color)
    return bool(group) and all(p.owner_id == player_id for p in group)


def _property_color(property_: Property) -> str:
    space = board_data.space_by_index(property_.space_index)
    color = space.get("color")
    if space["type"] != "property" or not color:
        raise HouseError(f"{property_.name} cannot have houses built on it")
    return color


def build_house(db: Session, game: Game, *, player: Player, property_: Property) -> Transaction:
    color = _property_color(property_)
    if property_.owner_id != player.id:
        raise HouseError(f"{player.name} does not own {property_.name}")
    if property_.mortgaged:
        raise HouseError(f"{property_.name} is mortgaged")
    if property_.houses >= 5:
        raise HouseError(f"{property_.name} already has a hotel")
    if not owns_full_color_group(db, game.id, player.id, color):
        raise HouseError(f"{player.name} must own the entire {color.replace('_', ' ')} group to build here")

    group = _group_properties(db, game.id, color)
    if any(p.mortgaged for p in group):
        raise HouseError("Cannot build while any property in this color group is mortgaged")
    if property_.houses > min(p.houses for p in group):
        raise HouseError("Houses must be built evenly across the color group")

    cost = board_data.HOUSE_COSTS[color]
    if player.balance < cost:
        raise HouseError(f"{player.name} cannot afford a house here ({cost})")

    label = "hotel" if property_.houses == 4 else "house"
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
    color = _property_color(property_)
    if property_.owner_id != player.id:
        raise HouseError(f"{player.name} does not own {property_.name}")
    if property_.houses <= 0:
        raise HouseError(f"{property_.name} has no houses to sell")

    group = _group_properties(db, game.id, color)
    if property_.houses < max(p.houses for p in group):
        raise HouseError("Houses must be sold evenly across the color group")

    refund = board_data.HOUSE_COSTS[color] // 2
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
