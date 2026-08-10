"""Mystery decks are per-board data (`MysteryCard` rows), not Python
constants — this is what actually makes them GM-editable (spec §22).
Supports both draw modes from spec §21:

- probability (default): weighted random draw, with replacement.
- finite: a shuffled draw order per (game, deck), consumed without
  replacement until exhausted, then reshuffled.
"""

import random

from sqlalchemy.orm import Session

from app.game_engine.money_modes.banker_ledger import GameEngineError
from app.models import Game, MysteryCard


class MysteryError(GameEngineError):
    pass


def cards_for_deck(db: Session, board_id: str, deck_key: str) -> list[MysteryCard]:
    return (
        db.query(MysteryCard)
        .filter(MysteryCard.board_id == board_id, MysteryCard.deck_key == deck_key)
        .all()
    )


def _draw_finite(game: Game, deck_key: str, cards: list[MysteryCard]) -> MysteryCard:
    state = dict(game.mystery_deck_state)
    deck_state = state.get(deck_key)
    card_ids = [c.id for c in cards]

    needs_reshuffle = (
        not deck_state
        or set(deck_state.get("order", [])) != set(card_ids)
        or deck_state.get("index", 0) >= len(deck_state.get("order", []))
    )
    if needs_reshuffle:
        order = list(card_ids)
        random.shuffle(order)
        deck_state = {"order": order, "index": 0}

    card_id = deck_state["order"][deck_state["index"]]
    deck_state = {**deck_state, "index": deck_state["index"] + 1}
    state[deck_key] = deck_state
    game.mystery_deck_state = state  # reassign (not mutate in place) so the JSON column dirties

    return next(c for c in cards if c.id == card_id)


def draw(db: Session, game: Game, deck_key: str) -> MysteryCard:
    cards = cards_for_deck(db, game.board_id, deck_key)
    if not cards:
        raise MysteryError(f"No mystery cards configured for deck '{deck_key}' on this board")

    mode = game.ruleset_json.get("mystery_deck_mode", "probability")
    if mode == "finite":
        return _draw_finite(game, deck_key, cards)

    weights = [max(c.weight, 1) for c in cards]
    return random.choices(cards, weights=weights, k=1)[0]
