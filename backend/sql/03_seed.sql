-- =====================================================================
-- Static reference data required by every module.
-- Tax rates are fixed by the report §1.1.1(四).
-- =====================================================================

INSERT INTO security_category (category_id, category_name, tax_rate) VALUES
    (1, '普通股',  0.003000),
    (2, 'ETF',     0.001000),
    (3, '債券ETF', 0.000000)
ON CONFLICT (category_id) DO NOTHING;

-- Default Admin account is created by scripts/init_db.py (bcrypt hash needs Python).
