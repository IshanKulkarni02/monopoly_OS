"""Board editor: duplicate a board to make it yours, then add/remove/edit
tiles and groups on it, or re-run the constraint-based generator on it.
Preset boards (`is_preset=True`) are never edited directly — duplicate one
first, same pattern as `save_board_template` in `games.py`."""

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app import accounts, schemas
from app.db import get_db
from app.game_engine import board_engine, board_generator
from app.models import Board, BoardGroup, BoardTile, User

router = APIRouter(prefix="/api/boards/{key}", tags=["board_editor"])


def _get_owned_board(db: Session, key: str, user: User) -> Board:
    board = board_engine.get_board_by_key(db, key)
    if board is None:
        raise HTTPException(status_code=404, detail="Board not found")
    if board.owner_user_id != user.id:
        raise HTTPException(status_code=403, detail="You don't own this board")
    return board


def _get_tile(db: Session, board: Board, tile_id: str) -> BoardTile:
    tile = db.get(BoardTile, tile_id)
    if not tile or tile.board_id != board.id:
        raise HTTPException(status_code=404, detail="Tile not found")
    return tile


def _get_group(db: Session, board: Board, group_id: str) -> BoardGroup:
    group = db.get(BoardGroup, group_id)
    if not group or group.board_id != board.id:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


@router.post("/duplicate", response_model=schemas.BoardDetailOut)
def duplicate_board(
    key: str,
    payload: schemas.DuplicateBoardRequest,
    db: Session = Depends(get_db),
    x_session_token: str | None = Header(default=None),
):
    user = accounts.require_user(db, x_session_token)
    source = board_engine.get_board_by_key(db, key)
    if source is None:
        raise HTTPException(status_code=404, detail="Board not found")
    try:
        clone = board_engine.clone_board(
            db, source, key=payload.key, name=payload.name, description=payload.description, owner_user_id=user.id
        )
    except board_engine.BoardEngineError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return schemas.BoardDetailOut.model_validate(clone)


@router.patch("", response_model=schemas.BoardDetailOut)
def update_board(
    key: str,
    payload: schemas.UpdateBoardRequest,
    db: Session = Depends(get_db),
    x_session_token: str | None = Header(default=None),
):
    user = accounts.require_user(db, x_session_token)
    board = _get_owned_board(db, key, user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(board, field, value)
    db.commit()
    db.refresh(board)
    return schemas.BoardDetailOut.model_validate(board)


@router.delete("")
def delete_board(key: str, db: Session = Depends(get_db), x_session_token: str | None = Header(default=None)):
    user = accounts.require_user(db, x_session_token)
    board = _get_owned_board(db, key, user)
    try:
        board_engine.delete_board(db, board)
    except board_engine.BoardEngineError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "ok"}


@router.post("/tiles", response_model=schemas.BoardDetailOut)
def insert_tile(
    key: str,
    payload: schemas.InsertTileRequest,
    db: Session = Depends(get_db),
    x_session_token: str | None = Header(default=None),
):
    user = accounts.require_user(db, x_session_token)
    board = _get_owned_board(db, key, user)
    try:
        board_engine.insert_tile(
            db, board, position=payload.position, name=payload.name, kind=payload.kind,
            fields=payload.fields.model_dump(exclude_unset=True, exclude={"name", "kind"}),
        )
    except board_engine.BoardEngineError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.refresh(board)
    return schemas.BoardDetailOut.model_validate(board)


@router.patch("/tiles/{tile_id}", response_model=schemas.BoardDetailOut)
def update_tile(
    key: str,
    tile_id: str,
    payload: schemas.TileFieldsRequest,
    db: Session = Depends(get_db),
    x_session_token: str | None = Header(default=None),
):
    user = accounts.require_user(db, x_session_token)
    board = _get_owned_board(db, key, user)
    tile = _get_tile(db, board, tile_id)
    try:
        board_engine.update_tile(db, board, tile, payload.model_dump(exclude_unset=True))
    except board_engine.BoardEngineError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.refresh(board)
    return schemas.BoardDetailOut.model_validate(board)


@router.delete("/tiles/{tile_id}", response_model=schemas.BoardDetailOut)
def remove_tile(
    key: str, tile_id: str, db: Session = Depends(get_db), x_session_token: str | None = Header(default=None)
):
    user = accounts.require_user(db, x_session_token)
    board = _get_owned_board(db, key, user)
    tile = _get_tile(db, board, tile_id)
    try:
        board_engine.remove_tile(db, board, tile)
    except board_engine.BoardEngineError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.refresh(board)
    return schemas.BoardDetailOut.model_validate(board)


@router.post("/tiles/{tile_id}/move", response_model=schemas.BoardDetailOut)
def move_tile(
    key: str,
    tile_id: str,
    payload: schemas.MoveTileRequest,
    db: Session = Depends(get_db),
    x_session_token: str | None = Header(default=None),
):
    user = accounts.require_user(db, x_session_token)
    board = _get_owned_board(db, key, user)
    tile_a = _get_tile(db, board, tile_id)
    tile_b = _get_tile(db, board, payload.other_tile_id)
    try:
        board_engine.swap_tile_positions(db, board, tile_a, tile_b)
    except board_engine.BoardEngineError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.refresh(board)
    return schemas.BoardDetailOut.model_validate(board)


@router.post("/groups", response_model=schemas.BoardDetailOut)
def create_group(
    key: str,
    payload: schemas.CreateGroupRequest,
    db: Session = Depends(get_db),
    x_session_token: str | None = Header(default=None),
):
    user = accounts.require_user(db, x_session_token)
    board = _get_owned_board(db, key, user)
    try:
        board_engine.create_group(
            db, board, key=payload.key, name=payload.name, color=payload.color, rent_multiplier=payload.rent_multiplier
        )
    except board_engine.BoardEngineError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.refresh(board)
    return schemas.BoardDetailOut.model_validate(board)


@router.patch("/groups/{group_id}", response_model=schemas.BoardDetailOut)
def update_group(
    key: str,
    group_id: str,
    payload: schemas.UpdateGroupRequest,
    db: Session = Depends(get_db),
    x_session_token: str | None = Header(default=None),
):
    user = accounts.require_user(db, x_session_token)
    board = _get_owned_board(db, key, user)
    group = _get_group(db, board, group_id)
    board_engine.update_group(db, board, group, payload.model_dump(exclude_unset=True))
    db.refresh(board)
    return schemas.BoardDetailOut.model_validate(board)


@router.post("/generate", response_model=schemas.BoardDetailOut)
def generate_layout(
    key: str,
    payload: schemas.RegenerateLayoutRequest,
    db: Session = Depends(get_db),
    x_session_token: str | None = Header(default=None),
):
    user = accounts.require_user(db, x_session_token)
    board = _get_owned_board(db, key, user)
    try:
        board_engine.regenerate_layout(db, board, group_constraints=payload.group_constraints, seed=payload.seed)
    except (board_engine.BoardEngineError, board_generator.BoardGenerationError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.refresh(board)
    return schemas.BoardDetailOut.model_validate(board)
