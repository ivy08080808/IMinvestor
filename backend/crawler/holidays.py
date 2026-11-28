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

import json
from datetime import date, datetime
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import psycopg

HOLIDAY_URL = "https://www.twse.com.tw/rwd/zh/holidaySchedule/holidaySchedule?response=json"


def ensure_weekdays(conn: psycopg.Connection, start: date, end: date) -> int:
    """Insert a row for every date in [start, end] (weekday = trading) if missing."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO trading_calendar (calendar_date, is_trading_day)
            SELECT d::date, EXTRACT(ISODOW FROM d) < 6
            FROM generate_series(%s::date, %s::date, interval '1 day') d
            ON CONFLICT DO NOTHING
            """,
            (start, end),
        )
        return cur.rowcount


def _today_taipei() -> date:
    return datetime.now(ZoneInfo("Asia/Taipei")).date()


def _fetch_holiday_rows() -> list:
    req = Request(HOLIDAY_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    if str(payload.get("stat", "")).lower() != "ok":
        raise RuntimeError(f"TWSE holidaySchedule 回傳異常: {payload.get('stat')}")
    return payload["data"]


def sync_holidays(conn: psycopg.Connection) -> int:
    """Apply the TWSE holiday table to future dates; return rows changed."""
    rows = _fetch_holiday_rows()
    if not rows:
        return 0

    parsed = []
    for row in rows:
        d = date.fromisoformat(row[0])
        name = row[1]
        is_trading = ("開始交易日" in name) or ("最後交易日" in name)
        if d.isoweekday() >= 6:  # 週末一律非交易日
            is_trading = False
        parsed.append((d, is_trading))

    year = min(d for d, _ in parsed).year
    ensure_weekdays(conn, date(year, 1, 1), date(year, 12, 31))

    today = _today_taipei()
    changed = 0
    with conn.cursor() as cur:
        for d, is_trading in parsed:
            if d <= today:
                continue
            cur.execute(
                """
                UPDATE trading_calendar SET is_trading_day = %s
                WHERE calendar_date = %s AND is_trading_day IS DISTINCT FROM %s
                """,
                (is_trading, d, is_trading),
            )
            changed += cur.rowcount
    return changed