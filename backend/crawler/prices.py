"""Daily prices from MI_INDEX. Owner: 模組 A 行情與爬蟲.

Interface used by ``app.jobs`` (do not change the signature):

    import_daily_prices(conn, d) -> int   # rows inserted into DAILY_PRICE
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List

import psycopg

from app.errors import NotImplementedYet
from app.services import OWNER_A
from crawler import twse_client


def fetch_mi_index(d: date, use_cache: bool = True) -> Dict[str, Any]:
    """Raw MI_INDEX JSON for ``d`` (implemented: thin wrapper over the client)."""
    return twse_client.get_json_cached(
        twse_client.MI_INDEX_URL,
        {"date": d.strftime("%Y%m%d"), "type": "ALLBUT0999", "response": "json"},
        cache_key=f"MI_INDEX/{d:%Y%m%d}",
        use_cache=use_cache,
    )


def parse_mi_index(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract price rows from an MI_INDEX payload.

    * Use the table in ``payload["tables"]`` whose title contains "每日收盤行情".
    * Fields: 證券代號, 證券名稱, 成交股數, 成交筆數, 成交金額, 開盤價, 最高價,
      最低價, 收盤價, ... (index by field name, not by position).
    * Strip thousands separators; skip rows whose close is "--" (no trade =
      suspended) or volume is 0 (violates ``volume > 0``).
    * Return ``[{"security_id", "high_price", "low_price", "close_price",
      "volume"}]`` with Decimal prices and int volume. Do NOT keep 開盤價
      (plan §2: open is derived from the previous close).
    * ``payload["stat"] != "OK"`` (non-trading day / not published) -> ``[]``.
    """
    raise NotImplementedYet("解析每日收盤行情", OWNER_A)


def import_daily_prices(conn: psycopg.Connection, d: date) -> int:
    """Fetch, parse and insert DAILY_PRICE rows for ``d``; return rows inserted.

    * Called once per trading day at 15:00 by the scheduler (and by the backfill).
    * Insert only ids that exist in SECURITY; make sure TRADING_CALENDAR has ``d``.
    * ``INSERT ... ON CONFLICT (security_id, trade_date) DO NOTHING`` -> idempotent.
    * Commit inside ``with conn.transaction():``.
    * Raise on network/parse failure; ``app.jobs`` records it and settlement
      then expires that day's orders.
    """
    raise NotImplementedYet("匯入每日行情", OWNER_A)
