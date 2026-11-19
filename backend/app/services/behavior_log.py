"""Behaviour events in MongoDB (NoSQL). Owner: 模組 D 前端、NoSQL 與分析.

Collection ``behavior_events`` — one document per event::

    {
      "user_id": 12,              # null when not logged in
      "type": "search" | "view_security" | "login",
      "security_id": "2330",      # for view_security
      "query": "台積",             # for search
      "ts": ISODate(...)          # Asia/Taipei wall-clock time
    }

Indexes (create in scripts/init_mongo.py): ``{type: 1, ts: -1}``,
``{security_id: 1, ts: -1}``.

``log_event`` is best-effort: it must never raise or slow down a request.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app import clock
from app.db import mongo
from app.errors import NotImplementedYet
from app.services import OWNER_D

log = logging.getLogger(__name__)

COLLECTION = "behavior_events"
EVENT_TYPES = ("search", "view_security", "login")


def log_event(
    event_type: str,
    user_id: Optional[int] = None,
    security_id: Optional[str] = None,
    query: Optional[str] = None,
) -> None:
    """Insert one event; silently skip if MongoDB is unavailable (implemented)."""
    if event_type not in EVENT_TYPES:
        raise ValueError(f"unknown event type {event_type}")
    db = mongo()
    if db is None:
        return
    try:
        db[COLLECTION].insert_one(
            {
                "user_id": user_id,
                "type": event_type,
                "security_id": security_id,
                "query": query,
                "ts": clock.now(),
            }
        )
    except Exception as exc:  # noqa: BLE001 - logging must never break a request
        log.warning("behavior log failed: %s", exc)


def view_to_order_conversion(days: int = 7, top: int = 20) -> List[Dict[str, Any]]:
    """Top-``top`` viewed securities in the last ``days`` days vs. their order counts.

    1. Mongo aggregation::

           [{"$match": {"type": "view_security", "ts": {"$gte": since}}},
            {"$group": {"_id": "$security_id", "views": {"$sum": 1},
                        "viewers": {"$addToSet": "$user_id"}}},
            {"$sort": {"views": -1}}, {"$limit": top}]

    2. PostgreSQL: order counts for those ids in the same window.
    3. Merge in Python -> [{security_id, views, unique_viewers, orders, conversion}].
    """
    raise NotImplementedYet("瀏覽→下單轉換率分析", OWNER_D)
