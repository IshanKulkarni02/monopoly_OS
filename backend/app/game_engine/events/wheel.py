"""Spin-the-wheel: a single unified replacement for both the Chance and
Community Chest decks, resolving to the same `EventOutcome` shape so the
rest of the engine doesn't care which presentation produced it."""

import random

from app.game_engine.events.base import EventOutcome

WHEEL_SEGMENTS: list[EventOutcome] = [
    EventOutcome("bank_pays", 100, "Bank pays you $100!"),
    EventOutcome("bank_pays", 200, "Jackpot! Bank pays you $200!"),
    EventOutcome("pay_bank", 100, "Pay the bank $100."),
    EventOutcome("pay_bank", 50, "Pay the bank $50."),
    EventOutcome("pay_each_player", 25, "Pay each player $25."),
    EventOutcome("collect_each_player", 25, "Collect $25 from each player."),
    EventOutcome("jail_free", 0, "Get out of jail free!"),
    EventOutcome("pass_go", 0, "Advance to GO and collect your bonus!"),
    EventOutcome("nothing", 0, "Nothing happens — spin again next time."),
]


def spin() -> EventOutcome:
    return random.choice(WHEEL_SEGMENTS)
