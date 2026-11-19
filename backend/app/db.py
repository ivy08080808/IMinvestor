"""Database access: a PostgreSQL connection pool and an optional MongoDB handle.

Conventions (see docs/CONVENTIONS.md):

* Service functions receive an open ``psycopg.Connection`` as their first
  argument; they never open their own connections. This lets one request,
  one job, or one test control the transaction boundary.
* Rows are returned as dicts (``dict_row``).
* Write paths wrap their work in ``with conn.transaction():`` and take row
  locks in the global order ORDERS -> ACCOUNT -> HOLDING (plan §5.1).
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator, Optional

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from pymongo import MongoClient
from pymongo.database import Database

from app.config import settings

log = logging.getLogger(__name__)

_pool: Optional[ConnectionPool] = None
_mongo_client: Optional[MongoClient] = None


def _configure(conn: psycopg.Connection) -> None:
    """Per-connection setup executed when the pool creates a connection."""
    conn.execute("SET TIME ZONE 'Asia/Taipei'")


def init_pool(min_size: int = 1, max_size: int = 10) -> ConnectionPool:
    """Create the global connection pool (idempotent)."""
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            settings.database_url,
            min_size=min_size,
            max_size=max_size,
            # autocommit=True: a bare execute() commits immediately, and
            # `with conn.transaction():` opens a REAL transaction (not a
            # savepoint inside a forgotten implicit one). See CONVENTIONS.md.
            kwargs={"row_factory": dict_row, "autocommit": True},
            configure=_configure,
            open=True,
        )
    return _pool


def close_pool() -> None:
    """Close the global pool (called on application shutdown)."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


@contextmanager
def connection() -> Iterator[psycopg.Connection]:
    """Borrow a pooled connection. Uncommitted work is rolled back on return."""
    pool = init_pool()
    with pool.connection() as conn:
        yield conn


def get_conn() -> Iterator[psycopg.Connection]:
    """FastAPI dependency yielding a pooled connection for one request."""
    with connection() as conn:
        yield conn


def connect_direct() -> psycopg.Connection:
    """Open a standalone connection (for scripts and tests, outside the pool)."""
    conn = psycopg.connect(settings.database_url, row_factory=dict_row, autocommit=True)
    _configure(conn)
    return conn


def mongo() -> Optional[Database]:
    """Return the MongoDB database, or ``None`` if MongoDB is unreachable.

    Behaviour logging is best-effort: the trading system must keep working
    when MongoDB is down.
    """
    global _mongo_client
    try:
        if _mongo_client is None:
            _mongo_client = MongoClient(settings.mongo_url, serverSelectionTimeoutMS=500)
            _mongo_client.admin.command("ping")
        return _mongo_client[settings.mongo_db]
    except Exception as exc:  # noqa: BLE001 - any failure means "no Mongo"
        log.warning("MongoDB unavailable: %s", exc)
        _mongo_client = None
        return None
