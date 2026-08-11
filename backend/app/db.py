import json
import os
import sys
from pathlib import Path

from sqlalchemy import JSON, Boolean, create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def _default_data_dir() -> Path:
    """Dev/Docker: a `data/` folder next to the source tree, as always. A
    PyInstaller-bundled desktop build has no writable source tree (it runs
    from a temp extraction dir or a read-only app bundle), so it needs a
    real per-OS user data location instead."""
    if not getattr(sys, "frozen", False):
        return Path(__file__).resolve().parent.parent / "data"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "monopoly_OS"
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home())) / "monopoly_OS"
    return Path.home() / ".monopoly_os"


DATA_DIR = _default_data_dir()
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DATA_DIR / 'monopoly.db'}")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _add_missing_columns() -> None:
    """No migration system exists (Alembic or otherwise) — `create_all` only
    creates brand-new tables, it never alters an existing one. Every phase of
    this app's roadmap added columns to already-existing tables, so a SQLite
    file from an earlier version throws `no such column` the moment new code
    queries it. This adds whatever the current models declare but an on-disk
    table predates, backfilling existing rows with that column's normal
    Python-level default so old rows behave like freshly-created ones.
    Idempotent — safe to run on every startup, including a brand-new DB."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue  # create_all (just above) already created this one
            existing_cols = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing_cols or column.primary_key:
                    continue
                col_type = column.type.compile(dialect=engine.dialect)
                conn.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {col_type}'))
                literal = _default_literal(column)
                if literal is not None:
                    conn.execute(
                        text(f'UPDATE "{table.name}" SET "{column.name}" = :v WHERE "{column.name}" IS NULL'),
                        {"v": literal},
                    )

        # One-time legacy fix: pre-board-engine games stored the board choice
        # as a plain string in `board_template` (dropped from the model when
        # `board_id`/the `boards` table replaced it). Point those old rows at
        # their matching Board row instead of leaving `board_id` null, then
        # drop the dead column — it's NOT NULL in the old schema, so leaving
        # it in place breaks every future INSERT (the ORM never populates a
        # column it doesn't know about).
        games_cols = {c["name"] for c in inspector.get_columns("games")}
        if "board_template" in games_cols:
            conn.execute(
                text(
                    "UPDATE games SET board_id = "
                    "(SELECT id FROM boards WHERE boards.key = games.board_template) "
                    "WHERE board_id IS NULL AND board_template IS NOT NULL"
                )
            )
            conn.execute(text('ALTER TABLE games DROP COLUMN board_template'))


def _default_literal(column):
    default = column.default
    if default is None:
        return None
    if getattr(default, "is_callable", False):
        try:
            value = default.arg()
        except TypeError:
            value = default.arg(None)  # context-sensitive callable
    elif getattr(default, "is_scalar", False):
        value = default.arg
    else:
        return None
    if isinstance(column.type, JSON):
        return json.dumps(value)
    if isinstance(column.type, Boolean):
        return int(bool(value))
    return value


def init_db() -> None:
    from app import models  # noqa: F401  (ensure models are registered)
    from app.game_engine.seed_boards import seed_all

    Base.metadata.create_all(bind=engine)
    _add_missing_columns()
    db = SessionLocal()
    try:
        seed_all(db)
    finally:
        db.close()
