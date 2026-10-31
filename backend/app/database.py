"""
Database connection (SQLAlchemy 2.0 + PostgreSQL via psycopg 3).

    engine        -> manages a POOL of connections to Postgres
    SessionLocal  -> factory that creates a Session (one "unit of work")
    get_db()      -> FastAPI dependency: one Session per request, always closed

Usage in a route:
    def my_route(db: Session = Depends(get_db)):
        db.add(obj); db.commit()
"""
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import DATABASE_URL, SQL_ECHO

# pool_pre_ping: test a pooled connection before using it, so a restarted
# Postgres container doesn't cause "connection closed" errors.
engine = create_engine(DATABASE_URL, echo=SQL_ECHO, pool_pre_ping=True)

# expire_on_commit=False: objects keep their values after commit, so we can
# return them from a route without SQLAlchemy reloading them.
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Every model (table) inherits from this."""


def get_db() -> Iterator[Session]:
    # FastAPI runs the code before `yield` at the start of the request and
    # the code after it at the end - so the session is always closed.
    with SessionLocal() as db:
        yield db


def init_db() -> None:
    """Create tables that don't exist yet (called once at startup).

    Fine for learning. Real projects use migrations (Alembic) instead, so that
    changing a model also changes existing tables safely.
    """
    from . import models  # noqa: F401  (import registers the models on Base)

    Base.metadata.create_all(bind=engine)
