"""/api/securities — search, quotes, history, order rule."""

from __future__ import annotations

from datetime import date, timedelta
from typing import List, Optional

import psycopg
from fastapi import APIRouter, Depends, Query

from app import clock
from app.db import get_conn
from app.errors import AppError
from app.schemas import OrderRuleOut, PriceBarOut, QuoteOut, SecurityOut
from app.security import CurrentUser, current_user
from app.services import behavior_log, quote_service

router = APIRouter(prefix="/api/securities", tags=["securities"])


@router.get("", response_model=List[SecurityOut])
def search(
    q: str = Query("", description="證券代號前綴或名稱關鍵字"),
    limit: int = Query(20, ge=1, le=100),
    user: CurrentUser = Depends(current_user),
    conn: psycopg.Connection = Depends(get_conn),
) -> list:
    """Search active securities."""
    if q:
        behavior_log.log_event("search", user_id=user.user_id, query=q)
    return quote_service.search_securities(conn, q, limit)


@router.get("/quotes", response_model=List[QuoteOut])
def quotes(
    ids: str = Query(..., description="逗號分隔的證券代號，例如 2330,0050"),
    _: CurrentUser = Depends(current_user),
    conn: psycopg.Connection = Depends(get_conn),
) -> list:
    """Latest quotes for several securities."""
    id_list = [s.strip() for s in ids.split(",") if s.strip()]
    return quote_service.get_quotes(conn, id_list)


@router.get("/{security_id}/quote", response_model=QuoteOut)
def quote(
    security_id: str,
    user: CurrentUser = Depends(current_user),
    conn: psycopg.Connection = Depends(get_conn),
) -> dict:
    """Latest quote of one security (also logs a view event to MongoDB)."""
    behavior_log.log_event("view_security", user_id=user.user_id, security_id=security_id)
    rows = quote_service.get_quotes(conn, [security_id])
    if not rows:
        raise AppError("NOT_FOUND", f"找不到證券 {security_id}。", status_code=404)
    return rows[0]


@router.get("/{security_id}/history", response_model=List[PriceBarOut])
def history(
    security_id: str,
    date_from: Optional[date] = Query(None, alias="from"),
    date_to: Optional[date] = Query(None, alias="to"),
    _: CurrentUser = Depends(current_user),
    conn: psycopg.Connection = Depends(get_conn),
) -> list:
    """Daily bars, newest first. Defaults to the last 90 days."""
    end = date_to or clock.today()
    start = date_from or (end - timedelta(days=90))
    return quote_service.get_history(conn, security_id, start, end)


@router.get("/{security_id}/order-rule", response_model=OrderRuleOut)
def order_rule(
    security_id: str,
    _: CurrentUser = Depends(current_user),
    conn: psycopg.Connection = Depends(get_conn),
) -> dict:
    """Belong date, reference price and ±10% band for the order panel."""
    return quote_service.get_order_rule(conn, security_id)
