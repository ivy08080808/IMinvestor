"""Runtime configuration loaded from environment variables / the project-root .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from dotenv import load_dotenv

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def _csv(value: str) -> List[str]:
    """Split a comma-separated env value into a list of non-empty strings."""
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    """Immutable application settings."""

    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql://iminvestor:iminvestor_dev@localhost:5432/iminvestor"
    )
    mongo_url: str = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    mongo_db: str = os.getenv("MONGO_DB", "iminvestor")
    jwt_secret: str = os.getenv("JWT_SECRET", "dev-only-change-me")
    jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "720"))
    cors_origins: List[str] = field(
        default_factory=lambda: _csv(
            os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
        )
    )
    scheduler_enabled: bool = os.getenv("SCHEDULER_ENABLED", "1") == "1"
    admin_username: str = os.getenv("ADMIN_USERNAME", "admin")
    admin_email: str = os.getenv("ADMIN_EMAIL", "admin@iminvestor.local")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "admin1234")


settings = Settings()
