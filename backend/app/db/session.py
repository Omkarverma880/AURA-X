"""Engine and session management."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _engine_kwargs() -> dict[str, Any]:
    if settings.is_sqlite:
        # check_same_thread=False is required either way: FastAPI runs sync
        # dependencies in a worker threadpool, so the thread that opens a
        # connection is rarely the thread that uses it.
        #
        # An in-memory database (":memory:") only exists for the lifetime of
        # a single connection, so it genuinely needs StaticPool to pin every
        # checkout to that one connection. A file-based database has no such
        # requirement - pinning it to one shared connection instead makes it
        # actively unsafe, because sqlite3 connection objects are not safe
        # for concurrent use from multiple threads even with
        # check_same_thread=False disabled: two requests landing on
        # different threadpool threads at the same moment corrupt the shared
        # cursor state ("bad parameter or other API misuse"). The default
        # pool hands each thread its own connection to the same file instead.
        if ":memory:" in settings.DATABASE_URL:
            from sqlalchemy.pool import StaticPool

            return {
                "connect_args": {"check_same_thread": False},
                "poolclass": StaticPool,
            }
        return {"connect_args": {"check_same_thread": False, "timeout": 15}}
    return {
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_pre_ping": True,
        "pool_recycle": 1800,
    }


engine: Engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    future=True,
    **_engine_kwargs(),
)


@event.listens_for(Engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record) -> None:
    """SQLite ignores foreign keys unless explicitly told not to - the
    ownership tests depend on FK enforcement behaving like PostgreSQL.

    WAL mode lets readers and a writer proceed concurrently instead of
    blocking on each other, which matters once each thread has its own
    connection to the same file (see _engine_kwargs).
    """
    if settings.is_sqlite:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        if ":memory:" not in settings.DATABASE_URL:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=15000")
        cursor.close()


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a session that always gets closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
