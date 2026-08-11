from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app import accounts, schemas
from app.db import get_db

router = APIRouter(prefix="/api/auth", tags=["accounts"])


@router.post("/signup", response_model=schemas.AuthResponse)
def signup(payload: schemas.SignupRequest, db: Session = Depends(get_db)):
    try:
        user, session = accounts.signup(db, email=payload.email, password=payload.password, name=payload.name)
    except accounts.AccountError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return schemas.AuthResponse(user=schemas.UserOut.model_validate(user), session_token=session.token)


@router.post("/login", response_model=schemas.AuthResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    try:
        user, session = accounts.login(db, email=payload.email, password=payload.password)
    except accounts.AccountError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return schemas.AuthResponse(user=schemas.UserOut.model_validate(user), session_token=session.token)


@router.post("/logout")
def logout(db: Session = Depends(get_db), x_session_token: str | None = Header(default=None)):
    if x_session_token:
        accounts.logout(db, token=x_session_token)
    return {"status": "ok"}


@router.get("/me", response_model=schemas.UserOut)
def me(db: Session = Depends(get_db), x_session_token: str | None = Header(default=None)):
    user = accounts.require_user(db, x_session_token)
    return schemas.UserOut.model_validate(user)
