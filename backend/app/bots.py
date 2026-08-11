import asyncio

from sqlalchemy.orm import Session

from app.connection_manager import manager
from app.game_engine import bankruptcy, bot_ai
from app.game_engine.money_modes.banker_ledger import GameEngineError, InsufficientFundsError
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
        except InsufficientFundsError as exc:
            # A bot that can't cover a mandatory payment (rent/tax/fine)
            # goes bankrupt to whoever it owed, exactly like a human could
            # choose to — see `bankruptcy.py`. This replaces the old
            # force-end-turn stopgap, which just left an insolvent bot
            # stuck forever instead of actually resolving the game.
            db.rollback()
            current = db.get(Player, current.id)
            creditor = db.get(Player, exc.creditor_player_id) if exc.creditor_player_id else None
            try:
                bankruptcy.declare_bankruptcy(db, game, player=current, creditor=creditor)
                db.commit()
            except GameEngineError:
                db.rollback()
                return
        except GameEngineError:
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
