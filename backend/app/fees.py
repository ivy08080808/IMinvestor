"""Pure money calculations (report §1.1.1 (四)). No database access.

All functions take and return :class:`~decimal.Decimal`; never pass floats.
Settlement, order placement and the frontend estimate must all use these
functions so the numbers agree everywhere.

Definitions, for price :math:`P`, quantity :math:`q`, amount :math:`A = Pq`:

* commission  :math:`f = \\max(1, \\lfloor 0.001425 A \\rfloor)`
* tax (sell)  :math:`x = \\lfloor r_c A \\rfloor`, :math:`r_c` = category tax rate
* buy freeze  :math:`A + f`
* sell credit :math:`A - f - x`
* new average cost after buying :math:`q` with holding :math:`Q` at :math:`\\bar c`:
  :math:`\\bar c' = (\\bar c Q + A + f) / (Q + q)`, rounded to 4 dp
* realized P&L of a sell :math:`A - f - x - \\bar c q`
"""

from __future__ import annotations

from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, Decimal
from typing import Tuple

from app.constants import COMMISSION_RATE, MIN_COMMISSION, PRICE_LIMIT_RATE

_CENT = Decimal("0.01")
_ONE = Decimal("1")
_COST_DP = Decimal("0.0001")


def trade_amount(price: Decimal, quantity: int) -> Decimal:
    """Return price × quantity rounded to 2 dp."""
    return (price * quantity).quantize(_CENT, rounding=ROUND_HALF_UP)


def commission(amount: Decimal) -> Decimal:
    """Return the brokerage fee: floor(amount × 0.1425%), minimum 1 NTD."""
    fee = (amount * COMMISSION_RATE).quantize(_ONE, rounding=ROUND_FLOOR)
    return max(fee, MIN_COMMISSION)


def transaction_tax(amount: Decimal, tax_rate: Decimal) -> Decimal:
    """Return the securities transaction tax (sell only): floor(amount × rate)."""
    return (amount * tax_rate).quantize(_ONE, rounding=ROUND_FLOOR)


def buy_freeze_amount(price: Decimal, quantity: int) -> Decimal:
    """Cash frozen when a buy order is placed (= cash debited when it fills)."""
    amount = trade_amount(price, quantity)
    return amount + commission(amount)


def sell_credit(price: Decimal, quantity: int, tax_rate: Decimal) -> Decimal:
    """Cash credited when a sell order fills."""
    amount = trade_amount(price, quantity)
    return amount - commission(amount) - transaction_tax(amount, tax_rate)


def new_average_cost(
    old_avg: Decimal, old_qty: int, price: Decimal, buy_qty: int
) -> Decimal:
    """Moving-average cost after a buy fill; resets naturally when old_qty == 0."""
    if old_qty + buy_qty <= 0:
        raise ValueError("resulting quantity must be positive")
    amount = trade_amount(price, buy_qty)
    total = old_avg * old_qty + amount + commission(amount)
    return (total / (old_qty + buy_qty)).quantize(_COST_DP, rounding=ROUND_HALF_UP)


def realized_profit(
    price: Decimal, quantity: int, tax_rate: Decimal, average_cost: Decimal
) -> Decimal:
    """Realized P&L of a sell fill, rounded to 4 dp (TRADE.realized_profit)."""
    profit = sell_credit(price, quantity, tax_rate) - average_cost * quantity
    return profit.quantize(_COST_DP, rounding=ROUND_HALF_UP)


def price_limits(reference_price: Decimal) -> Tuple[Decimal, Decimal]:
    """Return the inclusive [low, high] order-price band (±10% of reference).

    The band is rounded inward to 2 dp so that every returned bound is itself
    a valid order price.
    """
    low = (reference_price * (1 - PRICE_LIMIT_RATE)).quantize(_CENT, rounding=ROUND_CEILING)
    high = (reference_price * (1 + PRICE_LIMIT_RATE)).quantize(_CENT, rounding=ROUND_FLOOR)
    return low, high
