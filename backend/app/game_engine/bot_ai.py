"""AI opponents for solo virtual play.

A bot's whole turn is driven through the exact same functions a human
player's client calls — `turn_engine.roll_dice`, `banker_ledger.apply_purchase`,
`houses.build_house`, `turn_engine.end_turn` — so a bot can never do anything
a human couldn't have done by clicking the same buttons. Only the *decisions*
(cash buffer to keep, whether to buy, which upgrade to build) are bot-specific.
"""

from sqlalchemy.orm import Session

from app.game_engine import board_engine, houses, turn_engine
from app.game_engine.money_modes import banker_ledger
from app.models import Game, Player, Property

CASH_BUFFER = 100  # a bot never spends itself down below this

# The jail-choice heuristic below is a rough decision, not a payment — it
# doesn't need the live per-game `jail_fine` ruleset value to make a
# reasonable call, so it uses this fixed estimate rather than requiring a
# `game` argument just for this one number.
JAIL_FINE_ESTIMATE = 50


def _decide_jail_choice(player: Player) -> dict:
    if player.jail_free_cards > 0:
        return {"use_jail_free_card": True, "pay_fine": False}
    if player.balance - JAIL_FINE_ESTIMATE >= CASH_BUFFER:
        return {"pay_fine": True, "use_jail_free_card": False}
    return {"use_jail_free_card": False, "pay_fine": False}  # try rolling out instead


def _maybe_build_house(db: Session, game: Game, player: Player) -> None:
    """Build at most one upgrade per turn, on the cheapest eligible group, so
    a bot's turn stays bounded and doesn't require deeper strategy."""
    owned = db.query(Property).filter(Property.game_id == game.id, Property.owner_id == player.id).all()
    if not owned:
        return
    tiles_by_property = {p.id: board_engine.tile_at(db, game.board_id, p.space_index) for p in owned}
    group_ids = {t.group_id for t in tiles_by_property.values() if t.group_id and t.upgrade_costs}

    def cheapest_upgrade_cost(group_id: str) -> int:
        return next(
            (t.upgrade_costs[0] for t in tiles_by_property.values() if t.group_id == group_id and t.upgrade_costs),
            0,
        )

    for group_id in sorted(group_ids, key=cheapest_upgrade_cost):
        if not houses.owns_full_group(db, game.id, player.id, group_id):
            continue
        group = [p for p in owned if tiles_by_property[p.id].group_id == group_id]
        if any(p.mortgaged for p in group):
            continue
        max_level = board_engine.max_upgrade_level(tiles_by_property[group[0].id])
        min_houses = min(p.houses for p in group)
        candidate = next((p for p in group if p.houses == min_houses and p.houses < max_level), None)
        if candidate is None:
            continue
        cost = tiles_by_property[candidate.id].upgrade_costs[candidate.houses]
        if player.balance - cost < CASH_BUFFER:
            continue
        try:
            houses.build_house(db, game, player=player, property_=candidate)
            return  # one upgrade per turn is plenty
        except houses.HouseError:
            continue


def play_bot_turn(db: Session, game: Game, *, player: Player) -> dict:
    jail_choice = _decide_jail_choice(player) if player.in_jail else {}
    result = turn_engine.roll_dice(db, game, player=player, **jail_choice)

    landing = result.get("landing") or {}
    if landing.get("outcome") == "purchasable":
        price = landing.get("price", 0)
        if player.balance - price >= CASH_BUFFER:
            prop = db.get(Property, landing["property_id"])
            if prop is not None:
                banker_ledger.apply_purchase(db, game, player=player, property_=prop)

    if result.get("outcome") != "stayed_in_jail":
        _maybe_build_house(db, game, player)
        turn_engine.end_turn(db, game, player=player)

    return result
