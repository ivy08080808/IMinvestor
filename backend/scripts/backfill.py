"""One-time historical backfill (run once at installation). Owner: 模組 A 行情與爬蟲.

Usage (from backend/)::

    python -m scripts.backfill --from 2026-01-01 --to 2026-11-19

Steps:
1. ``securities.sync_securities(conn)``
2. ``holidays.ensure_weekdays(conn, from, to)``
3. For each weekday d in range: ``payload = prices.fetch_mi_index(d)``;
   if ``stat != "OK"`` or no rows -> mark d non-trading in TRADING_CALENDAR;
   else insert rows (same code path as ``prices.import_daily_prices``).
4. ``holidays.sync_holidays(conn)`` for future dates.

Raw JSON is cached in data/raw/, so an interrupted run can simply be restarted.
After the backfill, daily data comes ONLY from the automatic 15:00 job.
"""

from __future__ import annotations

import argparse
import os
from datetime import date, timedelta

import psycopg

from crawler import holidays, prices, securities

DEFAULT_DSN = "postgresql://iminvestor:iminvestor_dev@localhost:5432/iminvestor"


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", dest="date_from", type=date.fromisoformat, default=date(2026, 1, 1))
    parser.add_argument("--to", dest="date_to", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()

    dsn = os.environ.get("DATABASE_URL", DEFAULT_DSN)
    today = date.today()
    failed = []
    trading_days = 0
    total_rows = 0

    with psycopg.connect(dsn) as conn:
        with conn.transaction():
            n = securities.sync_securities(conn)
        print(f"[1/4] securities synced, new: {n}")

        with conn.transaction():
            n = holidays.ensure_weekdays(conn, args.date_from, args.date_to)
        print(f"[2/4] calendar rows added: {n}")

        print(f"[3/4] importing prices {args.date_from} .. {args.date_to}")
        d = args.date_from
        while d <= args.date_to:
            if d.isoweekday() < 6:  # 週末不請求
                try:
                    rows = prices.parse_mi_index(prices.fetch_mi_index(d))
                    if rows:
                        inserted = prices.import_daily_prices(conn, d)
                        trading_days += 1
                        total_rows += inserted
                        print(f"  {d}  trading  parsed={len(rows)} inserted={inserted}")
                    elif d < today:
                        # 過去的平日沒有行情 = 休市
                        with conn.transaction():
                            with conn.cursor() as cur:
                                cur.execute(
                                    "UPDATE trading_calendar SET is_trading_day = FALSE "
                                    "WHERE calendar_date = %s",
                                    (d,),
                                )
                        print(f"  {d}  closed")
                    else:
                        print(f"  {d}  not published yet (left to the 15:00 job)")
                except Exception as exc:  # 單日失敗不中斷，最後列出來
                    failed.append(d)
                    print(f"  {d}  FAILED: {exc}")
            d += timedelta(days=1)

        with conn.transaction():
            n = holidays.sync_holidays(conn)
        print(f"[4/4] future holidays updated: {n}")

    print(f"done. trading days: {trading_days}, rows inserted: {total_rows}")
    if failed:
        print("failed dates (rerun the same command to retry):", ", ".join(map(str, failed)))


if __name__ == "__main__":
    main()