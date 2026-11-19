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
from datetime import date


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", dest="date_from", type=date.fromisoformat, default=date(2026, 1, 1))
    parser.add_argument("--to", dest="date_to", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()
    raise SystemExit(f"TODO(模組 A): backfill {args.date_from} .. {args.date_to}")


if __name__ == "__main__":
    main()
