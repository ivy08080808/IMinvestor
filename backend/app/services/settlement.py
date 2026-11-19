"""Daily settlement of pending orders. Owner: 模組 B 交易核心.

Called ONLY by ``app.jobs.run_for_date`` after the day's prices have been
imported. There is no manual trigger (plan v2: fully automatic at 15:00).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import psycopg

from app.errors import NotImplementedYet
from app.services import OWNER_B


@dataclass(frozen=True)
class SettleResult:
    """Counts written into SETTLEMENT_RUN."""

    filled: int
    expired: int


def settle_day(conn: psycopg.Connection, d: date) -> SettleResult:
    """Settle every order with ``belong_date = d`` and status '待成交'.

    Algorithm (plan §5.2), complexity O(K log N) for K pending orders:

    1. ``ids = SELECT order_id FROM orders WHERE belong_date = d AND status = '待成交'
       ORDER BY order_id`` (uses idx_orders_pending_belong).
    2. For EACH id, a separate ``with conn.transaction():`` so one failure only
       rolls back that order (report: "任一步驟失敗則該筆回復"):

       a. ``SELECT ... FROM orders WHERE order_id = :id FOR UPDATE``; skip if the
          status is no longer '待成交' (a cancel won the lock).
       b. Lock ACCOUNT, then HOLDING (lock order ORDERS -> ACCOUNT -> HOLDING).
       c. Expire (status '已失效', release freeze) when: account '凍結',
          security '停用', or no DAILY_PRICE row for (security, d).
       d. Fill condition: buy ``price > low_price``; sell ``price < high_price``
          (equal does NOT fill). Fill price = order price, whole quantity.
       e. Buy fill: frozen_cash -= fees.buy_freeze_amount(...);
          holding.average_cost = fees.new_average_cost(...); quantity += qty
          (INSERT holding row if absent). TRADE.realized_profit = NULL.
          Sell fill: holding.quantity -= qty, frozen_quantity -= qty;
          available_cash += fees.sell_credit(...);
          TRADE.realized_profit = fees.realized_profit(...).
          ``INSERT INTO trade (order_id, realized_profit, trade_time = clock.now())``;
          order status '已成交'.
       f. Not filled: status '已失效', release the freeze.
    3. Return the counts. If a transaction raises, log it, count the order as
       expired in a fresh transaction, and continue with the next order.
    """
    raise NotImplementedYet("盤後結算", OWNER_B)
