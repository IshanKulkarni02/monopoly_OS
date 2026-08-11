"""Core transaction + auto-banker logic, shared by every money mode.

`banker_ledger` (a human, or the auto-banker, logs a transaction and
balances update immediately) is the base case every other money mode reuses:
`cash_counter` is the same flow with a simpler UI, and `digital_transfer`'s
immediate "send" also calls straight through to `apply_transaction` — only
its request/confirm/decline flow (see `money_modes/digital_transfer.py`)
needs the extra pending-then-settle step.

Landing resolution (`apply_auto_banker_landing`) reads tile data from
`board_engine` rather than any hardcoded board — the same function works for
any board shape, any group layout, any rent model.
"""

from sqlalchemy.orm import Session

from app import logs
from app.game_engine import board_engine, challenges, currency, inflation
from app.game_engine.board_engine import BoardTile
from app.game_engine.valuation import estimate_net_worth
from app.models import Game, Player, Property, Transaction


class GameEngineError(Exception):
    pass


def get_property_by_space(db: Session, game_id: str, space_index: int) -> Property | None:
    return (
        db.query(Property)
        .filter(Property.game_id == game_id, Property.space_index == space_index)
        .first()
    )


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
    feeds_free_parking_pot: bool = False,
) -> Transaction:
    if amount < 0:
        raise GameEngineError("Transaction amount must be non-negative")

    currency_cfg = game.ruleset_json.get("currency", {})
    denominations = currency_cfg.get("denominations") or []
    track_notes = bool(currency_cfg.get("track_denominations")) and bool(denominations) and amount > 0

    if track_notes:
        # Rent-with-inflation, tax percentages, and mortgage-plus-interest
        # all routinely land on amounts that aren't a whole number of the
        # smallest note — e.g. 10% interest on a ₹170 mortgage is ₹187, not
        # payable in ₹10 notes. Round to the nearest note *before* touching
        # balance or denominations, once, so the balance change, the note
        # change, and the amount this transaction records all agree — not
        # three different numbers depending which one got rounded first.
        smallest = min(denominations)
        amount = round(amount / smallest) * smallest

    if from_player is not None and from_player.balance < amount:
        raise GameEngineError(f"{from_player.name} does not have enough cash for this transaction")

    if track_notes and from_player is not None:
        try:
            from_player.denominations = currency.pay_to_bank(from_player.denominations, amount, denominations)
        except currency.CurrencyError as exc:
            raise GameEngineError(f"{from_player.name} can't make this exact payment with their notes: {exc}") from exc

    if from_player is not None:
        from_player.balance -= amount
    if to_player is not None:
        to_player.balance += amount
    if to_player is None and feeds_free_parking_pot and game.ruleset_json.get("free_parking_pot"):
        game.free_parking_pot_amount += amount

    if track_notes and to_player is not None:
        to_player.denominations = currency.receive_from_bank(to_player.denominations, amount, denominations)

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


def compute_rent(
    db: Session, game: Game, *, tile: BoardTile, prop: Property, owner: Player, dice_roll: int | None
) -> int | None:
    """Returns the rent owed, or `None` if it can't be computed without a
    dice roll (utility-style tiles)."""
    model = tile.rent_model or "fixed_table"
    table = tile.rent_table or [0]

    if model == "fixed_table":
        level = min(prop.houses, len(table) - 1)
        base = table[level]
        if prop.houses == 0 and board_engine.owns_full_group(db, game.id, owner.id, tile.group_id):
            multiplier = board_engine.group_rent_multiplier(tile.group, game.ruleset_json)
            base = round(base * multiplier)
        return base

    count = max(board_engine.count_owned_in_group(db, game.id, owner.id, tile.group_id), 1)

    if model == "group_count_table":
        return table[min(count, len(table)) - 1]

    if model == "dice_multiplier_table":
        if dice_roll is None:
            return None
        return table[min(count, len(table)) - 1] * dice_roll

    return 0


def compute_tax(db: Session, game: Game, *, tile: BoardTile, player: Player) -> int:
    cfg = tile.tax_config or {}
    formula = cfg.get("formula", "fixed")
    if formula == "percent_cash":
        return round(player.balance * cfg.get("percent", 0.1))
    if formula == "percent_assets":
        return round(estimate_net_worth(db, game, player) * cfg.get("percent", 0.1))
    return cfg.get("amount", 0)


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
    size = board_engine.board_size(db, game.board_id)
    if not (0 <= space_index < size):
        raise GameEngineError(f"Invalid board position {space_index} for this game's board (size {size})")
    tile = board_engine.tile_at(db, game.board_id, space_index)
    kind = tile.kind

    if kind == "property":
        prop = get_property_by_space(db, game.id, space_index)
        if prop is None:
            return {"outcome": "error", "message": "Property not found for this game"}
        if prop.owner_id is None:
            return {"outcome": "purchasable", "property_id": prop.id, "property_name": prop.name, "price": prop.price, "space_type": kind}
        if prop.owner_id == player.id:
            return {"outcome": "own_property", "property_id": prop.id, "space_type": kind}
        if prop.mortgaged:
            return {"outcome": "mortgaged_no_rent", "property_id": prop.id, "space_type": kind}

        owner = db.get(Player, prop.owner_id)
        rent = compute_rent(db, game, tile=tile, prop=prop, owner=owner, dice_roll=dice_roll)
        if rent is None:
            return {
                "outcome": "needs_manual",
                "message": "This rent depends on the dice roll — enter it or have the banker log this manually.",
                "space_type": kind,
            }

        rent = inflation.inflated_amount(game, rent, "rent")
        txn = apply_transaction(
            db, game, from_player=player, to_player=owner, amount=rent,
            reason=f"rent:{tile.name}", created_by_player_id=player.id,
        )
        return {"outcome": "rent_paid", "transaction_id": txn.id, "amount": rent, "paid_to": owner.name, "space_type": kind}

    if kind == "tax":
        tax_amount = compute_tax(db, game, tile=tile, player=player)
        tax_amount = inflation.inflated_amount(game, tax_amount, "tax")
        txn = apply_transaction(
            db, game, from_player=player, to_player=None, amount=tax_amount,
            reason=f"tax:{tile.name}", created_by_player_id=player.id, feeds_free_parking_pot=True,
        )
        return {"outcome": "tax_paid", "transaction_id": txn.id, "amount": tax_amount, "space_type": kind}

    if kind == "go":
        txn = apply_pass_go(db, game, player=player)
        return {"outcome": "go_bonus", "transaction_id": txn.id, "amount": txn.amount, "space_type": kind}

    if kind == "go_to_jail":
        jail_tile = board_engine.first_tile_of_kind(db, game.board_id, "jail")
        if jail_tile is not None:
            player.position = jail_tile.position
        player.in_jail = True
        player.jail_turns = 0
        logs.write_event(db, game_id=game.id, kind="sent_to_jail", player_ids=[player.id], payload={})
        return {"outcome": "sent_to_jail", "space_type": kind}

    if kind == "vacation" and game.ruleset_json.get("free_parking_pot") and game.free_parking_pot_amount:
        payout = game.free_parking_pot_amount
        game.free_parking_pot_amount = 0
        txn = apply_transaction(
            db, game, from_player=None, to_player=player, amount=payout,
            reason="free_parking_pot", created_by_player_id=player.id,
        )
        return {"outcome": "vacation_pot", "transaction_id": txn.id, "amount": payout, "space_type": kind}

    return {"outcome": "no_action", "space_type": kind}
