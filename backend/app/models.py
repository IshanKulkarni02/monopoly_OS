import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _id() -> str:
    return uuid.uuid4().hex[:12]


def _token() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    """An optional persistent account. Anonymous ephemeral play (join-by-code,
    no login) still works everywhere it always has — a `User` only exists for
    people who want a saved identity across games, e.g. to own custom board
    templates. Nothing requires a `User` to exist."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    token: Mapped[str] = mapped_column(String, unique=True, index=True, default=_token)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped["User"] = relationship()


class Board(Base):
    """A reusable board layout — an ordered list of tiles plus their groups.

    Boards are templates, not per-game state: `Game.board_id` points at one,
    and `start_game` copies its purchasable tiles into per-game `Property`
    rows, the same way it always has — just sourced from here instead of the
    old hardcoded `board_data.py` constant.
    """

    __tablename__ = "boards"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    key: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String, default="")
    size: Mapped[int] = mapped_column(Integer)
    is_preset: Mapped[bool] = mapped_column(Boolean, default=False)
    owner_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    default_ruleset_overrides: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    groups: Mapped[list["BoardGroup"]] = relationship(back_populates="board", cascade="all, delete-orphan")
    tiles: Mapped[list["BoardTile"]] = relationship(
        back_populates="board", cascade="all, delete-orphan", order_by="BoardTile.position"
    )


class BoardGroup(Base):
    """A rent group — a classic color group, but also a railroad-style
    "count how many of these you own" group, or anything else a board wants.

    `rent_multiplier` overrides the ruleset's global `group_rent_multiplier`
    for this group specifically; leave it null to inherit the game default.
    """

    __tablename__ = "board_groups"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    board_id: Mapped[str] = mapped_column(ForeignKey("boards.id"))
    key: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    color: Mapped[str] = mapped_column(String, default="#888888")
    rent_multiplier: Mapped[float | None] = mapped_column(Float, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    board: Mapped["Board"] = relationship(back_populates="groups")

    __table_args__ = (UniqueConstraint("board_id", "key", name="uq_board_group_key"),)


class BoardTile(Base):
    """One position on a board. `kind` drives which fields the engine reads:

    - go: no extra config (amount comes from ruleset `pass_go_bonus`)
    - property: `price`, `group_id`, `rent_model`, `rent_table`, `upgrade_costs`, `mortgage_value`
    - mystery: `mystery_deck_key` selects which deck to draw from
    - tax: `tax_config` = {"formula": "fixed"|"percent_cash"|"percent_assets", "amount": int, "percent": float}
    - jail / vacation / go_to_jail: no extra config — behavior lives in the engine + ruleset
    - custom: `special_effects` = list of {"kind": ..., "params": {...}} actions applied in order

    `rent_model` (property tiles only):
    - fixed_table (default): rent_table[upgrade_level], doubled at level 0 if the
      owner holds the whole group (rate from group.rent_multiplier or the
      ruleset default) — the "unimproved monopoly" rule.
    - group_count_table: rent_table[count of same-group tiles owned - 1] (railroads)
    - dice_multiplier_table: rent_table[count owned - 1] * dice roll (utilities)
    """

    __tablename__ = "board_tiles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    board_id: Mapped[str] = mapped_column(ForeignKey("boards.id"))
    position: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String)
    kind: Mapped[str] = mapped_column(String)  # go|property|mystery|tax|jail|vacation|go_to_jail|custom
    group_id: Mapped[str | None] = mapped_column(ForeignKey("board_groups.id"), nullable=True)

    price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rent_model: Mapped[str] = mapped_column(String, default="fixed_table")
    rent_table: Mapped[list[int]] = mapped_column(JSON, default=list)
    upgrade_costs: Mapped[list[int]] = mapped_column(JSON, default=list)
    mortgage_value: Mapped[int | None] = mapped_column(Integer, nullable=True)

    tax_config: Mapped[dict] = mapped_column(JSON, default=dict)
    mystery_deck_key: Mapped[str] = mapped_column(String, default="mystery")
    special_effects: Mapped[list] = mapped_column(JSON, default=list)
    extra: Mapped[dict] = mapped_column(JSON, default=dict)

    board: Mapped["Board"] = relationship(back_populates="tiles")
    group: Mapped["BoardGroup | None"] = relationship()

    __table_args__ = (UniqueConstraint("board_id", "position", name="uq_board_tile_position"),)


class Game(Base):
    __tablename__ = "games"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    code: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String, default="Monopoly Night")
    status: Mapped[str] = mapped_column(String, default="lobby")  # lobby | active | ended
    money_mode: Mapped[str] = mapped_column(String, default="banker_ledger")
    banker_mode: Mapped[str] = mapped_column(String, default="manual")  # manual | auto
    play_mode: Mapped[str] = mapped_column(String, default="irl_companion")  # irl_companion | virtual
    board_id: Mapped[str | None] = mapped_column(ForeignKey("boards.id"), nullable=True)
    owner_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    ruleset_json: Mapped[dict] = mapped_column(JSON, default=dict)
    host_player_id: Mapped[str | None] = mapped_column(String, nullable=True)
    host_token: Mapped[str] = mapped_column(String, default=_token)
    inflation_multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    round_number: Mapped[int] = mapped_column(Integer, default=1)
    turn_order: Mapped[list[str]] = mapped_column(JSON, default=list)
    current_turn_player_id: Mapped[str | None] = mapped_column(String, nullable=True)
    # Setup-time dice-roll-for-order ceremony (IRL companion mode). A list of
    # {"player_id": ..., "roll": ...} in the order the host recorded them —
    # cleared once `turn_order` is finalized. Virtual mode never uses this;
    # it seeds turn order from join time instead (no physical dice to record).
    pending_turn_order_rolls: Mapped[list] = mapped_column(JSON, default=list)
    free_parking_pot_amount: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    board: Mapped["Board | None"] = relationship()
    players: Mapped[list["Player"]] = relationship(back_populates="game", cascade="all, delete-orphan")
    properties: Mapped[list["Property"]] = relationship(back_populates="game", cascade="all, delete-orphan")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="game", cascade="all, delete-orphan")
    events: Mapped[list["EventLogEntry"]] = relationship(back_populates="game", cascade="all, delete-orphan")


class Player(Base):
    __tablename__ = "players"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    game_id: Mapped[str] = mapped_column(ForeignKey("games.id"))
    name: Mapped[str] = mapped_column(String)
    token: Mapped[str] = mapped_column(String, default=_token)
    is_host: Mapped[bool] = mapped_column(Boolean, default=False)
    is_banker: Mapped[bool] = mapped_column(Boolean, default=False)
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False)
    balance: Mapped[int] = mapped_column(Integer, default=1500)
    denominations: Mapped[dict] = mapped_column(JSON, default=dict)  # {"100": 3, "20": 2, ...} — physical-money mode only
    status: Mapped[str] = mapped_column(String, default="active")  # active | bankrupt | left
    jail_free_cards: Mapped[int] = mapped_column(Integer, default=0)
    position: Mapped[int] = mapped_column(Integer, default=0)  # board space index; virtual play_mode only
    in_jail: Mapped[bool] = mapped_column(Boolean, default=False)
    jail_turns: Mapped[int] = mapped_column(Integer, default=0)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    game: Mapped["Game"] = relationship(back_populates="players")


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    game_id: Mapped[str] = mapped_column(ForeignKey("games.id"))
    space_index: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String)
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("players.id"), nullable=True)
    price: Mapped[int] = mapped_column(Integer, default=0)
    houses: Mapped[int] = mapped_column(Integer, default=0)
    mortgaged: Mapped[bool] = mapped_column(Boolean, default=False)

    game: Mapped["Game"] = relationship(back_populates="properties")
    owner: Mapped["Player | None"] = relationship()


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    game_id: Mapped[str] = mapped_column(ForeignKey("games.id"))
    type: Mapped[str] = mapped_column(String, default="banker_ledger")  # banker_ledger | cash_counter | digital_transfer
    from_player_id: Mapped[str | None] = mapped_column(ForeignKey("players.id"), nullable=True)
    to_player_id: Mapped[str | None] = mapped_column(ForeignKey("players.id"), nullable=True)
    amount: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String, default="")
    created_by_player_id: Mapped[str | None] = mapped_column(ForeignKey("players.id"), nullable=True)
    reversed: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String, default="confirmed")  # pending | confirmed | declined
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    game: Mapped["Game"] = relationship(back_populates="transactions")


class EventLogEntry(Base):
    __tablename__ = "event_log_entries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    game_id: Mapped[str] = mapped_column(ForeignKey("games.id"))
    kind: Mapped[str] = mapped_column(String)
    player_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    game: Mapped["Game"] = relationship(back_populates="events")
