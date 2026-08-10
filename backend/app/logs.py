from sqlalchemy.orm import Session

from app.models import EventLogEntry


def write_event(
    db: Session,
    *,
    game_id: str,
    kind: str,
    player_ids: list[str] | None = None,
    payload: dict | None = None,
) -> EventLogEntry:
    entry = EventLogEntry(
        game_id=game_id,
        kind=kind,
        player_ids=player_ids or [],
        payload=payload or {},
    )
    db.add(entry)
    db.flush()
    return entry
