"""Request / response models — the API contract between backend and frontend.

Changing a field here is a breaking change for the frontend: update
docs/API.md and tell the frontend owner in the same PR.

Money and prices are ``Decimal`` and serialised as JSON strings
(e.g. ``"1000000.00"``) so no precision is lost in the browser; the frontend
formats them for display only.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

Side = Literal["買", "賣"]
OrderStatus = Literal["待成交", "已成交", "已取消", "已失效"]


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
class RegisterIn(BaseModel):
    user_name: str = Field(min_length=1, max_length=20)
    email: str = Field(min_length=3, max_length=50, pattern=r"^[^@\s]+@[^@\s]+$")
    password: str = Field(min_length=6, max_length=72)   # bcrypt limit is 72 bytes


class LoginIn(BaseModel):
    user_name: str
    password: str


class UserOut(BaseModel):
    user_id: int
    user_name: str
    email: str
    role: Literal["User", "Admin"]


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6, max_length=72)


# ---------------------------------------------------------------------------
# Market clock
# ---------------------------------------------------------------------------
class SettlementRunOut(BaseModel):
    trade_date: date
    status: Literal["執行中", "完成", "失敗"]
    started_at: datetime
    finished_at: Optional[datetime] = None
    price_rows: int
    filled_count: int
    expired_count: int
    message: Optional[str] = None


class MarketStatusOut(BaseModel):
    now: datetime
    today: date
    is_trading_day: bool
    phase: Literal["HOLIDAY", "PRE_OPEN", "OPEN", "CLOSED", "SETTLING", "SETTLED"]
    phase_label: str
    can_place_order: bool
    order_belong_date: Optional[date] = None
    latest_price_date: Optional[date] = None
    message: str = ""


# ---------------------------------------------------------------------------
# Securities & quotes
# ---------------------------------------------------------------------------
class SecurityOut(BaseModel):
    security_id: str
    security_name: str
    category_id: int
    category_name: str
    status: Literal["啟用", "停用"]


class QuoteOut(BaseModel):
    """Latest quote of one security.

    open_price = TWSE's real opening price (stored).
    prev_close = previous trading day's close (參考價／昨收, derived with LAG);
    change / change_pct are relative to prev_close.
    """

    security_id: str
    security_name: str
    category_name: str
    trade_date: Optional[date] = None
    prev_close: Optional[Decimal] = None
    open_price: Optional[Decimal] = None
    high_price: Optional[Decimal] = None
    low_price: Optional[Decimal] = None
    close_price: Optional[Decimal] = None
    volume: Optional[int] = None
    change: Optional[Decimal] = None
    change_pct: Optional[Decimal] = None


class PriceBarOut(BaseModel):
    """One day of history.

    open_price = real opening price; prev_close = previous trading day's close
    (None on the security's first day); change is relative to prev_close.
    """

    trade_date: date
    prev_close: Optional[Decimal] = None
    open_price: Decimal
    high_price: Decimal
    low_price: Decimal
    close_price: Decimal
    volume: int
    change: Optional[Decimal] = None
    change_pct: Optional[Decimal] = None


class OrderRuleOut(BaseModel):
    """What the order panel needs before submitting."""

    security_id: str
    order_belong_date: Optional[date] = None
    reference_price: Optional[Decimal] = None
    limit_low: Optional[Decimal] = None
    limit_high: Optional[Decimal] = None
    tradable: bool
    reason: str = ""


# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------
class WatchlistAddIn(BaseModel):
    security_id: str


# ---------------------------------------------------------------------------
# Orders & trades
# ---------------------------------------------------------------------------
class OrderCreateIn(BaseModel):
    security_id: str
    side: Side
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    quantity: int = Field(gt=0)


class OrderOut(BaseModel):
    order_id: int
    security_id: str
    security_name: str
    side: Side
    price: Decimal
    quantity: int
    submit_time: datetime
    belong_date: date
    status: OrderStatus


class TradeOut(BaseModel):
    trade_id: int
    order_id: int
    security_id: str
    security_name: str
    side: Side
    price: Decimal
    quantity: int
    amount: Decimal                       # price × quantity
    fee: Decimal
    tax: Decimal
    net_amount: Decimal                   # buy: -(amount+fee); sell: amount-fee-tax
    realized_profit: Optional[Decimal] = None
    trade_time: datetime


# ---------------------------------------------------------------------------
# Account & portfolio
# ---------------------------------------------------------------------------
class AccountOut(BaseModel):
    user_id: int
    available_cash: Decimal
    frozen_cash: Decimal
    status: Literal["啟用", "凍結"]


class HoldingOut(BaseModel):
    security_id: str
    security_name: str
    quantity: int
    frozen_quantity: int
    average_cost: Decimal
    current_price: Optional[Decimal] = None
    market_value: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None
    return_rate: Optional[Decimal] = None
    today_pnl: Optional[Decimal] = None


class PortfolioOut(BaseModel):
    holdings: List[HoldingOut]
    available_cash: Decimal
    frozen_cash: Decimal
    holdings_value: Decimal
    total_assets: Decimal


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------
class SecurityUpsertIn(BaseModel):
    security_id: str = Field(min_length=1, max_length=10)
    security_name: str = Field(min_length=1, max_length=50)
    category_id: int
    status: Literal["啟用", "停用"] = "啟用"


class SecurityUpdateIn(BaseModel):
    security_name: Optional[str] = Field(default=None, max_length=50)
    category_id: Optional[int] = None
    status: Optional[Literal["啟用", "停用"]] = None


class CalendarDayIn(BaseModel):
    calendar_date: date
    is_trading_day: bool


class CalendarDayOut(BaseModel):
    calendar_date: date
    is_trading_day: bool


class AccountStatusIn(BaseModel):
    status: Literal["啟用", "凍結"]


class UserSummaryOut(BaseModel):
    user_id: int
    user_name: str
    email: str
    role: Literal["User", "Admin"]
    account_status: Optional[Literal["啟用", "凍結"]] = None
    available_cash: Optional[Decimal] = None
    frozen_cash: Optional[Decimal] = None


class SecurityStatsOut(BaseModel):
    security_id: str
    security_name: str
    order_count: int
    filled_count: int
    fill_rate: Optional[Decimal] = None
    filled_shares: int


class OkOut(BaseModel):
    ok: bool = True
