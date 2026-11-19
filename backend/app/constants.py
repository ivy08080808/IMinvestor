"""Canonical business constants shared by every module.

Never hard-code these strings or numbers elsewhere; import them from here so that
the database CHECK constraints (sql/00_schema.sql), the services and the frontend
(frontend/js/constants.js) stay consistent.
"""

from __future__ import annotations

from datetime import time
from decimal import Decimal

# ---- Roles (USERS.role) ------------------------------------------------------
ROLE_USER = "User"
ROLE_ADMIN = "Admin"

# ---- Account / security status ----------------------------------------------
ACCOUNT_ACTIVE = "啟用"
ACCOUNT_FROZEN = "凍結"
SECURITY_ACTIVE = "啟用"
SECURITY_DISABLED = "停用"

# ---- Orders ------------------------------------------------------------------
SIDE_BUY = "買"
SIDE_SELL = "賣"
ORDER_PENDING = "待成交"
ORDER_FILLED = "已成交"
ORDER_CANCELLED = "已取消"
ORDER_EXPIRED = "已失效"

# ---- Security categories (SECURITY_CATEGORY.category_id) --------------------
CATEGORY_STOCK = 1      # 普通股, tax 0.3%
CATEGORY_ETF = 2        # ETF, tax 0.1%
CATEGORY_BOND_ETF = 3   # 債券ETF, tax 0%

# ---- Settlement run status ---------------------------------------------------
RUN_RUNNING = "執行中"
RUN_DONE = "完成"
RUN_FAILED = "失敗"

# ---- Money rules (report §1.1.1 (四)) -----------------------------------------
INITIAL_CASH = Decimal("1000000.00")
COMMISSION_RATE = Decimal("0.001425")
MIN_COMMISSION = Decimal("1")
PRICE_LIMIT_RATE = Decimal("0.10")        # ±10% of reference price, inclusive

# ---- Market clock (Asia/Taipei) ----------------------------------------------
TIMEZONE = "Asia/Taipei"
MARKET_OPEN = time(9, 0)
MARKET_CLOSE = time(13, 30)
SETTLEMENT_TIME = time(15, 0)             # order cut-off AND automatic job time
