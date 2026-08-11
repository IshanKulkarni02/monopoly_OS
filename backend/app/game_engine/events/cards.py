"""Mystery-tile decks (original wording — not a reproduction of any
published card text). Drawn with replacement rather than tracking a
shuffled/discard pile, which keeps this stateless and good enough for a
party game.

A board's mystery tiles each carry a `mystery_deck_key`; boards that want a
classic Chance/Community-Chest split use `"chance"`/`"community_chest"`,
boards with a single unified deck (e.g. the current-game preset) use
`"mystery"`. Unknown keys fall back to `MYSTERY_DECK` rather than erroring,
so a hand-edited board with a typo'd key still draws something sensible.
"""

import random

from app.game_engine.events.base import EventOutcome

CHANCE_DECK: list[EventOutcome] = [
    EventOutcome("bank_pays", 50, "A forgotten refund arrives from the bank."),
    EventOutcome("bank_pays", 150, "Your investments have a great quarter."),
    EventOutcome("pay_bank", 100, "Property taxes are due."),
    EventOutcome("pay_bank", 75, "You owe back rent on a place you forgot about."),
    EventOutcome("pay_each_player", 25, "You throw a party for the whole table."),
    EventOutcome("collect_each_player", 25, "It's your birthday — everyone chips in."),
    EventOutcome("jail_free", 0, "You find a get-out-of-jail-free voucher."),
    EventOutcome("pass_go", 0, "A shortcut sends you straight back to GO."),
    EventOutcome("pay_bank", 50, "A parking fine catches up with you."),
]

COMMUNITY_CHEST_DECK: list[EventOutcome] = [
    EventOutcome("bank_pays", 100, "You win a neighborhood raffle."),
    EventOutcome("bank_pays", 200, "A relative remembers you in their will."),
    EventOutcome("pay_bank", 100, "A surprise bill arrives."),
    EventOutcome("pay_bank", 40, "You cover a shared utility bill."),
    EventOutcome("collect_each_player", 10, "Everyone pays you back for gas."),
    EventOutcome("pay_each_player", 10, "You lose a friendly bet with the table."),
    EventOutcome("jail_free", 0, "A lucky coupon keeps you out of jail."),
    EventOutcome("bank_pays", 75, "A lucky break pays off."),
]

MYSTERY_DECK: list[EventOutcome] = [
    EventOutcome("bank_pays", 100, "A festival bonus lands in your account."),
    EventOutcome("bank_pays", 250, "A lucky investment pays off big."),
    EventOutcome("pay_bank", 150, "An unexpected repair bill arrives."),
    EventOutcome("pay_bank", 80, "You cover a shared expense."),
    EventOutcome("pay_each_player", 40, "You treat the whole table."),
    EventOutcome("collect_each_player", 40, "Everyone chips in for your birthday."),
    EventOutcome("jail_free", 0, "You find a get-out-of-jail-free voucher."),
    EventOutcome("pass_go", 0, "A shortcut sends you straight back to GO."),
]

DECKS_BY_KEY: dict[str, list[EventOutcome]] = {
    "chance": CHANCE_DECK,
    "community_chest": COMMUNITY_CHEST_DECK,
    "mystery": MYSTERY_DECK,
}


def deck_for_key(key: str) -> list[EventOutcome]:
    return DECKS_BY_KEY.get(key, MYSTERY_DECK)


def draw(deck: list[EventOutcome]) -> EventOutcome:
    return random.choice(deck)
