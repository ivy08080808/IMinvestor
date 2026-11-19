"""Registration, login and password change (framework-owned, implemented)."""

from __future__ import annotations

from typing import Any, Dict

import psycopg
from psycopg import errors as pg_errors

from app.constants import ACCOUNT_ACTIVE, INITIAL_CASH, ROLE_USER
from app.errors import AppError
from app.security import CurrentUser, create_access_token, hash_password, verify_password


def register(conn: psycopg.Connection, user_name: str, email: str, password: str) -> Dict[str, Any]:
    """Create a User and its ACCOUNT with the initial cash, in one transaction.

    SQL::

        INSERT INTO users (user_name, password_hash, email, role) VALUES (...) RETURNING ...;
        INSERT INTO account (user_id, available_cash, frozen_cash, status)
        VALUES (:user_id, 1000000.00, 0, '啟用');
    """
    try:
        with conn.transaction():
            user = conn.execute(
                """
                INSERT INTO users (user_name, password_hash, email, role)
                VALUES (%s, %s, %s, %s)
                RETURNING user_id, user_name, email, role
                """,
                (user_name, hash_password(password), email, ROLE_USER),
            ).fetchone()
            conn.execute(
                """
                INSERT INTO account (user_id, available_cash, frozen_cash, status)
                VALUES (%s, %s, 0, %s)
                """,
                (user["user_id"], INITIAL_CASH, ACCOUNT_ACTIVE),
            )
    except pg_errors.UniqueViolation:
        raise AppError("USER_EXISTS", "使用者名稱或信箱已被使用。", status_code=409)
    return _token_response(user)


def login(conn: psycopg.Connection, user_name: str, password: str) -> Dict[str, Any]:
    """Verify credentials and issue an access token."""
    user = conn.execute(
        "SELECT user_id, user_name, email, role, password_hash FROM users WHERE user_name = %s",
        (user_name,),
    ).fetchone()
    if user is None or not verify_password(password, user["password_hash"]):
        raise AppError("BAD_CREDENTIALS", "帳號或密碼錯誤。", status_code=401)
    return _token_response(user)


def get_me(conn: psycopg.Connection, user_id: int) -> Dict[str, Any]:
    """Return the caller's profile."""
    user = conn.execute(
        "SELECT user_id, user_name, email, role FROM users WHERE user_id = %s", (user_id,)
    ).fetchone()
    if user is None:
        raise AppError("NOT_FOUND", "找不到使用者。", status_code=404)
    return user


def change_password(
    conn: psycopg.Connection, user_id: int, old_password: str, new_password: str
) -> None:
    """Replace the password hash after verifying the old password."""
    with conn.transaction():
        row = conn.execute(
            "SELECT password_hash FROM users WHERE user_id = %s FOR UPDATE", (user_id,)
        ).fetchone()
        if row is None or not verify_password(old_password, row["password_hash"]):
            raise AppError("BAD_CREDENTIALS", "舊密碼錯誤。", status_code=400)
        conn.execute(
            "UPDATE users SET password_hash = %s WHERE user_id = %s",
            (hash_password(new_password), user_id),
        )


def _token_response(user: Dict[str, Any]) -> Dict[str, Any]:
    """Build the TokenOut payload."""
    token = create_access_token(
        CurrentUser(user_id=user["user_id"], user_name=user["user_name"], role=user["role"])
    )
    profile = {k: user[k] for k in ("user_id", "user_name", "email", "role")}
    return {"access_token": token, "token_type": "bearer", "user": profile}
