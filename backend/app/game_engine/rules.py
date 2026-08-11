"""Default ruleset for a new game.

Stored as `Game.ruleset_json`. Every optional "twist" — and, as of the
data-driven board work, every number the engine used to hardcode — lives as
a key here so each phase is additive config, not a schema change. See
`board_engine.py` for how per-board data (prices, rent tables, groups)
layers on top of these game-wide defaults.
"""

DEFAULT_RULESET: dict = {
    "starting_cash": 1500,
    "pass_go_bonus": 200,
    "free_parking_pot": False,
    "event_system": "cards",  # cards | wheel
    "mystery_deck_mode": "probability",  # probability (draw w/ replacement, weighted) | finite (no replacement until exhausted)
    "challenge_before_buy": {"enabled": False, "type": "coin_flip"},
    "inflation": {"enabled": False, "trigger": "on_pass_go", "rate": 0.0, "scope": ["rent", "tax"]},

    "currency": {"symbol": "$", "denominations": [1, 5, 10, 20, 50, 100, 500], "track_denominations": False},

    "upgrade_requires_full_group": True,
    "mortgage_percentage": 0.5,
    "mortgage_interest": 0.1,
    "group_rent_multiplier": 2.0,

    "jail_fine": 50,
    "jail_max_turns": 3,
    "dice_count": 2,
    "turn_order_mode": "highest_roll_first",  # highest_roll_first | entry_order

    "auction_enabled": False,
    "auction_min_increment": 10,
    "trading_enabled": True,
    "bankruptcy_rule": "liquidate_then_eliminate",
    "win_condition": {"type": "last_standing"},
}


def build_ruleset(overrides: dict | None = None, base: dict | None = None) -> dict:
    ruleset = {**(base or DEFAULT_RULESET)}
    if overrides:
        for key, value in overrides.items():
            if key not in ruleset:
                continue
            if isinstance(ruleset[key], dict) and isinstance(value, dict):
                ruleset[key] = {**ruleset[key], **value}
            else:
                ruleset[key] = value
    return ruleset
