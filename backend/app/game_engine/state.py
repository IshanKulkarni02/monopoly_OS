import random
import string

from sqlalchemy.orm import Session

from app import logs
from app.game_engine import board_engine, currency, turn_engine
from app.game_engine.rules import build_ruleset
from app.models import Game, Player, Property

_CODE_ALPHABET = "".join(c for c in string.ascii_uppercase + string.digits if c not in "0O1I")

DEFAULT_BOARD_KEY = "classic"


def _seed_denominations(player: Player, ruleset: dict) -> None:
    cfg = ruleset.get("currency", {})
    if not cfg.get("track_denominations") or not cfg.get("denominations"):
        return
    player.denominations = currency.seed_denominations(player.balance, cfg["denominations"])


def generate_join_code(db: Session, length: int = 5) -> str:
    while True:
        code = "".join(random.choices(_CODE_ALPHABET, k=length))
        if not db.query(Game).filter(Game.code == code).first():
            return code


def create_game(
    db: Session,
    *,
    host_name: str,
    name: str = "Monopoly Night",
    ruleset_overrides: dict | None = None,
    board_key: str | None = None,
) -> tuple[Game, Player]:
    board = board_engine.get_board_by_key(db, board_key or DEFAULT_BOARD_KEY)
    if board is None:
        raise ValueError(f"Unknown board '{board_key or DEFAULT_BOARD_KEY}'")

    board_ruleset = build_ruleset(board.default_ruleset_overrides)
    ruleset_json = build_ruleset(ruleset_overrides, base=board_ruleset)

    game = Game(
        code=generate_join_code(db),
        name=name,
        board_id=board.id,
        ruleset_json=ruleset_json,
    )
    db.add(game)
    db.flush()

    host = Player(
        game_id=game.id,
        name=host_name,
        is_host=True,
        is_banker=True,
        balance=game.ruleset_json["starting_cash"],
    )
    _seed_denominations(host, game.ruleset_json)
    db.add(host)
    db.flush()

    game.host_player_id = host.id
    logs.write_event(
        db, game_id=game.id, kind="game_created", player_ids=[host.id],
        payload={"host_name": host_name, "board_key": board.key},
    )
    db.commit()
    db.refresh(game)
    db.refresh(host)
    return game, host


def join_game(db: Session, game: Game, *, name: str) -> Player:
    if game.status != "lobby":
        raise ValueError("This game has already started; new players can't join mid-game")
    player = Player(game_id=game.id, name=name, balance=game.ruleset_json["starting_cash"])
    _seed_denominations(player, game.ruleset_json)
    db.add(player)
    db.flush()
    logs.write_event(db, game_id=game.id, kind="player_joined", player_ids=[player.id], payload={"name": name})
    db.commit()
    db.refresh(player)
    return player


def add_bot(db: Session, game: Game, *, name: str | None = None) -> Player:
    if game.status != "lobby":
        raise ValueError("Can't add a bot after the game has started")
    if game.play_mode != "virtual":
        raise ValueError("Bots only play in virtual games — there's no physical board for them to sit at")

    bot_number = sum(1 for p in game.players if p.is_bot) + 1
    bot = Player(
        game_id=game.id,
        name=name or f"Bot {bot_number}",
        is_bot=True,
        balance=game.ruleset_json["starting_cash"],
    )
    _seed_denominations(bot, game.ruleset_json)
    db.add(bot)
    db.flush()
    logs.write_event(db, game_id=game.id, kind="bot_added", player_ids=[bot.id], payload={"name": bot.name})
    db.commit()
    db.refresh(bot)
    return bot


EXPORT_FORMAT_VERSION = 1

_PLAYER_EXPORT_FIELDS = [
    "name", "is_host", "is_banker", "is_bot", "balance", "denominations", "status",
    "jail_free_cards", "position", "in_jail", "jail_turns", "skip_next_turn", "extra_turns",
]


def export_game(game: Game) -> dict:
    """A portable snapshot of a game's *current playable state* — enough to
    resume it as a fresh game later (save game night, continue next week).
    Deliberately drops auth tokens (a fresh import always mints new ones —
    an exported file isn't something you'd want to hand someone your live
    game's tokens inside of) and the transaction/event log history (an
    audit trail, not state the game needs in order to keep being played) to
    keep the format simple. Players/properties reference each other by
    *index* into this blob's own lists, not by database id — ids get
    regenerated on import."""
    players = sorted(game.players, key=lambda p: p.joined_at)
    index_of = {p.id: i for i, p in enumerate(players)}
    return {
        "version": EXPORT_FORMAT_VERSION,
        "name": game.name,
        "board_key": game.board.key,
        "banker_mode": game.banker_mode,
        "money_mode": game.money_mode,
        "play_mode": game.play_mode,
        "ruleset_json": game.ruleset_json,
        "round_number": game.round_number,
        "inflation_multiplier": game.inflation_multiplier,
        "free_parking_pot_amount": game.free_parking_pot_amount,
        "mystery_deck_state": game.mystery_deck_state,
        "players": [{field: getattr(p, field) for field in _PLAYER_EXPORT_FIELDS} for p in players],
        "properties": [
            {
                "space_index": p.space_index,
                "owner_index": index_of.get(p.owner_id) if p.owner_id else None,
                "houses": p.houses,
                "mortgaged": p.mortgaged,
            }
            for p in game.properties
        ],
        "turn_order_indices": [index_of[pid] for pid in game.turn_order if pid in index_of],
        "current_turn_index": index_of.get(game.current_turn_player_id) if game.current_turn_player_id else None,
    }


def import_game(db: Session, data: dict) -> tuple[Game, Player]:
    if data.get("version") != EXPORT_FORMAT_VERSION:
        raise ValueError(f"Unsupported export format (expected version {EXPORT_FORMAT_VERSION})")
    board = board_engine.get_board_by_key(db, data["board_key"])
    if board is None:
        raise ValueError(f"Unknown board '{data['board_key']}' — that board no longer exists on this server")
    if not data.get("players"):
        raise ValueError("Export has no players")

    game = Game(
        code=generate_join_code(db),
        name=data.get("name", "Monopoly Night"),
        board_id=board.id,
        banker_mode=data.get("banker_mode", "manual"),
        money_mode=data.get("money_mode", "banker_ledger"),
        play_mode=data.get("play_mode", "irl_companion"),
        ruleset_json=data.get("ruleset_json") or build_ruleset(),
        round_number=data.get("round_number", 1),
        inflation_multiplier=data.get("inflation_multiplier", 1.0),
        free_parking_pot_amount=data.get("free_parking_pot_amount", 0),
        mystery_deck_state=data.get("mystery_deck_state", {}),
        status="active",
    )
    db.add(game)
    db.flush()

    players = []
    for p_data in data["players"]:
        player = Player(game_id=game.id, **{field: p_data[field] for field in _PLAYER_EXPORT_FIELDS if field in p_data})
        db.add(player)
        db.flush()
        players.append(player)

    game.host_player_id = next((p.id for p in players if p.is_host), players[0].id)

    for prop_data in data.get("properties", []):
        tile = board_engine.tile_at(db, board.id, prop_data["space_index"])
        owner_index = prop_data.get("owner_index")
        db.add(Property(
            game_id=game.id, space_index=prop_data["space_index"], name=tile.name, price=tile.price or 0,
            owner_id=players[owner_index].id if owner_index is not None else None,
            houses=prop_data.get("houses", 0), mortgaged=prop_data.get("mortgaged", False),
        ))

    turn_order_indices = data.get("turn_order_indices") or []
    game.turn_order = [players[i].id for i in turn_order_indices if i < len(players)]
    current_turn_index = data.get("current_turn_index")
    game.current_turn_player_id = players[current_turn_index].id if current_turn_index is not None else None

    logs.write_event(db, game_id=game.id, kind="game_imported", payload={"name": game.name, "player_count": len(players)})
    db.commit()
    db.refresh(game)
    host = db.get(Player, game.host_player_id)
    return game, host


def start_game(db: Session, game: Game) -> Game:
    if game.status != "lobby":
        raise ValueError("Game already started")
    if len(game.players) < 2:
        raise ValueError("Need at least 2 players to start")

    for tile in board_engine.purchasable_tiles(db, game.board_id):
        db.add(Property(game_id=game.id, space_index=tile.position, name=tile.name, price=tile.price or 0))

    if game.play_mode == "virtual":
        turn_engine.start_turn_order(game, game.players)

    game.status = "active"
    logs.write_event(db, game_id=game.id, kind="game_started", payload={"player_count": len(game.players)})
    db.commit()
    db.refresh(game)
    return game
