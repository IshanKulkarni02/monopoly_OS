"""Net worth estimation.

Backs the tax system's `percent_assets` formula (spec §23) and, since
Phase 6, the `PlayerOut.net_worth` field every player list shows — a quick
"who's winning" glance without a dedicated statistics view (that's Phase 7).
"""

from sqlalchemy.orm import Session

from app.game_engine import board_engine
from app.models import Game, Player, Property


def estimate_net_worth(db: Session, game: Game, player: Player) -> int:
    total = player.balance
    props = db.query(Property).filter(Property.game_id == game.id, Property.owner_id == player.id).all()
    for prop in props:
        tile = board_engine.tile_at(db, game.board_id, prop.space_index)
        if prop.mortgaged:
            # Still worth something encumbered — what you'd get back by
            # unmortgaging and reselling, not the zero a skipped property
            # implied before. Matches how a mortgaged property is valued
            # for a `percent_assets` tax charge or an at-a-glance standings
            # list: it's collateral, not nothing.
            total += board_engine.mortgage_value_for(tile, game.ruleset_json)
            continue
        total += prop.price
        if tile.upgrade_costs and prop.houses:
            total += sum(tile.upgrade_costs[: prop.houses])
    return total
