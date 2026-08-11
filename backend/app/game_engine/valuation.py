"""Net worth estimation.

Used today just to back the tax system's `percent_assets` formula (spec
§23). A fuller net-worth breakdown (liabilities, end-game scoring) is
planned for the game-lifecycle phase — this stays deliberately minimal
until that phase needs more from it.
"""

from sqlalchemy.orm import Session

from app.game_engine import board_engine
from app.models import Game, Player, Property


def estimate_net_worth(db: Session, game: Game, player: Player) -> int:
    total = player.balance
    props = db.query(Property).filter(Property.game_id == game.id, Property.owner_id == player.id).all()
    for prop in props:
        if prop.mortgaged:
            continue
        total += prop.price
        tile = board_engine.tile_at(db, game.board_id, prop.space_index)
        if tile.upgrade_costs and prop.houses:
            total += sum(tile.upgrade_costs[: prop.houses])
    return total
