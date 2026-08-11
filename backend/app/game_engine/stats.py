"""Aggregate statistics for a single game — a snapshot computed on request,
not stored incrementally. Reads straight from `Transaction`/`EventLogEntry`/
`Property` rather than the capped `recent_log` (100 entries) `GameStateOut`
exposes, so totals stay accurate even in a long game.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.game_engine.valuation import estimate_net_worth
from app.models import EventLogEntry, Game, Property, Transaction


def compute_stats(db: Session, game: Game) -> dict:
    players = sorted(game.players, key=lambda p: estimate_net_worth(db, game, p), reverse=True)
    properties_owned = {p.id: 0 for p in players}
    for prop in db.query(Property).filter(Property.game_id == game.id, Property.owner_id.isnot(None)).all():
        properties_owned[prop.owner_id] = properties_owned.get(prop.owner_id, 0) + 1

    player_stats = [
        {
            "player_id": p.id,
            "name": p.name,
            "net_worth": estimate_net_worth(db, game, p),
            "balance": p.balance,
            "properties_owned": properties_owned.get(p.id, 0),
            "status": p.status,
        }
        for p in players
    ]

    transactions = db.query(Transaction).filter(Transaction.game_id == game.id, Transaction.reversed.is_(False)).all()
    total_money_moved = sum(t.amount for t in transactions)

    most_valuable = (
        db.query(Property)
        .filter(Property.game_id == game.id, Property.owner_id.isnot(None))
        .order_by(Property.price.desc())
        .first()
    )
    most_valuable_out = None
    if most_valuable:
        owner = next((p for p in players if p.id == most_valuable.owner_id), None)
        most_valuable_out = {"name": most_valuable.name, "price": most_valuable.price, "owner_name": owner.name if owner else None}

    def _count_events(kind: str) -> int:
        return db.query(EventLogEntry).filter(EventLogEntry.game_id == game.id, EventLogEntry.kind == kind).count()

    duration_seconds = None
    if game.created_at:
        now = datetime.now(timezone.utc)
        created = game.created_at if game.created_at.tzinfo else game.created_at.replace(tzinfo=timezone.utc)
        duration_seconds = (now - created).total_seconds()

    return {
        "players": player_stats,
        "total_transactions": len(transactions),
        "total_money_moved": total_money_moved,
        "most_valuable_property": most_valuable_out,
        "auctions_won": _count_events("auction_won"),
        "trades_completed": _count_events("trade_accepted"),
        "bankruptcies": _count_events("bankruptcy"),
        "houses_built": _count_events("house_built"),
        "game_duration_seconds": duration_seconds,
    }
