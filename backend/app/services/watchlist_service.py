"""Watchlist. Owner: 模組 C 帳務與管理."""

from __future__ import annotations

from typing import Any, Dict, List

import psycopg

from app.errors import NotImplementedYet
from app.services import OWNER_C


def list_watchlist(conn: psycopg.Connection, user_id: int) -> List[Dict[str, Any]]:
    """Watched securities with their latest quote (``QuoteOut`` dicts).

    Hint: select the ids from WATCHLIST (only '啟用' securities) and reuse
    ``quote_service.get_quotes(conn, ids)`` so the open-price rule stays in one place.
    """
    raise NotImplementedYet("自選股清單", OWNER_C)


def add(conn: psycopg.Connection, user_id: int, security_id: str) -> None:
    """``INSERT INTO watchlist ... ON CONFLICT DO NOTHING``; unknown/disabled id -> 404."""
    raise NotImplementedYet("加入自選股", OWNER_C)


def remove(conn: psycopg.Connection, user_id: int, security_id: str) -> None:
    """``DELETE FROM watchlist WHERE user_id AND security_id`` (a real delete is fine here)."""
    raise NotImplementedYet("移除自選股", OWNER_C)
