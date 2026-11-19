"""/api/market — market clock and automatic settlement status (public)."""

from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends

from app import market
from app.db import get_conn
from app.schemas import MarketStatusOut

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/status", response_model=MarketStatusOut)
def status(conn: psycopg.Connection = Depends(get_conn)) -> dict:
    """Current Taipei time, phase, whether orders are accepted and their belong date."""
    return market.market_status(conn).to_dict()
