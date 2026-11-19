"""Shared fixtures. DB tests run inside a transaction that is always rolled back."""

from __future__ import annotations

from typing import Iterator

import psycopg
import pytest

from app.db import connect_direct


@pytest.fixture
def conn() -> Iterator[psycopg.Connection]:
    """A connection whose changes are discarded after the test (skips if no DB)."""
    try:
        c = connect_direct()
    except psycopg.OperationalError:
        pytest.skip("PostgreSQL not available (see README 安裝)")
    with c:
        with c.transaction(force_rollback=True):
            yield c
