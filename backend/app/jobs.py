"""The automatic 15:00 job: import the day's prices once, then settle (framework-owned).

Flow for trading day d (plan §4.3)::

    claim SETTLEMENT_RUN(d) ──> crawler.prices.import_daily_prices(d)  [模組 A]
                           └──> services.settlement.settle_day(d)       [模組 B]
                           └──> SETTLEMENT_RUN(d).status = 完成 / 失敗

* Exactly once per day: the claim is ``INSERT ... ON CONFLICT DO NOTHING``.
  A row stuck in 執行中 for > 30 min (process crashed) may be re-claimed.
* If the price import fails, settlement still runs: securities without a price
  row for d are treated as suspended and their orders expire (report rule).
* No manual trigger exists anywhere in the system.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import List, Optional

import psycopg

from app import clock, market
from app.constants import RUN_DONE, RUN_FAILED, RUN_RUNNING, SETTLEMENT_TIME
from app.db import connection
from app.errors import NotImplementedYet
from app.services import settlement
from crawler import prices

log = logging.getLogger(__name__)

STALE_AFTER = timedelta(minutes=30)


def _claim(conn: psycopg.Connection, d: date, now: datetime) -> bool:
    """Atomically claim day ``d``; return False if it is done or running elsewhere."""
    with conn.transaction():
        conn.execute(
            """
            INSERT INTO trading_calendar (calendar_date, is_trading_day)
            VALUES (%s, true) ON CONFLICT (calendar_date) DO NOTHING
            """,
            (d,),
        )
        row = conn.execute(
            """
            INSERT INTO settlement_run (trade_date, status, started_at)
            VALUES (%(d)s, %(running)s, %(now)s)
            ON CONFLICT (trade_date) DO UPDATE
                SET status = EXCLUDED.status, started_at = EXCLUDED.started_at,
                    finished_at = NULL, message = NULL
                WHERE settlement_run.status = %(running)s
                  AND settlement_run.started_at < %(stale)s
            RETURNING trade_date
            """,
            {"d": d, "running": RUN_RUNNING, "now": now, "stale": now - STALE_AFTER},
        ).fetchone()
    return row is not None


def _describe(exc: Exception) -> str:
    """Human-readable error text for SETTLEMENT_RUN.message."""
    return exc.message if isinstance(exc, NotImplementedYet) else str(exc)


def run_for_date(d: date) -> None:
    """Import prices for ``d`` and settle its orders, recording the outcome."""
    with connection() as conn:
        if not _claim(conn, d, clock.now()):
            log.info("settlement for %s already done or running; skip", d)
            return

        # A stub module (NotImplementedYet) is recorded like any other failure,
        # so the day still finishes and the market leaves SETTLING. To re-run a
        # day during development: DELETE FROM settlement_run WHERE trade_date = ...
        status, messages, price_rows, filled, expired = RUN_DONE, [], 0, 0, 0
        try:
            price_rows = prices.import_daily_prices(conn, d)
        except Exception as exc:  # noqa: BLE001 - recorded, settlement continues
            log.warning("price import failed for %s: %s", d, exc)
            messages.append(f"行情匯入失敗：{_describe(exc)}")

        try:
            result = settlement.settle_day(conn, d)
            filled, expired = result.filled, result.expired
        except Exception as exc:  # noqa: BLE001
            log.warning("settlement failed for %s: %s", d, exc)
            status = RUN_FAILED
            messages.append(f"結算失敗：{_describe(exc)}")

        with conn.transaction():
            conn.execute(
                """
                UPDATE settlement_run
                SET status = %s, finished_at = %s, price_rows = %s,
                    filled_count = %s, expired_count = %s, message = %s
                WHERE trade_date = %s
                """,
                (status, clock.now(), price_rows, filled, expired,
                 "；".join(messages) or None, d),
            )
        log.info("settlement %s: %s (prices=%s filled=%s expired=%s)",
                 d, status, price_rows, filled, expired)


def daily_job() -> None:
    """Scheduler entry point, fired at 15:00 Asia/Taipei on weekdays."""
    d = clock.today()
    with connection() as conn:
        if not market.is_trading_day(conn, d):
            log.info("%s is not a trading day; nothing to do", d)
            return
    run_for_date(d)


def _due_days(conn: psycopg.Connection, now: datetime) -> List[date]:
    """Trading days whose 15:00 has passed but which have no finished run."""
    today = now.date()
    if market.is_trading_day(conn, today) and now.time() >= SETTLEMENT_TIME:
        last_due: Optional[date] = today
    else:
        row = conn.execute(
            """
            SELECT MAX(calendar_date) AS d FROM trading_calendar
            WHERE calendar_date < %s AND is_trading_day
            """,
            (today,),
        ).fetchone()
        last_due = row["d"] if row else None
    if last_due is None:
        return []

    last_run = conn.execute("SELECT MAX(trade_date) AS d FROM settlement_run").fetchone()["d"]
    if last_run is None:
        # First start after installation: history came from the backfill,
        # so only the most recent due day needs the automatic job.
        return [last_due]
    rows = conn.execute(
        """
        SELECT calendar_date AS d FROM trading_calendar
        WHERE is_trading_day AND calendar_date > %s AND calendar_date <= %s
        UNION
        SELECT trade_date FROM settlement_run WHERE status = %s
        ORDER BY 1
        """,
        (last_run, last_due, RUN_RUNNING),
    ).fetchall()
    return [r["d"] for r in rows]


def catch_up() -> None:
    """On startup, run the job for days missed while the server was down."""
    with connection() as conn:
        days = _due_days(conn, clock.now())
    for d in days:
        log.info("catch-up settlement for %s", d)
        run_for_date(d)
