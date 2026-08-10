"""Player-to-player trading: cash, properties, and jail-free cards, in any
combination, proposed by one player and accepted/declined by another.

Trades are a durable `Trade` row (not ephemeral JSON on `Game` the way an
auction is) — several can be proposed across a game, need a stable id to
accept/decline/cancel, and stay visible as history afterward, the same
reasoning that makes `Transaction` its own table.
"""

from sqlalchemy.orm import Session

from app import logs
from app.game_engine.money_modes.banker_ledger import GameEngineError, apply_transaction
from app.models import Game, Player, Property, Trade


class TradeError(GameEngineError):
    pass


def _validate_side(db: Session, game: Game, *, player: Player, cash: int, property_ids: list[str], jail_cards: int) -> list[Property]:
    if cash < 0 or jail_cards < 0:
        raise TradeError("Cash and jail-free card counts can't be negative")
    if player.balance < cash:
        raise TradeError(f"{player.name} can't offer {cash} — only has {player.balance}")
    if player.jail_free_cards < jail_cards:
        raise TradeError(f"{player.name} doesn't have {jail_cards} jail-free card(s)")

    properties = []
    for pid in property_ids:
        prop = db.get(Property, pid)
        if not prop or prop.game_id != game.id:
            raise TradeError("Property not found in this game")
        if prop.owner_id != player.id:
            raise TradeError(f"{player.name} doesn't own {prop.name}")
        properties.append(prop)
    return properties


def propose_trade(
    db: Session,
    game: Game,
    *,
    proposer: Player,
    recipient: Player,
    offer_cash: int = 0,
    offer_property_ids: list[str] | None = None,
    offer_jail_cards: int = 0,
    request_cash: int = 0,
    request_property_ids: list[str] | None = None,
    request_jail_cards: int = 0,
) -> Trade:
    if not game.ruleset_json.get("trading_enabled", True):
        raise TradeError("Trading is not enabled for this game")
    if proposer.id == recipient.id:
        raise TradeError("Can't trade with yourself")

    offer_property_ids = offer_property_ids or []
    request_property_ids = request_property_ids or []
    if not any([offer_cash, offer_property_ids, offer_jail_cards, request_cash, request_property_ids, request_jail_cards]):
        raise TradeError("A trade needs to offer or request something")

    _validate_side(db, game, player=proposer, cash=offer_cash, property_ids=offer_property_ids, jail_cards=offer_jail_cards)
    _validate_side(db, game, player=recipient, cash=request_cash, property_ids=request_property_ids, jail_cards=request_jail_cards)

    trade = Trade(
        game_id=game.id,
        proposer_id=proposer.id,
        recipient_id=recipient.id,
        offer_cash=offer_cash,
        offer_property_ids=offer_property_ids,
        offer_jail_cards=offer_jail_cards,
        request_cash=request_cash,
        request_property_ids=request_property_ids,
        request_jail_cards=request_jail_cards,
    )
    db.add(trade)
    db.flush()
    logs.write_event(
        db, game_id=game.id, kind="trade_proposed", player_ids=[proposer.id, recipient.id],
        payload={"trade_id": trade.id, "proposer": proposer.name, "recipient": recipient.name},
    )
    return trade


def respond_to_trade(db: Session, game: Game, *, trade: Trade, accept: bool) -> Trade:
    if trade.status != "pending":
        raise TradeError(f"This trade is already {trade.status}")

    if not accept:
        trade.status = "declined"
        logs.write_event(db, game_id=game.id, kind="trade_declined", player_ids=[trade.proposer_id, trade.recipient_id], payload={"trade_id": trade.id})
        return trade

    proposer = db.get(Player, trade.proposer_id)
    recipient = db.get(Player, trade.recipient_id)

    # Re-validate against *current* state: either side may have spent cash,
    # mortgaged, or given away a property since this trade was proposed.
    # Deliberately doesn't auto-decline the trade on failure here — the
    # router rolls back the whole transaction on any raised error (the same
    # invariant every other endpoint relies on), which would silently wipe
    # a "mark it declined" write anyway. Leave it pending; the proposer or
    # recipient can explicitly cancel/decline it once they see why it failed.
    _validate_side(db, game, player=proposer, cash=trade.offer_cash, property_ids=trade.offer_property_ids, jail_cards=trade.offer_jail_cards)
    _validate_side(db, game, player=recipient, cash=trade.request_cash, property_ids=trade.request_property_ids, jail_cards=trade.request_jail_cards)

    net = trade.offer_cash - trade.request_cash
    if net > 0:
        apply_transaction(db, game, from_player=proposer, to_player=recipient, amount=net, reason=f"trade:{trade.id}", created_by_player_id=proposer.id)
    elif net < 0:
        apply_transaction(db, game, from_player=recipient, to_player=proposer, amount=-net, reason=f"trade:{trade.id}", created_by_player_id=recipient.id)

    for pid in trade.offer_property_ids:
        db.get(Property, pid).owner_id = recipient.id
    for pid in trade.request_property_ids:
        db.get(Property, pid).owner_id = proposer.id

    proposer.jail_free_cards += trade.request_jail_cards - trade.offer_jail_cards
    recipient.jail_free_cards += trade.offer_jail_cards - trade.request_jail_cards

    trade.status = "accepted"
    logs.write_event(
        db, game_id=game.id, kind="trade_accepted", player_ids=[proposer.id, recipient.id],
        payload={"trade_id": trade.id, "proposer": proposer.name, "recipient": recipient.name},
    )
    return trade


def cancel_trade(db: Session, game: Game, *, trade: Trade) -> Trade:
    if trade.status != "pending":
        raise TradeError(f"This trade is already {trade.status}")
    trade.status = "cancelled"
    logs.write_event(db, game_id=game.id, kind="trade_cancelled", player_ids=[trade.proposer_id, trade.recipient_id], payload={"trade_id": trade.id})
    return trade
