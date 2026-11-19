"""Trading calendar maintenance. Owner: 模組 A 行情與爬蟲.

* Past dates: a date is a trading day iff MI_INDEX for it returns stat "OK"
  with price rows (set by the backfill).
* Future dates: weekends are non-trading; then apply the TWSE holiday table.
  "市場無交易，僅辦理結算交割作業" = non-trading; "開始交易日" /
  "最後交易日" = trading. The endpoint ignores ``queryYear`` and returns the
  latest published year only (verified 2026-11-19).
* Admin edits (typhoon days) must not be overwritten for dates in the past.
"""

from __future__ import annotations

from datetime import date

import psycopg

from app.errors import NotImplementedYet
from app.services import OWNER_A


def ensure_weekdays(conn: psycopg.Connection, start: date, end: date) -> int:
    """Insert a row for every date in [start, end] (weekday = trading) if missing.

    ``INSERT ... SELECT d::date, EXTRACT(ISODOW FROM d) < 6
    FROM generate_series(start, end, interval '1 day') d ON CONFLICT DO NOTHING``
    """
    raise NotImplementedYet("建立交易日曆", OWNER_A)


def sync_holidays(conn: psycopg.Connection) -> int:
    """Apply the TWSE holiday table to future dates; return rows changed."""
    raise NotImplementedYet("同步休市日", OWNER_A)
