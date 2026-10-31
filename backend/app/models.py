"""
SQLAlchemy models = database TABLES.  (Pydantic schemas in schemas.py = API shapes.)

    users  1 ──< todos    one user has many todos
    users  1 ──< tokens   one user has many tokens (one per login / device)

Deleting a user deletes their todos and tokens (ON DELETE CASCADE).
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(30))
    hashed_password: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    todos: Mapped[list["Todo"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    tokens: Mapped[list["Token"]] = relationship(back_populates="user", cascade="all, delete-orphan")


# Unique on lower(username), so "Vicky" and "vicky" can't both exist
Index("uq_users_username_lower", func.lower(User.username), unique=True)


class Todo(Base):
    __tablename__ = "todos"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    owner: Mapped[User] = relationship(back_populates="todos")


class Token(Base):
    """
    One row per issued JWT (per login).

    We store the token's unique id (the JWT "jti" claim), not the token
    string itself: if the table ever leaked, nobody could reuse the rows to
    log in. The jti is enough to look a token up and revoke it.

    A JWT alone can't be "un-issued" - it stays valid until it expires.
    Checking this table on every request is what makes logout really work.
    """

    __tablename__ = "tokens"

    jti: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user_agent: Mapped[str | None] = mapped_column(String(300))

    user: Mapped[User] = relationship(back_populates="tokens")
