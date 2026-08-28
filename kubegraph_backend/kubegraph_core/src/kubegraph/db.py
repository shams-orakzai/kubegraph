"""Database layer (SQLAlchemy 2.0).

Defaults to a local SQLite file so it runs with zero setup. Point DATABASE_URL
at PostgreSQL in production (e.g. postgresql+psycopg://user:pass@host/db) with no
code changes — this is the persistence path noted in the architecture doc.
"""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./kubegraph.db")

# check_same_thread only matters for SQLite + FastAPI's threadpool.
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency — yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables. Imported models must be registered before this runs."""
    from kubegraph.models import user  # noqa: F401  (registers the table)
    Base.metadata.create_all(bind=engine)
