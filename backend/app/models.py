import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _id() -> str:
    return uuid.uuid4().hex[:12]


def _token() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Game(Base):
    __tablename__ = "games"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_id)
    code: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String, default="Monopoly Night")
    status: Mapped[str] = mapped_column(String, default="lobby")  # lobby | active | ended
    money_mode: Mapped[str] = mapped_column(String, default="banker_ledger")
    banker_mode: Mapped[str] = mapped_column(String, default="manual")  # manual | auto
    board_template: Mapped[str] = mapped_column(String, default="classic")
    ruleset_json: Mapped[dict] = mapped_column(JSON, default=dict)
    host_player_id: Mapped[str | None] = mapped_column(String, nullable=True)
    host_token: Mapped[str] = mapped_column(String, default=_token)
    inflation_multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    round_number: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

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
    balance: Mapped[int] = mapped_column(Integer, default=1500)
    status: Mapped[str] = mapped_column(String, default="active")  # active | bankrupt | left
    jail_free_cards: Mapped[int] = mapped_column(Integer, default=0)
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
