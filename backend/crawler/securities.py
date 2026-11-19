"""Security list from the TWSE ISIN page. Owner: 模組 A 行情與爬蟲."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import psycopg

from app.constants import CATEGORY_BOND_ETF, CATEGORY_ETF, CATEGORY_STOCK
from app.errors import NotImplementedYet
from app.services import OWNER_A


def classify(security_id: str, cfi_code: str) -> Optional[int]:
    """Map an ISIN row to a SECURITY_CATEGORY id, or None if not tradable (implemented).

    * CFI ``ES*`` -> 普通股
    * CFI ``CE*`` and id ends with ``B`` (e.g. 00679B) -> 債券ETF
    * other ``CE*`` -> ETF
    * anything else (preferred shares, TDR, warrants, ...) -> None (not imported)
    """
    cfi = cfi_code.strip().upper()
    if cfi.startswith("ES"):
        return CATEGORY_STOCK
    if cfi.startswith("CE"):
        return CATEGORY_BOND_ETF if security_id.strip().upper().endswith("B") else CATEGORY_ETF
    return None


def fetch_isin_list() -> List[Dict[str, Any]]:
    """Download and parse ``ISIN_URL?strMode=2`` (Big5 HTML).

    Return ``[{"security_id", "security_name", "cfi_code"}]``. The first column
    is "代號　名稱" separated by a full-width space (U+3000).
    """
    raise NotImplementedYet("抓取證券清單", OWNER_A)


def sync_securities(conn: psycopg.Connection) -> int:
    """Upsert tradable securities; return the number of new rows.

    ``INSERT ... ON CONFLICT (security_id) DO UPDATE SET security_name = EXCLUDED.security_name``
    — never overwrite ``status`` or ``category_id`` an Admin has changed.
    """
    raise NotImplementedYet("同步證券清單", OWNER_A)
