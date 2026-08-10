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
