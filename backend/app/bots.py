import asyncio

from sqlalchemy.orm import Session

from app.connection_manager import manager
from app.game_engine import bot_ai
from app.game_engine.money_modes.banker_ledger import GameEngineError
from app.game_engine.turn_engine import end_turn
from app.models import Game, Player
from app.serializers import serialize_game_state

MAX_BOT_TURNS_PER_CALL = 50


async def run_bots_until_human(db: Session, game: Game) -> None:
    """After a human ends their turn (or the game starts), let any
    consecutive bot players play themselves out, broadcasting after each one
    so watchers see the bots' turns happen in sequence instead of jumping
    straight to the next human's turn."""
    for _ in range(MAX_BOT_TURNS_PER_CALL):
        current = db.get(Player, game.current_turn_player_id) if game.current_turn_player_id else None
        if not current or not current.is_bot or current.status != "active":
            return

        try:
            bot_ai.play_bot_turn(db, game, player=current)
            db.commit()
        except GameEngineError:
            # A bot that can't afford what it owes has nowhere to go until
            # bankruptcy handling exists — force its turn to end rather than
            # freeze the game for everyone else.
            db.rollback()
            try:
                end_turn(db, game, player=current)
                db.commit()
            except GameEngineError:
                db.rollback()
                return

        state = serialize_game_state(db, game)
        await manager.broadcast(game.code, {"type": "state", "game": state.model_dump(mode="json")})
        await asyncio.sleep(0.4)
