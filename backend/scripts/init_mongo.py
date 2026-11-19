"""Create MongoDB indexes for behaviour events (framework-owned, implemented).

Usage (from backend/)::

    python -m scripts.init_mongo
"""

from __future__ import annotations

from app.db import mongo
from app.services.behavior_log import COLLECTION


def main() -> None:
    """Create the indexes documented in app/services/behavior_log.py."""
    db = mongo()
    if db is None:
        raise SystemExit("MongoDB is not reachable; check MONGO_URL in .env")
    col = db[COLLECTION]
    col.create_index([("type", 1), ("ts", -1)])
    col.create_index([("security_id", 1), ("ts", -1)])
    print("MongoDB indexes ensured on", COLLECTION)


if __name__ == "__main__":
    main()
