"""Order placement, cancellation and order history. Owner: 模組 B 交易核心.

Lock order (plan §5.1) — every write path in the system follows it:

    ORDERS  ->  ACCOUNT  ->  HOLDING

Placement never locks existing ORDERS rows, so it cannot deadlock with
cancel / settlement. Use READ COMMITTED (default) + explicit FOR UPDATE.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

import psycopg

from app.errors import NotImplementedYet
from app.services import OWNER_B


def place_order(
    conn: psycopg.Connection,
    user_id: int,
    security_id: str,
    side: str,
    price: Decimal,
    quantity: int,
) -> Dict[str, Any]:
    """Validate and create a limit order, freezing cash (buy) or shares (sell).

    Returns the created order as an ``OrderOut`` dict.

    Steps, all inside ONE ``with conn.transaction():``

    1. ``t = clock.now()``; ``belong = market.order_belong_date(conn, t)``
       (raises SETTLING / CALENDAR_MISSING).
    2. ``SELECT ... FROM account WHERE user_id = :uid FOR UPDATE``;
       status must be '啟用' else AppError("ACCOUNT_FROZEN").
    3. Security must exist with status '啟用' else AppError("SECURITY_DISABLED").
    4. ``ref = market.reference_price(conn, sid, belong)``; None ->
       AppError("NO_PRICE"); ``low, high = fees.price_limits(ref)``;
       price outside [low, high] -> AppError("PRICE_OUT_OF_RANGE").
    5. Buy: ``need = fees.buy_freeze_amount(price, qty)``;
       available_cash < need -> AppError("INSUFFICIENT_CASH");
       ``UPDATE account SET available_cash = available_cash - need,
       frozen_cash = frozen_cash + need``.
       Sell: ``SELECT ... FROM holding WHERE user_id AND security_id FOR UPDATE``;
       quantity - frozen_quantity < qty -> AppError("INSUFFICIENT_SHARES");
       ``UPDATE holding SET frozen_quantity = frozen_quantity + qty``.
    6. ``INSERT INTO orders (..., submit_time = t, belong_date = belong,
       status = '待成交') RETURNING *``.
    7. ``behavior_log.log_event(...)`` is NOT needed here (orders are in PG).
    """
    raise NotImplementedYet("下單", OWNER_B)


def cancel_order(conn: psycopg.Connection, user_id: int, order_id: int) -> Dict[str, Any]:
    """Cancel a pending order and release its frozen cash / shares.

    Allowed even when the account is frozen (report §1.1.1).

    1. ``SELECT * FROM orders WHERE order_id = :oid AND user_id = :uid FOR UPDATE``
       (not found -> 404). Status != '待成交' -> AppError("NOT_CANCELLABLE")
       — this is how "settlement got the lock first" surfaces to the user.
    2. Buy: release ``fees.buy_freeze_amount(price, qty)`` from frozen_cash
       back to available_cash (lock ACCOUNT). Sell: frozen_quantity -= qty
       (lock HOLDING).
    3. ``UPDATE orders SET status = '已取消'``. Return the ``OrderOut`` dict.
    """
    raise NotImplementedYet("取消委託", OWNER_B)


def list_orders(
    conn: psycopg.Connection,
    user_id: Optional[int],
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Orders newest first (``OrderOut`` dicts). ``user_id=None`` = all users (Admin).

    Uses idx_orders_user_submit.
    """
    raise NotImplementedYet("查詢委託紀錄", OWNER_B)
