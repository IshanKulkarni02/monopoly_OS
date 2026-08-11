"""Win-condition checks and the game-over transition.

`Game.status` has had an `"ended"` value since the very first schema, but
nothing ever set it — this is the module that finally does. Only one
condition is implemented: `last_standing` (the only real, well-defined
option for a game with no fixed end date or round limit). A round-limit or
richest-after-N-rounds condition is a reasonable future addition once there's
a real notion of "rounds" tied to actual turns rather than just the
inflation system's manual `round_number` advance — deliberately not built
here to avoid half-implementing a second mode.
"""

from sqlalchemy.orm import Session

from app import logs
from app.models import Game, Player


def check_win_condition(db: Session, game: Game) -> Player | None:
    """Call this any time a player might have just become the last one
    standing (today: only from `bankruptcy.declare_bankruptcy`). No-ops if
    the game already ended, hasn't started, or never had more than one
    player (so a solo test game doesn't instantly "win")."""
    if game.status != "active" or len(game.players) < 2:
        return None
    if game.ruleset_json.get("win_condition", {}).get("type") != "last_standing":
        return None

    active = [p for p in game.players if p.status == "active"]
    if len(active) != 1:
        return None

    winner = active[0]
    game.status = "ended"
    game.winner_player_id = winner.id
    logs.write_event(db, game_id=game.id, kind="game_over", player_ids=[winner.id], payload={"winner": winner.name, "reason": "last_standing"})
    return winner
