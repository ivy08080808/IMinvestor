"""Account, holdings with live P&L, and trade history. Owner: 模組 C 帳務與管理.

P&L is computed at query time and never stored (report §1.1.1 (五)):

* current price  = close of the latest DAILY_PRICE row
* unrealized P&L = current×qty − est. sell fee − est. tax − avg_cost×qty
  (use ``fees.commission`` / ``fees.transaction_tax`` with the category tax rate)
* return rate    = unrealized P&L ÷ (avg_cost × qty)
* today P&L      = (current − previous close) × qty
* total assets   = available_cash + frozen_cash + Σ current×qty
"""

from __future__ import annotations

from typing import Any, Dict, List

import psycopg

from app.errors import AppError, NotImplementedYet
from app.services import OWNER_C


def get_account(conn: psycopg.Connection, user_id: int) -> Dict[str, Any]:
    """Return the ``AccountOut`` dict (implemented: needed by the status bar)."""
    row = conn.execute(
        "SELECT user_id, available_cash, frozen_cash, status FROM account WHERE user_id = %s",
        (user_id,),
    ).fetchone()
    if row is None:
        raise AppError("NOT_FOUND", "找不到資金帳戶。", status_code=404)
    return row


def get_portfolio(conn: psycopg.Connection, user_id: int) -> Dict[str, Any]:
    """Holdings with quantity > 0 plus totals. Returns a ``PortfolioOut`` dict."""
    raise NotImplementedYet("庫存與損益", OWNER_C)


def list_trades(
    conn: psycopg.Connection, user_id: int, limit: int = 50, offset: int = 0
) -> List[Dict[str, Any]]:
    """Trade history newest first (``TradeOut`` dicts).

    TRADE stores only order_id / realized_profit / trade_time; price, quantity,
    side come from ORDERS, and amount / fee / tax are recomputed with ``app.fees``
    (report §2.2: derived values are not stored).
    """
    raise NotImplementedYet("成交紀錄", OWNER_C)
