"""/api/admin — 業務經營者 functions (role Admin)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import List, Optional

import psycopg
from fastapi import APIRouter, Depends, Query

from app import clock
from app.db import get_conn
from app.schemas import (
    AccountOut,
    AccountStatusIn,
    CalendarDayIn,
    CalendarDayOut,
    OrderOut,
    PortfolioOut,
    SecurityOut,
    SecurityStatsOut,
    SecurityUpdateIn,
    SecurityUpsertIn,
    SettlementRunOut,
    TradeOut,
    UserSummaryOut,
)
from app.security import CurrentUser, require_admin
from app.services import admin_service, order_service, portfolio_service

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


# ---- securities ---------------------------------------------------------------
@router.get("/securities", response_model=List[SecurityOut])
def list_securities(q: Optional[str] = None, limit: int = Query(50, ge=1, le=500),
                    offset: int = Query(0, ge=0),
                    conn: psycopg.Connection = Depends(get_conn)) -> list:
    """All securities including disabled ones."""
    return admin_service.list_securities(conn, q, limit, offset)


@router.post("/securities", response_model=SecurityOut, status_code=201)
def create_security(body: SecurityUpsertIn, conn: psycopg.Connection = Depends(get_conn)) -> dict:
    """Add a security."""
    return admin_service.create_security(conn, body.model_dump())


@router.patch("/securities/{security_id}", response_model=SecurityOut)
def update_security(security_id: str, body: SecurityUpdateIn,
                    conn: psycopg.Connection = Depends(get_conn)) -> dict:
    """Edit name / category / status (status 停用 replaces deletion)."""
    return admin_service.update_security(conn, security_id, body.model_dump(exclude_none=True))


# ---- calendar -----------------------------------------------------------------
@router.get("/calendar", response_model=List[CalendarDayOut])
def list_calendar(date_from: Optional[date] = Query(None, alias="from"),
                  date_to: Optional[date] = Query(None, alias="to"),
                  conn: psycopg.Connection = Depends(get_conn)) -> list:
    """Calendar rows; defaults to today .. +60 days."""
    start = date_from or clock.today()
    end = date_to or (start + timedelta(days=60))
    return admin_service.list_calendar(conn, start, end)


@router.put("/calendar", response_model=CalendarDayOut)
def upsert_calendar_day(body: CalendarDayIn, conn: psycopg.Connection = Depends(get_conn)) -> dict:
    """Register a holiday (or a make-up trading day)."""
    return admin_service.upsert_calendar_day(conn, body.calendar_date, body.is_trading_day)


# ---- users --------------------------------------------------------------------
@router.get("/users", response_model=List[UserSummaryOut])
def list_users(q: Optional[str] = None, limit: int = Query(50, ge=1, le=500),
               offset: int = Query(0, ge=0),
               conn: psycopg.Connection = Depends(get_conn)) -> list:
    """Users with account status and cash."""
    return admin_service.list_users(conn, q, limit, offset)


@router.put("/users/{user_id}/status", response_model=AccountOut)
def set_account_status(user_id: int, body: AccountStatusIn,
                       conn: psycopg.Connection = Depends(get_conn)) -> dict:
    """Freeze or unfreeze an account. Users are never deleted."""
    return admin_service.set_account_status(conn, user_id, body.status)


@router.get("/users/{user_id}/portfolio", response_model=PortfolioOut)
def user_portfolio(user_id: int, conn: psycopg.Connection = Depends(get_conn)) -> dict:
    """Any user's holdings (reuses the user-side service)."""
    return portfolio_service.get_portfolio(conn, user_id)


@router.get("/users/{user_id}/orders", response_model=List[OrderOut])
def user_orders(user_id: int, status: Optional[str] = None,
                limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0),
                conn: psycopg.Connection = Depends(get_conn)) -> list:
    """Any user's orders."""
    return order_service.list_orders(conn, user_id, status, limit, offset)


@router.get("/users/{user_id}/trades", response_model=List[TradeOut])
def user_trades(user_id: int, limit: int = Query(50, ge=1, le=500),
                offset: int = Query(0, ge=0),
                conn: psycopg.Connection = Depends(get_conn)) -> list:
    """Any user's trades."""
    return portfolio_service.list_trades(conn, user_id, limit, offset)


# ---- statistics & automation ------------------------------------------------------
@router.get("/stats/securities", response_model=List[SecurityStatsOut])
def security_stats(date_from: Optional[date] = Query(None, alias="from"),
                   date_to: Optional[date] = Query(None, alias="to"),
                   limit: int = Query(50, ge=1, le=500),
                   conn: psycopg.Connection = Depends(get_conn)) -> list:
    """Per-security order and fill statistics; defaults to the last 30 days."""
    end = date_to or clock.today()
    start = date_from or (end - timedelta(days=30))
    return admin_service.security_stats(conn, start, end, limit)


@router.get("/settlement-runs", response_model=List[SettlementRunOut])
def settlement_runs(limit: int = Query(30, ge=1, le=365),
                    conn: psycopg.Connection = Depends(get_conn)) -> list:
    """History of the automatic 15:00 jobs (read-only; there is no manual trigger)."""
    return admin_service.list_settlement_runs(conn, limit)
