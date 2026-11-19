"""Password hashing, JWT tokens and role-based FastAPI dependencies.

Routers declare who may call them with one of:

* ``Depends(current_user)``  - any logged-in user
* ``Depends(require_user)``  - role = User (has an ACCOUNT)
* ``Depends(require_admin)`` - role = Admin
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.constants import ROLE_ADMIN, ROLE_USER
from app.errors import AppError

_bearer = HTTPBearer(auto_error=False)
_ALGORITHM = "HS256"


@dataclass(frozen=True)
class CurrentUser:
    """Identity extracted from a valid access token."""

    user_id: int
    user_name: str
    role: str


def hash_password(password: str) -> str:
    """Return a 60-char bcrypt hash (fits USERS.password_hash char(60))."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    """Check a plaintext password against a stored bcrypt hash."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.strip().encode("ascii"))


def create_access_token(user: CurrentUser) -> str:
    """Issue a signed JWT carrying user id, name and role."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": str(user.user_id),
        "name": user.user_name,
        "role": user.role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_ALGORITHM)


def current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> CurrentUser:
    """Resolve the caller from the ``Authorization: Bearer <token>`` header."""
    if credentials is None:
        raise AppError("UNAUTHENTICATED", "請先登入。", status_code=401)
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[_ALGORITHM])
    except jwt.PyJWTError:
        raise AppError("UNAUTHENTICATED", "登入已失效，請重新登入。", status_code=401)
    return CurrentUser(user_id=int(payload["sub"]), user_name=payload["name"], role=payload["role"])


def require_user(user: CurrentUser = Depends(current_user)) -> CurrentUser:
    """Allow only role = User."""
    if user.role != ROLE_USER:
        raise AppError("FORBIDDEN", "此功能僅限一般使用者。", status_code=403)
    return user


def require_admin(user: CurrentUser = Depends(current_user)) -> CurrentUser:
    """Allow only role = Admin."""
    if user.role != ROLE_ADMIN:
        raise AppError("FORBIDDEN", "此功能僅限管理者。", status_code=403)
    return user
