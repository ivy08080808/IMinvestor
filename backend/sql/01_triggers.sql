-- =====================================================================
-- Cross-table constraints that CHECK cannot express (report §2.2).
-- =====================================================================

-- 1) Only a USERS row with role = 'User' may own an ACCOUNT.
CREATE OR REPLACE FUNCTION trg_account_role_check() RETURNS trigger AS $$
BEGIN
    IF (SELECT role FROM users WHERE user_id = NEW.user_id) IS DISTINCT FROM 'User' THEN
        RAISE EXCEPTION 'account can only be created for role=User (user_id=%)', NEW.user_id
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS account_role_check ON account;
CREATE TRIGGER account_role_check
    BEFORE INSERT OR UPDATE OF user_id ON account
    FOR EACH ROW EXECUTE FUNCTION trg_account_role_check();

-- 2) TRADE.realized_profit must be NULL for a buy and NOT NULL for a sell.
CREATE OR REPLACE FUNCTION trg_trade_profit_check() RETURNS trigger AS $$
DECLARE
    v_side varchar(2);
BEGIN
    SELECT side INTO v_side FROM orders WHERE order_id = NEW.order_id;
    IF v_side = '買' AND NEW.realized_profit IS NOT NULL THEN
        RAISE EXCEPTION 'realized_profit must be NULL for a buy (order_id=%)', NEW.order_id
            USING ERRCODE = 'check_violation';
    ELSIF v_side = '賣' AND NEW.realized_profit IS NULL THEN
        RAISE EXCEPTION 'realized_profit is required for a sell (order_id=%)', NEW.order_id
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trade_profit_check ON trade;
CREATE TRIGGER trade_profit_check
    BEFORE INSERT OR UPDATE ON trade
    FOR EACH ROW EXECUTE FUNCTION trg_trade_profit_check();
