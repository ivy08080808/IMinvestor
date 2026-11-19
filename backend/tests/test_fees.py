"""Unit tests for app.fees (report §1.1.1 (四)). No database needed."""

from __future__ import annotations

from decimal import Decimal

from app import fees

D = Decimal


def test_commission_floor_and_minimum() -> None:
    assert fees.commission(D("100000.00")) == D("142")      # 142.5 -> 142
    assert fees.commission(D("500.00")) == D("1")           # 0.71 -> min 1


def test_tax_by_category() -> None:
    amount = D("100000.00")
    assert fees.transaction_tax(amount, D("0.003")) == D("300")
    assert fees.transaction_tax(amount, D("0.001")) == D("100")
    assert fees.transaction_tax(amount, D("0")) == D("0")


def test_buy_freeze_equals_amount_plus_fee() -> None:
    assert fees.buy_freeze_amount(D("100.00"), 1000) == D("100142.00")


def test_moving_average_cost_and_reset() -> None:
    first = fees.new_average_cost(D("0"), 0, D("100.00"), 1000)
    assert first == D("100.1420")
    second = fees.new_average_cost(first, 1000, D("110.00"), 1000)
    # (100142 + 110000 + 156) / 2000
    assert second == D("105.1490")


def test_realized_profit() -> None:
    # sell 1000 @ 110 with avg 100.142, stock tax 0.3%: 110000 - 156 - 330 - 100142
    assert fees.realized_profit(D("110.00"), 1000, D("0.003"), D("100.1420")) == D("9372.0000")


def test_price_limits_are_inclusive_and_valid_prices() -> None:
    assert fees.price_limits(D("100.00")) == (D("90.00"), D("110.00"))
    low, high = fees.price_limits(D("10.05"))           # 9.045 .. 11.055
    assert (low, high) == (D("9.05"), D("11.05"))
