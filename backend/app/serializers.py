from sqlalchemy.orm import Session

from app import schemas
from app.models import EventLogEntry, Game


def serialize_game_state(db: Session, game: Game) -> schemas.GameStateOut:
    recent = (
        db.query(EventLogEntry)
        .filter(EventLogEntry.game_id == game.id)
        .order_by(EventLogEntry.created_at.desc())
        .limit(100)
        .all()
    )
    recent.reverse()

    return schemas.GameStateOut(
        id=game.id,
        code=game.code,
        name=game.name,
        status=game.status,
        money_mode=game.money_mode,
        banker_mode=game.banker_mode,
        ruleset=game.ruleset_json,
        players=[schemas.PlayerOut.model_validate(p) for p in sorted(game.players, key=lambda p: p.joined_at)],
        properties=[schemas.PropertyOut.model_validate(p) for p in sorted(game.properties, key=lambda p: p.space_index)],
        recent_log=[schemas.EventLogOut.model_validate(e) for e in recent],
    )
