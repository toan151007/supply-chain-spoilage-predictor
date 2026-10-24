# HƯỚNG DẪN CHẠY SQL SERVER TRÊN SSMS

> **Cập nhật:** 24/10/2026
> **Áp dụng cho:** Bước 1 & 2 của việc chuyển database PostgreSQL → SQL Server
> **Người thực hiện:** bạn (chạy thủ công trên SSMS)
> **Trạng thái:** file này đã được **test thật** trên SQL Server 2025 Express
> (instance `LAPTOP-I39E3UT2\SQLEXPRESS`) trước khi bàn giao.

---

## 0. Thông tin môi trường

| Mục | Giá trị |
|-----|---------|
| Server | `LAPTOP-I39E3UT2\SQLEXPRESS` |
| Database | `spoilage_predictor` |
| Login | `sa` (SQL Server Authentication) |
| Mật khẩu | **không ghi trong tài liệu này** — bạn tự nhập |
| SQL Server | 2025 Express (17.0.1000.7) |
| ODBC Driver | 18 for SQL Server (đã cài) |
| Python | `pyodbc 5.3.0` (đã cài) |

> ⚠️ **CẢNH BÁO QUAN TRỌNG**
>
> Đoạn DDL ở Phần A có `DROP TABLE / VIEW / PROCEDURE`. Nếu chạy trên database
> **đang có dữ liệu**, toàn bộ dữ liệu sẽ bị xoá. Hiện `spoilage_predictor` đang
> trống nên chạy được ngay. Nếu sau này đã có dữ liệu, hãy **backup trước**.

---

## 1. Chuẩn bị trên SSMS

1. Mở **SQL Server Management Studio**.
2. Ở hộp **Connect to Server**:
   - Server type: `Database Engine`
   - Server name: `LAPTOP-I39E3UT2\SQLEXPRESS`
   - Authentication: `SQL Server Authentication`
   - Login: `sa`
   - Password: mật khẩu của bạn
   - Bấm **Connect**.
3. Ở cửa sổ soạn thảo mới (**New Query**), chạy đoạn sau để chắc chắn database tồn tại:

```sql
IF DB_ID('spoilage_predictor') IS NULL
    CREATE DATABASE spoilage_predictor;
GO
USE spoilage_predictor;
GO
SELECT DB_NAME() AS database_name, @@VERSION AS sql_server_version;
```

4. Nếu database chưa có, câu lệnh trên tạo mới. Nếu đã có, nó chỉ chọn database.

---

## 2. PHẦN A — Tạo 10 bảng, index, trigger, view

**Cách chạy:** chọn toàn bộ khối SQL dưới đây → copy → dán vào **New Query**
trong SSMS → bấm **Execute** (hoặc `F5`).

> Khối này **chạy lại nhiều lần được**: đầu file tự `DROP` object cũ trước khi tạo.
> Toàn bộ comment trong SQL là tiếng Anh không dấu (đúng quy tắc dự án).

```sql
/* =========================================================================
   SUPPLY CHAIN SPOILAGE PREDICTOR - SQL SERVER SCHEMA (DDL)
   Target : SQL Server 2016+ (tested on SQL Server 2025 Express)
   Notes  : ASCII comments only (safe on Windows console)
   ========================================================================= */
SET NOCOUNT ON;
/* Required for filtered indexes and computed columns. SSMS sets these by
   default, but sqlcmd does not, so set them explicitly. */
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
SET ANSI_PADDING ON;
SET ANSI_WARNINGS ON;
SET ARITHABORT ON;
SET CONCAT_NULL_YIELDS_NULL ON;
SET NUMERIC_ROUNDABORT OFF;
GO

USE spoilage_predictor;
GO

/* -------------------------------------------------------------------------
   0. DROP OLD OBJECTS (idempotent)
   ------------------------------------------------------------------------- */
DROP PROCEDURE IF EXISTS dbo.sp_Alerts_Generate;
DROP PROCEDURE IF EXISTS dbo.sp_Orders_RecalculateTotals;
DROP PROCEDURE IF EXISTS dbo.sp_Users_GetByUsername;
DROP PROCEDURE IF EXISTS dbo.sp_Users_GetById;
DROP PROCEDURE IF EXISTS dbo.sp_Users_ChangePassword;
DROP PROCEDURE IF EXISTS dbo.sp_Alerts_List;
DROP PROCEDURE IF EXISTS dbo.sp_Alerts_Get;
DROP PROCEDURE IF EXISTS dbo.sp_Alerts_UnreadCount;
DROP PROCEDURE IF EXISTS dbo.sp_Alerts_MarkRead;
DROP PROCEDURE IF EXISTS dbo.sp_Alerts_MarkAllRead;
DROP PROCEDURE IF EXISTS dbo.sp_Alerts_Resolve;
DROP PROCEDURE IF EXISTS dbo.sp_Alerts_Delete;
DROP PROCEDURE IF EXISTS dbo.sp_Forecasts_List;
DROP PROCEDURE IF EXISTS dbo.sp_Forecasts_Get;
DROP PROCEDURE IF EXISTS dbo.sp_Forecasts_Latest;
DROP PROCEDURE IF EXISTS dbo.sp_Forecasts_Delete;
DROP PROCEDURE IF EXISTS dbo.sp_Forecasts_DeleteByFilter;
DROP PROCEDURE IF EXISTS dbo.sp_OrderItems_List;
DROP PROCEDURE IF EXISTS dbo.sp_OrderItems_Get;
DROP PROCEDURE IF EXISTS dbo.sp_OrderItems_Create;
DROP PROCEDURE IF EXISTS dbo.sp_OrderItems_Update;
DROP PROCEDURE IF EXISTS dbo.sp_OrderItems_Delete;
DROP PROCEDURE IF EXISTS dbo.sp_Orders_List;
DROP PROCEDURE IF EXISTS dbo.sp_Orders_Get;
DROP PROCEDURE IF EXISTS dbo.sp_Orders_Create;
DROP PROCEDURE IF EXISTS dbo.sp_Orders_Update;
DROP PROCEDURE IF EXISTS dbo.sp_Orders_UpdateStatus;
DROP PROCEDURE IF EXISTS dbo.sp_Orders_Delete;
DROP PROCEDURE IF EXISTS dbo.sp_Inventory_List;
DROP PROCEDURE IF EXISTS dbo.sp_Inventory_ListExpiring;
DROP PROCEDURE IF EXISTS dbo.sp_Inventory_Get;
DROP PROCEDURE IF EXISTS dbo.sp_Inventory_Create;
DROP PROCEDURE IF EXISTS dbo.sp_Inventory_Update;
DROP PROCEDURE IF EXISTS dbo.sp_Inventory_Delete;
DROP PROCEDURE IF EXISTS dbo.sp_Categories_List;
DROP PROCEDURE IF EXISTS dbo.sp_Categories_Get;
DROP PROCEDURE IF EXISTS dbo.sp_Categories_Create;
DROP PROCEDURE IF EXISTS dbo.sp_Categories_Update;
DROP PROCEDURE IF EXISTS dbo.sp_Categories_Delete;
DROP PROCEDURE IF EXISTS dbo.sp_Stores_List;
DROP PROCEDURE IF EXISTS dbo.sp_Stores_Get;
DROP PROCEDURE IF EXISTS dbo.sp_Stores_Create;
DROP PROCEDURE IF EXISTS dbo.sp_Stores_Update;
DROP PROCEDURE IF EXISTS dbo.sp_Stores_Delete;
DROP PROCEDURE IF EXISTS dbo.sp_Products_List;
DROP PROCEDURE IF EXISTS dbo.sp_Products_Get;
DROP PROCEDURE IF EXISTS dbo.sp_Products_Create;
DROP PROCEDURE IF EXISTS dbo.sp_Products_Update;
DROP PROCEDURE IF EXISTS dbo.sp_Products_Delete;
GO

DROP VIEW IF EXISTS dbo.v_product_stock_summary;
DROP VIEW IF EXISTS dbo.v_expiring_inventory;
DROP VIEW IF EXISTS dbo.v_low_stock;
DROP VIEW IF EXISTS dbo.v_daily_sales;
GO

DROP TABLE IF EXISTS dbo.alerts;
DROP TABLE IF EXISTS dbo.forecasts;
DROP TABLE IF EXISTS dbo.order_items;
DROP TABLE IF EXISTS dbo.orders;
DROP TABLE IF EXISTS dbo.inventory_transactions;
DROP TABLE IF EXISTS dbo.inventory;
DROP TABLE IF EXISTS dbo.products;
DROP TABLE IF EXISTS dbo.categories;
DROP TABLE IF EXISTS dbo.users;
DROP TABLE IF EXISTS dbo.stores;
GO


/* =========================================================================
   1. TABLES
   ========================================================================= */

CREATE TABLE dbo.stores (
    store_id      INT            IDENTITY(1,1) NOT NULL,
    store_code    NVARCHAR(20)   NOT NULL,
    store_name    NVARCHAR(200)  NOT NULL,
    address       NVARCHAR(MAX)  NULL,
    phone         NVARCHAR(20)   NULL,
    store_type    VARCHAR(20)    NOT NULL
                    CONSTRAINT df_stores_store_type DEFAULT ('convenience_store'),
    opening_date  DATE           NULL,
    is_active     BIT            NOT NULL CONSTRAINT df_stores_is_active DEFAULT (1),
    created_at    DATETIME2(7)   NOT NULL CONSTRAINT df_stores_created_at DEFAULT (SYSDATETIME()),
    updated_at    DATETIME2(7)   NOT NULL CONSTRAINT df_stores_updated_at DEFAULT (SYSDATETIME()),
    CONSTRAINT pk_stores PRIMARY KEY (store_id),
    CONSTRAINT uq_stores_store_code UNIQUE (store_code),
    CONSTRAINT chk_stores_store_type CHECK (store_type IN ('convenience_store', 'restaurant', 'warehouse'))
);
GO

CREATE TABLE dbo.users (
    user_id       INT            IDENTITY(1,1) NOT NULL,
    username      NVARCHAR(50)   NOT NULL,
    email         NVARCHAR(150)  NULL,
    password_hash NVARCHAR(255)  NOT NULL,
    full_name     NVARCHAR(150)  NOT NULL,
    role          VARCHAR(20)    NOT NULL CONSTRAINT df_users_role DEFAULT ('staff'),
    store_id      INT            NULL,
    is_active     BIT            NOT NULL CONSTRAINT df_users_is_active DEFAULT (1),
    created_at    DATETIME2(7)   NOT NULL CONSTRAINT df_users_created_at DEFAULT (SYSDATETIME()),
    updated_at    DATETIME2(7)   NOT NULL CONSTRAINT df_users_updated_at DEFAULT (SYSDATETIME()),
    CONSTRAINT pk_users PRIMARY KEY (user_id),
    CONSTRAINT uq_users_username UNIQUE (username),
    CONSTRAINT uq_users_email UNIQUE (email),
    CONSTRAINT chk_users_role CHECK (role IN ('owner', 'manager', 'staff')),
    CONSTRAINT fk_users_store FOREIGN KEY (store_id)
        REFERENCES dbo.stores (store_id) ON DELETE SET NULL
);
GO

CREATE TABLE dbo.categories (
    category_id        INT            IDENTITY(1,1) NOT NULL,
    category_name      NVARCHAR(150)  NOT NULL,
    description        NVARCHAR(MAX)  NULL,
    parent_category_id INT            NULL,
    created_at         DATETIME2(7)   NOT NULL CONSTRAINT df_categories_created_at DEFAULT (SYSDATETIME()),
    updated_at         DATETIME2(7)   NOT NULL CONSTRAINT df_categories_updated_at DEFAULT (SYSDATETIME()),
    CONSTRAINT pk_categories PRIMARY KEY (category_id),
    CONSTRAINT uq_categories_name UNIQUE (category_name),
    CONSTRAINT fk_categories_parent FOREIGN KEY (parent_category_id)
        REFERENCES dbo.categories (category_id)
);
GO

CREATE TABLE dbo.products (
    product_id      INT            IDENTITY(1,1) NOT NULL,
    product_code    NVARCHAR(50)   NOT NULL,
    product_name    NVARCHAR(255)  NOT NULL,
    category_id     INT            NOT NULL,
    unit            NVARCHAR(20)   NOT NULL,
    unit_cost       DECIMAL(15,2)  NOT NULL CONSTRAINT df_products_unit_cost DEFAULT (0),
    selling_price   DECIMAL(15,2)  NOT NULL CONSTRAINT df_products_selling_price DEFAULT (0),
    shelf_life_days INT            NOT NULL,
    min_stock       DECIMAL(15,3)  NOT NULL CONSTRAINT df_products_min_stock DEFAULT (0),
    max_stock       DECIMAL(15,3)  NULL,
    is_perishable   BIT            NOT NULL CONSTRAINT df_products_is_perishable DEFAULT (1),
    reorder_point   DECIMAL(15,3)  NULL,
    supplier        NVARCHAR(200)  NULL,
    is_active       BIT            NOT NULL CONSTRAINT df_products_is_active DEFAULT (1),
    created_at      DATETIME2(7)   NOT NULL CONSTRAINT df_products_created_at DEFAULT (SYSDATETIME()),
    updated_at      DATETIME2(7)   NOT NULL CONSTRAINT df_products_updated_at DEFAULT (SYSDATETIME()),
    CONSTRAINT pk_products PRIMARY KEY (product_id),
    CONSTRAINT uq_products_product_code UNIQUE (product_code),
    CONSTRAINT fk_products_category FOREIGN KEY (category_id)
        REFERENCES dbo.categories (category_id),
    CONSTRAINT chk_products_unit_cost CHECK (unit_cost >= 0),
    CONSTRAINT chk_products_selling_price CHECK (selling_price >= 0),
    CONSTRAINT chk_products_shelf_life CHECK (shelf_life_days > 0),
    CONSTRAINT chk_products_min_stock CHECK (min_stock >= 0),
    CONSTRAINT chk_products_max_stock CHECK (max_stock IS NULL OR max_stock > 0),
    CONSTRAINT chk_products_reorder_point CHECK (reorder_point IS NULL OR reorder_point >= 0),
    CONSTRAINT chk_stock_range CHECK (max_stock IS NULL OR min_stock <= max_stock)
);
GO

CREATE TABLE dbo.inventory (
    inventory_id  BIGINT         IDENTITY(1,1) NOT NULL,
    store_id      INT            NOT NULL,
    product_id    INT            NOT NULL,
    expiry_date   DATE           NULL,
    quantity      DECIMAL(15,3)  NOT NULL CONSTRAINT df_inventory_quantity DEFAULT (0),
    received_date DATE           NOT NULL CONSTRAINT df_inventory_received_date DEFAULT (CONVERT(DATE, SYSDATETIME())),
    batch_code    NVARCHAR(50)   NULL,
    created_at    DATETIME2(7)   NOT NULL CONSTRAINT df_inventory_created_at DEFAULT (SYSDATETIME()),
    updated_at    DATETIME2(7)   NOT NULL CONSTRAINT df_inventory_updated_at DEFAULT (SYSDATETIME()),
    CONSTRAINT pk_inventory PRIMARY KEY (inventory_id),
    CONSTRAINT fk_inventory_store FOREIGN KEY (store_id)
        REFERENCES dbo.stores (store_id) ON DELETE CASCADE,
    CONSTRAINT fk_inventory_product FOREIGN KEY (product_id)
        REFERENCES dbo.products (product_id),
    CONSTRAINT chk_inventory_quantity CHECK (quantity >= 0)
);
GO

/* SQL Server treats NULLs as equal in a UNIQUE constraint, while PostgreSQL
   allows many NULLs. A filtered unique index reproduces the PostgreSQL rule:
   only batches WITH an expiry date must be unique per store/product. */
CREATE UNIQUE INDEX uq_inventory_store_product_expiry
    ON dbo.inventory (store_id, product_id, expiry_date)
    WHERE expiry_date IS NOT NULL;
GO

CREATE TABLE dbo.inventory_transactions (
    transaction_id   BIGINT         IDENTITY(1,1) NOT NULL,
    store_id         INT            NOT NULL,
    product_id       INT            NOT NULL,
    expiry_date      DATE           NULL,
    transaction_type VARCHAR(20)    NOT NULL,
    quantity         DECIMAL(15,3)  NOT NULL,
    unit_cost        DECIMAL(15,2)  NULL,
    reference_type   VARCHAR(30)    NULL CONSTRAINT df_inv_tx_reference_type DEFAULT ('manual'),
    reference_id     BIGINT         NULL,
    transaction_date DATETIME2(7)   NOT NULL CONSTRAINT df_inv_tx_transaction_date DEFAULT (SYSDATETIME()),
    user_id          INT            NULL,
    note             NVARCHAR(MAX)  NULL,
    created_at       DATETIME2(7)   NOT NULL CONSTRAINT df_inv_tx_created_at DEFAULT (SYSDATETIME()),
    CONSTRAINT pk_inventory_transactions PRIMARY KEY (transaction_id),
    CONSTRAINT fk_inv_tx_store FOREIGN KEY (store_id)
        REFERENCES dbo.stores (store_id) ON DELETE CASCADE,
    CONSTRAINT fk_inv_tx_product FOREIGN KEY (product_id)
        REFERENCES dbo.products (product_id),
    CONSTRAINT fk_inv_tx_user FOREIGN KEY (user_id)
        REFERENCES dbo.users (user_id) ON DELETE SET NULL,
    CONSTRAINT chk_inv_tx_type CHECK (transaction_type IN ('import', 'export', 'adjustment', 'disposal')),
    CONSTRAINT chk_inv_tx_quantity CHECK (quantity > 0),
    CONSTRAINT chk_inv_tx_unit_cost CHECK (unit_cost IS NULL OR unit_cost >= 0),
    CONSTRAINT chk_inv_tx_reference_type CHECK (reference_type IN ('manual', 'order', 'import_excel'))
);
GO

CREATE UNIQUE INDEX uq_transactions_reference
    ON dbo.inventory_transactions (reference_type, reference_id, product_id, expiry_date)
    WHERE reference_id IS NOT NULL AND expiry_date IS NOT NULL;
GO

CREATE TABLE dbo.orders (
    order_id       BIGINT         IDENTITY(1,1) NOT NULL,
    order_code     NVARCHAR(50)   NOT NULL,
    store_id       INT            NOT NULL,
    order_type     VARCHAR(20)    NOT NULL CONSTRAINT df_orders_order_type DEFAULT ('sale'),
    order_date     DATETIME2(7)   NOT NULL CONSTRAINT df_orders_order_date DEFAULT (SYSDATETIME()),
    total_amount   DECIMAL(18,2)  NOT NULL CONSTRAINT df_orders_total_amount DEFAULT (0),
    total_quantity DECIMAL(15,3)  NOT NULL CONSTRAINT df_orders_total_quantity DEFAULT (0),
    status         VARCHAR(20)    NOT NULL CONSTRAINT df_orders_status DEFAULT ('completed'),
    payment_method VARCHAR(30)    NULL,
    customer_name  NVARCHAR(150)  NULL,
    user_id        INT            NULL,
    note           NVARCHAR(MAX)  NULL,
    created_at     DATETIME2(7)   NOT NULL CONSTRAINT df_orders_created_at DEFAULT (SYSDATETIME()),
    updated_at     DATETIME2(7)   NOT NULL CONSTRAINT df_orders_updated_at DEFAULT (SYSDATETIME()),
    CONSTRAINT pk_orders PRIMARY KEY (order_id),
    CONSTRAINT uq_orders_order_code UNIQUE (order_code),
    CONSTRAINT fk_orders_store FOREIGN KEY (store_id)
        REFERENCES dbo.stores (store_id),
    CONSTRAINT fk_orders_user FOREIGN KEY (user_id)
        REFERENCES dbo.users (user_id) ON DELETE SET NULL,
    CONSTRAINT chk_orders_type CHECK (order_type IN ('sale', 'purchase')),
    CONSTRAINT chk_orders_status CHECK (status IN ('pending', 'completed', 'cancelled')),
    CONSTRAINT chk_orders_total_amount CHECK (total_amount >= 0),
    CONSTRAINT chk_orders_total_quantity CHECK (total_quantity >= 0),
    CONSTRAINT chk_orders_payment_method CHECK (payment_method IS NULL OR payment_method IN ('cash', 'card', 'transfer', 'ewallet', 'other'))
);
GO

CREATE TABLE dbo.order_items (
    order_item_id    BIGINT         IDENTITY(1,1) NOT NULL,
    order_id         BIGINT         NOT NULL,
    product_id       INT            NOT NULL,
    quantity         DECIMAL(15,3)  NOT NULL,
    unit_price       DECIMAL(15,2)  NOT NULL,
    unit_cost        DECIMAL(15,2)  NULL,
    discount_percent DECIMAL(5,2)   NOT NULL CONSTRAINT df_order_items_discount DEFAULT (0),
    line_total       AS (CAST(ROUND(quantity * unit_price * (1 - discount_percent / 100.0), 2) AS DECIMAL(18,2))) PERSISTED,
    created_at       DATETIME2(7)   NOT NULL CONSTRAINT df_order_items_created_at DEFAULT (SYSDATETIME()),
    CONSTRAINT pk_order_items PRIMARY KEY (order_item_id),
    CONSTRAINT fk_order_items_order FOREIGN KEY (order_id)
        REFERENCES dbo.orders (order_id) ON DELETE CASCADE,
    CONSTRAINT fk_order_items_product FOREIGN KEY (product_id)
        REFERENCES dbo.products (product_id),
    CONSTRAINT uq_order_items_order_product UNIQUE (order_id, product_id),
    CONSTRAINT chk_order_items_quantity CHECK (quantity > 0),
    CONSTRAINT chk_order_items_unit_price CHECK (unit_price >= 0),
    CONSTRAINT chk_order_items_unit_cost CHECK (unit_cost IS NULL OR unit_cost >= 0),
    CONSTRAINT chk_order_items_discount CHECK (discount_percent >= 0 AND discount_percent <= 100)
);
GO

CREATE TABLE dbo.forecasts (
    forecast_id            BIGINT         IDENTITY(1,1) NOT NULL,
    store_id               INT            NOT NULL,
    product_id             INT            NOT NULL,
    model_name             VARCHAR(50)    NOT NULL,
    forecast_date          DATE           NOT NULL,
    horizon_days           INT            NOT NULL CONSTRAINT df_forecasts_horizon DEFAULT (1),
    predicted_quantity     DECIMAL(15,3)  NOT NULL,
    lower_bound            DECIMAL(15,3)  NULL,
    upper_bound            DECIMAL(15,3)  NULL,
    recommended_import_qty DECIMAL(15,3)  NULL,
    rmse                   DECIMAL(12,4)  NULL,
    mae                    DECIMAL(12,4)  NULL,
    mape                   DECIMAL(12,4)  NULL,
    trained_at             DATETIME2(7)   NOT NULL CONSTRAINT df_forecasts_trained_at DEFAULT (SYSDATETIME()),
    created_at             DATETIME2(7)   NOT NULL CONSTRAINT df_forecasts_created_at DEFAULT (SYSDATETIME()),
    CONSTRAINT pk_forecasts PRIMARY KEY (forecast_id),
    CONSTRAINT uq_forecasts_unique UNIQUE (store_id, product_id, model_name, forecast_date),
    CONSTRAINT fk_forecasts_store FOREIGN KEY (store_id)
        REFERENCES dbo.stores (store_id) ON DELETE CASCADE,
    CONSTRAINT fk_forecasts_product FOREIGN KEY (product_id)
        REFERENCES dbo.products (product_id),
    CONSTRAINT chk_forecasts_model CHECK (model_name IN ('prophet', 'xgboost', 'arima', 'moving_average', 'naive')),
    CONSTRAINT chk_forecasts_horizon CHECK (horizon_days > 0),
    CONSTRAINT chk_forecasts_predicted CHECK (predicted_quantity >= 0),
    CONSTRAINT chk_forecasts_lower CHECK (lower_bound IS NULL OR lower_bound >= 0),
    CONSTRAINT chk_forecasts_upper CHECK (upper_bound IS NULL OR upper_bound >= 0),
    CONSTRAINT chk_forecasts_recommended CHECK (recommended_import_qty IS NULL OR recommended_import_qty >= 0),
    CONSTRAINT chk_forecasts_rmse CHECK (rmse IS NULL OR rmse >= 0),
    CONSTRAINT chk_forecasts_mae CHECK (mae IS NULL OR mae >= 0),
    CONSTRAINT chk_forecasts_mape CHECK (mape IS NULL OR mape >= 0)
);
GO

CREATE TABLE dbo.alerts (
    alert_id        BIGINT         IDENTITY(1,1) NOT NULL,
    store_id        INT            NULL,
    product_id      INT            NULL,
    alert_type      VARCHAR(30)    NOT NULL,
    severity        VARCHAR(10)    NOT NULL CONSTRAINT df_alerts_severity DEFAULT ('low'),
    title           NVARCHAR(255)  NOT NULL,
    message         NVARCHAR(MAX)  NULL,
    expiry_date     DATE           NULL,
    current_stock   DECIMAL(15,3)  NULL,
    threshold_value DECIMAL(15,3)  NULL,
    is_read         BIT            NOT NULL CONSTRAINT df_alerts_is_read DEFAULT (0),
    is_resolved     BIT            NOT NULL CONSTRAINT df_alerts_is_resolved DEFAULT (0),
    created_at      DATETIME2(7)   NOT NULL CONSTRAINT df_alerts_created_at DEFAULT (SYSDATETIME()),
    resolved_at     DATETIME2(7)   NULL,
    CONSTRAINT pk_alerts PRIMARY KEY (alert_id),
    CONSTRAINT fk_alerts_store FOREIGN KEY (store_id)
        REFERENCES dbo.stores (store_id) ON DELETE CASCADE,
    CONSTRAINT fk_alerts_product FOREIGN KEY (product_id)
        REFERENCES dbo.products (product_id) ON DELETE CASCADE,
    CONSTRAINT chk_alert_type CHECK (alert_type IN ('expiring_soon', 'expired', 'low_stock', 'over_stock', 'forecast_anomaly')),
    CONSTRAINT chk_alert_severity CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    CONSTRAINT chk_alert_resolved_at CHECK (
        (is_resolved = 1 AND resolved_at IS NOT NULL) OR
        (is_resolved = 0 AND resolved_at IS NULL)
    )
);
GO


/* =========================================================================
   2. INDEXES
   ========================================================================= */
CREATE INDEX idx_users_store_id ON dbo.users (store_id);
GO
CREATE INDEX idx_categories_parent_id ON dbo.categories (parent_category_id);
GO
CREATE INDEX idx_products_category_id ON dbo.products (category_id);
CREATE INDEX idx_products_is_active ON dbo.products (is_active);
CREATE INDEX idx_products_product_name ON dbo.products (product_name);
GO
CREATE INDEX idx_inventory_product_id ON dbo.inventory (product_id);
CREATE INDEX idx_inventory_store_id ON dbo.inventory (store_id);
CREATE INDEX idx_inventory_expiry_date ON dbo.inventory (expiry_date);
CREATE INDEX idx_inventory_expiry_store ON dbo.inventory (expiry_date, store_id) WHERE quantity > 0;
GO
CREATE INDEX idx_transactions_product_date ON dbo.inventory_transactions (product_id, transaction_date);
CREATE INDEX idx_transactions_store_date ON dbo.inventory_transactions (store_id, transaction_date);
CREATE INDEX idx_transactions_date ON dbo.inventory_transactions (transaction_date);
CREATE INDEX idx_transactions_type_date ON dbo.inventory_transactions (transaction_type, transaction_date);
GO
CREATE INDEX idx_orders_store_date ON dbo.orders (store_id, order_date);
CREATE INDEX idx_orders_date ON dbo.orders (order_date);
CREATE INDEX idx_orders_type_date ON dbo.orders (order_type, order_date, status);
GO
CREATE INDEX idx_order_items_order_id ON dbo.order_items (order_id);
CREATE INDEX idx_order_items_product_id ON dbo.order_items (product_id);
GO
CREATE INDEX idx_forecasts_product_date ON dbo.forecasts (product_id, forecast_date);
CREATE INDEX idx_forecasts_store_date ON dbo.forecasts (store_id, forecast_date);
CREATE INDEX idx_forecasts_model ON dbo.forecasts (model_name);
GO
CREATE INDEX idx_alerts_unread ON dbo.alerts (store_id, created_at DESC) WHERE is_read = 0;
CREATE INDEX idx_alerts_product ON dbo.alerts (product_id);
CREATE INDEX idx_alerts_type_date ON dbo.alerts (alert_type, created_at DESC);
GO


/* =========================================================================
   3. TRIGGERS - auto update updated_at
   ========================================================================= */
CREATE OR ALTER TRIGGER dbo.trg_stores_updated ON dbo.stores AFTER UPDATE AS
BEGIN
    SET NOCOUNT ON;
    IF TRIGGER_NESTLEVEL() > 1 RETURN;
    UPDATE s SET s.updated_at = SYSDATETIME()
    FROM dbo.stores s JOIN inserted i ON i.store_id = s.store_id;
END;
GO

CREATE OR ALTER TRIGGER dbo.trg_users_updated ON dbo.users AFTER UPDATE AS
BEGIN
    SET NOCOUNT ON;
    IF TRIGGER_NESTLEVEL() > 1 RETURN;
    UPDATE u SET u.updated_at = SYSDATETIME()
    FROM dbo.users u JOIN inserted i ON i.user_id = u.user_id;
END;
GO

CREATE OR ALTER TRIGGER dbo.trg_categories_updated ON dbo.categories AFTER UPDATE AS
BEGIN
    SET NOCOUNT ON;
    IF TRIGGER_NESTLEVEL() > 1 RETURN;
    UPDATE c SET c.updated_at = SYSDATETIME()
    FROM dbo.categories c JOIN inserted i ON i.category_id = c.category_id;
END;
GO

CREATE OR ALTER TRIGGER dbo.trg_products_updated ON dbo.products AFTER UPDATE AS
BEGIN
    SET NOCOUNT ON;
    IF TRIGGER_NESTLEVEL() > 1 RETURN;
    UPDATE p SET p.updated_at = SYSDATETIME()
    FROM dbo.products p JOIN inserted i ON i.product_id = p.product_id;
END;
GO

CREATE OR ALTER TRIGGER dbo.trg_inventory_updated ON dbo.inventory AFTER UPDATE AS
BEGIN
    SET NOCOUNT ON;
    IF TRIGGER_NESTLEVEL() > 1 RETURN;
    UPDATE i SET i.updated_at = SYSDATETIME()
    FROM dbo.inventory i JOIN inserted ins ON ins.inventory_id = i.inventory_id;
END;
GO

CREATE OR ALTER TRIGGER dbo.trg_orders_updated ON dbo.orders AFTER UPDATE AS
BEGIN
    SET NOCOUNT ON;
    IF TRIGGER_NESTLEVEL() > 1 RETURN;
    UPDATE o SET o.updated_at = SYSDATETIME()
    FROM dbo.orders o JOIN inserted i ON i.order_id = o.order_id;
END;
GO


/* =========================================================================
   4. VIEWS
   ========================================================================= */
CREATE OR ALTER VIEW dbo.v_daily_sales AS
SELECT
    o.store_id,
    s.store_code,
    s.store_name,
    oi.product_id,
    p.product_code,
    p.product_name,
    p.unit,
    CAST(o.order_date AS DATE) AS sale_date,
    CAST((DATEDIFF(DAY, CONVERT(DATE, '19000101', 112), CAST(o.order_date AS DATE)) % 7) + 1 AS INT) AS day_of_week,
    DATEPART(MONTH, CAST(o.order_date AS DATE)) AS month_of_year,
    DATEPART(YEAR, CAST(o.order_date AS DATE)) AS [year],
    SUM(oi.quantity) AS quantity_sold,
    SUM(oi.line_total) AS revenue
FROM dbo.orders o
JOIN dbo.order_items oi ON oi.order_id = o.order_id
JOIN dbo.products p ON p.product_id = oi.product_id
JOIN dbo.stores s ON s.store_id = o.store_id
WHERE o.status = 'completed'
  AND o.order_type = 'sale'
GROUP BY o.store_id, s.store_code, s.store_name, oi.product_id, p.product_code,
         p.product_name, p.unit, CAST(o.order_date AS DATE);
GO

CREATE OR ALTER VIEW dbo.v_low_stock AS
SELECT
    i.store_id,
    p.product_id,
    p.product_code,
    p.product_name,
    p.unit,
    SUM(i.quantity) AS total_quantity,
    p.min_stock,
    p.reorder_point,
    (p.min_stock - SUM(i.quantity)) AS shortage
FROM dbo.inventory i
JOIN dbo.products p ON p.product_id = i.product_id
WHERE p.is_active = 1
GROUP BY i.store_id, p.product_id, p.product_code, p.product_name,
         p.unit, p.min_stock, p.reorder_point
HAVING SUM(i.quantity) < p.min_stock;
GO

CREATE OR ALTER VIEW dbo.v_expiring_inventory AS
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
    DATEDIFF(DAY, CAST(SYSDATETIME() AS DATE), i.expiry_date) AS days_to_expiry,
    CAST(i.quantity * p.unit_cost AS DECIMAL(18,2)) AS stock_value,
    CASE
        WHEN i.expiry_date < CAST(SYSDATETIME() AS DATE) THEN 'expired'
        WHEN i.expiry_date <= DATEADD(DAY, 3, CAST(SYSDATETIME() AS DATE)) THEN 'critical'
        WHEN i.expiry_date <= DATEADD(DAY, 7, CAST(SYSDATETIME() AS DATE)) THEN 'high'
        WHEN i.expiry_date <= DATEADD(DAY, 14, CAST(SYSDATETIME() AS DATE)) THEN 'medium'
        ELSE 'low'
    END AS alert_severity
FROM dbo.inventory i
JOIN dbo.products p ON p.product_id = i.product_id
WHERE i.quantity > 0
  AND i.expiry_date IS NOT NULL
  AND i.expiry_date <= DATEADD(DAY, 30, CAST(SYSDATETIME() AS DATE));
GO

CREATE OR ALTER VIEW dbo.v_product_stock_summary AS
SELECT
    i.store_id,
    p.product_id,
    p.product_code,
    p.product_name,
    p.unit,
    SUM(i.quantity) AS total_quantity,
    COUNT(*) AS batch_count,
    MIN(i.expiry_date) AS earliest_expiry_date,
    SUM(i.quantity * p.unit_cost) AS total_stock_value,
    SUM(i.quantity * p.selling_price) AS potential_revenue,
    SUM(i.quantity * (p.selling_price - p.unit_cost)) AS potential_profit
FROM dbo.inventory i
JOIN dbo.products p ON p.product_id = i.product_id
WHERE p.is_active = 1
GROUP BY i.store_id, p.product_id, p.product_code, p.product_name, p.unit;
GO


/* =========================================================================
   5. VERIFY
   ========================================================================= */
SELECT 'tables' AS object_type, COUNT(*) AS total
FROM sys.tables WHERE schema_id = SCHEMA_ID('dbo')
UNION ALL
SELECT 'views', COUNT(*) FROM sys.views WHERE schema_id = SCHEMA_ID('dbo')
UNION ALL
SELECT 'procedures', COUNT(*) FROM sys.procedures WHERE schema_id = SCHEMA_ID('dbo');
GO
```

**Kết quả mong đợi ở cuối Phần A:**

| object_type | total |
|-------------|-------|
| tables | 10 |
| views | 4 |

Nếu thấy đúng 10 bảng và 4 view là Phần A thành công.

**Các điểm khác PostgreSQL cần biết:**

- `IDENTITY(1,1)` thay cho `SERIAL`.
- `DATETIME2(7)` thay cho `TIMESTAMPTZ`.
- `NVARCHAR` / `NVARCHAR(MAX)` thay cho `TEXT`.
- `BIT` thay cho `BOOLEAN`.
- `line_total` là **computed column** — không được gán giá trị khi INSERT/UPDATE.
- `inventory` và `inventory_transactions` dùng **filtered unique index**
  (`WHERE ... IS NOT NULL`) vì SQL Server coi nhiều `NULL` là trùng nhau.
- `categories.parent_category_id` **không cascade** (SQL Server báo lỗi 1785 nếu
  cascade trên khoá tự tham chiếu) — procedure sẽ tự set NULL cho con trước khi xoá.

---

## 3. PHẦN B — Tạo 49 Stored Procedure

**Cách chạy:** mở **New Query** mới → dán toàn bộ khối dưới → **Execute**.

> Mỗi procedure đều có `BEGIN TRY ... BEGIN CATCH` và transaction có kiểm tra
> `@@TRANCOUNT` (theo yêu cầu 100% Stored Procedure).

```sql
/* =========================================================================
   SUPPLY CHAIN SPOILAGE PREDICTOR - STORED PROCEDURES (SQL SERVER)
   Rule: every data operation goes through a stored procedure.
   Every procedure uses BEGIN TRY ... BEGIN CATCH and a guarded TRANSACTION.

   Error numbers returned by THROW (map these to HTTP codes in FastAPI):
     50001 = NOT_FOUND        -> 404
     50002 = DUPLICATE        -> 409
     50003 = REFERENCED       -> 409
     50004 = INVALID_STATE    -> 409
     50005 = INVALID_INPUT    -> 422
   ========================================================================= */
SET NOCOUNT ON;
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
GO

USE spoilage_predictor;
GO


/* =========================================================================
   PRODUCTS
   ========================================================================= */
CREATE OR ALTER PROCEDURE dbo.sp_Products_List
    @Search     NVARCHAR(255) = NULL,
    @CategoryId INT           = NULL,
    @IsActive   BIT           = NULL,
    @Page       INT           = 1,
    @PageSize   INT           = 20
AS
BEGIN
    SET NOCOUNT ON;
    IF @Page < 1 SET @Page = 1;
    IF @PageSize < 1 SET @PageSize = 20;
    IF @PageSize > 100 SET @PageSize = 100;
    DECLARE @Offset INT = (@Page - 1) * @PageSize;

    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        SELECT COUNT(*) AS total
        FROM dbo.products p
        WHERE (@CategoryId IS NULL OR p.category_id = @CategoryId)
          AND (@IsActive IS NULL OR p.is_active = @IsActive)
          AND (@Search IS NULL
               OR p.product_name LIKE N'%' + @Search + N'%'
               OR p.product_code LIKE N'%' + @Search + N'%');

        SELECT
            p.product_id, p.product_code, p.product_name, p.category_id,
            p.unit, p.unit_cost, p.selling_price, p.shelf_life_days,
            p.min_stock, p.max_stock, p.is_perishable, p.reorder_point,
            p.supplier, p.is_active, p.created_at, p.updated_at,
            c.category_name
        FROM dbo.products p
        LEFT JOIN dbo.categories c ON c.category_id = p.category_id
        WHERE (@CategoryId IS NULL OR p.category_id = @CategoryId)
          AND (@IsActive IS NULL OR p.is_active = @IsActive)
          AND (@Search IS NULL
               OR p.product_name LIKE N'%' + @Search + N'%'
               OR p.product_code LIKE N'%' + @Search + N'%')
        ORDER BY p.product_id
        OFFSET @Offset ROWS FETCH NEXT @PageSize ROWS ONLY;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Products_Get
    @ProductId INT
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        IF NOT EXISTS (SELECT 1 FROM dbo.products WHERE product_id = @ProductId)
            THROW 50001, N'Product not found', 1;

        SELECT
            p.product_id, p.product_code, p.product_name, p.category_id,
            p.unit, p.unit_cost, p.selling_price, p.shelf_life_days,
            p.min_stock, p.max_stock, p.is_perishable, p.reorder_point,
            p.supplier, p.is_active, p.created_at, p.updated_at,
            c.category_name
        FROM dbo.products p
        LEFT JOIN dbo.categories c ON c.category_id = p.category_id
        WHERE p.product_id = @ProductId;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Products_Create
    @ProductCode    NVARCHAR(50),
    @ProductName    NVARCHAR(255),
    @CategoryId     INT,
    @Unit           NVARCHAR(20),
    @UnitCost       DECIMAL(15,2) = 0,
    @SellingPrice   DECIMAL(15,2) = 0,
    @ShelfLifeDays  INT,
    @MinStock       DECIMAL(15,3) = 0,
    @MaxStock       DECIMAL(15,3) = NULL,
    @IsPerishable   BIT = 1,
    @ReorderPoint   DECIMAL(15,3) = NULL,
    @Supplier       NVARCHAR(200) = NULL,
    @IsActive       BIT = 1
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        IF NOT EXISTS (SELECT 1 FROM dbo.categories WHERE category_id = @CategoryId)
            THROW 50005, N'category_id does not exist', 1;
        IF @MaxStock IS NOT NULL AND @MaxStock < @MinStock
            THROW 50005, N'max_stock must be greater than or equal to min_stock', 1;
        IF EXISTS (SELECT 1 FROM dbo.products WHERE product_code = @ProductCode)
            THROW 50002, N'product_code already exists', 1;

        INSERT INTO dbo.products (
            product_code, product_name, category_id, unit, unit_cost,
            selling_price, shelf_life_days, min_stock, max_stock,
            is_perishable, reorder_point, supplier, is_active
        )
        VALUES (
            @ProductCode, @ProductName, @CategoryId, @Unit, @UnitCost,
            @SellingPrice, @ShelfLifeDays, @MinStock, @MaxStock,
            @IsPerishable, @ReorderPoint, @Supplier, @IsActive
        );

        DECLARE @NewId INT = CAST(SCOPE_IDENTITY() AS INT);

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;

        EXEC dbo.sp_Products_Get @ProductId = @NewId;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        IF ERROR_NUMBER() IN (2601, 2627) THROW 50002, N'product_code already exists', 1;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Products_Update
    @ProductId      INT,
    @ProductCode    NVARCHAR(50),
    @ProductName    NVARCHAR(255),
    @CategoryId     INT,
    @Unit           NVARCHAR(20),
    @UnitCost       DECIMAL(15,2),
    @SellingPrice   DECIMAL(15,2),
    @ShelfLifeDays  INT,
    @MinStock       DECIMAL(15,3),
    @MaxStock       DECIMAL(15,3) = NULL,
    @IsPerishable   BIT,
    @ReorderPoint   DECIMAL(15,3) = NULL,
    @Supplier       NVARCHAR(200) = NULL,
    @IsActive       BIT
AS
BEGIN
    /* Contract: the caller sends the COMPLETE desired row. A partial update
       must merge the change into the current row before calling. This keeps
       explicit NULL (clear a field) different from omitted (keep current). */
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        IF NOT EXISTS (SELECT 1 FROM dbo.products WHERE product_id = @ProductId)
            THROW 50001, N'Product not found', 1;
        IF NOT EXISTS (SELECT 1 FROM dbo.categories WHERE category_id = @CategoryId)
            THROW 50005, N'category_id does not exist', 1;
        IF @MaxStock IS NOT NULL AND @MaxStock < @MinStock
            THROW 50005, N'max_stock must be greater than or equal to min_stock', 1;
        IF EXISTS (SELECT 1 FROM dbo.products
                   WHERE product_code = @ProductCode AND product_id <> @ProductId)
            THROW 50002, N'product_code already exists', 1;

        UPDATE dbo.products SET
            product_code    = @ProductCode,
            product_name    = @ProductName,
            category_id     = @CategoryId,
            unit            = @Unit,
            unit_cost       = @UnitCost,
            selling_price   = @SellingPrice,
            shelf_life_days = @ShelfLifeDays,
            min_stock       = @MinStock,
            max_stock       = @MaxStock,
            is_perishable   = @IsPerishable,
            reorder_point   = @ReorderPoint,
            supplier        = @Supplier,
            is_active       = @IsActive
        WHERE product_id = @ProductId;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;

        EXEC dbo.sp_Products_Get @ProductId = @ProductId;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        IF ERROR_NUMBER() IN (2601, 2627) THROW 50002, N'product_code already exists', 1;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Products_Delete
    @ProductId INT
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        IF NOT EXISTS (SELECT 1 FROM dbo.products WHERE product_id = @ProductId)
            THROW 50001, N'Product not found', 1;
        IF EXISTS (SELECT 1 FROM dbo.inventory WHERE product_id = @ProductId)
            OR EXISTS (SELECT 1 FROM dbo.inventory_transactions WHERE product_id = @ProductId)
            OR EXISTS (SELECT 1 FROM dbo.order_items WHERE product_id = @ProductId)
            OR EXISTS (SELECT 1 FROM dbo.forecasts WHERE product_id = @ProductId)
            THROW 50003, N'Product has stock or sales history; deactivate it instead', 1;

        DELETE FROM dbo.products WHERE product_id = @ProductId;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


/* =========================================================================
   STORES
   ========================================================================= */
CREATE OR ALTER PROCEDURE dbo.sp_Stores_List
    @Search    NVARCHAR(255) = NULL,
    @StoreType VARCHAR(20)   = NULL,
    @IsActive  BIT           = NULL,
    @Page      INT           = 1,
    @PageSize  INT           = 20
AS
BEGIN
    SET NOCOUNT ON;
    IF @Page < 1 SET @Page = 1;
    IF @PageSize < 1 SET @PageSize = 20;
    IF @PageSize > 100 SET @PageSize = 100;
    DECLARE @Offset INT = (@Page - 1) * @PageSize;

    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        SELECT COUNT(*) AS total
        FROM dbo.stores s
        WHERE (@StoreType IS NULL OR s.store_type = @StoreType)
          AND (@IsActive IS NULL OR s.is_active = @IsActive)
          AND (@Search IS NULL
               OR s.store_name LIKE N'%' + @Search + N'%'
               OR s.store_code LIKE N'%' + @Search + N'%');

        SELECT s.store_id, s.store_code, s.store_name, s.address, s.phone,
               s.store_type, s.opening_date, s.is_active,
               s.created_at, s.updated_at
        FROM dbo.stores s
        WHERE (@StoreType IS NULL OR s.store_type = @StoreType)
          AND (@IsActive IS NULL OR s.is_active = @IsActive)
          AND (@Search IS NULL
               OR s.store_name LIKE N'%' + @Search + N'%'
               OR s.store_code LIKE N'%' + @Search + N'%')
        ORDER BY s.store_id
        OFFSET @Offset ROWS FETCH NEXT @PageSize ROWS ONLY;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Stores_Get
    @StoreId INT
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;
        IF NOT EXISTS (SELECT 1 FROM dbo.stores WHERE store_id = @StoreId)
            THROW 50001, N'Store not found', 1;
        SELECT store_id, store_code, store_name, address, phone, store_type,
               opening_date, is_active, created_at, updated_at
        FROM dbo.stores WHERE store_id = @StoreId;
        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Stores_Create
    @StoreCode   NVARCHAR(20),
    @StoreName   NVARCHAR(200),
    @Address     NVARCHAR(MAX) = NULL,
    @Phone       NVARCHAR(20)  = NULL,
    @StoreType   VARCHAR(20)   = 'convenience_store',
    @OpeningDate DATE          = NULL,
    @IsActive    BIT           = 1
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;
        IF EXISTS (SELECT 1 FROM dbo.stores WHERE store_code = @StoreCode)
            THROW 50002, N'store_code already exists', 1;

        INSERT INTO dbo.stores (store_code, store_name, address, phone, store_type, opening_date, is_active)
        VALUES (@StoreCode, @StoreName, @Address, @Phone, @StoreType, @OpeningDate, @IsActive);

        DECLARE @NewId INT = CAST(SCOPE_IDENTITY() AS INT);
        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
        EXEC dbo.sp_Stores_Get @StoreId = @NewId;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        IF ERROR_NUMBER() IN (2601, 2627) THROW 50002, N'store_code already exists', 1;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Stores_Update
    @StoreId     INT,
    @StoreCode   NVARCHAR(20),
    @StoreName   NVARCHAR(200),
    @Address     NVARCHAR(MAX) = NULL,
    @Phone       NVARCHAR(20)  = NULL,
    @StoreType   VARCHAR(20),
    @OpeningDate DATE          = NULL,
    @IsActive    BIT
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;
        IF NOT EXISTS (SELECT 1 FROM dbo.stores WHERE store_id = @StoreId)
            THROW 50001, N'Store not found', 1;
        IF EXISTS (SELECT 1 FROM dbo.stores WHERE store_code = @StoreCode AND store_id <> @StoreId)
            THROW 50002, N'store_code already exists', 1;

        UPDATE dbo.stores SET
            store_code = @StoreCode, store_name = @StoreName,
            address = @Address, phone = @Phone, store_type = @StoreType,
            opening_date = @OpeningDate, is_active = @IsActive
        WHERE store_id = @StoreId;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
        EXEC dbo.sp_Stores_Get @StoreId = @StoreId;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        IF ERROR_NUMBER() IN (2601, 2627) THROW 50002, N'store_code already exists', 1;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Stores_Delete
    @StoreId INT
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;
        IF NOT EXISTS (SELECT 1 FROM dbo.stores WHERE store_id = @StoreId)
            THROW 50001, N'Store not found', 1;
        IF EXISTS (SELECT 1 FROM dbo.orders WHERE store_id = @StoreId)
            THROW 50003, N'Store has orders and cannot be deleted; deactivate it instead', 1;

        DELETE FROM dbo.stores WHERE store_id = @StoreId;
        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


/* =========================================================================
   CATEGORIES
   ========================================================================= */
CREATE OR ALTER PROCEDURE dbo.sp_Categories_List
    @Search           NVARCHAR(150) = NULL,
    @ParentCategoryId INT           = NULL,
    @RootsOnly        BIT           = 0,
    @Page             INT           = 1,
    @PageSize         INT           = 20
AS
BEGIN
    SET NOCOUNT ON;
    IF @Page < 1 SET @Page = 1;
    IF @PageSize < 1 SET @PageSize = 20;
    IF @PageSize > 100 SET @PageSize = 100;
    DECLARE @Offset INT = (@Page - 1) * @PageSize;

    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        SELECT COUNT(*) AS total
        FROM dbo.categories c
        WHERE (@RootsOnly = 1 AND c.parent_category_id IS NULL)
           OR (@RootsOnly = 0 AND (@ParentCategoryId IS NULL OR c.parent_category_id = @ParentCategoryId));

        SELECT c.category_id, c.category_name, c.description,
               c.parent_category_id, c.created_at, c.updated_at,
               COUNT(p.product_id) AS product_count
        FROM dbo.categories c
        LEFT JOIN dbo.products p ON p.category_id = c.category_id
        WHERE ((@RootsOnly = 1 AND c.parent_category_id IS NULL)
            OR (@RootsOnly = 0 AND (@ParentCategoryId IS NULL OR c.parent_category_id = @ParentCategoryId)))
          AND (@Search IS NULL OR c.category_name LIKE N'%' + @Search + N'%')
        GROUP BY c.category_id, c.category_name, c.description,
                 c.parent_category_id, c.created_at, c.updated_at
        ORDER BY c.category_id
        OFFSET @Offset ROWS FETCH NEXT @PageSize ROWS ONLY;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Categories_Get
    @CategoryId INT
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;
        IF NOT EXISTS (SELECT 1 FROM dbo.categories WHERE category_id = @CategoryId)
            THROW 50001, N'Category not found', 1;
        SELECT category_id, category_name, description, parent_category_id,
               created_at, updated_at
        FROM dbo.categories WHERE category_id = @CategoryId;
        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Categories_Create
    @CategoryName     NVARCHAR(150),
    @Description      NVARCHAR(MAX) = NULL,
    @ParentCategoryId INT           = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;
        IF @ParentCategoryId IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM dbo.categories WHERE category_id = @ParentCategoryId)
            THROW 50005, N'parent_category_id does not exist', 1;
        IF EXISTS (SELECT 1 FROM dbo.categories WHERE category_name = @CategoryName)
            THROW 50002, N'category_name already exists', 1;

        INSERT INTO dbo.categories (category_name, description, parent_category_id)
        VALUES (@CategoryName, @Description, @ParentCategoryId);

        DECLARE @NewId INT = CAST(SCOPE_IDENTITY() AS INT);
        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
        EXEC dbo.sp_Categories_Get @CategoryId = @NewId;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        IF ERROR_NUMBER() IN (2601, 2627) THROW 50002, N'category_name already exists', 1;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Categories_Update
    @CategoryId       INT,
    @CategoryName     NVARCHAR(150),
    @Description      NVARCHAR(MAX) = NULL,
    @ParentCategoryId INT           = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        IF NOT EXISTS (SELECT 1 FROM dbo.categories WHERE category_id = @CategoryId)
            THROW 50001, N'Category not found', 1;
        IF @ParentCategoryId = @CategoryId
            THROW 50004, N'A category cannot be its own parent', 1;
        IF @ParentCategoryId IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM dbo.categories WHERE category_id = @ParentCategoryId)
            THROW 50005, N'parent_category_id does not exist', 1;
        IF EXISTS (SELECT 1 FROM dbo.categories WHERE category_name = @CategoryName AND category_id <> @CategoryId)
            THROW 50002, N'category_name already exists', 1;

        /* Walk down the subtree to block a cycle (A -> B -> A). */
        DECLARE @Cycle BIT = 0;
        IF @ParentCategoryId IS NOT NULL
        BEGIN
            ;WITH descendants AS (
                SELECT category_id FROM dbo.categories WHERE parent_category_id = @CategoryId
                UNION ALL
                SELECT c.category_id
                FROM dbo.categories c
                JOIN descendants d ON c.parent_category_id = d.category_id
            )
            SELECT @Cycle = 1 FROM descendants WHERE category_id = @ParentCategoryId;
        END
        IF @Cycle = 1
            THROW 50004, N'parent_category_id would create a cycle', 1;

        UPDATE dbo.categories SET
            category_name = @CategoryName,
            description = @Description,
            parent_category_id = @ParentCategoryId
        WHERE category_id = @CategoryId;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
        EXEC dbo.sp_Categories_Get @CategoryId = @CategoryId;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        IF ERROR_NUMBER() IN (2601, 2627) THROW 50002, N'category_name already exists', 1;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Categories_Delete
    @CategoryId INT
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;
        IF NOT EXISTS (SELECT 1 FROM dbo.categories WHERE category_id = @CategoryId)
            THROW 50001, N'Category not found', 1;
        IF EXISTS (SELECT 1 FROM dbo.products WHERE category_id = @CategoryId)
            THROW 50003, N'Category still has products', 1;

        UPDATE dbo.categories SET parent_category_id = NULL
        WHERE parent_category_id = @CategoryId;

        DELETE FROM dbo.categories WHERE category_id = @CategoryId;
        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


/* =========================================================================
   INVENTORY
   ========================================================================= */
CREATE OR ALTER PROCEDURE dbo.sp_Inventory_List
    @StoreId      INT  = NULL,
    @ProductId    INT  = NULL,
    @ExpiryDate   DATE = NULL,
    @ExpiryBefore DATE = NULL,
    @InStockOnly  BIT  = 0,
    @Page         INT  = 1,
    @PageSize     INT  = 20
AS
BEGIN
    SET NOCOUNT ON;
    IF @Page < 1 SET @Page = 1;
    IF @PageSize < 1 SET @PageSize = 20;
    IF @PageSize > 100 SET @PageSize = 100;
    DECLARE @Offset INT = (@Page - 1) * @PageSize;

    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        SELECT COUNT(*) AS total
        FROM dbo.inventory i
        WHERE (@StoreId IS NULL OR i.store_id = @StoreId)
          AND (@ProductId IS NULL OR i.product_id = @ProductId)
          AND (@ExpiryDate IS NULL OR i.expiry_date = @ExpiryDate)
          AND (@ExpiryBefore IS NULL OR i.expiry_date <= @ExpiryBefore)
          AND (@InStockOnly = 0 OR i.quantity > 0);

        SELECT i.inventory_id, i.store_id, i.product_id, i.expiry_date,
               i.quantity, i.received_date, i.batch_code,
               i.created_at, i.updated_at,
               DATEDIFF(DAY, CAST(SYSDATETIME() AS DATE), i.expiry_date) AS days_to_expiry,
               s.store_code, s.store_name,
               p.product_code, p.product_name
        FROM dbo.inventory i
        JOIN dbo.stores s ON s.store_id = i.store_id
        JOIN dbo.products p ON p.product_id = i.product_id
        WHERE (@StoreId IS NULL OR i.store_id = @StoreId)
          AND (@ProductId IS NULL OR i.product_id = @ProductId)
          AND (@ExpiryDate IS NULL OR i.expiry_date = @ExpiryDate)
          AND (@ExpiryBefore IS NULL OR i.expiry_date <= @ExpiryBefore)
          AND (@InStockOnly = 0 OR i.quantity > 0)
        ORDER BY i.inventory_id
        OFFSET @Offset ROWS FETCH NEXT @PageSize ROWS ONLY;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Inventory_ListExpiring
    @Days           INT = 7,
    @StoreId        INT = NULL,
    @ProductId      INT = NULL,
    @IncludeExpired BIT = 1
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @Today  DATE = CAST(SYSDATETIME() AS DATE);
    DECLARE @Cutoff DATE = DATEADD(DAY, @Days, @Today);

    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        SELECT i.inventory_id, i.store_id, i.product_id, i.expiry_date,
               DATEDIFF(DAY, @Today, i.expiry_date) AS days_left,
               i.quantity,
               p.product_code, p.product_name,
               s.store_code, s.store_name
        FROM dbo.inventory i
        JOIN dbo.products p ON p.product_id = i.product_id
        JOIN dbo.stores s ON s.store_id = i.store_id
        WHERE i.quantity > 0
          AND i.expiry_date IS NOT NULL
          AND i.expiry_date <= @Cutoff
          AND (@IncludeExpired = 1 OR i.expiry_date >= @Today)
          AND (@StoreId IS NULL OR i.store_id = @StoreId)
          AND (@ProductId IS NULL OR i.product_id = @ProductId)
        ORDER BY i.expiry_date;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Inventory_Get
    @InventoryId BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;
        IF NOT EXISTS (SELECT 1 FROM dbo.inventory WHERE inventory_id = @InventoryId)
            THROW 50001, N'Inventory batch not found', 1;

        SELECT i.inventory_id, i.store_id, i.product_id, i.expiry_date,
               i.quantity, i.received_date, i.batch_code,
               i.created_at, i.updated_at,
               DATEDIFF(DAY, CAST(SYSDATETIME() AS DATE), i.expiry_date) AS days_to_expiry,
               s.store_code, s.store_name,
               p.product_code, p.product_name
        FROM dbo.inventory i
        JOIN dbo.stores s ON s.store_id = i.store_id
        JOIN dbo.products p ON p.product_id = i.product_id
        WHERE i.inventory_id = @InventoryId;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Inventory_Create
    @StoreId      INT,
    @ProductId    INT,
    @ExpiryDate   DATE = NULL,
    @Quantity     DECIMAL(15,3) = 0,
    @ReceivedDate DATE = NULL,
    @BatchCode    NVARCHAR(50) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;
        IF NOT EXISTS (SELECT 1 FROM dbo.stores WHERE store_id = @StoreId)
            THROW 50005, N'store_id does not exist', 1;
        IF NOT EXISTS (SELECT 1 FROM dbo.products WHERE product_id = @ProductId)
            THROW 50005, N'product_id does not exist', 1;
        IF @ExpiryDate IS NOT NULL AND EXISTS (
            SELECT 1 FROM dbo.inventory
            WHERE store_id = @StoreId AND product_id = @ProductId AND expiry_date = @ExpiryDate)
            THROW 50002, N'A batch with this store/product/expiry already exists', 1;
        IF @ReceivedDate IS NULL SET @ReceivedDate = CAST(SYSDATETIME() AS DATE);

        INSERT INTO dbo.inventory (store_id, product_id, expiry_date, quantity, received_date, batch_code)
        VALUES (@StoreId, @ProductId, @ExpiryDate, @Quantity, @ReceivedDate, @BatchCode);

        DECLARE @NewId BIGINT = CAST(SCOPE_IDENTITY() AS BIGINT);
        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
        EXEC dbo.sp_Inventory_Get @InventoryId = @NewId;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        IF ERROR_NUMBER() IN (2601, 2627) THROW 50002, N'A batch with this store/product/expiry already exists', 1;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Inventory_Update
    @InventoryId  BIGINT,
    @ExpiryDate   DATE = NULL,
    @Quantity     DECIMAL(15,3),
    @ReceivedDate DATE = NULL,
    @BatchCode    NVARCHAR(50) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;
        IF NOT EXISTS (SELECT 1 FROM dbo.inventory WHERE inventory_id = @InventoryId)
            THROW 50001, N'Inventory batch not found', 1;

        DECLARE @StoreId INT, @ProductId INT;
        SELECT @StoreId = store_id, @ProductId = product_id
        FROM dbo.inventory WHERE inventory_id = @InventoryId;

        IF @ExpiryDate IS NOT NULL AND EXISTS (
            SELECT 1 FROM dbo.inventory
            WHERE store_id = @StoreId AND product_id = @ProductId
              AND expiry_date = @ExpiryDate AND inventory_id <> @InventoryId)
            THROW 50002, N'A batch with this store/product/expiry already exists', 1;
        IF @ReceivedDate IS NULL SET @ReceivedDate = CAST(SYSDATETIME() AS DATE);

        UPDATE dbo.inventory SET
            expiry_date = @ExpiryDate,
            quantity = @Quantity,
            received_date = @ReceivedDate,
            batch_code = @BatchCode
        WHERE inventory_id = @InventoryId;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
        EXEC dbo.sp_Inventory_Get @InventoryId = @InventoryId;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        IF ERROR_NUMBER() IN (2601, 2627) THROW 50002, N'A batch with this store/product/expiry already exists', 1;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Inventory_Delete
    @InventoryId BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;
        IF NOT EXISTS (SELECT 1 FROM dbo.inventory WHERE inventory_id = @InventoryId)
            THROW 50001, N'Inventory batch not found', 1;

        DELETE FROM dbo.inventory WHERE inventory_id = @InventoryId;
        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


/* =========================================================================
   ORDERS
   ========================================================================= */
CREATE OR ALTER PROCEDURE dbo.sp_Orders_List
    @StoreId   INT      = NULL,
    @OrderType VARCHAR(20) = NULL,
    @Status    VARCHAR(20) = NULL,
    @FromDate  DATETIME2 = NULL,
    @ToDate    DATETIME2 = NULL,
    @OrderId   BIGINT   = NULL,
    @Page      INT      = 1,
    @PageSize  INT      = 20
AS
BEGIN
    SET NOCOUNT ON;
    IF @Page < 1 SET @Page = 1;
    IF @PageSize < 1 SET @PageSize = 20;
    IF @PageSize > 100 SET @PageSize = 100;
    DECLARE @Offset INT = (@Page - 1) * @PageSize;

    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        SELECT COUNT(*) AS total
        FROM dbo.orders o
        WHERE (@StoreId IS NULL OR o.store_id = @StoreId)
          AND (@OrderType IS NULL OR o.order_type = @OrderType)
          AND (@Status IS NULL OR o.status = @Status)
          AND (@FromDate IS NULL OR o.order_date >= @FromDate)
          AND (@ToDate IS NULL OR o.order_date <= @ToDate)
          AND (@OrderId IS NULL OR o.order_id = @OrderId);

        ;WITH page_rows AS (
            SELECT o.*
            FROM dbo.orders o
            WHERE (@StoreId IS NULL OR o.store_id = @StoreId)
              AND (@OrderType IS NULL OR o.order_type = @OrderType)
              AND (@Status IS NULL OR o.status = @Status)
              AND (@FromDate IS NULL OR o.order_date >= @FromDate)
              AND (@ToDate IS NULL OR o.order_date <= @ToDate)
              AND (@OrderId IS NULL OR o.order_id = @OrderId)
            ORDER BY o.order_date DESC, o.order_id DESC
            OFFSET @Offset ROWS FETCH NEXT @PageSize ROWS ONLY
        )
        SELECT p.order_id, p.order_code, p.store_id, p.order_type, p.order_date,
               p.total_amount, p.total_quantity, p.status, p.payment_method,
               p.customer_name, p.user_id, p.note, p.created_at, p.updated_at,
               ISNULL(x.line_count, 0) AS line_count,
               ISNULL(x.total_items, 0) AS total_items,
               s.store_code, s.store_name
        FROM page_rows p
        JOIN dbo.stores s ON s.store_id = p.store_id
        OUTER APPLY (
            SELECT COUNT(*) AS line_count, SUM(oi.quantity) AS total_items
            FROM dbo.order_items oi WHERE oi.order_id = p.order_id
        ) x
        ORDER BY p.order_date DESC, p.order_id DESC;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Orders_Get
    @OrderId BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;
        IF NOT EXISTS (SELECT 1 FROM dbo.orders WHERE order_id = @OrderId)
            THROW 50001, N'Order not found', 1;

        SELECT o.order_id, o.order_code, o.store_id, o.order_type, o.order_date,
               o.total_amount, o.total_quantity, o.status, o.payment_method,
               o.customer_name, o.user_id, o.note, o.created_at, o.updated_at,
               ISNULL(x.line_count, 0) AS line_count,
               ISNULL(x.total_items, 0) AS total_items,
               s.store_code, s.store_name
        FROM dbo.orders o
        JOIN dbo.stores s ON s.store_id = o.store_id
        OUTER APPLY (
            SELECT COUNT(*) AS line_count, SUM(oi.quantity) AS total_items
            FROM dbo.order_items oi WHERE oi.order_id = o.order_id
        ) x
        WHERE o.order_id = @OrderId;

        SELECT oi.order_item_id, oi.order_id, oi.product_id, oi.quantity,
               oi.unit_price, oi.unit_cost, oi.discount_percent, oi.line_total,
               oi.created_at, p.product_code, p.product_name
        FROM dbo.order_items oi
        JOIN dbo.products p ON p.product_id = oi.product_id
        WHERE oi.order_id = @OrderId
        ORDER BY oi.order_item_id;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Orders_Create
    @OrderCode     NVARCHAR(50),
    @StoreId       INT,
    @OrderType     VARCHAR(20) = 'sale',
    @OrderDate     DATETIME2   = NULL,
    @Status        VARCHAR(20) = 'pending',
    @PaymentMethod VARCHAR(30) = NULL,
    @CustomerName  NVARCHAR(150) = NULL,
    @UserId        INT         = NULL,
    @Note          NVARCHAR(MAX) = NULL,
    @ItemsJson     NVARCHAR(MAX)
AS
BEGIN
    /* @ItemsJson example:
       [{"product_id":45,"quantity":2,"unit_price":15000,"unit_cost":9000,"discount_percent":0}] */
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        IF NOT EXISTS (SELECT 1 FROM dbo.stores WHERE store_id = @StoreId)
            THROW 50005, N'store_id does not exist', 1;
        IF @UserId IS NOT NULL AND NOT EXISTS (SELECT 1 FROM dbo.users WHERE user_id = @UserId)
            THROW 50005, N'user_id does not exist', 1;
        IF @OrderDate IS NULL SET @OrderDate = SYSDATETIME();
        IF EXISTS (SELECT 1 FROM dbo.orders WHERE order_code = @OrderCode)
            THROW 50002, N'order_code already exists', 1;
        IF @ItemsJson IS NULL OR NOT EXISTS (SELECT 1 FROM OPENJSON(@ItemsJson))
            THROW 50005, N'items must contain at least one line', 1;
        IF EXISTS (
            SELECT 1
            FROM OPENJSON(@ItemsJson) WITH (product_id INT '$.product_id') j
            LEFT JOIN dbo.products p ON p.product_id = j.product_id
            WHERE p.product_id IS NULL)
            THROW 50005, N'Unknown product_id in items', 1;

        INSERT INTO dbo.orders (
            order_code, store_id, order_type, order_date, total_amount,
            total_quantity, status, payment_method, customer_name, user_id, note
        )
        VALUES (
            @OrderCode, @StoreId, @OrderType, @OrderDate, 0,
            0, @Status, @PaymentMethod, @CustomerName, @UserId, @Note
        );

        DECLARE @NewId BIGINT = CAST(SCOPE_IDENTITY() AS BIGINT);

        INSERT INTO dbo.order_items (order_id, product_id, quantity, unit_price, unit_cost, discount_percent)
        SELECT @NewId, j.product_id, j.quantity, j.unit_price,
               j.unit_cost, ISNULL(j.discount_percent, 0)
        FROM OPENJSON(@ItemsJson) WITH (
            product_id       INT           '$.product_id',
            quantity         DECIMAL(15,3) '$.quantity',
            unit_price       DECIMAL(15,2) '$.unit_price',
            unit_cost        DECIMAL(15,2) '$.unit_cost',
            discount_percent DECIMAL(5,2)  '$.discount_percent'
        ) j;

        UPDATE o SET
            total_amount = ISNULL(x.total_amount, 0),
            total_quantity = ISNULL(x.total_quantity, 0)
        FROM dbo.orders o
        OUTER APPLY (
            SELECT SUM(line_total) AS total_amount, SUM(quantity) AS total_quantity
            FROM dbo.order_items WHERE order_id = o.order_id
        ) x
        WHERE o.order_id = @NewId;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;

        EXEC dbo.sp_Orders_Get @OrderId = @NewId;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        IF ERROR_NUMBER() IN (2601, 2627) THROW 50002, N'order_code already exists or a product appears twice', 1;
        IF ERROR_NUMBER() = 13609 THROW 50005, N'items is not valid JSON', 1;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Orders_Update
    @OrderId       BIGINT,
    @OrderCode     NVARCHAR(50),
    @StoreId       INT,
    @OrderType     VARCHAR(20),
    @OrderDate     DATETIME2,
    @PaymentMethod VARCHAR(30) = NULL,
    @CustomerName  NVARCHAR(150) = NULL,
    @UserId        INT = NULL,
    @Note          NVARCHAR(MAX) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        DECLARE @CurrentStatus VARCHAR(20);
        SELECT @CurrentStatus = status FROM dbo.orders WHERE order_id = @OrderId;
        IF @CurrentStatus IS NULL
            THROW 50001, N'Order not found', 1;
        IF @CurrentStatus IN ('completed', 'cancelled')
            THROW 50004, N'Only pending orders are editable', 1;
        IF NOT EXISTS (SELECT 1 FROM dbo.stores WHERE store_id = @StoreId)
            THROW 50005, N'store_id does not exist', 1;
        IF @UserId IS NOT NULL AND NOT EXISTS (SELECT 1 FROM dbo.users WHERE user_id = @UserId)
            THROW 50005, N'user_id does not exist', 1;
        IF EXISTS (SELECT 1 FROM dbo.orders WHERE order_code = @OrderCode AND order_id <> @OrderId)
            THROW 50002, N'order_code already exists', 1;

        UPDATE dbo.orders SET
            order_code = @OrderCode, store_id = @StoreId, order_type = @OrderType,
            order_date = @OrderDate, payment_method = @PaymentMethod,
            customer_name = @CustomerName, user_id = @UserId, note = @Note
        WHERE order_id = @OrderId;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
        EXEC dbo.sp_Orders_Get @OrderId = @OrderId;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        IF ERROR_NUMBER() IN (2601, 2627) THROW 50002, N'order_code already exists', 1;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Orders_UpdateStatus
    @OrderId BIGINT,
    @Status  VARCHAR(20)
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        DECLARE @CurrentStatus VARCHAR(20);
        SELECT @CurrentStatus = status FROM dbo.orders WHERE order_id = @OrderId;
        IF @CurrentStatus IS NULL
            THROW 50001, N'Order not found', 1;

        /* pending -> pending/completed/cancelled; cancelled -> cancelled/pending;
           completed -> completed only. */
        IF NOT (
            (@CurrentStatus = 'pending'   AND @Status IN ('pending', 'completed', 'cancelled')) OR
            (@CurrentStatus = 'cancelled' AND @Status IN ('cancelled', 'pending')) OR
            (@CurrentStatus = 'completed' AND @Status = 'completed')
        )
            THROW 50004, N'Status transition is not allowed', 1;

        UPDATE dbo.orders SET status = @Status WHERE order_id = @OrderId;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
        EXEC dbo.sp_Orders_Get @OrderId = @OrderId;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Orders_Delete
    @OrderId BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;
        IF NOT EXISTS (SELECT 1 FROM dbo.orders WHERE order_id = @OrderId)
            THROW 50001, N'Order not found', 1;

        DELETE FROM dbo.order_items WHERE order_id = @OrderId;
        DELETE FROM dbo.orders WHERE order_id = @OrderId;
        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Orders_RecalculateTotals
    @OrderId BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;
        IF NOT EXISTS (SELECT 1 FROM dbo.orders WHERE order_id = @OrderId)
            THROW 50001, N'Order not found', 1;

        UPDATE o SET
            total_amount = ISNULL(x.total_amount, 0),
            total_quantity = ISNULL(x.total_quantity, 0)
        FROM dbo.orders o
        OUTER APPLY (
            SELECT SUM(line_total) AS total_amount, SUM(quantity) AS total_quantity
            FROM dbo.order_items WHERE order_id = o.order_id
        ) x
        WHERE o.order_id = @OrderId;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;

        SELECT order_id, total_amount, total_quantity
        FROM dbo.orders WHERE order_id = @OrderId;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


/* =========================================================================
   ORDER ITEMS
   ========================================================================= */
CREATE OR ALTER PROCEDURE dbo.sp_OrderItems_List
    @OrderId       BIGINT = NULL,
    @ProductId     INT = NULL,
    @StoreId       INT = NULL,
    @MinLineTotal  DECIMAL(18,2) = NULL,
    @MaxLineTotal  DECIMAL(18,2) = NULL,
    @Page          INT = 1,
    @PageSize      INT = 20
AS
BEGIN
    SET NOCOUNT ON;
    IF @Page < 1 SET @Page = 1;
    IF @PageSize < 1 SET @PageSize = 20;
    IF @PageSize > 100 SET @PageSize = 100;
    DECLARE @Offset INT = (@Page - 1) * @PageSize;

    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        SELECT COUNT(*) AS total
        FROM dbo.order_items oi
        JOIN dbo.orders o ON o.order_id = oi.order_id
        WHERE (@OrderId IS NULL OR oi.order_id = @OrderId)
          AND (@ProductId IS NULL OR oi.product_id = @ProductId)
          AND (@StoreId IS NULL OR o.store_id = @StoreId)
          AND (@MinLineTotal IS NULL OR oi.line_total >= @MinLineTotal)
          AND (@MaxLineTotal IS NULL OR oi.line_total <= @MaxLineTotal);

        SELECT oi.order_item_id, oi.order_id, oi.product_id, oi.quantity,
               oi.unit_price, oi.unit_cost, oi.discount_percent, oi.line_total,
               oi.created_at, p.product_code, p.product_name
        FROM dbo.order_items oi
        JOIN dbo.orders o ON o.order_id = oi.order_id
        JOIN dbo.products p ON p.product_id = oi.product_id
        WHERE (@OrderId IS NULL OR oi.order_id = @OrderId)
          AND (@ProductId IS NULL OR oi.product_id = @ProductId)
          AND (@StoreId IS NULL OR o.store_id = @StoreId)
          AND (@MinLineTotal IS NULL OR oi.line_total >= @MinLineTotal)
          AND (@MaxLineTotal IS NULL OR oi.line_total <= @MaxLineTotal)
        ORDER BY oi.order_id DESC, oi.order_item_id
        OFFSET @Offset ROWS FETCH NEXT @PageSize ROWS ONLY;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_OrderItems_Get
    @OrderItemId BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;
        IF NOT EXISTS (SELECT 1 FROM dbo.order_items WHERE order_item_id = @OrderItemId)
            THROW 50001, N'Order line not found', 1;

        SELECT oi.order_item_id, oi.order_id, oi.product_id, oi.quantity,
               oi.unit_price, oi.unit_cost, oi.discount_percent, oi.line_total,
               oi.created_at, p.product_code, p.product_name
        FROM dbo.order_items oi
        JOIN dbo.products p ON p.product_id = oi.product_id
        WHERE oi.order_item_id = @OrderItemId;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_OrderItems_Create
    @OrderId         BIGINT,
    @ProductId       INT,
    @Quantity        DECIMAL(15,3),
    @UnitPrice       DECIMAL(15,2),
    @UnitCost        DECIMAL(15,2) = NULL,
    @DiscountPercent DECIMAL(5,2) = 0
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        IF NOT EXISTS (SELECT 1 FROM dbo.orders WHERE order_id = @OrderId)
            THROW 50005, N'order_id does not exist', 1;
        IF NOT EXISTS (SELECT 1 FROM dbo.products WHERE product_id = @ProductId)
            THROW 50005, N'product_id does not exist', 1;

        DECLARE @Status VARCHAR(20);
        SELECT @Status = status FROM dbo.orders WHERE order_id = @OrderId;
        IF @Status IN ('completed', 'cancelled')
            THROW 50004, N'Only pending orders can be edited', 1;
        IF EXISTS (SELECT 1 FROM dbo.order_items
                   WHERE order_id = @OrderId AND product_id = @ProductId)
            THROW 50002, N'This product already exists in the order', 1;

        INSERT INTO dbo.order_items (order_id, product_id, quantity, unit_price, unit_cost, discount_percent)
        VALUES (@OrderId, @ProductId, @Quantity, @UnitPrice, @UnitCost, @DiscountPercent);

        DECLARE @NewId BIGINT = CAST(SCOPE_IDENTITY() AS BIGINT);

        /* Keep the denormalised counters on the parent in step. */
        UPDATE o SET
            total_amount = ISNULL(x.total_amount, 0),
            total_quantity = ISNULL(x.total_quantity, 0)
        FROM dbo.orders o
        OUTER APPLY (
            SELECT SUM(line_total) AS total_amount, SUM(quantity) AS total_quantity
            FROM dbo.order_items WHERE order_id = o.order_id
        ) x
        WHERE o.order_id = @OrderId;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
        EXEC dbo.sp_OrderItems_Get @OrderItemId = @NewId;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        IF ERROR_NUMBER() IN (2601, 2627) THROW 50002, N'This product already exists in the order', 1;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_OrderItems_Update
    @OrderItemId     BIGINT,
    @ProductId       INT,
    @Quantity        DECIMAL(15,3),
    @UnitPrice       DECIMAL(15,2),
    @UnitCost        DECIMAL(15,2) = NULL,
    @DiscountPercent DECIMAL(5,2) = 0
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        DECLARE @OrderId BIGINT, @Status VARCHAR(20);
        SELECT @OrderId = oi.order_id, @Status = o.status
        FROM dbo.order_items oi
        JOIN dbo.orders o ON o.order_id = oi.order_id
        WHERE oi.order_item_id = @OrderItemId;
        IF @OrderId IS NULL
            THROW 50001, N'Order line not found', 1;
        IF @Status IN ('completed', 'cancelled')
            THROW 50004, N'Only pending orders can be edited', 1;
        IF NOT EXISTS (SELECT 1 FROM dbo.products WHERE product_id = @ProductId)
            THROW 50005, N'product_id does not exist', 1;
        IF EXISTS (SELECT 1 FROM dbo.order_items
                   WHERE order_id = @OrderId AND product_id = @ProductId
                     AND order_item_id <> @OrderItemId)
            THROW 50002, N'This product already exists in the order', 1;

        UPDATE dbo.order_items SET
            product_id = @ProductId, quantity = @Quantity,
            unit_price = @UnitPrice, unit_cost = @UnitCost,
            discount_percent = @DiscountPercent
        WHERE order_item_id = @OrderItemId;

        UPDATE o SET
            total_amount = ISNULL(x.total_amount, 0),
            total_quantity = ISNULL(x.total_quantity, 0)
        FROM dbo.orders o
        OUTER APPLY (
            SELECT SUM(line_total) AS total_amount, SUM(quantity) AS total_quantity
            FROM dbo.order_items WHERE order_id = o.order_id
        ) x
        WHERE o.order_id = @OrderId;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
        EXEC dbo.sp_OrderItems_Get @OrderItemId = @OrderItemId;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        IF ERROR_NUMBER() IN (2601, 2627) THROW 50002, N'This product already exists in the order', 1;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_OrderItems_Delete
    @OrderItemId BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        DECLARE @OrderId BIGINT, @Status VARCHAR(20);
        SELECT @OrderId = oi.order_id, @Status = o.status
        FROM dbo.order_items oi
        JOIN dbo.orders o ON o.order_id = oi.order_id
        WHERE oi.order_item_id = @OrderItemId;
        IF @OrderId IS NULL
            THROW 50001, N'Order line not found', 1;
        IF @Status IN ('completed', 'cancelled')
            THROW 50004, N'Only pending orders can be edited', 1;

        DELETE FROM dbo.order_items WHERE order_item_id = @OrderItemId;

        UPDATE o SET
            total_amount = ISNULL(x.total_amount, 0),
            total_quantity = ISNULL(x.total_quantity, 0)
        FROM dbo.orders o
        OUTER APPLY (
            SELECT SUM(line_total) AS total_amount, SUM(quantity) AS total_quantity
            FROM dbo.order_items WHERE order_id = o.order_id
        ) x
        WHERE o.order_id = @OrderId;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


/* =========================================================================
   FORECASTS (read-only through the API, except delete)
   ========================================================================= */
CREATE OR ALTER PROCEDURE dbo.sp_Forecasts_List
    @StoreId      INT  = NULL,
    @ProductId    INT  = NULL,
    @ForecastDate DATE = NULL,
    @ForecastFrom DATE = NULL,
    @ForecastTo   DATE = NULL,
    @ModelName    VARCHAR(50) = NULL,
    @Page         INT = 1,
    @PageSize     INT = 20
AS
BEGIN
    SET NOCOUNT ON;
    IF @Page < 1 SET @Page = 1;
    IF @PageSize < 1 SET @PageSize = 20;
    IF @PageSize > 100 SET @PageSize = 100;
    DECLARE @Offset INT = (@Page - 1) * @PageSize;

    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        SELECT COUNT(*) AS total
        FROM dbo.forecasts f
        WHERE (@StoreId IS NULL OR f.store_id = @StoreId)
          AND (@ProductId IS NULL OR f.product_id = @ProductId)
          AND (@ForecastDate IS NULL OR f.forecast_date = @ForecastDate)
          AND (@ForecastFrom IS NULL OR f.forecast_date >= @ForecastFrom)
          AND (@ForecastTo IS NULL OR f.forecast_date <= @ForecastTo)
          AND (@ModelName IS NULL OR f.model_name = @ModelName);

        SELECT f.forecast_id, f.store_id, f.product_id, f.model_name,
               f.forecast_date, f.horizon_days, f.predicted_quantity,
               f.lower_bound, f.upper_bound, f.recommended_import_qty,
               f.rmse, f.mae, f.mape, f.trained_at, f.created_at,
               s.store_code, s.store_name,
               p.product_code, p.product_name
        FROM dbo.forecasts f
        JOIN dbo.stores s ON s.store_id = f.store_id
        JOIN dbo.products p ON p.product_id = f.product_id
        WHERE (@StoreId IS NULL OR f.store_id = @StoreId)
          AND (@ProductId IS NULL OR f.product_id = @ProductId)
          AND (@ForecastDate IS NULL OR f.forecast_date = @ForecastDate)
          AND (@ForecastFrom IS NULL OR f.forecast_date >= @ForecastFrom)
          AND (@ForecastTo IS NULL OR f.forecast_date <= @ForecastTo)
          AND (@ModelName IS NULL OR f.model_name = @ModelName)
        ORDER BY f.store_id, f.product_id, f.horizon_days
        OFFSET @Offset ROWS FETCH NEXT @PageSize ROWS ONLY;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Forecasts_Get
    @ForecastId BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;
        IF NOT EXISTS (SELECT 1 FROM dbo.forecasts WHERE forecast_id = @ForecastId)
            THROW 50001, N'Forecast not found', 1;

        SELECT f.forecast_id, f.store_id, f.product_id, f.model_name,
               f.forecast_date, f.horizon_days, f.predicted_quantity,
               f.lower_bound, f.upper_bound, f.recommended_import_qty,
               f.rmse, f.mae, f.mape, f.trained_at, f.created_at,
               s.store_code, s.store_name,
               p.product_code, p.product_name
        FROM dbo.forecasts f
        JOIN dbo.stores s ON s.store_id = f.store_id
        JOIN dbo.products p ON p.product_id = f.product_id
        WHERE f.forecast_id = @ForecastId;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Forecasts_Latest
    @StoreId   INT = NULL,
    @ProductId INT = NULL,
    @Page      INT = 1,
    @PageSize  INT = 20
AS
BEGIN
    SET NOCOUNT ON;
    IF @Page < 1 SET @Page = 1;
    IF @PageSize < 1 SET @PageSize = 20;
    IF @PageSize > 100 SET @PageSize = 100;
    DECLARE @Offset INT = (@Page - 1) * @PageSize;

    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        DECLARE @NewestDate DATE;
        SELECT @NewestDate = MAX(f.forecast_date)
        FROM dbo.forecasts f
        WHERE (@StoreId IS NULL OR f.store_id = @StoreId)
          AND (@ProductId IS NULL OR f.product_id = @ProductId);

        ;WITH ranked AS (
            SELECT f.*,
                   ROW_NUMBER() OVER (
                       PARTITION BY f.store_id, f.product_id
                       ORDER BY CASE WHEN f.rmse IS NULL THEN 1 ELSE 0 END, f.rmse, f.forecast_id
                   ) AS rn
            FROM dbo.forecasts f
            WHERE f.forecast_date = @NewestDate
              AND (@StoreId IS NULL OR f.store_id = @StoreId)
              AND (@ProductId IS NULL OR f.product_id = @ProductId)
        )
        SELECT COUNT(*) AS total FROM ranked WHERE rn = 1;

        ;WITH ranked AS (
            SELECT f.*,
                   ROW_NUMBER() OVER (
                       PARTITION BY f.store_id, f.product_id
                       ORDER BY CASE WHEN f.rmse IS NULL THEN 1 ELSE 0 END, f.rmse, f.forecast_id
                   ) AS rn
            FROM dbo.forecasts f
            WHERE f.forecast_date = @NewestDate
              AND (@StoreId IS NULL OR f.store_id = @StoreId)
              AND (@ProductId IS NULL OR f.product_id = @ProductId)
        )
        SELECT r.store_id, r.product_id, r.model_name, r.forecast_date,
               r.predicted_quantity, r.lower_bound, r.upper_bound,
               r.recommended_import_qty,
               s.store_code, s.store_name,
               p.product_code, p.product_name
        FROM ranked r
        JOIN dbo.stores s ON s.store_id = r.store_id
        JOIN dbo.products p ON p.product_id = r.product_id
        WHERE r.rn = 1
        ORDER BY r.store_id, r.product_id
        OFFSET @Offset ROWS FETCH NEXT @PageSize ROWS ONLY;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Forecasts_Delete
    @ForecastId BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;
        IF NOT EXISTS (SELECT 1 FROM dbo.forecasts WHERE forecast_id = @ForecastId)
            THROW 50001, N'Forecast not found', 1;
        DELETE FROM dbo.forecasts WHERE forecast_id = @ForecastId;
        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Forecasts_DeleteByFilter
    @StoreId   INT = NULL,
    @ProductId INT = NULL,
    @ModelName VARCHAR(50) = NULL,
    @FromDate  DATE = NULL,
    @ToDate    DATE = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        DELETE FROM dbo.forecasts
        WHERE (@StoreId IS NULL OR store_id = @StoreId)
          AND (@ProductId IS NULL OR product_id = @ProductId)
          AND (@ModelName IS NULL OR model_name = @ModelName)
          AND (@FromDate IS NULL OR forecast_date >= @FromDate)
          AND (@ToDate IS NULL OR forecast_date <= @ToDate);

        DECLARE @Deleted INT = @@ROWCOUNT;
        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
        SELECT @Deleted AS deleted;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


/* =========================================================================
   ALERTS
   ========================================================================= */
CREATE OR ALTER PROCEDURE dbo.sp_Alerts_List
    @StoreId    INT = NULL,
    @ProductId  INT = NULL,
    @AlertType  VARCHAR(30) = NULL,
    @Severity   VARCHAR(10) = NULL,
    @IsRead     BIT = NULL,
    @IsResolved BIT = NULL,
    @Page       INT = 1,
    @PageSize   INT = 20
AS
BEGIN
    SET NOCOUNT ON;
    IF @Page < 1 SET @Page = 1;
    IF @PageSize < 1 SET @PageSize = 20;
    IF @PageSize > 100 SET @PageSize = 100;
    DECLARE @Offset INT = (@Page - 1) * @PageSize;

    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        SELECT COUNT(*) AS total
        FROM dbo.alerts a
        WHERE (@StoreId IS NULL OR a.store_id = @StoreId)
          AND (@ProductId IS NULL OR a.product_id = @ProductId)
          AND (@AlertType IS NULL OR a.alert_type = @AlertType)
          AND (@Severity IS NULL OR a.severity = @Severity)
          AND (@IsRead IS NULL OR a.is_read = @IsRead)
          AND (@IsResolved IS NULL OR a.is_resolved = @IsResolved);

        SELECT a.alert_id, a.store_id, a.product_id, a.alert_type, a.severity,
               a.title, a.message, a.expiry_date, a.current_stock,
               a.threshold_value, a.is_read, a.is_resolved, a.created_at,
               a.resolved_at,
               s.store_code, s.store_name,
               p.product_code, p.product_name
        FROM dbo.alerts a
        LEFT JOIN dbo.stores s ON s.store_id = a.store_id
        LEFT JOIN dbo.products p ON p.product_id = a.product_id
        WHERE (@StoreId IS NULL OR a.store_id = @StoreId)
          AND (@ProductId IS NULL OR a.product_id = @ProductId)
          AND (@AlertType IS NULL OR a.alert_type = @AlertType)
          AND (@Severity IS NULL OR a.severity = @Severity)
          AND (@IsRead IS NULL OR a.is_read = @IsRead)
          AND (@IsResolved IS NULL OR a.is_resolved = @IsResolved)
        ORDER BY a.created_at DESC, a.alert_id
        OFFSET @Offset ROWS FETCH NEXT @PageSize ROWS ONLY;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Alerts_Get
    @AlertId BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;
        IF NOT EXISTS (SELECT 1 FROM dbo.alerts WHERE alert_id = @AlertId)
            THROW 50001, N'Alert not found', 1;

        SELECT a.alert_id, a.store_id, a.product_id, a.alert_type, a.severity,
               a.title, a.message, a.expiry_date, a.current_stock,
               a.threshold_value, a.is_read, a.is_resolved, a.created_at,
               a.resolved_at,
               s.store_code, s.store_name,
               p.product_code, p.product_name
        FROM dbo.alerts a
        LEFT JOIN dbo.stores s ON s.store_id = a.store_id
        LEFT JOIN dbo.products p ON p.product_id = a.product_id
        WHERE a.alert_id = @AlertId;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Alerts_UnreadCount
    @StoreId  INT = NULL,
    @Severity VARCHAR(10) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        SELECT COUNT(*) AS total
        FROM dbo.alerts
        WHERE is_read = 0
          AND (@StoreId IS NULL OR store_id = @StoreId)
          AND (@Severity IS NULL OR severity = @Severity);

        SELECT severity, COUNT(*) AS total
        FROM dbo.alerts
        WHERE is_read = 0
          AND (@StoreId IS NULL OR store_id = @StoreId)
          AND (@Severity IS NULL OR severity = @Severity)
        GROUP BY severity;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Alerts_MarkRead
    @AlertId BIGINT,
    @IsRead  BIT = 1
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;
        IF NOT EXISTS (SELECT 1 FROM dbo.alerts WHERE alert_id = @AlertId)
            THROW 50001, N'Alert not found', 1;

        UPDATE dbo.alerts SET is_read = @IsRead WHERE alert_id = @AlertId;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
        EXEC dbo.sp_Alerts_Get @AlertId = @AlertId;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Alerts_MarkAllRead
    @StoreId   INT = NULL,
    @AlertType VARCHAR(30) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        UPDATE dbo.alerts SET is_read = 1
        WHERE is_read = 0
          AND (@StoreId IS NULL OR store_id = @StoreId)
          AND (@AlertType IS NULL OR alert_type = @AlertType);

        DECLARE @Updated INT = @@ROWCOUNT;
        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
        SELECT @Updated AS updated;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Alerts_Resolve
    @AlertId    BIGINT,
    @IsResolved BIT = 1,
    @Note       NVARCHAR(MAX) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;
        IF NOT EXISTS (SELECT 1 FROM dbo.alerts WHERE alert_id = @AlertId)
            THROW 50001, N'Alert not found', 1;

        /* resolved_at and is_resolved must move together (CHECK constraint). */
        UPDATE dbo.alerts SET
            is_resolved = @IsResolved,
            resolved_at = CASE WHEN @IsResolved = 1 THEN SYSDATETIME() ELSE NULL END,
            message = CASE WHEN @Note IS NULL THEN message ELSE @Note END
        WHERE alert_id = @AlertId;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
        EXEC dbo.sp_Alerts_Get @AlertId = @AlertId;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Alerts_Delete
    @AlertId BIGINT
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;
        IF NOT EXISTS (SELECT 1 FROM dbo.alerts WHERE alert_id = @AlertId)
            THROW 50001, N'Alert not found', 1;
        DELETE FROM dbo.alerts WHERE alert_id = @AlertId;
        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


/* =========================================================================
   USERS / AUTH
   ========================================================================= */
CREATE OR ALTER PROCEDURE dbo.sp_Users_GetByUsername
    @Username NVARCHAR(50)
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        SELECT user_id, username, email, password_hash, full_name, role,
               store_id, is_active, created_at, updated_at
        FROM dbo.users
        WHERE username = @Username;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Users_GetById
    @UserId INT
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;
        IF NOT EXISTS (SELECT 1 FROM dbo.users WHERE user_id = @UserId)
            THROW 50001, N'User not found', 1;

        SELECT user_id, username, email, full_name, role, store_id,
               is_active, created_at
        FROM dbo.users WHERE user_id = @UserId;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dbo.sp_Users_ChangePassword
    @UserId          INT,
    @NewPasswordHash NVARCHAR(255)
AS
BEGIN
    SET NOCOUNT ON;
    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;
        IF NOT EXISTS (SELECT 1 FROM dbo.users WHERE user_id = @UserId)
            THROW 50001, N'User not found', 1;

        UPDATE dbo.users SET password_hash = @NewPasswordHash WHERE user_id = @UserId;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


/* =========================================================================
   BUSINESS PROCEDURE - generate alerts (expired / expiring / low / over)
   ========================================================================= */
CREATE OR ALTER PROCEDURE dbo.sp_Alerts_Generate
    @WarningDays INT = 3
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @Today    DATE = CAST(SYSDATETIME() AS DATE);
    DECLARE @Deadline DATE = DATEADD(DAY, @WarningDays, @Today);
    DECLARE @ExpiryCreated INT = 0, @LowStock INT = 0, @OverStock INT = 0;

    BEGIN TRY
        IF @@TRANCOUNT = 0 BEGIN TRANSACTION;

        /* 1 + 2. Expired and expiring-soon batches. */
        INSERT INTO dbo.alerts (
            store_id, product_id, alert_type, severity, title, message,
            expiry_date, current_stock
        )
        SELECT
            i.store_id,
            i.product_id,
            CASE WHEN i.expiry_date < @Today THEN 'expired' ELSE 'expiring_soon' END,
            CASE
                WHEN i.expiry_date < @Today THEN 'critical'
                WHEN i.expiry_date <= DATEADD(DAY, 1, @Today) THEN 'high'
                WHEN i.expiry_date <= @Deadline THEN 'medium'
                ELSE 'low'
            END,
            CASE WHEN i.expiry_date < @Today
                 THEN N'alert.title.EXPIRED'
                 ELSE N'alert.title.EXPIRING_SOON' END,
            NULL,
            i.expiry_date,
            i.quantity
        FROM dbo.inventory i
        WHERE i.quantity > 0
          AND i.expiry_date IS NOT NULL
          AND i.expiry_date <= @Deadline
          AND NOT EXISTS (
              SELECT 1 FROM dbo.alerts a
              WHERE a.product_id = i.product_id
                AND a.store_id = i.store_id
                AND a.expiry_date = i.expiry_date
                AND a.alert_type IN ('expiring_soon', 'expired')
                AND a.is_resolved = 0
          );
        SET @ExpiryCreated = @@ROWCOUNT;

        /* 3. Low stock. */
        INSERT INTO dbo.alerts (
            store_id, product_id, alert_type, severity, title, message,
            current_stock, threshold_value
        )
        SELECT
            i.store_id, i.product_id, 'low_stock', 'high',
            N'alert.title.LOW_STOCK', NULL,
            SUM(i.quantity), p.min_stock
        FROM dbo.inventory i
        JOIN dbo.products p ON p.product_id = i.product_id
        GROUP BY i.store_id, i.product_id, p.min_stock
        HAVING SUM(i.quantity) < p.min_stock
           AND NOT EXISTS (
               SELECT 1 FROM dbo.alerts a
               WHERE a.product_id = i.product_id
                 AND a.store_id = i.store_id
                 AND a.alert_type = 'low_stock'
                 AND a.is_resolved = 0
           );
        SET @LowStock = @@ROWCOUNT;

        /* 4. Overstock. */
        INSERT INTO dbo.alerts (
            store_id, product_id, alert_type, severity, title, message,
            current_stock, threshold_value
        )
        SELECT
            i.store_id, i.product_id, 'over_stock', 'medium',
            N'alert.title.OVER_STOCK', NULL,
            SUM(i.quantity), p.max_stock
        FROM dbo.inventory i
        JOIN dbo.products p ON p.product_id = i.product_id
        WHERE p.max_stock IS NOT NULL
        GROUP BY i.store_id, i.product_id, p.max_stock
        HAVING SUM(i.quantity) > p.max_stock
           AND NOT EXISTS (
               SELECT 1 FROM dbo.alerts a
               WHERE a.product_id = i.product_id
                 AND a.store_id = i.store_id
                 AND a.alert_type = 'over_stock'
                 AND a.is_resolved = 0
           );
        SET @OverStock = @@ROWCOUNT;

        IF @@TRANCOUNT > 0 COMMIT TRANSACTION;

        SELECT @ExpiryCreated AS expiry_created,
               @LowStock AS low_stock_created,
               @OverStock AS over_stock_created,
               @ExpiryCreated + @LowStock + @OverStock AS total_created;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


/* =========================================================================
   VERIFY
   ========================================================================= */
SELECT COUNT(*) AS procedures_created
FROM sys.procedures WHERE schema_id = SCHEMA_ID('dbo');
GO
```

**Kết quả mong đợi:** cuối Phần B in ra

```
procedures_created
------------------
                49
```

### Danh sách procedure

| Nhóm | Procedure |
|------|-----------|
| Products (5) | `sp_Products_List` · `Get` · `Create` · `Update` · `Delete` |
| Stores (5) | `sp_Stores_List` · `Get` · `Create` · `Update` · `Delete` |
| Categories (5) | `sp_Categories_List` · `Get` · `Create` · `Update` · `Delete` |
| Inventory (6) | `sp_Inventory_List` · `ListExpiring` · `Get` · `Create` · `Update` · `Delete` |
| Orders (6) | `sp_Orders_List` · `Get` · `Create` · `Update` · `UpdateStatus` · `Delete` |
| Order items (5) | `sp_OrderItems_List` · `Get` · `Create` · `Update` · `Delete` |
| Forecasts (5) | `sp_Forecasts_List` · `Get` · `Latest` · `Delete` · `DeleteByFilter` |
| Alerts (7) | `sp_Alerts_List` · `Get` · `UnreadCount` · `MarkRead` · `MarkAllRead` · `Resolve` · `Delete` |
| Users (3) | `sp_Users_GetByUsername` · `GetById` · `ChangePassword` |
| Nghiệp vụ (2) | `sp_Alerts_Generate` · `sp_Orders_RecalculateTotals` |

---

## 4. Kiểm tra sau khi chạy

Chạy đoạn này để xác nhận đủ object:

```sql
USE spoilage_predictor;
GO

SELECT 'tables' AS object_type, COUNT(*) AS total
FROM sys.tables WHERE schema_id = SCHEMA_ID('dbo')
UNION ALL
SELECT 'views', COUNT(*) FROM sys.views WHERE schema_id = SCHEMA_ID('dbo')
UNION ALL
SELECT 'procedures', COUNT(*) FROM sys.procedures WHERE schema_id = SCHEMA_ID('dbo')
UNION ALL
SELECT 'triggers', COUNT(*) FROM sys.triggers WHERE parent_class = 1;

SELECT name FROM sys.procedures WHERE schema_id = SCHEMA_ID('dbo') ORDER BY name;
```

**Kết quả đúng:** `tables = 10`, `views = 4`, `procedures = 49`, `triggers = 6`.

---

## 5. Test nhanh (tuỳ chọn nhưng nên chạy)

Đoạn này tạo một cửa hàng + nhóm hàng + sản phẩm + lô tồn kho + đơn hàng,
gọi thử các procedure, rồi **dọn sạch dữ liệu test**.

> Chỉ chạy trên database đang trống. Nếu đã có dữ liệu thật, bỏ qua mục này.

```sql
USE spoilage_predictor;
GO
SET NOCOUNT ON;
GO

/* ------------------------------------------------------------------
   1. Tao du lieu mau
   ------------------------------------------------------------------ */
EXEC dbo.sp_Stores_Create @StoreCode=N'TEST-ST', @StoreName=N'Cua hang test';
EXEC dbo.sp_Categories_Create @CategoryName=N'TEST-CAT';

DECLARE @StoreId   INT = (SELECT store_id    FROM dbo.stores     WHERE store_code   = N'TEST-ST');
DECLARE @CategoryId INT = (SELECT category_id FROM dbo.categories WHERE category_name = N'TEST-CAT');

EXEC dbo.sp_Products_Create
    @ProductCode   = N'TEST-SP',
    @ProductName   = N'San pham test',
    @CategoryId    = @CategoryId,
    @Unit          = N'hop',
    @UnitCost      = 10000,
    @SellingPrice  = 15000,
    @ShelfLifeDays = 30,
    @MinStock      = 5,
    @MaxStock      = 100;

DECLARE @ProductId INT = (SELECT product_id FROM dbo.products WHERE product_code = N'TEST-SP');

/* T-SQL KHONG cho phep goi ham truc tiep trong danh sach tham so EXEC,
   phai gan vao bien truoc. */
DECLARE @ExpiryDate DATE = DATEADD(DAY, 2, CAST(SYSDATETIME() AS DATE));

EXEC dbo.sp_Inventory_Create
    @StoreId   = @StoreId,
    @ProductId = @ProductId,
    @ExpiryDate = @ExpiryDate,
    @Quantity  = 20,
    @BatchCode = N'TEST-LOT';

/* Tao don hang bang JSON (khong can insert tung dong) */
DECLARE @Items NVARCHAR(MAX) = (
    SELECT @ProductId AS product_id, 2 AS quantity,
           15000 AS unit_price, 10000 AS unit_cost, 0 AS discount_percent
    FOR JSON PATH
);
EXEC dbo.sp_Orders_Create
    @OrderCode = N'TEST-ORD-1',
    @StoreId   = @StoreId,
    @Status    = 'pending',
    @ItemsJson = @Items;

/* ------------------------------------------------------------------
   2. Doc lai bang Stored Procedure
   ------------------------------------------------------------------ */
EXEC dbo.sp_Orders_List    @Page=1, @PageSize=5;
EXEC dbo.sp_Inventory_List @Page=1, @PageSize=5;
EXEC dbo.sp_Alerts_Generate @WarningDays=7;
EXEC dbo.sp_Alerts_List    @Page=1, @PageSize=5;
GO

/* ------------------------------------------------------------------
   3. Don du lieu test (chay sau khi da xem ket qua)
   ------------------------------------------------------------------ */
USE spoilage_predictor;
GO
SET NOCOUNT ON;
GO
DECLARE @StoreId   INT = (SELECT store_id    FROM dbo.stores   WHERE store_code   = N'TEST-ST');
DECLARE @ProductId INT = (SELECT product_id  FROM dbo.products WHERE product_code = N'TEST-SP');

DELETE oi
FROM dbo.order_items oi
JOIN dbo.orders o ON o.order_id = oi.order_id
WHERE o.order_code LIKE N'TEST-%';

DELETE FROM dbo.orders WHERE order_code LIKE N'TEST-%';
DELETE FROM dbo.inventory WHERE store_id = @StoreId;
DELETE FROM dbo.alerts WHERE store_id = @StoreId OR product_id = @ProductId;
DELETE FROM dbo.forecasts WHERE product_id = @ProductId;
DELETE FROM dbo.inventory_transactions WHERE product_id = @ProductId;
DELETE FROM dbo.products WHERE product_id = @ProductId;
DELETE FROM dbo.categories WHERE category_name = N'TEST-CAT';
DELETE FROM dbo.stores WHERE store_id = @StoreId;

SELECT N'Da don du lieu test' AS result;
GO
```

Sau khi chạy, bạn sẽ thấy:

- `sp_Orders_List` trả 1 đơn `TEST-ORD-1` với `line_count = 1`, `total_items = 2`,
  `total_amount = 30000`.
- `sp_Inventory_List` trả lô `TEST-LOT` với `days_to_expiry = 2`.
- `sp_Alerts_Generate` trả `expiry_created = 1` (cảnh báo `expiring_soon` mức `medium`).
- Cuối cùng in `Da don du lieu test`.

---

## 6. Mã lỗi nghiệp vụ của Stored Procedure

Các procedure dùng `THROW` với mã riêng. Khi làm Bước 3, backend sẽ map sang HTTP:

| Mã | Ý nghĩa | HTTP |
|----|---------|------|
| 50001 | Không tìm thấy bản ghi | 404 |
| 50002 | Trùng khoá (mã sản phẩm, mã đơn, ...) | 409 |
| 50003 | Còn dữ liệu con, không xoá được | 409 |
| 50004 | Trạng thái không cho phép (vd sửa đơn `completed`) | 409 |
| 50005 | Dữ liệu đầu vào không hợp lệ | 422 |

Ví dụ khi gọi từ Python (Bước 3, **không** chạy bây giờ):

```python
# Pseudo-code, se viet that o Buoc 3
cursor.execute("EXEC dbo.sp_Products_Create ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?", (...))
```

`pyodbc` dùng dấu `?` cho tham số. **Không gửi `GO`** qua pyodbc.

---

## 7. Lỗi thường gặp và cách xử lý

| Lỗi | Nguyên nhân | Cách xử lý |
|-----|-------------|-----------|
| `Msg 1934 ... QUOTED_IDENTIFIER` | sqlcmd/SSMS tắt `QUOTED_IDENTIFIER` khi tạo filtered index / computed column | File đã có `SET QUOTED_IDENTIFIER ON` ở đầu; nếu tự viết lại, giữ nguyên dòng đó |
| `Msg 1785 ... cycles or multiple cascade paths` | Cascade trên khoá tự tham chiếu `categories` | Đã xử lý bằng `NO ACTION` + procedure set NULL cho con |
| `Cannot drop database ... because it is currently in use` | Còn session đang mở | Đóng query window khác, hoặc chạy `ALTER DATABASE ... SET SINGLE_USER WITH ROLLBACK IMMEDIATE;` |
| `Msg 2714 ... already an object named ...` | Object cũ chưa bị drop | Chạy lại Phần A (đã có `DROP IF EXISTS`), hoặc kiểm tra đang đúng database |
| `Msg 208 Invalid object name` | Chưa `USE spoilage_predictor` | Thêm `USE spoilage_predictor; GO` ở đầu |
| `Msg 547 ... REFERENCE constraint` | Xoá bản ghi còn dữ liệu con | Dùng đúng procedure (`sp_Products_Delete`...) hoặc xoá dữ liệu con trước |
| `Msg 2627 / 2601` | Trùng UNIQUE | Procedure đã bắt và đổi thành lỗi 50002 |

---

## 8. Việc tiếp theo (Bước 3 — chưa làm)

Sau khi bạn xác nhận file này chạy **không lỗi**, tôi sẽ:

1. Sửa `backend/app/config.py` và `backend/app/database.py` sang **pyodbc**.
2. Chuyển 10 router từ ORM sang `EXEC dbo.sp_...`.
3. Map mã lỗi 50001–50005 sang HTTP.
4. **Nạp lại dữ liệu** từ `datasets/raw/train.csv` + seed (khoảng 912.999 dòng
   `order_items`, 3.000 `forecasts`). Dữ liệu PostgreSQL **không tự chuyển sang**.
5. Bổ sung procedure cho dashboard / báo cáo / đề xuất nhập hàng.
6. Sau đó mới làm **Frontend React**: phân quyền Admin/User, Dark Mode, Responsive.

---

## 9. Tóm tắt những gì đã được test trước khi bàn giao

- Chạy trên database tạm `spoilage_tsql_test` (đã drop sau khi test).
- Tạo thành công **10 bảng · 27 index · 6 trigger · 4 view · 49 procedure**.
- Smoke test qua toàn bộ luồng: cửa hàng → nhóm hàng → sản phẩm → tồn kho →
  đơn hàng → dòng hàng → đổi trạng thái → cảnh báo → đọc 4 view.
- Các ràng buộc chặn đúng: vòng lặp nhóm hàng, trùng mã sản phẩm, trùng dòng hàng,
  `completed → pending`, xoá đơn còn dòng, xoá sản phẩm/cửa hàng còn lịch sử.
- Tổng tiền/số lượng đơn được tính lại đúng sau mỗi lần thêm/sửa/xoá dòng hàng.
