"""/api/auth — register, login, profile, password."""

from __future__ import annotations

import psycopg
from fastapi import APIRouter, Depends

from app.db import get_conn
from app.schemas import ChangePasswordIn, LoginIn, OkOut, RegisterIn, TokenOut, UserOut
from app.security import CurrentUser, current_user
from app.services import auth_service, behavior_log

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut, status_code=201)
def register(body: RegisterIn, conn: psycopg.Connection = Depends(get_conn)) -> dict:
    """Create a User with a 1,000,000 NTD account and log them in."""
    return auth_service.register(conn, body.user_name, body.email, body.password)


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, conn: psycopg.Connection = Depends(get_conn)) -> dict:
    """Exchange user name + password for a bearer token."""
    result = auth_service.login(conn, body.user_name, body.password)
    behavior_log.log_event("login", user_id=result["user"]["user_id"])
    return result


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser = Depends(current_user), conn: psycopg.Connection = Depends(get_conn)) -> dict:
    """Return the caller's profile."""
    return auth_service.get_me(conn, user.user_id)


@router.post("/password", response_model=OkOut)
def change_password(
    body: ChangePasswordIn,
    user: CurrentUser = Depends(current_user),
    conn: psycopg.Connection = Depends(get_conn),
) -> dict:
    """Change the caller's password."""
    auth_service.change_password(conn, user.user_id, body.old_password, body.new_password)
    return {"ok": True}
