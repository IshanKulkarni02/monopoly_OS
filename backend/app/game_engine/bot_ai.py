"""AI opponents for solo virtual play.

A bot's whole turn is driven through the exact same functions a human
player's client calls — `turn_engine.roll_dice`, `banker_ledger.apply_purchase`,
`houses.build_house`, `turn_engine.end_turn` — so a bot can never do anything
a human couldn't have done by clicking the same buttons. Only the *decisions*
(cash buffer to keep, whether to buy, which house to build) are bot-specific.
"""

from sqlalchemy.orm import Session

from app.game_engine import board_data, houses, turn_engine
from app.game_engine.money_modes import banker_ledger
from app.models import Game, Player, Property

CASH_BUFFER = 100  # a bot never spends itself down below this


def _decide_jail_choice(player: Player) -> dict:
    if player.jail_free_cards > 0:
        return {"use_jail_free_card": True, "pay_fine": False}
    if player.balance - board_data.JAIL_FINE >= CASH_BUFFER:
        return {"pay_fine": True, "use_jail_free_card": False}
    return {"use_jail_free_card": False, "pay_fine": False}  # try rolling out instead


def _maybe_build_house(db: Session, game: Game, player: Player) -> None:
    """Build at most one house per turn, on the cheapest eligible group, so a
    bot's turn stays bounded and doesn't require deeper strategy."""
    owned = db.query(Property).filter(Property.game_id == game.id, Property.owner_id == player.id).all()
    colors = {board_data.space_by_index(p.space_index).get("color") for p in owned}
    colors.discard(None)

    for color in sorted(colors, key=lambda c: board_data.HOUSE_COSTS.get(c, 0)):
        if not houses.owns_full_color_group(db, game.id, player.id, color):
            continue
        group = [p for p in owned if board_data.space_by_index(p.space_index).get("color") == color]
        if any(p.mortgaged for p in group):
            continue
        cost = board_data.HOUSE_COSTS[color]
        if player.balance - cost < CASH_BUFFER:
            continue
        min_houses = min(p.houses for p in group)
        candidate = next((p for p in group if p.houses == min_houses and p.houses < 5), None)
        if candidate is None:
            continue
        try:
            houses.build_house(db, game, player=player, property_=candidate)
            return  # one house per turn is plenty
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
