"""Turn order + dice/movement engine for `play_mode = "virtual"` games.

Landing resolution itself is not duplicated here — once a roll moves a
player to a new space, this hands off to
`banker_ledger.apply_auto_banker_landing`, the exact same auto-banker logic
IRL companion games use when a player self-declares a landing. The only
thing virtual mode adds is *where* that space index comes from: a
server-tracked position instead of a player's own declaration.
"""

import random

from sqlalchemy.orm import Session

from app import logs
from app.game_engine import board_data
from app.game_engine.events import cards, resolve, wheel
from app.game_engine.money_modes.banker_ledger import (
    GameEngineError,
    apply_auto_banker_landing,
    apply_pass_go,
    apply_transaction,
)
from app.models import Game, Player


def start_turn_order(game: Game, players: list[Player]) -> None:
    ordered = sorted(players, key=lambda p: p.joined_at)
    game.turn_order = [p.id for p in ordered]
    game.current_turn_player_id = game.turn_order[0] if game.turn_order else None


def require_current_player(game: Game, player: Player) -> None:
    if game.play_mode != "virtual":
        raise GameEngineError("This game is not in virtual play mode")
    if game.current_turn_player_id != player.id:
        raise GameEngineError("It's not your turn")


def end_turn(db: Session, game: Game, *, player: Player) -> None:
    require_current_player(game, player)
    order = game.turn_order
    active_ids = [pid for pid in order if _status(db, pid) == "active"]
    if not active_ids:
        return
    idx = active_ids.index(player.id) if player.id in active_ids else -1
    next_id = active_ids[(idx + 1) % len(active_ids)]
    game.current_turn_player_id = next_id
    logs.write_event(db, game_id=game.id, kind="turn_ended", player_ids=[player.id], payload={"next_player_id": next_id})


def _status(db: Session, player_id: str) -> str:
    p = db.get(Player, player_id)
    return p.status if p else "left"


def roll_dice(
    db: Session,
    game: Game,
    *,
    player: Player,
    use_jail_free_card: bool = False,
    pay_fine: bool = False,
) -> dict:
    require_current_player(game, player)

    if player.in_jail:
        if use_jail_free_card and player.jail_free_cards > 0:
            player.jail_free_cards -= 1
            player.in_jail = False
            player.jail_turns = 0
        elif pay_fine:
            apply_transaction(
                db, game, from_player=player, to_player=None, amount=board_data.JAIL_FINE,
                reason="jail fine", created_by_player_id=player.id,
            )
            player.in_jail = False
            player.jail_turns = 0

    die1, die2 = random.randint(1, 6), random.randint(1, 6)
    is_doubles = die1 == die2

    if player.in_jail:
        if is_doubles:
            player.in_jail = False
            player.jail_turns = 0
        else:
            player.jail_turns += 1
            if player.jail_turns >= 3:
                apply_transaction(
                    db, game, from_player=player, to_player=None, amount=board_data.JAIL_FINE,
                    reason="jail fine (released after 3 tries)", created_by_player_id=player.id,
                )
                player.in_jail = False
                player.jail_turns = 0
            else:
                end_turn(db, game, player=player)
                return {"outcome": "stayed_in_jail", "dice": [die1, die2]}

    old_position = player.position
    total = die1 + die2
    new_position = (old_position + total) % board_data.BOARD_SIZE
    passed_go = old_position + total >= board_data.BOARD_SIZE
    player.position = new_position

    # `apply_auto_banker_landing`'s own "go" branch covers landing exactly on
    # GO; this covers passing it en route to somewhere else.
    if passed_go and new_position != 0:
        apply_pass_go(db, game, player=player)

    landing = apply_auto_banker_landing(db, game, player=player, space_index=new_position, dice_roll=total)

    # A virtual board has no physical Chance/Community Chest deck to draw
    # from by hand, so resolve it automatically as part of the landing.
    if landing.get("space_type") in ("chance", "community_chest"):
        event_system = game.ruleset_json.get("event_system", "cards")
        if event_system == "wheel":
            outcome = wheel.spin()
        else:
            deck = cards.CHANCE_DECK if landing["space_type"] == "chance" else cards.COMMUNITY_CHEST_DECK
            outcome = cards.draw(deck)
        landing = {**landing, "event": resolve.apply_event_outcome(db, game, player=player, outcome=outcome)}

    return {
        "outcome": "moved",
        "dice": [die1, die2],
        "doubles": is_doubles,
        "position": new_position,
        "landing": landing,
    }
