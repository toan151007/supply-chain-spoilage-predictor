-- =============================================================================
--  MIGRATION 004 - Fix misleading table/view comments
--  File    : database/03-migrations/004-fix-comments.sql
--  Target  : PostgreSQL 13+
--
--  WHY THIS MIGRATION EXISTS
--  The original schema described inventory_transactions as "the most important
--  table for the forecasting model" and as the "main data source for demand
--  forecasting". That was wrong.
--
--  After the decision to store sales in orders + order_items, the real
--  forecasting input is v_daily_sales, which is built from those two tables.
--  inventory_transactions remains the stock movement audit trail.
--
--  WHY A MIGRATION INSTEAD OF RE-RUNNING 01-schema/02-create-tables.sql
--  That script starts with DROP TABLE ... CASCADE. Re-running it destroys all
--  seeded and imported data. This migration only touches catalog metadata
--  (comments), so it is safe to run on a populated database.
--
--  SAFETY
--  - Contains only COMMENT ON statements
--  - No DROP, no TRUNCATE, no DELETE, no DDL on columns/constraints
--  - Fully reversible: the previous wording is quoted below
--
--  USAGE:
--    psql -U postgres -d spoilage_predictor -v ON_ERROR_STOP=1 \
--         -f database/03-migrations/004-fix-comments.sql
--
--  REVERSING THIS MIGRATION (restore the old, incorrect wording):
--    COMMENT ON TABLE inventory_transactions IS
--      'Stock import/export history - main data source for the demand forecasting model';
--    COMMENT ON VIEW v_daily_sales IS
--      'Daily revenue and quantity sold - input data for the demand forecasting model';
-- =============================================================================

BEGIN;

SET client_min_messages = WARNING;

-- ---------------------------------------------------------------------------
--  inventory_transactions: audit trail, not the forecasting input
-- ---------------------------------------------------------------------------
COMMENT ON TABLE inventory_transactions IS
    'Stock movement audit trail - used for stock analysis, expiry alerts and FIFO. NOT the demand forecasting input.';

-- ---------------------------------------------------------------------------
--  v_daily_sales: the actual forecasting input
-- ---------------------------------------------------------------------------
COMMENT ON VIEW v_daily_sales IS
    'Daily quantity and revenue per product/shop - PRIMARY data source for the demand forecasting model (ARIMA / Prophet / XGBoost). Built from orders + order_items.';


COMMIT;


-- =============================================================================
--  VERIFICATION
-- =============================================================================
\echo '--- inventory_transactions comment (must NOT mention forecasting) ---'
SELECT obj_description('inventory_transactions'::regclass) AS comment;

\echo '--- v_daily_sales comment (must name orders + order_items) ---'
SELECT obj_description('v_daily_sales'::regclass, 'pg_class') AS comment;

\echo '--- Row counts must be UNCHANGED after this migration ---'
SELECT 'inventory'              AS bang, COUNT(*) AS so_dong FROM inventory
UNION ALL SELECT 'inventory_transactions', COUNT(*) FROM inventory_transactions
UNION ALL SELECT 'orders',               COUNT(*) FROM orders
UNION ALL SELECT 'order_items',           COUNT(*) FROM order_items
UNION ALL SELECT 'products',              COUNT(*) FROM products
UNION ALL SELECT 'alerts',                COUNT(*) FROM alerts
ORDER BY bang;

\echo '--- Expected: inventory 1330, transactions 11412, orders 3650, order_items 182500, products 50, alerts 518 ---'


-- =============================================================================
--  NOTES
-- =============================================================================
--
--  1. WHY COMMENTS MATTER HERE:
--     PostgreSQL stores these strings as catalog metadata. They are visible in
--     pgAdmin, in psql \d+ output and in any schema dump. A reviewer reading
--     them would otherwise be told that forecasting runs off
--     inventory_transactions, which contradicts the implementation.
--
--  2. RELATIONSHIP TO THE REPORT:
--     The same wording appears in docs/05-tham-khao/giai-thich-comment-sql.md,
--     which is the Vietnamese translation table for these comments. That file
--     was updated in the same commit so the two never drift apart.
--
--  3. CHAPTER 2 NEEDS NO CHANGE:
--     Chapter 2 is theory only and names no tables. Verified by searching the
--     whole chapter for "inventory_transactions" and "sales" - zero matches.
-- =============================================================================
