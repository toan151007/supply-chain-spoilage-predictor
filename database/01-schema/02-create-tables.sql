-- =============================================================================
--  PROJECT: SUPPLY CHAIN SPOILAGE PREDICTOR
--  Retail / F&B supply chain management platform
--
--  TASK     : Create database schema - 10 tables
--  NORMAL   : 3NF
--  DATABASE : PostgreSQL 13 or later
--  FILE     : database/01-schema/02-create-tables.sql
--
--  USAGE:
--    psql -U postgres -c "CREATE DATABASE spoilage_predictor;"
--    psql -U postgres -d spoilage_predictor -f database/01-schema/02-create-tables.sql
--
--  ENCODING NOTE:
--    This file uses ASCII characters only (English comments) so it runs
--    without errors on Windows PowerShell / cmd.
--    If Vietnamese text is added later, run psql with:
--      $env:PGCLIENTENCODING = "UTF8"
--
--  DESIGN NOTES:
--    1. CHECK constraints are used instead of PostgreSQL ENUM types.
--       ENUM is hard to extend (adding a value needs ALTER TYPE) and does not
--       work well with SQLAlchemy ORM during migrations.
--    2. All quantity columns use NUMERIC, never FLOAT/DOUBLE PRECISION.
--       Float rounding errors would corrupt stock levels, which is especially
--       dangerous for products sold by weight or volume (kg, litre).
--    3. All timestamp columns use TIMESTAMPTZ to avoid timezone drift.
--    4. expiry_date lives in inventory and inventory_transactions, NOT in
--       products. Expiry belongs to a specific BATCH in a specific STORE,
--       it is not a fixed attribute of the product itself.
-- =============================================================================

BEGIN;

-- Extension used to generate primary key values
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Drop old tables so this script can be re-run many times (WARNING: data loss)
DROP TABLE IF EXISTS alerts           CASCADE;
DROP TABLE IF EXISTS forecasts        CASCADE;
DROP TABLE IF EXISTS order_items      CASCADE;
DROP TABLE IF EXISTS orders           CASCADE;
DROP TABLE IF EXISTS inventory_transactions CASCADE;
DROP TABLE IF EXISTS inventory        CASCADE;
DROP TABLE IF EXISTS products         CASCADE;
DROP TABLE IF EXISTS categories       CASCADE;
DROP TABLE IF EXISTS users            CASCADE;
DROP TABLE IF EXISTS stores           CASCADE;
DROP VIEW  IF EXISTS v_daily_sales            CASCADE;
DROP VIEW  IF EXISTS v_low_stock              CASCADE;
DROP VIEW  IF EXISTS v_expiring_inventory     CASCADE;
DROP VIEW  IF EXISTS v_product_stock_summary  CASCADE;
DROP FUNCTION IF EXISTS fn_generate_inventory_alerts() CASCADE;
DROP FUNCTION IF EXISTS fn_update_updated_at()         CASCADE;


-- =============================================================================
--  SHARED FUNCTION
-- =============================================================================

-- Auto-update the updated_at field on every row change.
-- Needed for the project because it allows tracing "who edited stock and when".
CREATE OR REPLACE FUNCTION fn_update_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


-- =============================================================================
--  TABLE 1: stores - Shops / Branches
-- -----------------------------------------------------------------------------
--  The project targets a chain of retail shops, so this table is the root entity
--  for all business data in the system.
-- =============================================================================
CREATE TABLE stores (
    store_id      SERIAL          PRIMARY KEY,
    store_code    VARCHAR(20)     NOT NULL UNIQUE,
    store_name    VARCHAR(200)    NOT NULL,
    address       TEXT,
    phone         VARCHAR(20),
    store_type    VARCHAR(20)     NOT NULL DEFAULT 'convenience_store'
                    CHECK (store_type IN ('convenience_store', 'restaurant', 'warehouse')),
    opening_date  DATE,
    is_active     BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  stores                  IS 'Shop / branch in the retail or F&B chain';
COMMENT ON COLUMN stores.store_id         IS 'Primary key, auto generated';
COMMENT ON COLUMN stores.store_code       IS 'Unique shop code, example: CH01, CH02';
COMMENT ON COLUMN stores.store_name       IS 'Shop name shown on the user interface';
COMMENT ON COLUMN stores.store_type       IS 'Shop type: convenience_store, restaurant, warehouse';
COMMENT ON COLUMN stores.opening_date     IS 'Date the shop started operating';
COMMENT ON COLUMN stores.is_active        IS 'TRUE = operating, FALSE = closed';


-- =============================================================================
--  TABLE 2: users - System accounts
-- -----------------------------------------------------------------------------
--  store_id NULL means the user manages the whole system (chain owner)
--  and can see data from all branches.
-- =============================================================================
CREATE TABLE users (
    user_id       SERIAL          PRIMARY KEY,
    username      VARCHAR(50)     NOT NULL UNIQUE,
    email         VARCHAR(150)    UNIQUE,
    password_hash VARCHAR(255)    NOT NULL,
    full_name     VARCHAR(150)    NOT NULL,
    role          VARCHAR(20)     NOT NULL DEFAULT 'staff'
                    CHECK (role IN ('owner', 'manager', 'staff')),
    store_id      INTEGER         REFERENCES stores(store_id) ON DELETE SET NULL,
    is_active     BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  users               IS 'System user accounts';
COMMENT ON COLUMN users.user_id       IS 'Primary key, auto generated';
COMMENT ON COLUMN users.username      IS 'Login name, unique';
COMMENT ON COLUMN users.password_hash IS 'Password hashed with bcrypt - NEVER store plain text';
COMMENT ON COLUMN users.role          IS 'Role: owner (chain owner), manager (stock manager), staff (employee)';
COMMENT ON COLUMN users.store_id      IS 'Working branch, NULL if manages the whole system';

CREATE INDEX idx_users_store_id ON users(store_id);


-- =============================================================================
--  TABLE 3: categories - Product categories
-- -----------------------------------------------------------------------------
--  Self-referencing foreign key (parent_category_id) supports multi-level
--  categories, example: Food > Beverages > Soft drinks.
-- =============================================================================
CREATE TABLE categories (
    category_id        SERIAL        PRIMARY KEY,
    category_name      VARCHAR(150)  NOT NULL UNIQUE,
    description        TEXT,
    parent_category_id INTEGER       REFERENCES categories(category_id) ON DELETE SET NULL,
    created_at         TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  categories                    IS 'Product category groups, supports multi-level grouping';
COMMENT ON COLUMN categories.category_id        IS 'Primary key, auto generated';
COMMENT ON COLUMN categories.category_name      IS 'Category name, unique';
COMMENT ON COLUMN categories.parent_category_id IS 'Parent category, NULL if top level';

CREATE INDEX idx_categories_parent_id ON categories(parent_category_id);


-- =============================================================================
--  TABLE 4: products - Products
-- -----------------------------------------------------------------------------
--  This table stores FIXED product attributes (not batch specific).
--  There is no expiry_date here because expiry belongs to a batch
--  - see the inventory table.
--
--  Units: retail and F&B sell by piece, kg, box, litre, bottle.
--  Quantities use NUMERIC so fractional sales by kg or litre are supported.
-- =============================================================================
CREATE TABLE products (
    product_id      SERIAL          PRIMARY KEY,
    product_code    VARCHAR(50)     NOT NULL UNIQUE,
    product_name    VARCHAR(255)    NOT NULL,
    category_id     INTEGER         NOT NULL REFERENCES categories(category_id) ON DELETE RESTRICT,
    unit            VARCHAR(20)     NOT NULL,
    unit_cost       NUMERIC(15,2)   NOT NULL DEFAULT 0 CHECK (unit_cost   >= 0),
    selling_price   NUMERIC(15,2)   NOT NULL DEFAULT 0 CHECK (selling_price >= 0),
    -- Shelf life in days counted from the received date, used to calculate
    -- the expiry date when a batch is created
    shelf_life_days INTEGER         NOT NULL CHECK (shelf_life_days > 0),
    -- Stock thresholds used to generate automatic alerts
    min_stock       NUMERIC(15,3)   NOT NULL DEFAULT 0 CHECK (min_stock >= 0),
    max_stock       NUMERIC(15,3)   CHECK (max_stock IS NULL OR max_stock > 0),
    -- Short shelf life product: the project focuses on these (under 90 days)
    is_perishable   BOOLEAN         NOT NULL DEFAULT TRUE,
    -- Stock level below this triggers a reorder suggestion
    reorder_point   NUMERIC(15,3)   CHECK (reorder_point IS NULL OR reorder_point >= 0),
    supplier        VARCHAR(200),
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_stock_range CHECK (max_stock IS NULL OR min_stock <= max_stock)
);

COMMENT ON TABLE  products                  IS 'Product information - fixed attributes, not batch specific';
COMMENT ON COLUMN products.product_id       IS 'Primary key, auto generated';
COMMENT ON COLUMN products.product_code     IS 'Unique product code (SKU), example: SP0001';
COMMENT ON COLUMN products.product_name     IS 'Product name';
COMMENT ON COLUMN products.category_id      IS 'Product category';
COMMENT ON COLUMN products.unit             IS 'Unit of measure: piece, kg, litre, box, bottle, carton';
COMMENT ON COLUMN products.unit_cost        IS 'Purchase cost / cost of goods (VND)';
COMMENT ON COLUMN products.selling_price    IS 'Retail selling price (VND)';
COMMENT ON COLUMN products.shelf_life_days  IS 'Days the product keeps after receiving, used to set batch expiry date';
COMMENT ON COLUMN products.min_stock        IS 'Minimum stock level - below this an alert is raised';
COMMENT ON COLUMN products.max_stock        IS 'Maximum stock level - above this an overstock alert is raised';
COMMENT ON COLUMN products.is_perishable    IS 'TRUE = short shelf life food, the main focus of this project';
COMMENT ON COLUMN products.reorder_point    IS 'Reorder point - suggests importing stock when reached';
COMMENT ON COLUMN products.supplier         IS 'Default supplier';

CREATE INDEX idx_products_category_id ON products(category_id);
CREATE INDEX idx_products_is_active    ON products(is_active);
CREATE INDEX idx_products_product_name ON products(product_name);


-- =============================================================================
--  TABLE 5: inventory - Current stock per batch
-- -----------------------------------------------------------------------------
--  Each row = ONE BATCH of ONE PRODUCT in ONE SHOP.
--  UNIQUE (store_id, product_id, expiry_date) allows the same product to have
--  several batches with different expiry dates. This is required to manage
--  expiry tracking and apply FIFO (sell the earliest expiry batch first).
--
--  Relationship: inventory is the CURRENT snapshot, updated from
--  inventory_transactions. This data feeds the DASHBOARD and ALERTS.
-- =============================================================================
CREATE TABLE inventory (
    inventory_id   BIGSERIAL       PRIMARY KEY,
    store_id       INTEGER         NOT NULL REFERENCES stores(store_id)   ON DELETE CASCADE,
    product_id     INTEGER         NOT NULL REFERENCES products(product_id) ON DELETE RESTRICT,
    expiry_date    DATE,
    quantity       NUMERIC(15,3)   NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    -- Date this batch was received, used to report slow moving stock
    received_date  DATE            NOT NULL DEFAULT CURRENT_DATE,
    batch_code     VARCHAR(50),
    created_at     TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_inventory_store_product_expiry UNIQUE (store_id, product_id, expiry_date)
);

COMMENT ON TABLE  inventory               IS 'Current stock, per batch, per shop';
COMMENT ON COLUMN inventory.inventory_id   IS 'Primary key, auto generated';
COMMENT ON COLUMN inventory.expiry_date    IS 'Expiry date of THIS batch - used for alerts and FIFO ordering';
COMMENT ON COLUMN inventory.quantity       IS 'Quantity remaining in this batch, never negative';
COMMENT ON COLUMN inventory.received_date  IS 'Date the batch was received, used to report slow moving stock';
COMMENT ON COLUMN inventory.batch_code     IS 'Supplier batch code, optional';

-- Index serving expiry alert queries (filter by expiry date)
CREATE INDEX idx_inventory_product_id  ON inventory(product_id);
CREATE INDEX idx_inventory_store_id    ON inventory(store_id);
CREATE INDEX idx_inventory_expiry_date ON inventory(expiry_date);
-- Index serving the query "expiring within N days"
CREATE INDEX idx_inventory_expiry_store ON inventory(expiry_date, store_id) WHERE quantity > 0;


-- =============================================================================
--  TABLE 6: inventory_transactions - Stock movement history
-- -----------------------------------------------------------------------------
--  *** THIS IS THE MOST IMPORTANT TABLE FOR THE FORECASTING MODEL ***
--  It holds the time series input data for ARIMA / Prophet / XGBoost.
--
--  Critical technical note - CENSORED DEMAND:
--  When a product runs out of stock, recorded sales become 0 even though
--  customers still wanted to buy. If this data is fed to a forecasting model,
--  the model learns the wrong relation "low sales = low demand" and will
--  under-forecast in later periods. These days must be detected and
--  corrected before training.
-- =============================================================================
CREATE TABLE inventory_transactions (
    transaction_id   BIGSERIAL     PRIMARY KEY,
    store_id         INTEGER       NOT NULL REFERENCES stores(store_id)    ON DELETE CASCADE,
    product_id       INTEGER       NOT NULL REFERENCES products(product_id) ON DELETE RESTRICT,
    expiry_date      DATE,
    transaction_type VARCHAR(20)   NOT NULL
                      CHECK (transaction_type IN ('import', 'export', 'adjustment', 'disposal')),
    quantity         NUMERIC(15,3) NOT NULL CHECK (quantity > 0),
    unit_cost        NUMERIC(15,2) CHECK (unit_cost IS NULL OR unit_cost >= 0),
    reference_type   VARCHAR(30)   DEFAULT 'manual'
                      CHECK (reference_type IN ('manual', 'order', 'import_excel')),
    reference_id     BIGINT,
    transaction_date TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    user_id          INTEGER       REFERENCES users(user_id) ON DELETE SET NULL,
    note             TEXT,
    created_at       TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

    -- Prevent duplicate movements: the same order cannot export the same
    -- batch twice
    CONSTRAINT uq_transactions_reference UNIQUE (reference_type, reference_id, product_id, expiry_date)
);

COMMENT ON TABLE  inventory_transactions                     IS 'Stock import/export history - main data source for the demand forecasting model';
COMMENT ON COLUMN inventory_transactions.transaction_id     IS 'Primary key, auto generated';
COMMENT ON COLUMN inventory_transactions.expiry_date        IS 'Expiry date of the batch at the time of the movement';
COMMENT ON COLUMN inventory_transactions.transaction_type   IS 'import, export (sale), adjustment (stocktake), disposal (spoilage write-off)';
COMMENT ON COLUMN inventory_transactions.quantity           IS 'Movement quantity, always positive - direction is decided by transaction_type';
COMMENT ON COLUMN inventory_transactions.reference_type     IS 'Origin of the record: manual, order, import_excel';
COMMENT ON COLUMN inventory_transactions.reference_id       IS 'Reference key to the source record in orders when reference_type = order';
COMMENT ON COLUMN inventory_transactions.transaction_date   IS 'When the movement happened - the most important column for forecasting';
COMMENT ON COLUMN inventory_transactions.note               IS 'Note, for example the reason a batch was written off';

-- ===== INDEXES SERVING FORECASTING (optimise product + time queries) =====
CREATE INDEX idx_transactions_product_date ON inventory_transactions(product_id, transaction_date);
CREATE INDEX idx_transactions_store_date   ON inventory_transactions(store_id, transaction_date);
CREATE INDEX idx_transactions_date          ON inventory_transactions(transaction_date);
CREATE INDEX idx_transactions_type_date     ON inventory_transactions(transaction_type, transaction_date);


-- =============================================================================
--  TABLE 7: orders - Orders
-- -----------------------------------------------------------------------------
--  order_type distinguishes SALE orders from PURCHASE orders.
--  Keeping both in one table allows symmetric two-way stock flow reporting.
-- =============================================================================
CREATE TABLE orders (
    order_id        BIGSERIAL       PRIMARY KEY,
    order_code      VARCHAR(50)     NOT NULL UNIQUE,
    store_id        INTEGER         NOT NULL REFERENCES stores(store_id) ON DELETE RESTRICT,
    order_type      VARCHAR(20)     NOT NULL DEFAULT 'sale'
                      CHECK (order_type IN ('sale', 'purchase')),
    order_date      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    total_amount    NUMERIC(18,2)   NOT NULL DEFAULT 0 CHECK (total_amount >= 0),
    total_quantity  NUMERIC(15,3)   NOT NULL DEFAULT 0 CHECK (total_quantity >= 0),
    status          VARCHAR(20)     NOT NULL DEFAULT 'completed'
                      CHECK (status IN ('pending', 'completed', 'cancelled')),
    payment_method  VARCHAR(30)
                      CHECK (payment_method IS NULL OR payment_method IN
                             ('cash', 'card', 'transfer', 'ewallet', 'other')),
    customer_name   VARCHAR(150),
    user_id         INTEGER         REFERENCES users(user_id) ON DELETE SET NULL,
    note            TEXT,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  orders               IS 'Sales orders (sale) and purchase orders (purchase)';
COMMENT ON COLUMN orders.order_code     IS 'Unique order code';
COMMENT ON COLUMN orders.order_type     IS 'sale = sold to customer, purchase = purchased into stock';
COMMENT ON COLUMN orders.status         IS 'pending, completed, or cancelled';
COMMENT ON COLUMN orders.total_amount   IS 'Total amount after discount (VND)';
COMMENT ON COLUMN orders.total_quantity IS 'Total quantity of all items in the order';

CREATE INDEX idx_orders_store_date  ON orders(store_id, order_date);
CREATE INDEX idx_orders_date        ON orders(order_date);
CREATE INDEX idx_orders_type_date   ON orders(order_type, order_date, status);


-- =============================================================================
--  TABLE 8: order_items - Order line items
-- -----------------------------------------------------------------------------
--  line_total uses GENERATED ALWAYS AS ... STORED: PostgreSQL computes it,
--  it cannot be edited by hand, so it can never drift due to a manual
--  calculation mistake. (Requires PostgreSQL 12 or later.)
-- =============================================================================
CREATE TABLE order_items (
    order_item_id   BIGSERIAL       PRIMARY KEY,
    order_id        BIGINT          NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id      INTEGER         NOT NULL REFERENCES products(product_id) ON DELETE RESTRICT,
    quantity        NUMERIC(15,3)   NOT NULL CHECK (quantity > 0),
    unit_price      NUMERIC(15,2)   NOT NULL CHECK (unit_price >= 0),
    unit_cost       NUMERIC(15,2)   CHECK (unit_cost IS NULL OR unit_cost >= 0),
    discount_percent NUMERIC(5,2)   NOT NULL DEFAULT 0
                      CHECK (discount_percent >= 0 AND discount_percent <= 100),
    line_total      NUMERIC(18,2)
                      GENERATED ALWAYS AS
                      (ROUND(quantity * unit_price * (1 - discount_percent / 100), 2))
                      STORED,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    -- A product appears at most once in the same order
    CONSTRAINT uq_order_items_order_product UNIQUE (order_id, product_id)
);

COMMENT ON TABLE  order_items                  IS 'Line items of each order';
COMMENT ON COLUMN order_items.line_total       IS 'Line amount = quantity * unit price * (1 - discount %), auto computed';
COMMENT ON COLUMN order_items.discount_percent IS 'Discount percentage from 0 to 100';
COMMENT ON COLUMN order_items.unit_cost        IS 'Cost at time of sale, used for gross margin';

CREATE INDEX idx_order_items_order_id   ON order_items(order_id);
CREATE INDEX idx_order_items_product_id ON order_items(product_id);


-- =============================================================================
--  TABLE 9: forecasts - Demand forecast results
-- -----------------------------------------------------------------------------
--  Stores results of EACH model so they can be compared fairly on the same
--  test set - this is mandatory when evaluating forecasting models.
--
--  Design note: the recommended import quantity is calculated outside the
--  forecasting model, from: predicted demand - current stock + safety stock,
--  while also checking expiry dates so we never suggest importing goods with
--  a shelf life that is too short. See the algorithm design document.
-- =============================================================================
CREATE TABLE forecasts (
    forecast_id             BIGSERIAL     PRIMARY KEY,
    store_id                INTEGER       NOT NULL REFERENCES stores(store_id)    ON DELETE CASCADE,
    product_id              INTEGER       NOT NULL REFERENCES products(product_id) ON DELETE RESTRICT,
    model_name              VARCHAR(50)   NOT NULL
                            CHECK (model_name IN ('prophet', 'xgboost', 'arima',
                                                  'moving_average', 'naive')),
    forecast_date           DATE          NOT NULL,
    horizon_days            INTEGER       NOT NULL DEFAULT 1 CHECK (horizon_days > 0),
    predicted_quantity      NUMERIC(15,3) NOT NULL CHECK (predicted_quantity >= 0),
    lower_bound             NUMERIC(15,3) CHECK (lower_bound IS NULL OR lower_bound >= 0),
    upper_bound             NUMERIC(15,3) CHECK (upper_bound IS NULL OR upper_bound >= 0),
    recommended_import_qty  NUMERIC(15,3) CHECK (recommended_import_qty IS NULL OR recommended_import_qty >= 0),
    rmse                    NUMERIC(12,4) CHECK (rmse IS NULL OR rmse >= 0),
    mae                     NUMERIC(12,4) CHECK (mae  IS NULL OR mae  >= 0),
    mape                    NUMERIC(12,4) CHECK (mape IS NULL OR mape  >= 0),
    trained_at              TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    created_at              TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

    -- One result per product, shop, model and forecast date
    -- prevents duplicates when the job re-runs
    CONSTRAINT uq_forecasts_unique UNIQUE (store_id, product_id, model_name, forecast_date)
);

COMMENT ON TABLE  forecasts                          IS 'Demand forecast results per model';
COMMENT ON COLUMN forecasts.model_name               IS 'Model: prophet, xgboost, arima, moving_average, naive';
COMMENT ON COLUMN forecasts.forecast_date            IS 'The predicted date (in the future relative to training time)';
COMMENT ON COLUMN forecasts.horizon_days             IS 'Days predicted ahead from the training time';
COMMENT ON COLUMN forecasts.predicted_quantity       IS 'Predicted quantity sold';
COMMENT ON COLUMN forecasts.lower_bound              IS 'Lower confidence bound, used for safety stock calculation';
COMMENT ON COLUMN forecasts.upper_bound              IS 'Upper confidence bound';
COMMENT ON COLUMN forecasts.recommended_import_qty   IS 'Suggested import quantity, derived from the forecast and current stock';
COMMENT ON COLUMN forecasts.rmse                     IS 'Root mean squared error - main accuracy metric';
COMMENT ON COLUMN forecasts.mae                      IS 'Mean absolute error';
COMMENT ON COLUMN forecasts.mape                     IS 'Mean absolute percentage error - easiest metric to explain to managers';
COMMENT ON COLUMN forecasts.trained_at               IS 'When the model was run, to check if the result is still valid';

CREATE INDEX idx_forecasts_product_date  ON forecasts(product_id, forecast_date);
CREATE INDEX idx_forecasts_store_date    ON forecasts(store_id, forecast_date);
CREATE INDEX idx_forecasts_model         ON forecasts(model_name);


-- =============================================================================
--  TABLE 10: alerts - Alerts
-- -----------------------------------------------------------------------------
--  alert_type covers both rule based alerts and model based alerts.
--  This is the central table for the WebSocket real-time feature:
--  whenever a row is inserted, the backend pushes it to the frontend.
-- =============================================================================
CREATE TABLE alerts (
    alert_id       BIGSERIAL     PRIMARY KEY,
    store_id       INTEGER       REFERENCES stores(store_id)    ON DELETE CASCADE,
    product_id     INTEGER       REFERENCES products(product_id) ON DELETE CASCADE,
    alert_type     VARCHAR(30)   NOT NULL
                   CHECK (alert_type IN ('expiring_soon', 'expired', 'low_stock',
                                         'over_stock', 'forecast_anomaly')),
    severity       VARCHAR(10)   NOT NULL DEFAULT 'low'
                   CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    title          VARCHAR(255)  NOT NULL,
    message        TEXT,
    expiry_date    DATE,
    current_stock  NUMERIC(15,3),
    threshold_value NUMERIC(15,3),
    is_read        BOOLEAN       NOT NULL DEFAULT FALSE,
    is_resolved    BOOLEAN       NOT NULL DEFAULT FALSE,
    created_at     TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    resolved_at    TIMESTAMPTZ,

    -- An alert cannot be closed and unresolved at the same time
    CONSTRAINT chk_alert_resolved_at CHECK (
        (is_resolved AND resolved_at IS NOT NULL) OR
        (NOT is_resolved AND resolved_at IS NULL)
    )
);

COMMENT ON TABLE  alerts                     IS 'System alerts: expiry, abnormal stock, forecast deviation';
COMMENT ON COLUMN alerts.alert_type          IS 'expiring_soon, expired, low_stock, over_stock, forecast_anomaly';
COMMENT ON COLUMN alerts.severity            IS 'Severity level: low, medium, high, critical';
COMMENT ON COLUMN alerts.current_stock       IS 'Stock level at the moment the alert was created';
COMMENT ON COLUMN alerts.threshold_value     IS 'Threshold that was crossed, explains why the alert fired';
COMMENT ON COLUMN alerts.is_read             IS 'Has the user read this alert';
COMMENT ON COLUMN alerts.is_resolved         IS 'Has the issue been handled';
COMMENT ON COLUMN alerts.resolved_at         IS 'When the alert was closed';

-- Index serving unread alert queries (the real-time feature)
CREATE INDEX idx_alerts_unread    ON alerts(store_id, created_at DESC) WHERE is_read = FALSE;
CREATE INDEX idx_alerts_product   ON alerts(product_id);
CREATE INDEX idx_alerts_type_date ON alerts(alert_type, created_at DESC);


-- =============================================================================
--  TRIGGERS - Auto update updated_at
-- =============================================================================
CREATE TRIGGER trg_stores_updated
    BEFORE UPDATE ON stores
    FOR EACH ROW EXECUTE FUNCTION fn_update_updated_at();

CREATE TRIGGER trg_users_updated
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION fn_update_updated_at();

CREATE TRIGGER trg_categories_updated
    BEFORE UPDATE ON categories
    FOR EACH ROW EXECUTE FUNCTION fn_update_updated_at();

CREATE TRIGGER trg_products_updated
    BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION fn_update_updated_at();

CREATE TRIGGER trg_inventory_updated
    BEFORE UPDATE ON inventory
    FOR EACH ROW EXECUTE FUNCTION fn_update_updated_at();

CREATE TRIGGER trg_orders_updated
    BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION fn_update_updated_at();


-- =============================================================================
--  BUSINESS FUNCTION - Automatic alert generation
-- -----------------------------------------------------------------------------
--  This function demonstrates the alert mechanism of phase 1.
--  In the real system the backend calls it on a schedule (cron job) each day,
--  or directly after every import/export transaction.
--
--  Alerts are generated by 4 rules:
--    1. Expired       - expiry date is earlier than today
--    2. Expiring soon - expires within <= 3 days and stock remains
--    3. Low stock     - total stock < min_stock
--    4. Overstock     - total stock > max_stock
--
--  Duplicate guard: an alert is only created when there is no unresolved
--  alert of the same type for the same product.
-- =============================================================================
CREATE OR REPLACE FUNCTION fn_generate_inventory_alerts(
    p_warning_days INTEGER DEFAULT 3
)
RETURNS TABLE (
    alert_type_return VARCHAR(30),
    product_id_return INTEGER,
    store_id_return   INTEGER,
    severity_return   VARCHAR(10)
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_today     DATE := CURRENT_DATE;
    v_deadline  DATE := CURRENT_DATE + p_warning_days;
BEGIN
    -- 1 & 2. EXPIRY ALERTS --------------------------------------------------
    RETURN QUERY
    INSERT INTO alerts (
        store_id, product_id, alert_type, severity,
        title, message, expiry_date, current_stock
    )
    SELECT
        i.store_id,
        i.product_id,
        CASE WHEN i.expiry_date < v_today THEN 'expired' ELSE 'expiring_soon' END,
        CASE
            WHEN i.expiry_date < v_today                            THEN 'critical'
            WHEN i.expiry_date <= v_today + 1                       THEN 'high'
            WHEN i.expiry_date <= v_deadline                        THEN 'medium'
            ELSE 'low'
        END,
        p.product_name || ' - ' ||
            CASE WHEN i.expiry_date < v_today
                 THEN 'EXPIRED since ' || TO_CHAR(i.expiry_date, 'DD/MM/YYYY')
                 ELSE 'EXPIRING on ' || TO_CHAR(i.expiry_date, 'DD/MM/YYYY') END,
        'Batch remaining ' || i.quantity || ' ' || p.unit ||
            '. Handle before ' || TO_CHAR(i.expiry_date, 'DD/MM/YYYY') || '.',
        i.expiry_date,
        i.quantity
    FROM inventory i
    JOIN products p ON p.product_id = i.product_id
    WHERE i.quantity > 0
      AND i.expiry_date IS NOT NULL
      AND i.expiry_date <= v_deadline
      AND NOT EXISTS (
          SELECT 1 FROM alerts a
          WHERE a.product_id   = i.product_id
            AND a.store_id     = i.store_id
            AND a.expiry_date  = i.expiry_date
            AND a.alert_type IN ('expiring_soon', 'expired')
            AND a.is_resolved = FALSE
      )
    RETURNING alerts.alert_type, alerts.product_id, alerts.store_id, alerts.severity;

    -- 3. LOW STOCK ALERTS ----------------------------------------------------
    RETURN QUERY
    INSERT INTO alerts (
        store_id, product_id, alert_type, severity,
        title, message, current_stock, threshold_value
    )
    SELECT
        i.store_id,
        i.product_id,
        'low_stock',
        'high',
        p.product_name || ' - LOW STOCK',
        'Current stock ' || SUM(i.quantity) || ' ' || p.unit ||
            ', below minimum level ' || p.min_stock || ' ' || p.unit || '.',
        SUM(i.quantity),
        p.min_stock
    FROM inventory i
    JOIN products p ON p.product_id = i.product_id
    GROUP BY i.store_id, i.product_id, p.product_name, p.unit, p.min_stock
    HAVING SUM(i.quantity) < p.min_stock
       AND NOT EXISTS (
           SELECT 1 FROM alerts a
           WHERE a.product_id = i.product_id
             AND a.store_id   = i.store_id
             AND a.alert_type = 'low_stock'
             AND a.is_resolved = FALSE
       )
    RETURNING alerts.alert_type, alerts.product_id, alerts.store_id, alerts.severity;

    -- 4. OVERSTOCK ALERTS (risk of over-ordering) -----------------------------
    RETURN QUERY
    INSERT INTO alerts (
        store_id, product_id, alert_type, severity,
        title, message, current_stock, threshold_value
    )
    SELECT
        i.store_id,
        i.product_id,
        'over_stock',
        'medium',
        p.product_name || ' - OVERSTOCK',
        'Current stock ' || SUM(i.quantity) || ' ' || p.unit ||
            ', above maximum level ' || p.max_stock || ' ' || p.unit ||
            '. Consider reducing the next import.',
        SUM(i.quantity),
        p.max_stock
    FROM inventory i
    JOIN products p ON p.product_id = i.product_id
    WHERE p.max_stock IS NOT NULL
    GROUP BY i.store_id, i.product_id, p.product_name, p.unit, p.max_stock
    HAVING SUM(i.quantity) > p.max_stock
       AND NOT EXISTS (
           SELECT 1 FROM alerts a
           WHERE a.product_id = i.product_id
             AND a.store_id   = i.store_id
             AND a.alert_type = 'over_stock'
             AND a.is_resolved = FALSE
       )
    RETURNING alerts.alert_type, alerts.product_id, alerts.store_id, alerts.severity;

END;
$$;

COMMENT ON FUNCTION fn_generate_inventory_alerts(INTEGER) IS
    'Generate automatic alerts: expired, expiring soon, low stock, overstock. Returns the number of alerts created.';


-- =============================================================================
--  VIEWS - QUERIES FOR THE USER INTERFACE AND FORECASTING MODEL
-- =============================================================================

-- View 1: Daily sales - MAIN DATA SOURCE FOR THE FORECASTING MODEL.
-- Note: only completed orders are counted, and censored days must be tracked.
-- If stock is 0 on a day, recorded sales do NOT reflect real demand - use the
-- censored flag to correct the data before training the model.
CREATE OR REPLACE VIEW v_daily_sales AS
SELECT
    o.store_id,
    p.store_code,
    oi.product_id,
    p.product_code,
    p.product_name,
    p.unit,
    CAST(o.order_date AS DATE)                AS sale_date,
    EXTRACT(ISODOW FROM o.order_date)::INT   AS day_of_week,
    EXTRACT(MONTH  FROM o.order_date)::INT   AS month_of_year,
    EXTRACT(YEAR   FROM o.order_date)::INT   AS year,
    SUM(oi.quantity)                          AS quantity_sold,
    SUM(oi.line_total)                        AS revenue
FROM orders o
JOIN order_items oi ON oi.order_id = o.order_id
JOIN products  p   ON p.product_id = oi.product_id
WHERE o.status = 'completed'
  AND o.order_type = 'sale'
GROUP BY o.store_id, p.store_code, oi.product_id, p.product_code,
         p.product_name, p.unit, o.order_date;

COMMENT ON VIEW v_daily_sales IS 'Daily revenue and quantity sold - input data for the demand forecasting model';


-- View 2: Stock below the minimum level - for the alert chart
CREATE OR REPLACE VIEW v_low_stock AS
SELECT
    i.store_id,
    p.product_id,
    p.product_code,
    p.product_name,
    p.unit,
    SUM(i.quantity)  AS total_quantity,
    p.min_stock,
    p.reorder_point,
    (p.min_stock - SUM(i.quantity)) AS shortage
FROM inventory i
JOIN products p ON p.product_id = i.product_id
WHERE p.is_active = TRUE
GROUP BY i.store_id, p.product_id, p.product_code, p.product_name,
         p.unit, p.min_stock, p.reorder_point
HAVING SUM(i.quantity) < p.min_stock;

COMMENT ON VIEW v_low_stock IS 'Products with stock below the minimum level, with the shortage quantity';


-- View 3: Batches expiring soon - for the alert feature, run on a schedule
CREATE OR REPLACE VIEW v_expiring_inventory AS
SELECT
    i.store_id,
    i.inventory_id,
    i.product_id,
    p.product_code,
    p.product_name,
    p.unit,
    i.batch_code,
    i.quantity,
    i.expiry_date,
    i.received_date,
    (i.expiry_date - CURRENT_DATE)                       AS days_to_expiry,
    (i.quantity * p.unit_cost)                           AS stock_value,
    CASE
        WHEN i.expiry_date < CURRENT_DATE                        THEN 'expired'
        WHEN i.expiry_date <= CURRENT_DATE + 3                   THEN 'critical'
        WHEN i.expiry_date <= CURRENT_DATE + 7                   THEN 'high'
        WHEN i.expiry_date <= CURRENT_DATE + 14                  THEN 'medium'
        ELSE 'low'
    END AS alert_severity
FROM inventory i
JOIN products p ON p.product_id = i.product_id
WHERE i.quantity > 0
  AND i.expiry_date IS NOT NULL
  AND i.expiry_date <= CURRENT_DATE + 30;

COMMENT ON VIEW v_expiring_inventory IS 'Batches still in stock expiring within 30 days, with alert severity';


-- View 4: Stock summary per product - for the dashboard
CREATE OR REPLACE VIEW v_product_stock_summary AS
SELECT
    i.store_id,
    p.product_id,
    p.product_code,
    p.product_name,
    p.unit,
    SUM(i.quantity)                          AS total_quantity,
    COUNT(*)                                 AS batch_count,
    MIN(i.expiry_date)                       AS earliest_expiry_date,
    SUM(i.quantity * p.unit_cost)            AS total_stock_value,
    SUM(i.quantity * p.selling_price)        AS potential_revenue,
    SUM(i.quantity * (p.selling_price - p.unit_cost)) AS potential_profit
FROM inventory i
JOIN products p ON p.product_id = i.product_id
WHERE p.is_active = TRUE
GROUP BY i.store_id, p.product_id, p.product_code, p.product_name, p.unit;

COMMENT ON VIEW v_product_stock_summary IS 'Stock, stock value and potential gross profit summary per product';


COMMIT;


-- =============================================================================
--  POST-CREATE VERIFICATION
-- =============================================================================
\echo '--- Tables created ---'
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_type = 'BASE TABLE'
ORDER BY table_name;

\echo '--- Table count (expected: 10) ---'
SELECT COUNT(*) AS total_tables
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';

\echo '--- Foreign key check ---'
SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS references_table
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage ccu
    ON tc.constraint_name = ccu.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema = 'public'
ORDER BY tc.table_name;

\echo '--- Schema created successfully. Next step: run database/02-seed/seed-data.sql ---'

-- =============================================================================
--  TECHNICAL NOTES
-- =============================================================================
--
--  1. CENSORED DEMAND (the most important issue when forecasting retail):
--     View v_daily_sales only records actual sales. When a product is out of
--     stock, sales are 0 even though customers still had demand. When training
--     a model you must:
--       - Use purchase orders to detect which days were out of stock
--       - Correct sales on preceding days with an estimated demand figure
--       - Or treat zero stock as a censored flag for that day
--
--  2. FIFO AND EXPIRY:
--     UNIQUE (store_id, product_id, expiry_date) allows tracking several
--     batches of the same product. The standard business rule when exporting
--     is to take the batch with the earliest expiry date first to minimise
--     spoilage.
--
--  3. VIEW INDEXES:
--     The views can be indexed for faster queries:
--       CREATE INDEX idx_v_daily_sales ON v_daily_sales(product_id, sale_date);
--     Not created yet because the transaction table is still small.
--     Re-evaluate once real data is available.
--
--  4. MIGRATION:
--     Future schema changes must go in database/03-migrations/ with ordered
--     names 01_, 02_, 03_... Do NOT edit this file directly after release.
-- =============================================================================
