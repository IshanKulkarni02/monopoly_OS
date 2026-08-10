"""UPI-style cashless money mode: players move money themselves instead of a
banker logging it for them.

- `send`: I'm paying my own money out — no confirmation needed, applies
  immediately (reuses `banker_ledger.apply_transaction`).
- `request` / `confirm` / `decline`: I'm asking someone else to pay me —
  money only moves once *they* confirm, since only the paying side can
  authorize cash leaving their account.
"""

from sqlalchemy.orm import Session

from app import logs
from app.game_engine.money_modes.banker_ledger import GameEngineError, apply_transaction
from app.models import Game, Player, Transaction


def send(db: Session, game: Game, *, sender: Player, to_player: Player, amount: int, reason: str) -> Transaction:
    if sender.id == to_player.id:
        raise GameEngineError("Cannot send money to yourself")
    return apply_transaction(
        db,
        game,
        from_player=sender,
        to_player=to_player,
        amount=amount,
        reason=reason or "transfer",
        created_by_player_id=sender.id,
        txn_type="digital_transfer",
    )


def request(db: Session, game: Game, *, requester: Player, from_player: Player, amount: int, reason: str) -> Transaction:
    if requester.id == from_player.id:
        raise GameEngineError("Cannot request money from yourself")
    if amount < 0:
        raise GameEngineError("Amount must be non-negative")

    txn = Transaction(
        game_id=game.id,
        type="digital_transfer",
        from_player_id=from_player.id,
        to_player_id=requester.id,
        amount=amount,
        reason=reason or "request",
        created_by_player_id=requester.id,
        status="pending",
    )
    db.add(txn)
    db.flush()
    logs.write_event(
        db,
        game_id=game.id,
        kind="transfer_requested",
        player_ids=[requester.id, from_player.id],
        payload={
            "transaction_id": txn.id,
            "requester": requester.name,
            "from": from_player.name,
            "amount": amount,
            "reason": txn.reason,
        },
    )
    return txn


def confirm(db: Session, game: Game, *, txn: Transaction) -> Transaction:
    if txn.status != "pending":
        raise GameEngineError("This request is no longer pending")
    from_player = db.get(Player, txn.from_player_id)
    to_player = db.get(Player, txn.to_player_id)
    if from_player.balance < txn.amount:
        raise GameEngineError(f"{from_player.name} does not have enough cash to confirm this")

    from_player.balance -= txn.amount
    to_player.balance += txn.amount
    txn.status = "confirmed"
    db.flush()

    logs.write_event(
        db,
        game_id=game.id,
        kind="transaction",
        player_ids=[from_player.id, to_player.id],
        payload={
            "transaction_id": txn.id,
            "from": from_player.name,
            "to": to_player.name,
            "amount": txn.amount,
            "reason": txn.reason,
        },
    )
    return txn


def decline(db: Session, game: Game, *, txn: Transaction) -> Transaction:
    if txn.status != "pending":
        raise GameEngineError("This request is no longer pending")
    txn.status = "declined"
    db.flush()
    logs.write_event(
        db,
        game_id=game.id,
        kind="transfer_declined",
        player_ids=[p for p in (txn.from_player_id, txn.to_player_id) if p],
        payload={"transaction_id": txn.id, "amount": txn.amount, "reason": txn.reason},
    )
    return txn
