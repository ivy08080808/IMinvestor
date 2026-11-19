"""/api/orders, /api/trades, /api/account, /api/portfolio — the caller's trading (role User)."""

from __future__ import annotations

from typing import List, Optional

import psycopg
from fastapi import APIRouter, Depends, Query

from app.db import get_conn
from app.schemas import AccountOut, OrderCreateIn, OrderOut, PortfolioOut, TradeOut
from app.security import CurrentUser, require_user
from app.services import order_service, portfolio_service

router = APIRouter(prefix="/api", tags=["trading"])


@router.post("/orders", response_model=OrderOut, status_code=201)
def place_order(body: OrderCreateIn, user: CurrentUser = Depends(require_user),
                conn: psycopg.Connection = Depends(get_conn)) -> dict:
    """Submit a limit order."""
    return order_service.place_order(conn, user.user_id, body.security_id, body.side,
                                     body.price, body.quantity)


@router.post("/orders/{order_id}/cancel", response_model=OrderOut)
def cancel_order(order_id: int, user: CurrentUser = Depends(require_user),
                 conn: psycopg.Connection = Depends(get_conn)) -> dict:
    """Cancel a pending order."""
    return order_service.cancel_order(conn, user.user_id, order_id)


@router.get("/orders", response_model=List[OrderOut])
def list_orders(
    status: Optional[str] = Query(None, description="待成交 / 已成交 / 已取消 / 已失效"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: CurrentUser = Depends(require_user),
    conn: psycopg.Connection = Depends(get_conn),
) -> list:
    """The caller's orders, newest first."""
    return order_service.list_orders(conn, user.user_id, status, limit, offset)


@router.get("/trades", response_model=List[TradeOut])
def list_trades(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: CurrentUser = Depends(require_user),
    conn: psycopg.Connection = Depends(get_conn),
) -> list:
    """The caller's trades, newest first (also serves the cash-detail page)."""
    return portfolio_service.list_trades(conn, user.user_id, limit, offset)


@router.get("/account", response_model=AccountOut)
def account(user: CurrentUser = Depends(require_user),
            conn: psycopg.Connection = Depends(get_conn)) -> dict:
    """Available and frozen cash, account status."""
    return portfolio_service.get_account(conn, user.user_id)


@router.get("/portfolio", response_model=PortfolioOut)
def portfolio(user: CurrentUser = Depends(require_user),
              conn: psycopg.Connection = Depends(get_conn)) -> dict:
    """Holdings with live P&L and total assets."""
    return portfolio_service.get_portfolio(conn, user.user_id)
