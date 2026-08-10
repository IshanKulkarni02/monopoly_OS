from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app import accounts, schemas
from app.db import get_db
from app.game_engine import board_engine
from app.models import Board

router = APIRouter(prefix="/api/boards", tags=["boards"])


@router.get("", response_model=list[schemas.BoardSummaryOut])
def list_boards(db: Session = Depends(get_db), x_session_token: str | None = Header(default=None)):
    """Presets are visible to everyone; custom boards are only visible to
    the account that saved them — logged-out visitors just see presets."""
    user = accounts.get_current_user(db, x_session_token)
    boards = (
        db.query(Board)
        .filter((Board.is_preset == True) | (Board.owner_user_id == (user.id if user else "__none__")))  # noqa: E712
        .order_by(Board.created_at.asc())
        .all()
    )
    return [schemas.BoardSummaryOut.model_validate(b) for b in boards]


@router.get("/{key}", response_model=schemas.BoardDetailOut)
def get_board(key: str, db: Session = Depends(get_db)):
    board = board_engine.get_board_by_key(db, key)
    if board is None:
        raise HTTPException(status_code=404, detail="Board not found")
    return schemas.BoardDetailOut.model_validate(board)
