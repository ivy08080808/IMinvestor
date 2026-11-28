"""Security list from the TWSE ISIN page. Owner: 模組 A 行情與爬蟲."""

from __future__ import annotations

import html
import re
from typing import Any, Dict, List, Optional

import psycopg

from app.constants import CATEGORY_BOND_ETF, CATEGORY_ETF, CATEGORY_STOCK
from crawler import twse_client


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


_TAG_RE = re.compile(r"<[^>]+>")


def _clean(cell_html: str) -> str:
    text = _TAG_RE.sub("", cell_html)
    return html.unescape(text).replace("\xa0", " ").strip()


def fetch_isin_list() -> List[Dict[str, Any]]:
    """Download and parse ``ISIN_URL?strMode=2`` (Big5 HTML).

    Return ``[{"security_id", "security_name", "cfi_code"}]``. The first column
    is "代號　名稱" separated by a full-width space (U+3000).
    """
    resp = twse_client.get(twse_client.ISIN_URL, params={"strMode": "2"})
    page = resp.content.decode("cp950", errors="replace")

    result: List[Dict[str, Any]] = []
    seen = set()
    for tr in re.findall(r"<tr.*?</tr>", page, flags=re.S | re.I):
        cells = [_clean(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S | re.I)]
        # 分類標題列只有 1 格；資料列至少 6 格（第 6 格是 CFICode）
        if len(cells) < 6 or "\u3000" not in cells[0]:
            continue
        security_id, security_name = (s.strip() for s in cells[0].split("\u3000", 1))
        cfi_code = cells[5]
        if not security_id or not security_name or security_id in seen:
            continue
        seen.add(security_id)
        result.append(
            {"security_id": security_id, "security_name": security_name, "cfi_code": cfi_code}
        )
    return result


def sync_securities(conn: psycopg.Connection) -> int:
    """Upsert tradable securities; return the number of new rows.

    ``INSERT ... ON CONFLICT (security_id) DO UPDATE SET security_name = EXCLUDED.security_name``
    — never overwrite ``status`` or ``category_id`` an Admin has changed.
    """
    new_rows = 0
    with conn.cursor() as cur:
        for row in fetch_isin_list():
            category_id = classify(row["security_id"], row["cfi_code"])
            if category_id is None:
                continue
            cur.execute(
                """
                INSERT INTO security (security_id, security_name, category_id, status)
                VALUES (%s, %s, %s, '啟用')
                ON CONFLICT (security_id)
                DO UPDATE SET security_name = EXCLUDED.security_name
                RETURNING (xmax = 0)
                """,
                (row["security_id"], row["security_name"], category_id),
            )
            if cur.fetchone()[0]:
                new_rows += 1
    return new_rows