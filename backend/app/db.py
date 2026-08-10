import os
import sys
from pathlib import Path

from sqlalchemy import create_engine
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


def init_db() -> None:
    from app import models  # noqa: F401  (ensure models are registered)
    from app.game_engine.seed_boards import seed_all

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_all(db)
    finally:
        db.close()
