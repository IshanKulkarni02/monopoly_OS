from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.db import get_db
from app.game_engine import board_engine
from app.models import Board

router = APIRouter(prefix="/api/boards", tags=["boards"])


@router.get("", response_model=list[schemas.BoardSummaryOut])
def list_boards(db: Session = Depends(get_db)):
    boards = db.query(Board).order_by(Board.created_at.asc()).all()
    return [schemas.BoardSummaryOut.model_validate(b) for b in boards]


@router.get("/{key}", response_model=schemas.BoardDetailOut)
def get_board(key: str, db: Session = Depends(get_db)):
    board = board_engine.get_board_by_key(db, key)
    if board is None:
        raise HTTPException(status_code=404, detail="Board not found")
    return schemas.BoardDetailOut.model_validate(board)
