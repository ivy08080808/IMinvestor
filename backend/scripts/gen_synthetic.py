"""Synthetic users / orders replayed on real 2026 prices. Owner: 模組 D 前端、NoSQL 與分析.

Goal: ~2,000 users and ~500,000 orders whose holdings, trades and cash are
CONSISTENT, by driving the real engine day by day instead of inserting rows:

    for d in trading days (2026-01 .. latest price date):
        for a random subset of users:
            place orders via order_service.place_order(conn, ...) with
            clock.now monkeypatched to a time on d before 15:00
        settlement.settle_day(conn, d)
        INSERT INTO settlement_run (trade_date, status='完成', ...)  # history

Depends on 模組 A (prices) and 模組 B (place_order, settle_day).
Also generate MongoDB behaviour events (search / view_security) with
timestamps across the same period for the NoSQL analysis.
Make it deterministic with ``random.seed(115)``.
"""

from __future__ import annotations


def main() -> None:
    """CLI entry point."""
    raise SystemExit("TODO(模組 D): generate synthetic users/orders")


if __name__ == "__main__":
    main()
