"""Default ruleset for a new game.

Stored as `Game.ruleset_json`. Every optional "twist" lives as a key here so
each phase is additive config, not a schema change.
"""

DEFAULT_RULESET: dict = {
    "starting_cash": 1500,
    "pass_go_bonus": 200,
    "free_parking_pot": False,
    "event_system": "cards",  # cards | wheel
    "challenge_before_buy": {"enabled": False, "type": "coin_flip"},
    "inflation": {"enabled": False, "trigger": "on_pass_go", "rate": 0.0, "scope": ["rent", "tax"]},
}


def build_ruleset(overrides: dict | None = None) -> dict:
    ruleset = {**DEFAULT_RULESET}
    if overrides:
        for key, value in overrides.items():
            if key not in ruleset:
                continue
            if isinstance(ruleset[key], dict) and isinstance(value, dict):
                ruleset[key] = {**ruleset[key], **value}
            else:
                ruleset[key] = value
    return ruleset
