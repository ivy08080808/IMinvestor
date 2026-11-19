-- =====================================================================
-- Secondary indexes. PK / UNIQUE indexes are created automatically.
-- Each index states the query it serves. The index-benchmark owner should
-- measure every one with EXPLAIN (ANALYZE, BUFFERS) before/after
-- (scripts/benchmark_index.py) and report the numbers.
-- =====================================================================

-- Settlement: pending orders of one trading day (partial index; most orders
-- are terminal, so the index stays small).
CREATE INDEX IF NOT EXISTS idx_orders_pending_belong
    ON orders (belong_date) WHERE status = '待成交';

-- "My orders" page: newest first per user.
CREATE INDEX IF NOT EXISTS idx_orders_user_submit
    ON orders (user_id, submit_time DESC);

-- Site-wide statistics per security.
CREATE INDEX IF NOT EXISTS idx_orders_security
    ON orders (security_id, belong_date);

-- All prices of one trading day (settlement join, market overview).
-- (security_id, trade_date) lookups already use the primary key.
CREATE INDEX IF NOT EXISTS idx_daily_price_date
    ON daily_price (trade_date);

-- Next / previous trading day lookups.
CREATE INDEX IF NOT EXISTS idx_calendar_trading
    ON trading_calendar (calendar_date) WHERE is_trading_day;

-- Fuzzy search by security name (requires pg_trgm; created in 00_schema.sql).
CREATE INDEX IF NOT EXISTS idx_security_name_trgm
    ON security USING gin (security_name gin_trgm_ops);
