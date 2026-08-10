"""Inflation twist: a running multiplier applied to rent/tax/price lookups.

Kept separate from `Game.ruleset_json` (which is static config) because the
multiplier is mutable runtime state that grows over the course of a game.
"""

from app.models import Game


def inflated_amount(game: Game, base_amount: int, category: str) -> int:
    cfg = game.ruleset_json.get("inflation", {})
    if not cfg.get("enabled") or category not in cfg.get("scope", []):
        return base_amount
    return round(base_amount * game.inflation_multiplier)


def on_pass_go(game: Game) -> None:
    cfg = game.ruleset_json.get("inflation", {})
    if cfg.get("enabled") and cfg.get("trigger") == "on_pass_go":
        game.inflation_multiplier *= 1 + cfg.get("rate", 0.0)


def advance_round(game: Game) -> None:
    game.round_number += 1
    cfg = game.ruleset_json.get("inflation", {})
    if cfg.get("enabled") and cfg.get("trigger") == "per_round":
        game.inflation_multiplier *= 1 + cfg.get("rate", 0.0)
