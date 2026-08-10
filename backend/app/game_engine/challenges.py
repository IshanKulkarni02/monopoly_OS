"""Optional buy-in challenge gate. Server-rolled so it can't be gamed
client-side; the only type implemented so far is a 50/50 coin flip."""

import random

from app.models import Game


def run_challenge(game: Game) -> tuple[bool, int]:
    cfg = game.ruleset_json.get("challenge_before_buy", {})
    challenge_type = cfg.get("type", "coin_flip")
    if challenge_type == "coin_flip":
        roll = random.randint(1, 100)
        return roll > 50, roll
    return True, 100
