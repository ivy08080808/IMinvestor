"""/api/watchlist — the caller's watchlist (role User)."""

from __future__ import annotations

from typing import List

import psycopg
from fastapi import APIRouter, Depends

from app.db import get_conn
from app.schemas import OkOut, QuoteOut, WatchlistAddIn
from app.security import CurrentUser, require_user
from app.services import watchlist_service

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


@router.get("", response_model=List[QuoteOut])
def list_watchlist(user: CurrentUser = Depends(require_user),
                   conn: psycopg.Connection = Depends(get_conn)) -> list:
    """Watched securities with latest quotes."""
    return watchlist_service.list_watchlist(conn, user.user_id)


@router.post("", response_model=OkOut, status_code=201)
def add(body: WatchlistAddIn, user: CurrentUser = Depends(require_user),
        conn: psycopg.Connection = Depends(get_conn)) -> dict:
    """Add a security to the watchlist."""
    watchlist_service.add(conn, user.user_id, body.security_id)
    return {"ok": True}


@router.delete("/{security_id}", response_model=OkOut)
def remove(security_id: str, user: CurrentUser = Depends(require_user),
           conn: psycopg.Connection = Depends(get_conn)) -> dict:
    """Remove a security from the watchlist."""
    watchlist_service.remove(conn, user.user_id, security_id)
    return {"ok": True}
