"""Securities search and quotes. Owner: 模組 A 行情與爬蟲.

Two different "opening" numbers — do not mix them up (plan §2):

* ``open_price`` — TWSE's real opening price, stored in DAILY_PRICE.
* ``prev_close`` — 參考價／昨收 = previous trading day's close, NOT stored,
  derived with ``LAG(close_price) OVER (PARTITION BY security_id ORDER BY trade_date)``.
  ``change = close - prev_close``, ``change_pct = change / prev_close × 100``.
  It is the same value as ``market.reference_price`` (±10% base) and the
  base of "今日損益".
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

import psycopg

from app import clock, fees, market
from app.constants import SECURITY_ACTIVE
from app.errors import AppError


def _escape_like(keyword: str) -> str:
    return keyword.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def search_securities(conn: psycopg.Connection, keyword: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Search active securities by id prefix or name substring.

    Returns: list of ``SecurityOut`` dicts. Only status = '啟用' (report: disabled
    securities are hidden from users).
    """
    kw = (keyword or "").strip()
    if not kw:
        return []
    return conn.execute(
        """
        SELECT s.security_id, s.security_name, s.category_id, c.category_name, s.status
        FROM security s JOIN security_category c USING (category_id)
        WHERE s.status = %(active)s
          AND (s.security_id LIKE %(like)s || '%%'
               OR s.security_name ILIKE '%%' || %(like)s || '%%')
        ORDER BY (s.security_id = %(kw)s) DESC, s.security_id
        LIMIT %(limit)s
        """,
        {"active": SECURITY_ACTIVE, "like": _escape_like(kw), "kw": kw, "limit": limit},
    ).fetchall()


def get_quotes(conn: psycopg.Connection, security_ids: List[str]) -> List[Dict[str, Any]]:
    """Latest quote for each id (watchlist, market list). Returns ``QuoteOut`` dicts."""
    ids = list(dict.fromkeys(security_ids))  # 去重並保留順序
    if not ids:
        return []
    rows = conn.execute(
        """
        SELECT s.security_id, s.security_name, c.category_name,
               p.trade_date, p.prev_close, p.open_price,
               p.high_price, p.low_price, p.close_price, p.volume,
               p.close_price - p.prev_close AS change,
               ROUND((p.close_price - p.prev_close) / p.prev_close * 100, 2) AS change_pct
        FROM security s
        JOIN security_category c USING (category_id)
        LEFT JOIN LATERAL (
            SELECT d.*, LEAD(d.close_price) OVER (ORDER BY d.trade_date DESC) AS prev_close
            FROM (SELECT * FROM daily_price dp
                  WHERE dp.security_id = s.security_id
                  ORDER BY dp.trade_date DESC LIMIT 2) d
            ORDER BY d.trade_date DESC LIMIT 1
        ) p ON true
        WHERE s.security_id = ANY(%s)
        """,
        (ids,),
    ).fetchall()
    order = {sid: i for i, sid in enumerate(ids)}
    return sorted(rows, key=lambda r: order.get(r["security_id"], len(order)))


def get_history(
    conn: psycopg.Connection, security_id: str, date_from: date, date_to: date
) -> List[Dict[str, Any]]:
    """Daily bars between two dates, newest first. Returns ``PriceBarOut`` dicts.

    LAG is computed over the whole series *before* filtering by date, otherwise
    the first day in the range would get ``prev_close = NULL``.
    """
    return conn.execute(
        """
        SELECT trade_date, prev_close, open_price, high_price, low_price, close_price, volume,
               close_price - prev_close AS change,
               ROUND((close_price - prev_close) / prev_close * 100, 2) AS change_pct
        FROM (
            SELECT trade_date, open_price, high_price, low_price, close_price, volume,
                   LAG(close_price) OVER (ORDER BY trade_date) AS prev_close
            FROM daily_price WHERE security_id = %s
        ) t
        WHERE trade_date BETWEEN %s AND %s
        ORDER BY trade_date DESC
        """,
        (security_id, date_from, date_to),
    ).fetchall()


def get_order_rule(conn: psycopg.Connection, security_id: str) -> Dict[str, Any]:
    """Belong date, reference price and ±10% band for the order panel (implemented).

    Placement (order_service.place_order) must apply exactly the same rule.
    """
    sec = conn.execute(
        "SELECT status FROM security WHERE security_id = %s", (security_id,)
    ).fetchone()
    if sec is None:
        raise AppError("NOT_FOUND", f"找不到證券 {security_id}。", status_code=404)

    result: Dict[str, Any] = {"security_id": security_id, "tradable": False, "reason": ""}
    if sec["status"] != SECURITY_ACTIVE:
        result["reason"] = "此證券已停用。"
        return result
    try:
        belong = market.order_belong_date(conn, clock.now())
    except AppError as exc:
        result["reason"] = exc.message
        return result

    ref: Optional[Any] = market.reference_price(conn, security_id, belong)
    result["order_belong_date"] = belong
    if ref is None:
        result["reason"] = "此證券尚無行情資料，無法下單。"
        return result
    low, high = fees.price_limits(ref)
    result.update(reference_price=ref, limit_low=low, limit_high=high, tradable=True)
    return result