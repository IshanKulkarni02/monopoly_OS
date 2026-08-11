"""Auctions: when a property goes unsold (a player lands on it and doesn't
buy), any active player — including the one who declined — can bid on it.
At most one auction runs at a time per game, state lives in
`Game.active_auction` (empty dict = none active), the same "ephemeral,
resolve-and-clear JSON on Game" shape `pending_turn_order_rolls` already
uses for a similar single-flight, multi-step ceremony.

Resolution rule: once every eligible player except the current top bidder
has passed, the top bidder wins at their bid. If everyone passes before
anyone ever bids, the auction fails — the property stays unowned (matches
the real rule: an unsold auction doesn't force a sale).
"""

from sqlalchemy.orm import Session

from app import logs
from app.game_engine.money_modes.banker_ledger import GameEngineError, apply_transaction
from app.models import Game, Player, Property


class AuctionError(GameEngineError):
    pass


def start_auction(db: Session, game: Game, *, property_: Property, started_by: Player) -> dict:
    if not game.ruleset_json.get("auction_enabled"):
        raise AuctionError("Auctions are not enabled for this game")
    if game.active_auction:
        raise AuctionError("An auction is already in progress")
    if property_.owner_id is not None:
        raise AuctionError(f"{property_.name} is already owned")
    if property_.mortgaged:
        raise AuctionError(f"{property_.name} is mortgaged and can't be auctioned")

    eligible_ids = [p.id for p in game.players if p.status == "active"]
    game.active_auction = {
        "property_id": property_.id,
        "property_name": property_.name,
        "current_bid": 0,
        "current_bidder_id": None,
        "eligible_ids": eligible_ids,
        "passed_ids": [],
        "started_by": started_by.id,
    }
    logs.write_event(
        db, game_id=game.id, kind="auction_started", player_ids=[started_by.id],
        payload={"property_id": property_.id, "property_name": property_.name},
    )
    return game.active_auction


def _min_next_bid(game: Game) -> int:
    auction = game.active_auction
    increment = max(int(game.ruleset_json.get("auction_min_increment", 10)), 1)
    return auction["current_bid"] + increment if auction["current_bidder_id"] else increment


def place_bid(db: Session, game: Game, *, player: Player, amount: int) -> dict:
    auction = game.active_auction
    if not auction:
        raise AuctionError("No auction is in progress")
    if player.id not in auction["eligible_ids"]:
        raise AuctionError(f"{player.name} isn't part of this auction")
    if player.id in auction["passed_ids"]:
        raise AuctionError(f"{player.name} already passed on this auction")

    minimum = _min_next_bid(game)
    if amount < minimum:
        raise AuctionError(f"Bid must be at least {minimum}")
    if player.balance < amount:
        raise AuctionError(f"{player.name} can't cover a bid of {amount}")

    # Never mutate `auction` in place: it's the same dict object SQLAlchemy
    # is tracking as the column's current value, and a plain JSON column
    # (not `MutableDict`-wrapped) only detects a *reassignment*, not an
    # in-place edit — mutating first and reassigning after still loses the
    # write, because by the time SQLAlchemy compares old vs. new it's
    # comparing the (already-mutated) object against itself. Build a fresh
    # dict instead, every time.
    game.active_auction = {**auction, "current_bid": amount, "current_bidder_id": player.id}
    logs.write_event(
        db, game_id=game.id, kind="auction_bid", player_ids=[player.id],
        payload={"property_id": auction["property_id"], "amount": amount},
    )
    return _maybe_resolve(db, game)


def pass_auction(db: Session, game: Game, *, player: Player) -> dict:
    auction = game.active_auction
    if not auction:
        raise AuctionError("No auction is in progress")
    if player.id not in auction["eligible_ids"]:
        raise AuctionError(f"{player.name} isn't part of this auction")
    if player.id == auction["current_bidder_id"]:
        raise AuctionError(f"{player.name} is already the highest bidder")
    if player.id in auction["passed_ids"]:
        return {"outcome": "already_passed"}

    game.active_auction = {**auction, "passed_ids": [*auction["passed_ids"], player.id]}
    logs.write_event(db, game_id=game.id, kind="auction_passed", player_ids=[player.id], payload={"property_id": auction["property_id"]})
    return _maybe_resolve(db, game)


def cancel_auction(db: Session, game: Game, *, actor: Player) -> dict:
    auction = game.active_auction
    if not auction:
        raise AuctionError("No auction is in progress")
    property_name = auction["property_name"]
    game.active_auction = {}
    logs.write_event(
        db, game_id=game.id, kind="auction_cancelled", player_ids=[actor.id],
        payload={"property_name": property_name},
    )
    return {"outcome": "cancelled", "property_name": property_name}


def _maybe_resolve(db: Session, game: Game) -> dict:
    auction = game.active_auction
    bidder_id = auction["current_bidder_id"]
    outstanding = [pid for pid in auction["eligible_ids"] if pid != bidder_id and pid not in auction["passed_ids"]]
    if outstanding:
        return {"outcome": "in_progress", "auction": auction}

    property_ = db.get(Property, auction["property_id"])
    if bidder_id is None:
        # Nobody bid — every eligible player passed. No sale.
        game.active_auction = {}
        logs.write_event(
            db, game_id=game.id, kind="auction_failed", player_ids=[],
            payload={"property_id": property_.id, "property_name": property_.name},
        )
        return {"outcome": "no_sale", "property_id": property_.id, "property_name": property_.name}

    winner = db.get(Player, bidder_id)
    price = auction["current_bid"]
    txn = apply_transaction(
        db, game, from_player=winner, to_player=None, amount=price,
        reason=f"auction win:{property_.name}", created_by_player_id=winner.id,
    )
    property_.owner_id = winner.id
    game.active_auction = {}
    logs.write_event(
        db, game_id=game.id, kind="auction_won", player_ids=[winner.id],
        payload={"property_id": property_.id, "property_name": property_.name, "amount": price},
    )
    return {
        "outcome": "sold",
        "property_id": property_.id,
        "property_name": property_.name,
        "winner_id": winner.id,
        "amount": price,
        "transaction_id": txn.id,
    }
