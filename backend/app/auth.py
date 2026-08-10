from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Game, Player


def get_game_or_404(db: Session, code: str) -> Game:
    game = db.query(Game).filter(Game.code == code.upper()).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


def require_host(game: Game, token: str | None) -> None:
    if not token or token != game.host_token:
        raise HTTPException(status_code=403, detail="Host token required")


def require_player(db: Session, game: Game, player_id: str, token: str | None) -> Player:
    player = db.get(Player, player_id)
    if not player or player.game_id != game.id:
        raise HTTPException(status_code=404, detail="Player not found in this game")
    if not token or token != player.token:
        raise HTTPException(status_code=403, detail="Invalid player token")
    return player


def require_banker(db: Session, game: Game, player_id: str, token: str | None) -> Player:
    player = require_player(db, game, player_id, token)
    if not player.is_banker:
        raise HTTPException(status_code=403, detail="Only the banker can do this")
    return player


def require_host_or_target_player(
    db: Session, game: Game, target_player_id: str, *, host_token: str | None, player_id: str | None, player_token: str | None
) -> Player:
    """Authorizes an action taken *for* `target_player_id` — either the host
    (driving on behalf of a player with no device connected) or that same
    player acting for themselves. Used by the IRL host-driven flows where
    either side may be the one holding the phone."""
    target = db.get(Player, target_player_id)
    if not target or target.game_id != game.id:
        raise HTTPException(status_code=404, detail="Player not found in this game")
    if host_token and host_token == game.host_token:
        return target
    if player_id == target_player_id and player_token and player_token == target.token:
        return target
    raise HTTPException(status_code=403, detail="Host token, or that player's own token, required")
