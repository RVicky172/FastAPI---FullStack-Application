from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import ACCESS_TOKEN_EXPIRE_MINUTES
from ..database import get_db
from ..models import Token as TokenRow
from ..models import User
from ..schemas import LoginRequest, SessionOut, Token, UserCreate, UserOut
from ..security import (
    create_access_token,
    get_current_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _find_user(db: Session, username: str) -> User | None:
    # Case-insensitive match - same rule as the unique index in models.py
    return db.scalar(select(User).where(func.lower(User.username) == username.lower()))


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(body: UserCreate, db: Session = Depends(get_db)):
    # `body` is already validated by Pydantic (length, pattern...).
    # If invalid, FastAPI auto-returns 422 before this function even runs.
    if _find_user(db, body.username):
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already taken")

    user = User(username=body.username, hashed_password=hash_password(body.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Two requests registered the same name at the same moment;
        # the unique index caught the second one.
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already taken")
    return user  # response_model=UserOut strips hashed_password


@router.post("/login", response_model=Token)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = _find_user(db, body.username)
    if user is None or not verify_password(body.password, user.hashed_password):
        # Same message for both cases so attackers can't discover usernames.
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect username or password")

    # Housekeeping: drop this user's expired tokens so the table doesn't grow forever
    db.execute(delete(TokenRow).where(
        TokenRow.user_id == user.id, TokenRow.expires_at < datetime.now(timezone.utc)
    ))

    return Token(
        access_token=create_access_token(db, user, request.headers.get("user-agent")),
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(token: TokenRow = Depends(get_current_token), db: Session = Depends(get_db)):
    """Revoke the token used for this request. It gets 401 from now on."""
    token.revoked_at = datetime.now(timezone.utc)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/sessions", response_model=list[SessionOut])
def sessions(current: TokenRow = Depends(get_current_token), db: Session = Depends(get_db)):
    """All active (not revoked, not expired) logins of the current user."""
    rows = db.scalars(
        select(TokenRow)
        .where(
            TokenRow.user_id == current.user_id,
            TokenRow.revoked_at.is_(None),
            TokenRow.expires_at > datetime.now(timezone.utc),
        )
        .order_by(TokenRow.created_at.desc())
    )
    return [
        SessionOut.model_validate(row).model_copy(update={"current": row.jti == current.jti})
        for row in rows
    ]
