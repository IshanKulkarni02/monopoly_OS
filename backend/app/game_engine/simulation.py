"""Headless game simulation — runs whole games with only bot players, no
human input and no WebSocket broadcast per move, to help evaluate a board
or ruleset before ever handing it to real players (spec's "Economy Lab").

Reuses the exact same engine functions real play uses (`bot_ai.play_bot_turn`,
`bankruptcy.declare_bankruptcy`, `win_conditions.check_win_condition`) so a
simulated game plays by the identical rules a live one would — the only
things specific to simulation are the turn-loop driver (no human to wait
for, so it just runs until the game ends or a turn cap is hit) and cleanup
(each simulated game is deleted after its stats are captured, so batches
of hundreds of runs don't pollute the real games list).
"""

from sqlalchemy.orm import Session

from app.game_engine import bot_ai, stats as game_stats, state as game_state, win_conditions
from app.game_engine.money_modes.banker_ledger import GameEngineError, InsufficientFundsError
from app.game_engine import bankruptcy
from app.models import Game, Player

DEFAULT_MAX_TURNS = 500


class SimulationError(Exception):
    pass


def _run_bot_turns_to_completion(db: Session, game: Game, *, max_turns: int) -> int:
    """Drives bot turns until the game ends or `max_turns` individual turns
    have been played (a safety cap — with only bots and no player ever
    walking away, a pathological ruleset could otherwise loop forever)."""
    turns = 0
    while game.status == "active" and turns < max_turns:
        current = db.get(Player, game.current_turn_player_id) if game.current_turn_player_id else None
        if not current or current.status != "active":
            break
        try:
            bot_ai.play_bot_turn(db, game, player=current)
        except InsufficientFundsError as exc:
            creditor = db.get(Player, exc.creditor_player_id) if exc.creditor_player_id else None
            try:
                bankruptcy.declare_bankruptcy(db, game, player=current, creditor=creditor)
            except GameEngineError:
                break
        except GameEngineError:
            break
        turns += 1
        db.flush()
    return turns


def simulate_one_game(
    db: Session,
    *,
    board_key: str,
    ruleset_overrides: dict | None,
    num_bots: int,
    max_turns: int = DEFAULT_MAX_TURNS,
) -> dict:
    """Plays one full all-bot game to completion (or the turn cap) and
    returns a summary. The game itself is deleted before returning — only
    the summary persists, so simulation never leaves real rows behind."""
    if num_bots < 2:
        raise SimulationError("Need at least 2 players to simulate a game")

    game, host = game_state.create_game(
        db, host_name="Sim 1", ruleset_overrides=ruleset_overrides, board_key=board_key
    )
    host.is_bot = True
    game.play_mode = "virtual"  # add_bot requires this; must be set before adding any bots
    db.flush()
    for i in range(num_bots - 1):
        game_state.add_bot(db, game, name=f"Sim {i + 2}")
    game_state.start_game(db, game)

    starting_order = list(game.turn_order)
    turns_played = _run_bot_turns_to_completion(db, game, max_turns=max_turns)

    winner = None
    if game.status != "ended":
        # Turn cap hit before a natural win — force a check so batches that
        # hit the cap still get a meaningful "who was ahead" result instead
        # of no winner at all.
        winner = win_conditions.check_win_condition(db, game)
    if game.winner_player_id:
        winner = db.get(Player, game.winner_player_id)

    summary_stats = game_stats.compute_stats(db, game)
    winner_start_index = starting_order.index(winner.id) if winner and winner.id in starting_order else None

    result = {
        "turns_played": turns_played,
        "hit_turn_cap": game.status == "active",
        "winner_name": winner.name if winner else None,
        "winner_start_index": winner_start_index,
        "player_count": num_bots,
        "final_net_worths": [p["net_worth"] for p in summary_stats["players"]],
        "bankruptcies": summary_stats["bankruptcies"],
        "auctions_won": summary_stats["auctions_won"],
        "trades_completed": summary_stats["trades_completed"],
        "houses_built": summary_stats["houses_built"],
        "total_money_moved": summary_stats["total_money_moved"],
    }

    db.delete(game)
    db.commit()
    return result


def simulate_batch(
    db: Session,
    *,
    board_key: str,
    ruleset_overrides: dict | None,
    num_games: int,
    num_bots: int,
    max_turns: int = DEFAULT_MAX_TURNS,
) -> dict:
    games = [
        simulate_one_game(db, board_key=board_key, ruleset_overrides=ruleset_overrides, num_bots=num_bots, max_turns=max_turns)
        for _ in range(num_games)
    ]
    return aggregate_results(games)


def aggregate_results(games: list[dict]) -> dict:
    n = len(games)
    if n == 0:
        return {"games_played": 0}

    completed = [g for g in games if not g["hit_turn_cap"]]
    avg_turns = sum(g["turns_played"] for g in games) / n

    wins_by_start_index: dict[int, int] = {}
    for g in games:
        if g["winner_start_index"] is not None:
            wins_by_start_index[g["winner_start_index"]] = wins_by_start_index.get(g["winner_start_index"], 0) + 1

    all_net_worths = [nw for g in games for nw in g["final_net_worths"]]

    return {
        "games_played": n,
        "games_hit_turn_cap": n - len(completed),
        "average_turns_played": round(avg_turns, 1),
        "win_rate_by_starting_position": {str(k): round(v / n, 3) for k, v in sorted(wins_by_start_index.items())},
        "average_final_net_worth": round(sum(all_net_worths) / len(all_net_worths), 1) if all_net_worths else 0,
        "average_bankruptcies_per_game": round(sum(g["bankruptcies"] for g in games) / n, 2),
        "average_auctions_per_game": round(sum(g["auctions_won"] for g in games) / n, 2),
        "average_trades_per_game": round(sum(g["trades_completed"] for g in games) / n, 2),
        "average_houses_built_per_game": round(sum(g["houses_built"] for g in games) / n, 2),
        "average_money_moved_per_game": round(sum(g["total_money_moved"] for g in games) / n, 1),
    }
