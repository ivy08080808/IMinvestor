"""Create (or re-create) the PostgreSQL schema and the default Admin.

Usage (from backend/)::

    python -m scripts.init_db            # schema + triggers + indexes + seed + admin
    python -m scripts.init_db --keep     # only (re)apply triggers/indexes/seed/admin

WARNING: without --keep, 00_schema.sql DROPs every table first.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from app.config import settings
from app.constants import ROLE_ADMIN
from app.db import connect_direct
from app.security import hash_password

SQL_DIR = Path(__file__).resolve().parents[1] / "sql"


def run_sql_file(conn, path: Path) -> None:  # type: ignore[no-untyped-def]
    """Execute one .sql file as a single script."""
    print(f"-> {path.name}")
    conn.execute(path.read_text(encoding="utf-8"))


def ensure_admin(conn) -> None:  # type: ignore[no-untyped-def]
    """Create the default Admin from .env if it does not exist."""
    conn.execute(
        """
        INSERT INTO users (user_name, password_hash, email, role)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (user_name) DO NOTHING
        """,
        (settings.admin_username, hash_password(settings.admin_password),
         settings.admin_email, ROLE_ADMIN),
    )
    print(f"-> admin user '{settings.admin_username}' ensured")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep", action="store_true", help="do not drop/recreate tables")
    args = parser.parse_args()

    with connect_direct() as conn:
        files = ["01_triggers.sql", "02_indexes.sql", "03_seed.sql"]
        if not args.keep:
            files.insert(0, "00_schema.sql")
        for name in files:
            run_sql_file(conn, SQL_DIR / name)
        ensure_admin(conn)
    print("done.")


if __name__ == "__main__":
    main()
