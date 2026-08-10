import random
import string

from sqlalchemy.orm import Session

from app import logs
from app.game_engine import board_data
from app.game_engine.rules import build_ruleset
from app.models import Game, Player, Property

_CODE_ALPHABET = "".join(c for c in string.ascii_uppercase + string.digits if c not in "0O1I")


def generate_join_code(db: Session, length: int = 5) -> str:
    while True:
        code = "".join(random.choices(_CODE_ALPHABET, k=length))
        if not db.query(Game).filter(Game.code == code).first():
            return code


def create_game(db: Session, *, host_name: str, name: str = "Monopoly Night", ruleset_overrides: dict | None = None) -> tuple[Game, Player]:
    game = Game(
        code=generate_join_code(db),
        name=name,
        ruleset_json=build_ruleset(ruleset_overrides),
    )
    db.add(game)
    db.flush()

    host = Player(
        game_id=game.id,
        name=host_name,
        is_host=True,
        is_banker=True,
        balance=game.ruleset_json["starting_cash"],
    )
    db.add(host)
    db.flush()

    game.host_player_id = host.id
    logs.write_event(db, game_id=game.id, kind="game_created", player_ids=[host.id], payload={"host_name": host_name})
    db.commit()
    db.refresh(game)
    db.refresh(host)
    return game, host


def join_game(db: Session, game: Game, *, name: str) -> Player:
    if game.status != "lobby":
        raise ValueError("This game has already started; new players can't join mid-game")
    player = Player(game_id=game.id, name=name, balance=game.ruleset_json["starting_cash"])
    db.add(player)
    db.flush()
    logs.write_event(db, game_id=game.id, kind="player_joined", player_ids=[player.id], payload={"name": name})
    db.commit()
    db.refresh(player)
    return player


def start_game(db: Session, game: Game) -> Game:
    if game.status != "lobby":
        raise ValueError("Game already started")
    if len(game.players) < 2:
        raise ValueError("Need at least 2 players to start")

    for space in board_data.purchasable_spaces():
        db.add(Property(game_id=game.id, space_index=space["index"], name=space["name"], price=space["price"]))

    game.status = "active"
    logs.write_event(db, game_id=game.id, kind="game_started", payload={"player_count": len(game.players)})
    db.commit()
    db.refresh(game)
    return game
