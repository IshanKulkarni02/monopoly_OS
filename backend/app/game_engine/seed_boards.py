"""Seeds the built-in board presets on startup (idempotent — checked by
`Board.key`, so this is safe to call on every boot).

Two boards ship with the engine:

- `classic`: the standard 40-space layout, ported tile-for-tile from what
  used to be the hardcoded `board_data.py` constant, so every existing game
  behaves identically now that it's reading from the database instead.
- `current_game`: the spec's own 24-tile, ₹5,000-starting-cash, five-group
  (2/3/3/3/4) INR layout — the proof that the data model is genuinely
  generic and not just "classic Monopoly with extra steps." Its non-corner
  layout is produced by `board_generator.generate_layout` with a fixed seed,
  so it's reproducible and doubles as a real exercise of the generator this
  engine will expose through the Board Editor.
"""

from sqlalchemy.orm import Session

from app.game_engine import board_engine, board_generator
from app.models import Board, BoardGroup, BoardTile

CLASSIC_GROUPS: dict[str, dict] = {
    "brown": {"name": "Brown", "color": "#8b5a2b"},
    "light_blue": {"name": "Light Blue", "color": "#7ec8e3"},
    "pink": {"name": "Pink", "color": "#d63384"},
    "orange": {"name": "Orange", "color": "#fd7e14"},
    "red": {"name": "Red", "color": "#dc3545"},
    "yellow": {"name": "Yellow", "color": "#ffc107"},
    "green": {"name": "Green", "color": "#198754"},
    "dark_blue": {"name": "Dark Blue", "color": "#0d3b8c"},
    "railroad": {"name": "Railroads", "color": "#2b2b2b"},
    "utility": {"name": "Utilities", "color": "#6c757d"},
}

CLASSIC_HOUSE_COSTS: dict[str, int] = {
    "brown": 50, "light_blue": 50, "pink": 100, "orange": 100,
    "red": 150, "yellow": 150, "green": 200, "dark_blue": 200,
}

# (position, name, kind, group_key, price, rent_table, tax_config, mystery_deck_key)
CLASSIC_TILES: list[tuple] = [
    (0, "GO", "go", None, None, None, None, None),
    (1, "Mediterranean Avenue", "property", "brown", 60, [2, 10, 30, 90, 160, 250], None, None),
    (2, "Community Chest", "mystery", None, None, None, None, "community_chest"),
    (3, "Baltic Avenue", "property", "brown", 60, [4, 20, 60, 180, 320, 450], None, None),
    (4, "Income Tax", "tax", None, None, None, {"formula": "fixed", "amount": 200}, None),
    (5, "Reading Railroad", "property", "railroad", 200, [25, 50, 100, 200], None, None),
    (6, "Oriental Avenue", "property", "light_blue", 100, [6, 30, 90, 270, 400, 550], None, None),
    (7, "Chance", "mystery", None, None, None, None, "chance"),
    (8, "Vermont Avenue", "property", "light_blue", 100, [6, 30, 90, 270, 400, 550], None, None),
    (9, "Connecticut Avenue", "property", "light_blue", 120, [8, 40, 100, 300, 450, 600], None, None),
    (10, "Jail", "jail", None, None, None, None, None),
    (11, "St. Charles Place", "property", "pink", 140, [10, 50, 150, 450, 625, 750], None, None),
    (12, "Electric Company", "property", "utility", 150, [4, 10], None, None),
    (13, "States Avenue", "property", "pink", 140, [10, 50, 150, 450, 625, 750], None, None),
    (14, "Virginia Avenue", "property", "pink", 160, [12, 60, 180, 500, 700, 900], None, None),
    (15, "Pennsylvania Railroad", "property", "railroad", 200, [25, 50, 100, 200], None, None),
    (16, "St. James Place", "property", "orange", 180, [14, 70, 200, 550, 750, 950], None, None),
    (17, "Community Chest", "mystery", None, None, None, None, "community_chest"),
    (18, "Tennessee Avenue", "property", "orange", 180, [14, 70, 200, 550, 750, 950], None, None),
    (19, "New York Avenue", "property", "orange", 200, [16, 80, 220, 600, 800, 1000], None, None),
    (20, "Free Parking", "vacation", None, None, None, None, None),
    (21, "Kentucky Avenue", "property", "red", 220, [18, 90, 250, 700, 875, 1050], None, None),
    (22, "Chance", "mystery", None, None, None, None, "chance"),
    (23, "Indiana Avenue", "property", "red", 220, [18, 90, 250, 700, 875, 1050], None, None),
    (24, "Illinois Avenue", "property", "red", 240, [20, 100, 300, 750, 925, 1100], None, None),
    (25, "B&O Railroad", "property", "railroad", 200, [25, 50, 100, 200], None, None),
    (26, "Atlantic Avenue", "property", "yellow", 260, [22, 110, 330, 800, 975, 1150], None, None),
    (27, "Ventnor Avenue", "property", "yellow", 260, [22, 110, 330, 800, 975, 1150], None, None),
    (28, "Water Works", "property", "utility", 150, [4, 10], None, None),
    (29, "Marvin Gardens", "property", "yellow", 280, [24, 120, 360, 850, 1025, 1200], None, None),
    (30, "Go To Jail", "go_to_jail", None, None, None, None, None),
    (31, "Pacific Avenue", "property", "green", 300, [26, 130, 390, 900, 1100, 1275], None, None),
    (32, "North Carolina Avenue", "property", "green", 300, [26, 130, 390, 900, 1100, 1275], None, None),
    (33, "Community Chest", "mystery", None, None, None, None, "community_chest"),
    (34, "Pennsylvania Avenue", "property", "green", 320, [28, 150, 450, 1000, 1200, 1400], None, None),
    (35, "Short Line", "property", "railroad", 200, [25, 50, 100, 200], None, None),
    (36, "Chance", "mystery", None, None, None, None, "chance"),
    (37, "Park Place", "property", "dark_blue", 350, [35, 175, 500, 1100, 1300, 1500], None, None),
    (38, "Luxury Tax", "tax", None, None, None, {"formula": "fixed", "amount": 100}, None),
    (39, "Boardwalk", "property", "dark_blue", 400, [50, 200, 600, 1400, 1700, 2000], None, None),
]


def seed_classic_board(db: Session) -> Board:
    existing = board_engine.get_board_by_key(db, "classic")
    if existing:
        return existing

    board = Board(
        key="classic",
        name="Classic (40-tile)",
        description="The standard 40-space Monopoly layout — 8 color groups, 4 railroads, 2 utilities.",
        size=40,
        is_preset=True,
        default_ruleset_overrides={"currency": {"symbol": "$", "denominations": [1, 5, 10, 20, 50, 100, 500]}},
    )
    db.add(board)
    db.flush()

    group_rows: dict[str, BoardGroup] = {}
    for i, (key, meta) in enumerate(CLASSIC_GROUPS.items()):
        g = BoardGroup(board_id=board.id, key=key, name=meta["name"], color=meta["color"], sort_order=i)
        db.add(g)
        db.flush()
        group_rows[key] = g

    for position, name, kind, group_key, price, rent_table, tax_config, deck_key in CLASSIC_TILES:
        if group_key == "railroad":
            rent_model = "group_count_table"
            upgrade_costs: list[int] = []
        elif group_key == "utility":
            rent_model = "dice_multiplier_table"
            upgrade_costs = []
        elif group_key is not None:
            rent_model = "fixed_table"
            upgrade_costs = [CLASSIC_HOUSE_COSTS[group_key]] * 5
        else:
            rent_model = "fixed_table"
            upgrade_costs = []

        db.add(BoardTile(
            board_id=board.id, position=position, name=name, kind=kind,
            group_id=group_rows[group_key].id if group_key else None,
            price=price, rent_model=rent_model, rent_table=rent_table or [],
            upgrade_costs=upgrade_costs, tax_config=tax_config or {},
            mystery_deck_key=deck_key or "mystery",
        ))

    db.commit()
    db.refresh(board)
    return board


# --- current_game: the spec's 24-tile, five-group, INR preset -------------

_TIER_DEFS = [
    # key, display name, swatch, member count, base price
    ("E", "Sunrise", "#a97142", 4, 120),
    ("D", "Harbor", "#c9a227", 3, 260),
    ("C", "Uptown", "#3a6ea8", 3, 480),
    ("B", "Skyline", "#2f6f4f", 3, 820),
    ("A", "Crown", "#7a2e22", 2, 1300),
]
_GROUP_GAP_CONSTRAINTS = {
    "A": {"min_gap": 1, "max_gap": 3},
    "B": {"min_gap": 1, "max_gap": 5},
    "C": {"min_gap": 3, "max_gap": 9},
    "D": {"min_gap": 5, "max_gap": 13},
    "E": {"min_gap": 4, "max_gap": 11},
}
_TIER_STEP = 1.15


def _round_to(value: float, nearest: int) -> int:
    return max(int(round(value / nearest) * nearest), nearest)


def _current_game_property_defs() -> dict[str, list[dict]]:
    defs: dict[str, list[dict]] = {}
    for key, name, color, count, base_price in _TIER_DEFS:
        members = []
        for i in range(count):
            price = _round_to(base_price * (_TIER_STEP ** i), 20)
            base_rent = _round_to(price * 0.08, 10)
            rent_table = [base_rent, base_rent * 3, base_rent * 7, base_rent * 15]
            upgrade_cost = _round_to(price * 0.5, 10)
            members.append({
                "name": f"{name} {i + 1}",
                "price": price,
                "rent_table": rent_table,
                "upgrade_costs": [upgrade_cost] * 3,
            })
        defs[key] = members
    return defs


def seed_current_game_board(db: Session, *, generator_seed: int = 42) -> Board:
    existing = board_engine.get_board_by_key(db, "current_game")
    if existing:
        return existing

    size = 24
    corners = [0, 6, 12, 18]
    property_defs = _current_game_property_defs()

    tile_specs = []
    for tier_key, members in property_defs.items():
        for i in range(len(members)):
            tile_specs.append({"key": f"prop_{tier_key}_{i}", "group_key": tier_key, "locked_position": None})
    for i in range(4):
        tile_specs.append({"key": f"mystery_{i}", "group_key": None, "locked_position": None})
    tile_specs.append({"key": "tax_1", "group_key": None, "locked_position": None})

    layout = board_generator.generate_layout(
        board_size=size,
        corner_positions=corners,
        tile_specs=tile_specs,
        group_constraints=_GROUP_GAP_CONSTRAINTS,
        seed=generator_seed,
        max_attempts=500,
    )

    board = Board(
        key="current_game",
        name="Current Game (24-tile, ₹)",
        description="The house layout: 15 properties in five groups (2/3/3/3/4), 4 mystery tiles, 1 tax tile, ₹5,000 starting cash.",
        size=size,
        is_preset=True,
        default_ruleset_overrides={
            "starting_cash": 5000,
            "currency": {"symbol": "₹", "denominations": [10, 20, 50, 100, 200, 500]},
        },
    )
    db.add(board)
    db.flush()

    group_rows: dict[str, BoardGroup] = {}
    for i, (key, name, color, _count, _base) in enumerate(_TIER_DEFS):
        g = BoardGroup(board_id=board.id, key=key, name=name, color=color, sort_order=i)
        db.add(g)
        db.flush()
        group_rows[key] = g

    db.add(BoardTile(board_id=board.id, position=corners[0], name="GO", kind="go"))
    db.add(BoardTile(board_id=board.id, position=corners[1], name="Jail", kind="jail"))
    db.add(BoardTile(board_id=board.id, position=corners[2], name="Vacation", kind="vacation"))
    db.add(BoardTile(board_id=board.id, position=corners[3], name="Go To Jail", kind="go_to_jail"))

    for tier_key, members in property_defs.items():
        for i, member in enumerate(members):
            position = layout[f"prop_{tier_key}_{i}"]
            db.add(BoardTile(
                board_id=board.id, position=position, name=member["name"], kind="property",
                group_id=group_rows[tier_key].id, price=member["price"], rent_model="fixed_table",
                rent_table=member["rent_table"], upgrade_costs=member["upgrade_costs"],
            ))

    for i in range(4):
        db.add(BoardTile(
            board_id=board.id, position=layout[f"mystery_{i}"], name="Mystery", kind="mystery",
            mystery_deck_key="mystery",
        ))

    db.add(BoardTile(
        board_id=board.id, position=layout["tax_1"], name="Tax", kind="tax",
        tax_config={"formula": "fixed", "amount": 200},
    ))

    db.commit()
    db.refresh(board)
    return board


def seed_all(db: Session) -> None:
    seed_classic_board(db)
    seed_current_game_board(db)
