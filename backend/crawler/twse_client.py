"""Polite HTTP client for TWSE (framework-owned, implemented).

TWSE temporarily blocks IPs that send requests too quickly, so every request
goes through :func:`get` which enforces a minimum interval and retries with
exponential back-off. JSON responses can be cached on disk so an interrupted
backfill resumes without re-downloading.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from app.config import PROJECT_ROOT

log = logging.getLogger(__name__)

MI_INDEX_URL = "https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX"
HOLIDAY_URL = "https://www.twse.com.tw/rwd/zh/holidaySchedule/holidaySchedule"
ISIN_URL = "https://isin.twse.com.tw/isin/C_public.jsp"

CACHE_DIR: Path = PROJECT_ROOT / "data" / "raw"
MIN_INTERVAL_SEC = 4.0
MAX_RETRIES = 5
_HEADERS = {"User-Agent": "Mozilla/5.0 (IMinvestor course project)"}

_lock = threading.Lock()
_last_request = 0.0


def get(url: str, params: Optional[Dict[str, Any]] = None, timeout: float = 30.0) -> requests.Response:
    """GET with a global minimum interval between requests and retries."""
    global _last_request
    for attempt in range(1, MAX_RETRIES + 1):
        with _lock:
            wait = MIN_INTERVAL_SEC - (time.monotonic() - _last_request)
            if wait > 0:
                time.sleep(wait)
            _last_request = time.monotonic()
        try:
            resp = requests.get(url, params=params, headers=_HEADERS, timeout=timeout)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            backoff = MIN_INTERVAL_SEC * (2 ** attempt)
            log.warning("TWSE request failed (%s/%s): %s; retry in %.0fs",
                        attempt, MAX_RETRIES, exc, backoff)
            if attempt == MAX_RETRIES:
                raise
            time.sleep(backoff)
    raise RuntimeError("unreachable")


def get_json_cached(url: str, params: Dict[str, Any], cache_key: str, use_cache: bool = True) -> Dict[str, Any]:
    """Return JSON from ``data/raw/<cache_key>.json`` or fetch and store it.

    Only responses with ``stat == "OK"`` are cached, so a "no data yet"
    answer is fetched again next time.
    """
    path = CACHE_DIR / f"{cache_key}.json"
    if use_cache and path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    payload = get(url, params).json()
    if str(payload.get("stat", "")).upper() == "OK":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return payload
