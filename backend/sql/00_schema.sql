-- =====================================================================
-- IMinvestor relational schema (PostgreSQL 16+)
-- Source of truth: 專案計劃書 §2.2–2.3, with the v3 FK change
--   (user-owned records use ON DELETE RESTRICT; users are frozen, never deleted).
--
-- Naming: all identifiers are lower_snake_case (PostgreSQL folds unquoted
-- identifiers to lower case). Enum-like columns store the Chinese values
-- used in the report; the canonical list lives in backend/app/constants.py.
-- =====================================================================

BEGIN;

-- Trigram search on security names (trusted extension: DB owner can create it).
CREATE EXTENSION IF NOT EXISTS pg_trgm;

DROP TABLE IF EXISTS settlement_run, trade, orders, watchlist, holding, account, users,
                     daily_price, security, security_category, trading_calendar CASCADE;

-- ---------------------------------------------------------------------
-- USERS
-- ---------------------------------------------------------------------
CREATE TABLE users (
    user_id        bigserial    PRIMARY KEY,
    user_name      varchar(20)  NOT NULL UNIQUE,
    password_hash  char(60)     NOT NULL,                 -- bcrypt
    email          varchar(50)  NOT NULL UNIQUE,
    role           varchar(10)  NOT NULL CHECK (role IN ('User', 'Admin'))
);

-- ---------------------------------------------------------------------
-- ACCOUNT  (1:1 with a USERS row whose role = 'User'; enforced by trigger)
-- ---------------------------------------------------------------------
CREATE TABLE account (
    user_id         bigint         PRIMARY KEY
                    REFERENCES users (user_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    available_cash  numeric(15,2)  NOT NULL CHECK (available_cash >= 0),
    frozen_cash     numeric(15,2)  NOT NULL DEFAULT 0 CHECK (frozen_cash >= 0),
    status          varchar(10)    NOT NULL DEFAULT '啟用' CHECK (status IN ('啟用', '凍結'))
);

-- ---------------------------------------------------------------------
-- SECURITY_CATEGORY / SECURITY
-- ---------------------------------------------------------------------
CREATE TABLE security_category (
    category_id    smallint      PRIMARY KEY,
    category_name  varchar(10)   NOT NULL UNIQUE CHECK (category_name IN ('普通股', 'ETF', '債券ETF')),
    tax_rate       numeric(7,6)  NOT NULL CHECK (tax_rate BETWEEN 0 AND 1)
);

CREATE TABLE security (
    security_id    varchar(10)  PRIMARY KEY,
    security_name  varchar(50)  NOT NULL,
    category_id    smallint     NOT NULL
                   REFERENCES security_category (category_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    status         varchar(10)  NOT NULL DEFAULT '啟用' CHECK (status IN ('啟用', '停用'))
);

-- ---------------------------------------------------------------------
-- TRADING_CALENDAR / DAILY_PRICE
-- ---------------------------------------------------------------------
CREATE TABLE trading_calendar (
    calendar_date   date     PRIMARY KEY,
    is_trading_day  boolean  NOT NULL
);

-- open_price is TWSE's real opening price of that day.
-- The reference price (參考價／昨收: base of change, ±10% limit, today's P&L)
-- is NOT stored; it is the previous trading day's close, derived with
-- LAG(close_price) at query time (plan §2).
CREATE TABLE daily_price (
    security_id  varchar(10)    NOT NULL
                 REFERENCES security (security_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    trade_date   date           NOT NULL
                 REFERENCES trading_calendar (calendar_date) ON DELETE RESTRICT ON UPDATE CASCADE,
    open_price   numeric(10,2)  NOT NULL CHECK (open_price  > 0),
    high_price   numeric(10,2)  NOT NULL CHECK (high_price  > 0),
    low_price    numeric(10,2)  NOT NULL CHECK (low_price   > 0),
    close_price  numeric(10,2)  NOT NULL CHECK (close_price > 0),
    volume       bigint         NOT NULL CHECK (volume > 0),
    PRIMARY KEY (security_id, trade_date),
    CHECK (low_price <= open_price  AND open_price  <= high_price),
    CHECK (low_price <= close_price AND close_price <= high_price)
);

-- ---------------------------------------------------------------------
-- HOLDING  (weak entity of ACCOUNT × SECURITY; rows kept when quantity = 0)
-- ---------------------------------------------------------------------
CREATE TABLE holding (
    user_id          bigint         NOT NULL
                     REFERENCES account (user_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    security_id      varchar(10)    NOT NULL
                     REFERENCES security (security_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    quantity         bigint         NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    frozen_quantity  bigint         NOT NULL DEFAULT 0,
    average_cost     numeric(14,4)  NOT NULL DEFAULT 0 CHECK (average_cost >= 0),
    updated_at       timestamp      NOT NULL DEFAULT (now() AT TIME ZONE 'Asia/Taipei'),
    PRIMARY KEY (user_id, security_id),
    CHECK (frozen_quantity BETWEEN 0 AND quantity)
);

-- ---------------------------------------------------------------------
-- WATCHLIST  (Cascade is fine: a watchlist is not a transaction record)
-- ---------------------------------------------------------------------
CREATE TABLE watchlist (
    user_id      bigint       NOT NULL
                 REFERENCES account (user_id) ON DELETE CASCADE ON UPDATE CASCADE,
    security_id  varchar(10)  NOT NULL
                 REFERENCES security (security_id) ON DELETE CASCADE ON UPDATE CASCADE,
    PRIMARY KEY (user_id, security_id)
);

-- ---------------------------------------------------------------------
-- ORDERS
-- ---------------------------------------------------------------------
CREATE TABLE orders (
    order_id     bigserial      PRIMARY KEY,
    user_id      bigint         NOT NULL
                 REFERENCES account (user_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    security_id  varchar(10)    NOT NULL
                 REFERENCES security (security_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    side         varchar(2)     NOT NULL CHECK (side IN ('買', '賣')),
    price        numeric(10,2)  NOT NULL CHECK (price > 0),
    quantity     bigint         NOT NULL CHECK (quantity > 0),
    submit_time  timestamp      NOT NULL,                 -- Asia/Taipei wall-clock time
    belong_date  date           NOT NULL
                 REFERENCES trading_calendar (calendar_date) ON DELETE RESTRICT ON UPDATE CASCADE,
    status       varchar(10)    NOT NULL DEFAULT '待成交'
                 CHECK (status IN ('待成交', '已成交', '已取消', '已失效'))
);

-- ---------------------------------------------------------------------
-- TRADE  (1:1 with a filled order; price/qty/fee/tax are derived, not stored)
-- ---------------------------------------------------------------------
CREATE TABLE trade (
    trade_id         bigserial      PRIMARY KEY,
    order_id         bigint         NOT NULL UNIQUE
                     REFERENCES orders (order_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    realized_profit  numeric(16,4),                        -- NULL for buys (trigger)
    trade_time       timestamp      NOT NULL
);

-- ---------------------------------------------------------------------
-- SETTLEMENT_RUN  (added in implementation; not in the proposal)
-- One row per trading day processed by the automatic 15:00 job.
-- Why it exists: "has day d been settled?" cannot be derived from
-- DAILY_PRICE alone, because a failed 15:00 fetch leaves d without prices
-- forever (orders then expire per report rules). The row is also the
-- idempotency guard: INSERT ... ON CONFLICT DO NOTHING ensures each day is
-- processed exactly once even if several workers start the job.
-- ---------------------------------------------------------------------
CREATE TABLE settlement_run (
    trade_date      date          PRIMARY KEY
                    REFERENCES trading_calendar (calendar_date) ON DELETE RESTRICT ON UPDATE CASCADE,
    status          varchar(10)   NOT NULL CHECK (status IN ('執行中', '完成', '失敗')),
    started_at      timestamp     NOT NULL,
    finished_at     timestamp,
    price_rows      integer       NOT NULL DEFAULT 0,     -- DAILY_PRICE rows imported
    filled_count    integer       NOT NULL DEFAULT 0,     -- orders -> 已成交
    expired_count   integer       NOT NULL DEFAULT 0,     -- orders -> 已失效
    message         text
);

COMMIT;
