"""Data-driven board lookups — the DB-backed replacement for the old
`board_data.py` constant. Every engine module that used to import
`BOARD_SIZE`, `space_by_index()`, `spaces_in_color_group()`, etc. now calls
the equivalent function here, passing `db` + a `board_id`.

Nothing in this module is specific to any one board layout — arbitrary tile
counts, arbitrary groups, arbitrary rent models all fall out of the same
lookups.
"""

from sqlalchemy.orm import Session

from app.models import Board, BoardGroup, BoardTile, Property

PURCHASABLE_KINDS = {"property"}


class BoardEngineError(Exception):
    pass


def get_board(db: Session, board_id: str) -> Board:
    board = db.get(Board, board_id)
    if board is None:
        raise BoardEngineError(f"Board {board_id} not found")
    return board


def get_board_by_key(db: Session, key: str) -> Board | None:
    return db.query(Board).filter(Board.key == key).first()


def board_size(db: Session, board_id: str) -> int:
    return get_board(db, board_id).size


def all_tiles(db: Session, board_id: str) -> list[BoardTile]:
    return db.query(BoardTile).filter(BoardTile.board_id == board_id).order_by(BoardTile.position).all()


def tile_at(db: Session, board_id: str, position: int) -> BoardTile:
    size = board_size(db, board_id)
    tile = (
        db.query(BoardTile)
        .filter(BoardTile.board_id == board_id, BoardTile.position == position % size)
        .first()
    )
    if tile is None:
        raise BoardEngineError(f"No tile at position {position} on board {board_id}")
    return tile


def purchasable_tiles(db: Session, board_id: str) -> list[BoardTile]:
    return [t for t in all_tiles(db, board_id) if t.kind in PURCHASABLE_KINDS]


def first_tile_of_kind(db: Session, board_id: str, kind: str) -> BoardTile | None:
    return (
        db.query(BoardTile)
        .filter(BoardTile.board_id == board_id, BoardTile.kind == kind)
        .order_by(BoardTile.position)
        .first()
    )


def group_tile_positions(db: Session, group_id: str) -> list[int]:
    return [t.position for t in db.query(BoardTile).filter(BoardTile.group_id == group_id).all()]


def owns_full_group(db: Session, game_id: str, player_id: str, group_id: str | None) -> bool:
    if group_id is None:
        return False
    positions = group_tile_positions(db, group_id)
    if not positions:
        return False
    props = db.query(Property).filter(Property.game_id == game_id, Property.space_index.in_(positions)).all()
    return len(props) == len(positions) and all(p.owner_id == player_id for p in props)


def count_owned_in_group(db: Session, game_id: str, owner_id: str, group_id: str | None) -> int:
    if group_id is None:
        return 0
    positions = group_tile_positions(db, group_id)
    if not positions:
        return 0
    return (
        db.query(Property)
        .filter(Property.game_id == game_id, Property.owner_id == owner_id, Property.space_index.in_(positions))
        .count()
    )


def max_upgrade_level(tile: BoardTile) -> int:
    return max(len(tile.rent_table) - 1, 0)


def mortgage_value_for(tile: BoardTile, ruleset: dict) -> int:
    if tile.mortgage_value is not None:
        return tile.mortgage_value
    pct = ruleset.get("mortgage_percentage", 0.5)
    return round((tile.price or 0) * pct)


def group_rent_multiplier(group: BoardGroup | None, ruleset: dict) -> float:
    if group is not None and group.rent_multiplier is not None:
        return group.rent_multiplier
    return ruleset.get("group_rent_multiplier", 2.0)


def clone_board(
    db: Session, source: Board, *, key: str, name: str, description: str, owner_user_id: str | None
) -> Board:
    """Duplicates a board's groups + tiles under a new key, e.g. "save this
    game's board as a reusable template." Doesn't touch `default_ruleset_overrides`
    beyond copying it forward — a saved template starts with the same
    currency/starting-cash defaults as what it was cloned from."""
    if get_board_by_key(db, key) is not None:
        raise BoardEngineError(f"A board with key '{key}' already exists")

    clone = Board(
        key=key, name=name, description=description, size=source.size, is_preset=False,
        owner_user_id=owner_user_id, default_ruleset_overrides=dict(source.default_ruleset_overrides),
    )
    db.add(clone)
    db.flush()

    group_map: dict[str, str] = {}
    for group in source.groups:
        new_group = BoardGroup(
            board_id=clone.id, key=group.key, name=group.name, color=group.color,
            rent_multiplier=group.rent_multiplier, sort_order=group.sort_order,
        )
        db.add(new_group)
        db.flush()
        group_map[group.id] = new_group.id

    for tile in source.tiles:
        db.add(BoardTile(
            board_id=clone.id, position=tile.position, name=tile.name, kind=tile.kind,
            group_id=group_map.get(tile.group_id) if tile.group_id else None,
            price=tile.price, rent_model=tile.rent_model, rent_table=list(tile.rent_table),
            upgrade_costs=list(tile.upgrade_costs), mortgage_value=tile.mortgage_value,
            tax_config=dict(tile.tax_config), mystery_deck_key=tile.mystery_deck_key,
            special_effects=list(tile.special_effects), extra=dict(tile.extra),
        ))

    db.commit()
    db.refresh(clone)
    return clone
