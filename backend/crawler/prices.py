"""Daily prices from MI_INDEX. Owner: 模組 A 行情與爬蟲.

Interface used by ``app.jobs`` (do not change the signature):

    import_daily_prices(conn, d) -> int   # rows inserted into DAILY_PRICE
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

import psycopg

from crawler import twse_client


def fetch_mi_index(d: date, use_cache: bool = True) -> Dict[str, Any]:
    """Raw MI_INDEX JSON for ``d`` (implemented: thin wrapper over the client)."""
    return twse_client.get_json_cached(
        twse_client.MI_INDEX_URL,
        {"date": d.strftime("%Y%m%d"), "type": "ALLBUT0999", "response": "json"},
        cache_key=f"MI_INDEX/{d:%Y%m%d}",
        use_cache=use_cache,
    )


def _to_decimal(text: Any) -> Optional[Decimal]:
    s = str(text).replace(",", "").strip()
    if s in ("", "--", "---"):
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def parse_mi_index(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract price rows from an MI_INDEX payload.

    * Use the table in ``payload["tables"]`` whose title contains "每日收盤行情".
    * Strip thousands separators; skip rows whose close is "--" (no trade =
      suspended) or volume is 0 (violates ``volume > 0``).
    * ``payload["stat"] != "OK"`` (non-trading day / not published) -> ``[]``.
    """
    if str(payload.get("stat", "")).upper() != "OK":
        return []

    table = None
    for t in payload.get("tables") or []:
        if "每日收盤行情" in (t.get("title") or ""):
            table = t
            break
    if table is None or not table.get("data"):
        return []

    idx = {name: i for i, name in enumerate(table["fields"])}
    needed = ["證券代號", "成交股數", "開盤價", "最高價", "最低價", "收盤價"]
    if any(name not in idx for name in needed):
        raise ValueError(f"MI_INDEX 欄位名稱改變了: {table['fields']}")

    rows: List[Dict[str, Any]] = []
    for r in table["data"]:
        security_id = str(r[idx["證券代號"]]).strip()
        volume_dec = _to_decimal(r[idx["成交股數"]])
        o = _to_decimal(r[idx["開盤價"]])
        h = _to_decimal(r[idx["最高價"]])
        low = _to_decimal(r[idx["最低價"]])
        c = _to_decimal(r[idx["收盤價"]])
        if not security_id or volume_dec is None or volume_dec <= 0:
            continue
        if None in (o, h, low, c) or min(o, h, low, c) <= 0:
            continue
        # 符合資料表的 CHECK 條件，否則整批寫入會失敗
        if not (low <= o <= h and low <= c <= h):
            continue
        rows.append(
            {
                "security_id": security_id,
                "open_price": o,
                "high_price": h,
                "low_price": low,
                "close_price": c,
                "volume": int(volume_dec),
            }
        )
    return rows


def import_daily_prices(conn: psycopg.Connection, d: date) -> int:
    """Fetch, parse and insert DAILY_PRICE rows for ``d``; return rows inserted.

    * Called once per trading day at 15:00 by the scheduler (and by the backfill).
    * Insert only ids that exist in SECURITY; make sure TRADING_CALENDAR has ``d``.
    * ``INSERT ... ON CONFLICT (security_id, trade_date) DO NOTHING`` -> idempotent.
    * Commit inside ``with conn.transaction():``.
    """
    rows = parse_mi_index(fetch_mi_index(d))
    if not rows:
        return 0

    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute("SELECT security_id FROM security")
            known = {r[0] for r in cur.fetchall()}
            rows = [r for r in rows if r["security_id"] in known]
            if not rows:
                return 0

            # 有行情就代表這天是交易日（過去日期以行情為準）
            cur.execute(
                """
                INSERT INTO trading_calendar (calendar_date, is_trading_day)
                VALUES (%s, TRUE)
                ON CONFLICT (calendar_date) DO UPDATE SET is_trading_day = TRUE
                """,
                (d,),
            )
            cur.execute(
                """
                INSERT INTO daily_price
                    (security_id, trade_date, open_price, high_price, low_price, close_price, volume)
                SELECT t.sid, %s::date, t.o, t.h, t.l, t.c, t.v
                FROM unnest(%s::varchar[], %s::numeric[], %s::numeric[],
                            %s::numeric[], %s::numeric[], %s::bigint[]) AS t(sid, o, h, l, c, v)
                ON CONFLICT (security_id, trade_date) DO NOTHING
                """,
                (
                    d,
                    [r["security_id"] for r in rows],
                    [r["open_price"] for r in rows],
                    [r["high_price"] for r in rows],
                    [r["low_price"] for r in rows],
                    [r["close_price"] for r in rows],
                    [r["volume"] for r in rows],
                ),
            )
            return cur.rowcount