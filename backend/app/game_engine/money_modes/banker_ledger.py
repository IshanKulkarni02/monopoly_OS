"""Core transaction + auto-banker logic, shared by every money mode.

`banker_ledger` (a human, or the auto-banker, logs a transaction and
balances update immediately) is the base case every other money mode reuses:
`cash_counter` is the same flow with a simpler UI, and `digital_transfer`'s
immediate "send" also calls straight through to `apply_transaction` — only
its request/confirm/decline flow (see `money_modes/digital_transfer.py`)
needs the extra pending-then-settle step.
"""

from sqlalchemy.orm import Session

from app import logs
from app.game_engine import board_data, challenges, inflation
from app.models import Game, Player, Property, Transaction


class GameEngineError(Exception):
    pass


def get_property_by_space(db: Session, game_id: str, space_index: int) -> Property | None:
    return (
        db.query(Property)
        .filter(Property.game_id == game_id, Property.space_index == space_index)
        .first()
    )


def _owned_count_by_type(db: Session, game_id: str, owner_id: str, space_type: str) -> int:
    owned = db.query(Property).filter(Property.game_id == game_id, Property.owner_id == owner_id).all()
    return sum(1 for p in owned if board_data.space_by_index(p.space_index)["type"] == space_type)


def apply_transaction(
    db: Session,
    game: Game,
    *,
    from_player: Player | None,
    to_player: Player | None,
    amount: int,
    reason: str,
    created_by_player_id: str | None,
    txn_type: str | None = None,
) -> Transaction:
    if amount < 0:
        raise GameEngineError("Transaction amount must be non-negative")
    if from_player is not None and from_player.balance < amount:
        raise GameEngineError(f"{from_player.name} does not have enough cash for this transaction")

    if from_player is not None:
        from_player.balance -= amount
    if to_player is not None:
        to_player.balance += amount

    txn = Transaction(
        game_id=game.id,
        type=txn_type or game.money_mode,
        from_player_id=from_player.id if from_player else None,
        to_player_id=to_player.id if to_player else None,
        amount=amount,
        reason=reason,
        created_by_player_id=created_by_player_id,
    )
    db.add(txn)
    db.flush()

    logs.write_event(
        db,
        game_id=game.id,
        kind="transaction",
        player_ids=[p for p in (from_player.id if from_player else None, to_player.id if to_player else None) if p],
        payload={
            "transaction_id": txn.id,
            "from": from_player.name if from_player else "Bank",
            "to": to_player.name if to_player else "Bank",
            "amount": amount,
            "reason": reason,
        },
    )
    return txn


def apply_purchase(db: Session, game: Game, *, player: Player, property_: Property) -> dict:
    """Buy `property_` for `player`, honoring the challenge-before-buy twist
    if it's enabled. Returns a result dict rather than just the Transaction
    since a failed challenge is a normal, non-error outcome (property stays
    unowned, no money moves) that the caller still needs to report.
    """
    if property_.owner_id is not None:
        raise GameEngineError(f"{property_.name} is already owned")
    if property_.mortgaged:
        raise GameEngineError(f"{property_.name} is mortgaged and cannot be purchased")

    price = inflation.inflated_amount(game, property_.price, "price")
    if player.balance < price:
        raise GameEngineError(f"{player.name} cannot afford {property_.name}")

    challenge_cfg = game.ruleset_json.get("challenge_before_buy", {})
    challenge_result = None
    if challenge_cfg.get("enabled"):
        passed, roll = challenges.run_challenge(game)
        challenge_result = {"type": challenge_cfg.get("type", "coin_flip"), "roll": roll, "passed": passed}
        if not passed:
            logs.write_event(
                db,
                game_id=game.id,
                kind="challenge_failed",
                player_ids=[player.id],
                payload={"property_id": property_.id, "property_name": property_.name, **challenge_result},
            )
            return {"purchased": False, "challenge": challenge_result, "transaction_id": None}

    txn = apply_transaction(
        db,
        game,
        from_player=player,
        to_player=None,
        amount=price,
        reason=f"purchase:{property_.name}",
        created_by_player_id=player.id,
    )
    property_.owner_id = player.id
    db.flush()

    logs.write_event(
        db,
        game_id=game.id,
        kind="purchase",
        player_ids=[player.id],
        payload={"property_id": property_.id, "property_name": property_.name, "price": price},
    )
    return {"purchased": True, "challenge": challenge_result, "transaction_id": txn.id}


def apply_pass_go(db: Session, game: Game, *, player: Player) -> Transaction:
    bonus = game.ruleset_json.get("pass_go_bonus", 200)
    txn = apply_transaction(
        db,
        game,
        from_player=None,
        to_player=player,
        amount=bonus,
        reason="pass_go",
        created_by_player_id=player.id,
    )
    inflation.on_pass_go(game)
    return txn


def apply_auto_banker_landing(
    db: Session,
    game: Game,
    *,
    player: Player,
    space_index: int,
    dice_roll: int | None = None,
) -> dict:
    """Compute and apply what happens when `player` declares they landed on
    `space_index`, without a human doing any math. Returns a dict describing
    the outcome so the frontend can show the right message/prompt.
    """
    space = board_data.space_by_index(space_index)
    space_type = space["type"]

    if space_type in board_data.PURCHASABLE_TYPES:
        prop = get_property_by_space(db, game.id, space_index)
        if prop is None:
            return {"outcome": "error", "message": "Property not found for this game"}
        if prop.owner_id is None:
            return {"outcome": "purchasable", "property_id": prop.id, "property_name": prop.name, "price": prop.price}
        if prop.owner_id == player.id:
            return {"outcome": "own_property", "property_id": prop.id}
        if prop.mortgaged:
            return {"outcome": "mortgaged_no_rent", "property_id": prop.id}

        owner = db.get(Player, prop.owner_id)

        if space_type == "property":
            rent = space["rent"][prop.houses]
        elif space_type == "railroad":
            count = _owned_count_by_type(db, game.id, owner.id, "railroad")
            rent = board_data.RAILROAD_RENTS[min(count, 4) - 1]
        elif space_type == "utility":
            if dice_roll is None:
                return {
                    "outcome": "needs_manual",
                    "message": "Utility rent depends on the dice roll — enter it or have the banker log this manually.",
                }
            count = _owned_count_by_type(db, game.id, owner.id, "utility")
            rent = board_data.UTILITY_MULTIPLIERS[min(count, 2) - 1] * dice_roll
        else:
            rent = 0

        rent = inflation.inflated_amount(game, rent, "rent")
        txn = apply_transaction(
            db,
            game,
            from_player=player,
            to_player=owner,
            amount=rent,
            reason=f"rent:{space['name']}",
            created_by_player_id=player.id,
        )
        return {"outcome": "rent_paid", "transaction_id": txn.id, "amount": rent, "paid_to": owner.name}

    if space_type == "tax":
        tax_amount = inflation.inflated_amount(game, space["tax_amount"], "tax")
        txn = apply_transaction(
            db,
            game,
            from_player=player,
            to_player=None,
            amount=tax_amount,
            reason=f"tax:{space['name']}",
            created_by_player_id=player.id,
        )
        return {"outcome": "tax_paid", "transaction_id": txn.id, "amount": tax_amount}

    if space_type == "go":
        txn = apply_pass_go(db, game, player=player)
        return {"outcome": "go_bonus", "transaction_id": txn.id, "amount": txn.amount}

    return {"outcome": "no_action", "space_type": space_type}
