"""SQLAlchemy engine and session wiring for the MySQL-backed store."""
from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DEFAULT_DATABASE_URL = (
    "mysql+pymysql://recoverai:recoverai@localhost:3306/recoverai?charset=utf8mb4"
)


class Base(DeclarativeBase):
    pass


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    # Managed MySQL providers (Railway, Aiven) hand out bare `mysql://` URLs,
    # which SQLAlchemy cannot resolve to a driver. Pin them to PyMySQL.
    if url.startswith("mysql://"):
        url = "mysql+pymysql://" + url[len("mysql://") :]
    return url


# pool_recycle sits below MySQL's default 8h wait_timeout so connections that
# idled long enough for the server to drop them are replaced before reuse,
# instead of surfacing as "MySQL server has gone away" mid-request.
engine = create_engine(
    _database_url(),
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    from app import models  # noqa: F401  -- registers mappers before create_all

    Base.metadata.create_all(bind=engine)
