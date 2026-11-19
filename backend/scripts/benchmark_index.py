"""Index benchmark for the report (§4.2.3). Owner: 模組 D 前端、NoSQL 與分析.

For each index in sql/02_indexes.sql and each heavy query in sql/analysis/:
1. ``DROP INDEX``; run ``EXPLAIN (ANALYZE, BUFFERS)`` 5 times, keep the median.
2. ``CREATE INDEX``; ``ANALYZE``; repeat.
3. Print a Markdown table: query, plan before/after, time before/after, speed-up.
"""

from __future__ import annotations


def main() -> None:
    """CLI entry point."""
    raise SystemExit("TODO(模組 D): index benchmark")


if __name__ == "__main__":
    main()
