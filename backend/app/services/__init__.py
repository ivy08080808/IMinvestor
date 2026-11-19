"""Business logic. Each service module has one owner (see docs/TASKS.md).

Rules for every service function:

1. First parameter is ``conn: psycopg.Connection``; never open connections here.
2. Raise :class:`app.errors.AppError` for business-rule violations.
3. Use ``app.clock.now()`` for time, ``app.fees`` for money, ``app.market`` for
   calendar / belong-date / reference price.
4. Return plain dicts whose keys match the response model in ``app.schemas``.
5. Unfinished functions raise ``NotImplementedYet(feature, owner)`` -> HTTP 501.
"""

OWNER_A = "模組 A 行情與爬蟲"
OWNER_B = "模組 B 交易核心"
OWNER_C = "模組 C 帳務與管理"
OWNER_D = "模組 D 前端、NoSQL 與分析"
