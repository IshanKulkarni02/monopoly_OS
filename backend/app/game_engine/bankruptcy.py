"""Bankruptcy: liquidate everything a player has, pay a creditor (or the
bank) as much as that raises, and eliminate the player from play.

Deliberately a *manual* action (an explicit "declare bankruptcy to ___"
call), not something `apply_transaction` triggers automatically when a
payment fails. Real Monopoly lets a player attempt to scrape together cash
first (sell houses, mortgage properties, even try to arrange a trade) before
giving up — modeling that as a forced auto-liquidation-and-retry inside the
payment call itself would mean every rent/tax/fine payment could silently
cascade into eliminating a player, which is a much bigger behavior change
than this phase needs. Instead: a mandatory payment that can't be covered
still just fails with `InsufficientFundsError` (unchanged), and the player
(or the host on their behalf, or `bots.py` for a bot) explicitly declares
bankruptcy against that same creditor as a separate, deliberate step.
"""

from sqlalchemy.orm import Session

from app import logs
from app.game_engine import board_engine
from app.game_engine.money_modes.banker_ledger import GameEngineError, apply_transaction
from app.game_engine.turn_engine import _next_active_player_id
from app.models import Game, Player, Property


class BankruptcyError(GameEngineError):
    pass


def declare_bankruptcy(db: Session, game: Game, *, player: Player, creditor: Player | None) -> dict:
    if player.status == "bankrupt":
        raise BankruptcyError(f"{player.name} is already bankrupt")
    if creditor is not None and creditor.id == player.id:
        raise BankruptcyError("A player can't go bankrupt to themselves")

    properties = db.query(Property).filter(Property.game_id == game.id, Property.owner_id == player.id).all()

    house_refund = 0
    for prop in properties:
        if prop.houses <= 0:
            continue
        tile = board_engine.tile_at(db, game.board_id, prop.space_index)
        for level in range(prop.houses, 0, -1):
            house_refund += tile.upgrade_costs[level - 1] // 2
        prop.houses = 0
    if house_refund:
        apply_transaction(
            db, game, from_player=None, to_player=player, amount=house_refund,
            reason="bankruptcy liquidation: sold all upgrades", created_by_player_id=player.id,
        )

    mortgage_proceeds = 0
    for prop in properties:
        if prop.mortgaged:
            continue
        tile = board_engine.tile_at(db, game.board_id, prop.space_index)
        mortgage_proceeds += board_engine.mortgage_value_for(tile, game.ruleset_json)
        prop.mortgaged = True
    if mortgage_proceeds:
        apply_transaction(
            db, game, from_player=None, to_player=player, amount=mortgage_proceeds,
            reason="bankruptcy liquidation: mortgaged all properties", created_by_player_id=player.id,
        )

    payout = player.balance
    if payout > 0:
        apply_transaction(
            db, game, from_player=player, to_player=creditor, amount=payout,
            reason=f"bankruptcy payout to {creditor.name if creditor else 'the bank'}",
            created_by_player_id=player.id,
        )

    transferred = []
    for prop in properties:
        if creditor is not None:
            prop.owner_id = creditor.id
        else:
            # Repossessed by the bank: reset to fresh/unowned rather than
            # leaving it unowned-but-mortgaged, which nothing could ever buy
            # or unmortgage (unmortgage requires an owner) — a dead tile
            # forever. Simpler and just as valid a house rule as the "buy a
            # mortgaged property from the bank, pay off the mortgage" rule
            # real Monopoly has, which this engine doesn't implement.
            prop.owner_id = None
            prop.mortgaged = False
        transferred.append(prop.name)

    player.status = "bankrupt"
    player.balance = 0
    player.denominations = {}
    player.jail_free_cards = 0

    if game.current_turn_player_id == player.id:
        next_id = _next_active_player_id(db, game, after_player_id=player.id)
        game.current_turn_player_id = None if next_id == player.id else next_id

    logs.write_event(
        db, game_id=game.id, kind="bankruptcy",
        player_ids=[player.id, creditor.id] if creditor else [player.id],
        payload={
            "player": player.name,
            "creditor": creditor.name if creditor else "the bank",
            "paid": payout,
            "properties_transferred": transferred,
        },
    )
    return {
        "player_id": player.id,
        "creditor_player_id": creditor.id if creditor else None,
        "paid": payout,
        "properties_transferred": transferred,
    }
