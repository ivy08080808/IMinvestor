"""Admin (業務經營者) functions. Owner: 模組 C 帳務與管理.

Users are never deleted: freezing the ACCOUNT is the only way to disable one
(plan §7). Securities are never deleted either: set status '停用'.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

import psycopg

from app.errors import NotImplementedYet
from app.services import OWNER_C


# ---- securities ---------------------------------------------------------------
def list_securities(
    conn: psycopg.Connection, keyword: Optional[str], limit: int = 50, offset: int = 0
) -> List[Dict[str, Any]]:
    """All securities including disabled ones (``SecurityOut`` dicts)."""
    raise NotImplementedYet("證券列表（Admin）", OWNER_C)


def create_security(conn: psycopg.Connection, data: Dict[str, Any]) -> Dict[str, Any]:
    """INSERT a security; duplicate id -> AppError("DUPLICATE", 409)."""
    raise NotImplementedYet("新增證券", OWNER_C)


def update_security(conn: psycopg.Connection, security_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """UPDATE name / category / status (only the provided fields)."""
    raise NotImplementedYet("修改證券", OWNER_C)


# ---- trading calendar ---------------------------------------------------------
def list_calendar(conn: psycopg.Connection, date_from: date, date_to: date) -> List[Dict[str, Any]]:
    """Calendar rows in a range (``CalendarDayOut`` dicts)."""
    raise NotImplementedYet("交易日曆查詢", OWNER_C)


def upsert_calendar_day(conn: psycopg.Connection, calendar_date: date, is_trading_day: bool) -> Dict[str, Any]:
    """INSERT ... ON CONFLICT (calendar_date) DO UPDATE.

    Must refuse to turn a day into a non-trading day if pending orders already
    belong to it (AppError("HAS_PENDING_ORDERS", 409)).
    """
    raise NotImplementedYet("登錄休市日", OWNER_C)


# ---- users / accounts ---------------------------------------------------------
def list_users(
    conn: psycopg.Connection, keyword: Optional[str], limit: int = 50, offset: int = 0
) -> List[Dict[str, Any]]:
    """Users with account status and cash (``UserSummaryOut`` dicts)."""
    raise NotImplementedYet("使用者列表", OWNER_C)


def set_account_status(conn: psycopg.Connection, user_id: int, status: str) -> Dict[str, Any]:
    """Freeze / unfreeze: ``SELECT ... FROM account WHERE user_id FOR UPDATE`` then UPDATE."""
    raise NotImplementedYet("凍結／解凍帳戶", OWNER_C)


# ---- statistics ---------------------------------------------------------------
def security_stats(
    conn: psycopg.Connection, date_from: date, date_to: date, limit: int = 50
) -> List[Dict[str, Any]]:
    """Per-security order count, filled count, fill rate, filled shares (``SecurityStatsOut``)."""
    raise NotImplementedYet("全站交易統計", OWNER_C)


# ---- automation visibility (framework-owned, implemented) ---------------------
def list_settlement_runs(conn: psycopg.Connection, limit: int = 30) -> List[Dict[str, Any]]:
    """Recent automatic 15:00 runs, newest first (``SettlementRunOut`` dicts)."""
    return conn.execute(
        """
        SELECT trade_date, status, started_at, finished_at,
               price_rows, filled_count, expired_count, message
        FROM settlement_run
        ORDER BY trade_date DESC
        LIMIT %s
        """,
        (limit,),
    ).fetchall()
