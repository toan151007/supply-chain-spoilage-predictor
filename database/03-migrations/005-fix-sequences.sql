-- =============================================================================
--  MIGRATION 005: Sync all ID sequences with the actual data
-- =============================================================================
--  WHY THIS MIGRATION EXISTS
--  ------------------------
--  The data was truncated with `TRUNCATE ... RESTART IDENTITY` and then
--  re-imported with explicit primary keys. Explicit inserts do NOT advance
--  the sequence, so the counters fell far behind the real row ids.
--
--  Symptom found on 12/10/2026 while testing the products API:
--      products_product_id_seq.last_value = 2
--      products.product_id               = 1..50
--  Every INSERT returned:
--      duplicate key value violates unique constraint "products_pkey"
--      Key (product_id)=(2) already exists.
--
--  WHY IT MATTERS
--  --------------
--  Any INSERT that lets the database assign the id (API POST, future seed
--  scripts) would collide with an existing row until the sequence is caught
--  up. This is a data-state bug, not a schema bug: the CREATE TABLE
--  definitions are correct and untouched by this migration.
--
--  HOW TO RUN
--  -----------
--  psql -U postgres -d spoilage_predictor \
--       -v ON_ERROR_STOP=1 -f database/03-migrations/005-fix-sequences.sql
--
--  IDEMPOTENT: safe to run more than once.
--
--  NOTE ON order_items: it has no standalone sequence because its
--  `order_item_id` is a plain BIGSERIAL column; the DO block below detects
--  that and reports it as "no sequence - skipped".
-- =============================================================================

DO $$
DECLARE
    r           RECORD;
    seq_value   BIGINT;
    max_value   BIGINT;
    fixed_count INT := 0;
BEGIN
    FOR r IN
        SELECT 'users'                  AS tbl, 'user_id'        AS col, 'users_user_id_seq'                             AS seq
        UNION ALL SELECT 'stores',               'store_id',      'stores_store_id_seq'
        UNION ALL SELECT 'categories',           'category_id',   'categories_category_id_seq'
        UNION ALL SELECT 'products',             'product_id',    'products_product_id_seq'
        UNION ALL SELECT 'inventory',            'inventory_id',  'inventory_inventory_id_seq'
        UNION ALL SELECT 'inventory_transactions','transaction_id','inventory_transactions_transaction_id_seq'
        UNION ALL SELECT 'orders',               'order_id',      'orders_order_id_seq'
        UNION ALL SELECT 'order_items',          'order_item_id', NULL
        UNION ALL SELECT 'forecasts',            'forecast_id',   'forecasts_forecast_id_seq'
        UNION ALL SELECT 'alerts',               'alert_id',      'alerts_alert_id_seq'
    LOOP
        -- Column holding the id must exist before anything else.
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name   = r.tbl
              AND column_name  = r.col
        ) THEN
            RAISE NOTICE 'MISSING COLUMN %.% - skipped', r.tbl, r.col;
            CONTINUE;
        END IF;

        IF r.seq IS NULL THEN
            RAISE NOTICE 'NO SEQUENCE  %-24 (% has no sequence)', r.tbl, r.col;
            CONTINUE;
        END IF;

        EXECUTE format('SELECT last_value FROM %I', r.seq) INTO seq_value;
        EXECUTE format('SELECT COALESCE(max(%I), 0) FROM %I', r.col, r.tbl)
            INTO max_value;

        IF seq_value < max_value THEN
            -- setval(sequence, value, true) means "next call returns value+1".
            EXECUTE format('SELECT setval(%L, %L, true)', r.seq, max_value);
            RAISE NOTICE 'FIXED       %-24 seq %-> max %  now set to %',
                r.tbl, seq_value, max_value, max_value;
            fixed_count := fixed_count + 1;
        ELSE
            RAISE NOTICE 'OK           %-24 seq %-8 max %-8', r.tbl, seq_value, max_value;
        END IF;
    END LOOP;

    RAISE NOTICE '';
    RAISE NOTICE 'Sequences fixed: %', fixed_count;
END
$$;

-- Verification query, safe to run any time afterwards.
-- Every row below should now show seq >= max.
--
-- SELECT s.sequencename, s.last_value
-- FROM pg_sequences s
-- WHERE s.schemaname = 'public'
-- ORDER BY s.sequencename;

COMMIT;