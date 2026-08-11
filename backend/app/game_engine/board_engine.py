"""Data-driven board lookups — the DB-backed replacement for the old
`board_data.py` constant. Every engine module that used to import
`BOARD_SIZE`, `space_by_index()`, `spaces_in_color_group()`, etc. now calls
the equivalent function here, passing `db` + a `board_id`.

Nothing in this module is specific to any one board layout — arbitrary tile
counts, arbitrary groups, arbitrary rent models all fall out of the same
lookups.
"""

from sqlalchemy.orm import Session

from app.game_engine import board_generator
from app.models import Board, BoardGroup, BoardTile, Property

PURCHASABLE_KINDS = {"property"}
VALID_KINDS = {"go", "property", "mystery", "tax", "jail", "vacation", "go_to_jail", "custom"}
VALID_RENT_MODELS = {"fixed_table", "group_count_table", "dice_multiplier_table"}
CORNER_KINDS = {"go", "jail", "vacation", "go_to_jail"}


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


# --- Board editor: tile/group CRUD + regenerating layout on demand -------
#
# All position shifts below go through a disjoint negative range first
# (`_stage`/`_unstage`) rather than shifting positions directly in place.
# `(board_id, position)` is unique, and a straight ascending-or-descending
# Python loop over positions isn't a reliable way to guarantee every
# intermediate UPDATE avoids colliding with a not-yet-moved row — staging
# through a range no real position ever occupies sidesteps the ordering
# question entirely instead of relying on it working out.

def _stage(position: int) -> int:
    return -(position + 1)


def _unstage(staged: int) -> int:
    return -staged - 1


def delete_board(db: Session, board: Board) -> None:
    if board.is_preset:
        raise BoardEngineError("Preset boards can't be deleted — duplicate one to customize it instead")
    db.delete(board)
    db.commit()


def create_group(db: Session, board: Board, *, key: str, name: str, color: str, rent_multiplier: float | None = None) -> BoardGroup:
    if db.query(BoardGroup).filter(BoardGroup.board_id == board.id, BoardGroup.key == key).first():
        raise BoardEngineError(f"Group '{key}' already exists on this board")
    sort_order = db.query(BoardGroup).filter(BoardGroup.board_id == board.id).count()
    group = BoardGroup(board_id=board.id, key=key, name=name, color=color, rent_multiplier=rent_multiplier, sort_order=sort_order)
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


def update_group(db: Session, board: Board, group: BoardGroup, fields: dict) -> BoardGroup:
    if group.board_id != board.id:
        raise BoardEngineError("That group doesn't belong to this board")
    for key, value in fields.items():
        setattr(group, key, value)
    db.commit()
    db.refresh(group)
    return group


def _validate_tile_fields(board: Board, db: Session, fields: dict) -> None:
    if "kind" in fields and fields["kind"] not in VALID_KINDS:
        raise BoardEngineError(f"Invalid tile kind '{fields['kind']}'")
    if "rent_model" in fields and fields["rent_model"] not in VALID_RENT_MODELS:
        raise BoardEngineError(f"Invalid rent model '{fields['rent_model']}'")
    if fields.get("group_id"):
        group = db.get(BoardGroup, fields["group_id"])
        if not group or group.board_id != board.id:
            raise BoardEngineError("That group doesn't belong to this board")
    for numeric_field in ("rent_table", "upgrade_costs"):
        value = fields.get(numeric_field)
        if value is not None and any((not isinstance(v, int)) or v < 0 for v in value):
            raise BoardEngineError(f"{numeric_field} must be a list of non-negative integers")


def update_tile(db: Session, board: Board, tile: BoardTile, fields: dict) -> BoardTile:
    if tile.board_id != board.id:
        raise BoardEngineError("That tile doesn't belong to this board")
    _validate_tile_fields(board, db, fields)
    for key, value in fields.items():
        setattr(tile, key, value)
    db.commit()
    db.refresh(tile)
    return tile


def insert_tile(db: Session, board: Board, *, position: int, name: str, kind: str, fields: dict | None = None) -> BoardTile:
    if not (0 <= position <= board.size):
        raise BoardEngineError(f"Position {position} is out of range for a board of size {board.size}")
    fields = dict(fields or {})
    _validate_tile_fields(board, db, {"kind": kind, **fields})

    shifted = db.query(BoardTile).filter(BoardTile.board_id == board.id, BoardTile.position >= position).all()
    for t in shifted:
        t.position = _stage(t.position + 1)
    db.flush()
    for t in shifted:
        t.position = _unstage(t.position)
    db.flush()

    tile = BoardTile(board_id=board.id, position=position, name=name, kind=kind, **fields)
    db.add(tile)
    board.size += 1
    db.commit()
    db.refresh(tile)
    return tile


def remove_tile(db: Session, board: Board, tile: BoardTile) -> None:
    if tile.board_id != board.id:
        raise BoardEngineError("That tile doesn't belong to this board")
    if board.size <= 4:
        raise BoardEngineError("A board needs at least 4 tiles")

    removed_position = tile.position
    db.delete(tile)
    db.flush()

    shifted = db.query(BoardTile).filter(BoardTile.board_id == board.id, BoardTile.position > removed_position).all()
    for t in shifted:
        t.position = _stage(t.position - 1)
    db.flush()
    for t in shifted:
        t.position = _unstage(t.position)

    board.size -= 1
    db.commit()


def swap_tile_positions(db: Session, board: Board, tile_a: BoardTile, tile_b: BoardTile) -> None:
    if tile_a.board_id != board.id or tile_b.board_id != board.id:
        raise BoardEngineError("Both tiles must belong to this board")
    if tile_a.id == tile_b.id:
        return
    a_pos, b_pos = tile_a.position, tile_b.position
    tile_a.position = _stage(a_pos)
    db.flush()
    tile_b.position = a_pos
    db.flush()
    tile_a.position = b_pos
    db.commit()


def regenerate_layout(
    db: Session, board: Board, *, group_constraints: dict[str, dict], seed: int | None = None
) -> Board:
    """Re-runs the constraint-based generator on this board's *existing*
    tiles — same names/prices/groups, new positions. Corner-kind tiles
    (go/jail/vacation/go_to_jail) never move; any other tile with
    `locked=True` keeps its current position too, same as a
    generator-time lock."""
    tiles = all_tiles(db, board.id)
    corner_positions = [t.position for t in tiles if t.kind in CORNER_KINDS]

    tile_specs = []
    for t in tiles:
        if t.kind in CORNER_KINDS:
            continue
        tile_specs.append({
            "key": t.id,
            "group_key": t.group.key if t.group else None,
            "locked_position": t.position if t.locked else None,
        })

    layout = board_generator.generate_layout(
        board_size=board.size, corner_positions=corner_positions, tile_specs=tile_specs,
        group_constraints=group_constraints, seed=seed,
    )

    movable = [t for t in tiles if t.kind not in CORNER_KINDS]
    for t in movable:
        t.position = _stage(layout[t.id])
    db.flush()
    for t in movable:
        t.position = _unstage(t.position)

    db.commit()
    db.refresh(board)
    return board
