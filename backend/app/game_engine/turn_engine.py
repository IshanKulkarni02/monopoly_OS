"""Turn order + dice/movement engine.

Originally virtual-mode-only; now shared by virtual play (server rolls the
dice) and IRL companion's tracked-position mode (a human reads a physical
die and the host or player enters it — see `roll_dice`'s `manual_dice`).
Landing resolution itself is never duplicated: once a roll moves a player to
a new space, this hands off to `banker_ledger.apply_auto_banker_landing`,
the same function every mode uses.
"""

import random
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app import logs
from app.game_engine import board_engine, mystery
from app.game_engine.events import resolve, wheel
from app.game_engine.events.base import EventOutcome
from app.game_engine.money_modes.banker_ledger import (
    GameEngineError,
    apply_auto_banker_landing,
    apply_pass_go,
    apply_transaction,
)
from app.models import Game, Player


def _now() -> datetime:
    return datetime.now(timezone.utc)


def start_turn_order(game: Game, players: list[Player]) -> None:
    ordered = sorted(players, key=lambda p: p.joined_at)
    game.turn_order = [p.id for p in ordered]
    game.current_turn_player_id = game.turn_order[0] if game.turn_order else None
    game.turn_started_at = _now() if game.current_turn_player_id else None


def require_current_player(game: Game, player: Player) -> None:
    if not game.turn_order:
        raise GameEngineError("Turn order hasn't been set for this game yet")
    if game.current_turn_player_id != player.id:
        raise GameEngineError("It's not your turn")


def end_turn(db: Session, game: Game, *, player: Player) -> None:
    require_current_player(game, player)

    if player.extra_turns > 0:
        player.extra_turns -= 1
        logs.write_event(db, game_id=game.id, kind="extra_turn_used", player_ids=[player.id], payload={"remaining": player.extra_turns})
        return

    next_id = _next_active_player_id(db, game, after_player_id=player.id)
    if next_id is None:
        return
    game.current_turn_player_id = next_id
    game.turn_started_at = _now()
    logs.write_event(db, game_id=game.id, kind="turn_ended", player_ids=[player.id], payload={"next_player_id": next_id})


def _next_active_player_id(db: Session, game: Game, *, after_player_id: str) -> str | None:
    """The active player whose turn follows `after_player_id`, skipping
    anyone with `skip_next_turn` set (consuming it as it's skipped past).
    Shared by `end_turn` and `bankruptcy.declare_bankruptcy` — the latter
    needs the exact same "who's up next" logic when it eliminates whoever
    currently holds the turn."""
    order = game.turn_order
    active_ids = [pid for pid in order if _status(db, pid) == "active"]
    if not active_ids:
        return None
    idx = active_ids.index(after_player_id) if after_player_id in active_ids else -1

    next_id = active_ids[(idx + 1) % len(active_ids)]
    for _ in range(len(active_ids)):  # bounded: never loop more than once per active player
        next_player = db.get(Player, next_id)
        if next_player and next_player.skip_next_turn:
            next_player.skip_next_turn = False
            logs.write_event(db, game_id=game.id, kind="turn_skipped", player_ids=[next_id], payload={})
            idx = active_ids.index(next_id)
            next_id = active_ids[(idx + 1) % len(active_ids)]
            continue
        break
    return next_id


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
    manual_dice: list[int] | None = None,
) -> dict:
    require_current_player(game, player)
    jail_fine = game.ruleset_json.get("jail_fine", 50)
    jail_max_turns = game.ruleset_json.get("jail_max_turns", 3)
    dice_count = max(int(game.ruleset_json.get("dice_count", 2)), 1)

    if player.in_jail:
        if use_jail_free_card and player.jail_free_cards > 0:
            player.jail_free_cards -= 1
            player.in_jail = False
            player.jail_turns = 0
        elif pay_fine:
            apply_transaction(
                db, game, from_player=player, to_player=None, amount=jail_fine,
                reason="jail fine", created_by_player_id=player.id, feeds_free_parking_pot=True,
            )
            player.in_jail = False
            player.jail_turns = 0

    if manual_dice is not None:
        if len(manual_dice) != dice_count:
            raise GameEngineError(f"This game rolls {dice_count} dice; got {len(manual_dice)} value(s)")
        dice = list(manual_dice)
    else:
        dice = [random.randint(1, 6) for _ in range(dice_count)]
    is_doubles = dice_count >= 2 and len(set(dice)) == 1

    if player.in_jail:
        if is_doubles:
            player.in_jail = False
            player.jail_turns = 0
        else:
            player.jail_turns += 1
            if player.jail_turns >= jail_max_turns:
                apply_transaction(
                    db, game, from_player=player, to_player=None, amount=jail_fine,
                    reason=f"jail fine (released after {jail_max_turns} tries)", created_by_player_id=player.id,
                    feeds_free_parking_pot=True,
                )
                player.in_jail = False
                player.jail_turns = 0
            else:
                end_turn(db, game, player=player)
                return {"outcome": "stayed_in_jail", "dice": dice}

    board_size = board_engine.board_size(db, game.board_id)
    old_position = player.position
    total = sum(dice)
    new_position = (old_position + total) % board_size
    passed_go = old_position + total >= board_size
    player.position = new_position

    # `apply_auto_banker_landing`'s own "go" branch covers landing exactly on
    # GO; this covers passing it en route to somewhere else.
    if passed_go and new_position != 0:
        apply_pass_go(db, game, player=player)

    landing = apply_auto_banker_landing(db, game, player=player, space_index=new_position, dice_roll=total)
    landing = _maybe_draw_mystery(db, game, player, new_position, landing)

    return {
        "outcome": "moved",
        "dice": dice,
        "doubles": is_doubles,
        "position": new_position,
        "landing": landing,
    }


def _maybe_draw_mystery(db: Session, game: Game, player: Player, position: int, landing: dict) -> dict:
    """A tracked board (virtual, or IRL once positions are tracked) has no
    physical deck for a human to draw from, so resolve it automatically as
    part of landing instead of waiting for a separate draw step."""
    if landing.get("space_type") != "mystery":
        return landing
    tile = board_engine.tile_at(db, game.board_id, position)
    event_system = game.ruleset_json.get("event_system", "cards")
    if event_system == "wheel":
        outcome = wheel.spin()
    else:
        card = mystery.draw(db, game, tile.mystery_deck_key)
        outcome = EventOutcome(kind=card.effect_kind, amount=card.amount, text=card.text, target_position=card.target_position)
    return {**landing, "event": resolve.apply_event_outcome(db, game, player=player, outcome=outcome)}


def record_order_roll(db: Session, game: Game, *, player: Player, roll: int) -> dict:
    """One entry in the IRL setup ceremony: a player physically rolls, the
    host (or the player, if self-serving) records the value. Once every
    active player has one recorded, finalize `turn_order` per the game's
    configured `turn_order_mode` and clear the ceremony state."""
    if game.turn_order:
        raise GameEngineError("Turn order has already been set for this game")
    if game.status != "active":
        raise GameEngineError("Game hasn't started yet")

    active_ids = [p.id for p in game.players if p.status == "active"]
    if player.id not in active_ids:
        raise GameEngineError(f"{player.name} is not an active player in this game")

    rolls = [r for r in game.pending_turn_order_rolls if r["player_id"] != player.id]
    rolls.append({"player_id": player.id, "player_name": player.name, "roll": roll})
    game.pending_turn_order_rolls = rolls

    recorded_ids = {r["player_id"] for r in rolls}
    if recorded_ids != set(active_ids):
        return {"outcome": "recorded", "waiting_on": [pid for pid in active_ids if pid not in recorded_ids]}

    mode = game.ruleset_json.get("turn_order_mode", "highest_roll_first")
    if mode == "entry_order":
        order = [r["player_id"] for r in rolls]
    else:
        max_roll = max(r["roll"] for r in rolls)
        tied = [r for r in rolls if r["roll"] == max_roll]
        if len(tied) > 1:
            tied_ids = {r["player_id"] for r in tied}
            game.pending_turn_order_rolls = [r for r in rolls if r["player_id"] not in tied_ids]
            logs.write_event(
                db, game_id=game.id, kind="turn_order_tie", player_ids=list(tied_ids),
                payload={"roll": max_roll, "players": [r["player_name"] for r in tied]},
            )
            return {"outcome": "tie", "tied_players": [r["player_name"] for r in tied], "roll": max_roll}
        order = [r["player_id"] for r in sorted(rolls, key=lambda r: r["roll"], reverse=True)]

    game.turn_order = order
    game.current_turn_player_id = order[0]
    game.turn_started_at = _now()
    game.pending_turn_order_rolls = []
    logs.write_event(db, game_id=game.id, kind="turn_order_set", player_ids=order, payload={"mode": mode, "order": order})
    return {"outcome": "order_set", "turn_order": order}


def move_player(db: Session, game: Game, *, player: Player, position: int, resolve_landing: bool = True) -> dict:
    """GM/host correction tool — e.g. resolving a physical Mystery card that
    reads "advance to ___" by moving the player there directly, rather than
    the automated engine guessing at an effect it doesn't model yet."""
    size = board_engine.board_size(db, game.board_id)
    if not (0 <= position < size):
        raise GameEngineError(f"Invalid board position {position} for this game's board (size {size})")

    old_position = player.position
    player.position = position % size
    logs.write_event(
        db, game_id=game.id, kind="player_moved", player_ids=[player.id],
        payload={"from": old_position, "to": player.position},
    )
    landing = None
    if resolve_landing:
        landing = apply_auto_banker_landing(db, game, player=player, space_index=player.position)
        landing = _maybe_draw_mystery(db, game, player, player.position, landing)
    return {"position": player.position, "landing": landing}


def swap_players(db: Session, game: Game, *, player_a: Player, player_b: Player) -> dict:
    player_a.position, player_b.position = player_b.position, player_a.position
    logs.write_event(
        db, game_id=game.id, kind="players_swapped",
        player_ids=[player_a.id, player_b.id],
        payload={"a": player_a.name, "b": player_b.name, "a_position": player_a.position, "b_position": player_b.position},
    )
    return {"a_position": player_a.position, "b_position": player_b.position}
