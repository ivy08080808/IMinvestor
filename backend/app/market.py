"""Trading calendar, market phase and order belong-date rules (plan §4).

This module is the only place that decides *which trading day an order
belongs to* and *whether orders may be placed right now*. Order placement,
the scheduler and the frontend status bar all go through it.

Phase table (t = now in Asia/Taipei, d = date(t), T(d) = is trading day):

==========  =====================================  ==============  =========
phase       condition                              belong date     can order
==========  =====================================  ==============  =========
HOLIDAY     not T(d)                               next(d)         yes
PRE_OPEN    T(d), t < 09:00                        d               yes
OPEN        T(d), 09:00 <= t < 13:30               d               yes
CLOSED      T(d), 13:30 <= t < 15:00               d               yes
SETTLING    T(d), t >= 15:00, run(d) not finished  —               no
SETTLED     T(d), t >= 15:00, run(d) finished      next(d)         yes
==========  =====================================  ==============  =========

SETTLING blocks orders because an order placed after 15:00 belongs to
next(d), whose ±10% reference price is d's close — not imported yet.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional

import psycopg

from app import clock
from app.constants import (
    MARKET_CLOSE,
    MARKET_OPEN,
    RUN_DONE,
    RUN_FAILED,
    SETTLEMENT_TIME,
)
from app.errors import AppError

log = logging.getLogger(__name__)

HOLIDAY = "HOLIDAY"
PRE_OPEN = "PRE_OPEN"
OPEN = "OPEN"
CLOSED = "CLOSED"
SETTLING = "SETTLING"
SETTLED = "SETTLED"

PHASE_LABELS: Dict[str, str] = {
    HOLIDAY: "休市",
    PRE_OPEN: "盤前",
    OPEN: "盤中",
    CLOSED: "收盤",
    SETTLING: "結算中",
    SETTLED: "盤後",
}


# ---------------------------------------------------------------------------
# Calendar queries
# ---------------------------------------------------------------------------
def is_trading_day(conn: psycopg.Connection, d: date) -> bool:
    """Return whether ``d`` is a trading day.

    If the calendar has no row for ``d`` we fall back to "weekday = trading
    day" and log a warning; Admin should register the calendar in advance.
    """
    row = conn.execute(
        "SELECT is_trading_day FROM trading_calendar WHERE calendar_date = %s", (d,)
    ).fetchone()
    if row is None:
        log.warning("trading_calendar has no row for %s; assuming weekday rule", d)
        return d.weekday() < 5
    return bool(row["is_trading_day"])


def next_trading_day(conn: psycopg.Connection, d: date) -> date:
    """Return the first trading day strictly after ``d``.

    Raises:
        AppError(CALENDAR_MISSING): no future trading day is registered.
    """
    row = conn.execute(
        """
        SELECT MIN(calendar_date) AS d
        FROM trading_calendar
        WHERE calendar_date > %s AND is_trading_day
        """,
        (d,),
    ).fetchone()
    if row is None or row["d"] is None:
        raise AppError(
            "CALENDAR_MISSING",
            f"交易日曆尚未登錄 {d} 之後的交易日，請 Admin 補登。",
            status_code=503,
        )
    return row["d"]


def settlement_finished(conn: psycopg.Connection, d: date) -> bool:
    """Return whether the automatic 15:00 job for ``d`` has finished (done or failed)."""
    row = conn.execute(
        "SELECT status FROM settlement_run WHERE trade_date = %s", (d,)
    ).fetchone()
    return row is not None and row["status"] in (RUN_DONE, RUN_FAILED)


def latest_price_date(conn: psycopg.Connection) -> Optional[date]:
    """Return the most recent date that has any DAILY_PRICE row."""
    row = conn.execute("SELECT MAX(trade_date) AS d FROM daily_price").fetchone()
    return row["d"] if row else None


def reference_price(
    conn: psycopg.Connection, security_id: str, belong: date
) -> Optional[Decimal]:
    """Close of the latest price strictly before ``belong`` (the ±10% base).

    This is the same value the frontend shows as "開盤價（參考價）" on ``belong``.
    Returns ``None`` if the security has no price yet (orders not allowed).
    """
    row = conn.execute(
        """
        SELECT close_price
        FROM daily_price
        WHERE security_id = %s AND trade_date < %s
        ORDER BY trade_date DESC
        LIMIT 1
        """,
        (security_id, belong),
    ).fetchone()
    return row["close_price"] if row else None


# ---------------------------------------------------------------------------
# Phase / belong date
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class MarketStatus:
    """Snapshot of the market clock, returned by GET /api/market/status."""

    now: datetime
    today: date
    is_trading_day: bool
    phase: str
    phase_label: str
    can_place_order: bool
    order_belong_date: Optional[date]
    latest_price_date: Optional[date]
    message: str

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-friendly dict."""
        return asdict(self)


def phase_at(conn: psycopg.Connection, t: datetime) -> str:
    """Return the market phase constant for time ``t``."""
    d = t.date()
    if not is_trading_day(conn, d):
        return HOLIDAY
    clock_time = t.time()
    if clock_time < MARKET_OPEN:
        return PRE_OPEN
    if clock_time < MARKET_CLOSE:
        return OPEN
    if clock_time < SETTLEMENT_TIME:
        return CLOSED
    return SETTLED if settlement_finished(conn, d) else SETTLING


def order_belong_date(conn: psycopg.Connection, t: datetime) -> date:
    """Report rule: before 15:00 on a trading day -> today, else next trading day.

    Raises:
        AppError(SETTLING): called while today's settlement is still running.
        AppError(CALENDAR_MISSING): no next trading day registered.
    """
    phase = phase_at(conn, t)
    if phase == SETTLING:
        raise AppError("SETTLING", "盤後結算中，請待結算完成後再下單。", status_code=409)
    if phase in (PRE_OPEN, OPEN, CLOSED):
        return t.date()
    return next_trading_day(conn, t.date())


def market_status(conn: psycopg.Connection, t: Optional[datetime] = None) -> MarketStatus:
    """Build the status snapshot shown in the frontend status bar."""
    t = t or clock.now()
    phase = phase_at(conn, t)
    belong: Optional[date] = None
    message = ""
    try:
        if phase != SETTLING:
            belong = order_belong_date(conn, t)
    except AppError as exc:
        message = exc.message
    if phase == SETTLING:
        message = "今日 15:00 自動結算進行中，暫停下單。"
    return MarketStatus(
        now=t,
        today=t.date(),
        is_trading_day=phase != HOLIDAY,
        phase=phase,
        phase_label=PHASE_LABELS[phase],
        can_place_order=belong is not None,
        order_belong_date=belong,
        latest_price_date=latest_price_date(conn),
        message=message,
    )
