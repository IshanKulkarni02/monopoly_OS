"""User accounts: signup/login/session verification.

Deliberately scoped down from a full identity platform — bcrypt-hashed
passwords, opaque random session tokens stored in `UserSession` (same
pattern as the existing host_token/player_token, not JWTs, so there's one
auth mental model in this codebase rather than two). No email verification
or password reset flow; this is a home-game app, not a public service, and
those add real complexity for a case that isn't the goal here.

Accounts are additive, not a replacement for the existing ephemeral
join-by-code identity — every endpoint that worked anonymously before still
does. A logged-in user just gets a `User.id` that `Game.owner_user_id` /
`Board.owner_user_id` can point at, so their games and saved board templates
follow them across devices.
"""

import re

import bcrypt
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import User, UserSession

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AccountError(Exception):
    pass


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def signup(db: Session, *, email: str, password: str, name: str) -> tuple[User, UserSession]:
    email = normalize_email(email)
    if not _EMAIL_RE.match(email):
        raise AccountError("That doesn't look like a valid email address")
    if len(password) < 8:
        raise AccountError("Password must be at least 8 characters")
    if db.query(User).filter(User.email == email).first():
        raise AccountError("An account with that email already exists")

    user = User(email=email, password_hash=hash_password(password), name=name.strip() or email)
    db.add(user)
    db.flush()
    session = UserSession(user_id=user.id)
    db.add(session)
    db.commit()
    db.refresh(user)
    db.refresh(session)
    return user, session


def login(db: Session, *, email: str, password: str) -> tuple[User, UserSession]:
    email = normalize_email(email)
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        raise AccountError("Incorrect email or password")

    session = UserSession(user_id=user.id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return user, session


def logout(db: Session, *, token: str) -> None:
    session = db.query(UserSession).filter(UserSession.token == token).first()
    if session:
        db.delete(session)
        db.commit()


def get_current_user(db: Session, token: str | None) -> User | None:
    if not token:
        return None
    session = db.query(UserSession).filter(UserSession.token == token).first()
    return session.user if session else None


def require_user(db: Session, token: str | None) -> User:
    user = get_current_user(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Sign in required")
    return user
