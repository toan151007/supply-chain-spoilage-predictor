-- =============================================================================
--  DỰ ÁN: NỀN TẢNG QUẢN TRỊ CHUỖI CUNG ỨNG CHỐNG LÃNG PHÍ
--  (Supply Chain Spoilage Predictor)
--
--  TÁC VỤ : Tạo lược đồ cơ sở dữ liệu — 10 bảng
--  CHUẨN   : 3NF
--  HỆ QTG  : PostgreSQL 13 trở lên
--  FILE    : database/01-schema/02-create-tables.sql
--
--  CÁCH DÙNG:
--    psql -U postgres -c "CREATE DATABASE spoilage_predictor;"
--    psql -U postgres -d spoilage_predictor -f database/01-schema/02-create-tables.sql
--
--  LƯU Ý THIẾT KẾ:
--    1. Sử dụng ràng buộc CHECK thay vì kiểu ENUM của PostgreSQL, vì ENUM rất
--       khó mở rộng (thêm giá trị mới cần ALTER TYPE) và không tương thích tốt
--       với SQLAlchemy ORM khi cần migrate.
--    2. Mọi cột số lượng dùng NUMERIC, tuyệt đối KHÔNG dùng FLOAT/DOUBLE
--       PRECISION — tránh sai số làm sai lệch tồn kho (đặc biệt nguy hiểm với
--       đơn vị tính là kg hoặc lít).
--    3. Mọi cột thời gian dùng TIMESTAMPTZ để không lệch múi giờ.
--    4. expiry_date đặt ở bảng inventory / inventory_transactions chứ không đặt
--       ở products, vì hạn sử dụng thuộc về TỪNG LÔ HÀNG tại TỪNG CỬA HÀNG,
--       không phải thuộc tính bất biến của sản phẩm.
-- =============================================================================

BEGIN;

-- Tạo extension sinh mã tự động cho khóa chính
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Xóa bảng cũ để script có thể chạy lại nhiều lần (cảnh báo: mất dữ liệu)
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
--  HÀM DÙNG CHUNG
-- =============================================================================

-- Tự động cập nhật trường updated_at mỗi khi có thay đổi dữ liệu.
-- Giúp theo dõi được thời điểm sửa chữa thông tin, cần thiết cho đồ án vì
-- cho phép truy vết "ai sửa tồn kho vào lúc mấy giờ".
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
--  BẢNG 1: stores — Cửa hàng / Chi nhánh
-- -----------------------------------------------------------------------------
--  Đề tài hỗ trợ chuỗi cửa hàng nhiều chi nhánh, nên cần bảng này làm thực thể
--  gốc cho toàn bộ dữ liệu nghiệp vụ.
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

COMMENT ON TABLE  stores                  IS 'Cửa hàng / chi nhánh trong chuỗi bán lẻ hoặc F&B';
COMMENT ON COLUMN stores.store_id         IS 'Khoá chính, tự sinh';
COMMENT ON COLUMN stores.store_code       IS 'Mã cửa hàng, duy nhất, ví dụ: CH01, CH02';
COMMENT ON COLUMN stores.store_name       IS 'Tên cửa hàng hiển thị trên giao diện';
COMMENT ON COLUMN stores.store_type       IS 'Loại cửa hàng: convenience_store (tiện lợi), restaurant (nhà hàng), warehouse (kho)';
COMMENT ON COLUMN stores.opening_date     IS 'Ngày bắt đầu hoạt động';
COMMENT ON COLUMN stores.is_active        IS 'TRUE = đang hoạt động, FALSE = đã ngừng';


-- =============================================================================
--  BẢNG 2: users — Người dùng hệ thống
-- -----------------------------------------------------------------------------
--  store_id NULL nghĩa là người dùng quản lý toàn hệ thống (chủ chuỗi),
--  được thấy dữ liệu của tất cả các chi nhánh.
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

COMMENT ON TABLE  users               IS 'Tài khoản người dùng hệ thống';
COMMENT ON COLUMN users.user_id       IS 'Khoá chính, tự sinh';
COMMENT ON COLUMN users.username      IS 'Tên đăng nhập, duy nhất';
COMMENT ON COLUMN users.password_hash IS 'Mật khẩu đã băm bằng bcrypt — KHÔNG BAO GIỜ lưu mật khẩu dạng chữ thường';
COMMENT ON COLUMN users.role          IS 'Vai trò: owner (chủ chuỗi), manager (quản lý kho), staff (nhân viên)';
COMMENT ON COLUMN users.store_id      IS 'Chi nhánh làm việc, NULL nếu quản lý toàn hệ thống';

CREATE INDEX idx_users_store_id ON users(store_id);


-- =============================================================================
--  BẢNG 3: categories — Phân loại sản phẩm
-- -----------------------------------------------------------------------------
--  Có khóa ngoại tự tham chiếu (parent_category_id) để hỗ trợ phân loại
--  nhiều cấp, ví dụ: Thực phẩm > Đồ uống > Nước giải khát.
-- =============================================================================
CREATE TABLE categories (
    category_id        SERIAL        PRIMARY KEY,
    category_name      VARCHAR(150)  NOT NULL UNIQUE,
    description        TEXT,
    parent_category_id INTEGER       REFERENCES categories(category_id) ON DELETE SET NULL,
    created_at         TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  categories                    IS 'Nhóm phân loại sản phẩm, hỗ trợ phân loại nhiều cấp';
COMMENT ON COLUMN categories.category_id        IS 'Khoá chính, tự sinh';
COMMENT ON COLUMN categories.category_name      IS 'Tên nhóm, duy nhất';
COMMENT ON COLUMN categories.parent_category_id IS 'Nhóm cha, NULL nếu là nhóm cấp cao nhất';

CREATE INDEX idx_categories_parent_id ON categories(parent_category_id);


-- =============================================================================
--  BẢNG 4: products — Sản phẩm
-- -----------------------------------------------------------------------------
--  Bảng này lưu thông tin THUỘC TÍNH của sản phẩm (bất biến theo lô hàng).
--  Không có expiry_date vì hạn sử dụng thuộc về lô hàng cụ thể — xem bảng inventory.
--
--  Đơn vị tính: vì bán lẻ/F&B nên có thể là "cái", "kg", "hộp", "lít",
--  "chai"... Số lượng lưu NUMERIC để hỗ trợ bán lẻ theo kg/lít (số thập phân).
-- =============================================================================
CREATE TABLE products (
    product_id      SERIAL          PRIMARY KEY,
    product_code    VARCHAR(50)     NOT NULL UNIQUE,
    product_name    VARCHAR(255)    NOT NULL,
    category_id     INTEGER         NOT NULL REFERENCES categories(category_id) ON DELETE RESTRICT,
    unit            VARCHAR(20)     NOT NULL,
    unit_cost       NUMERIC(15,2)   NOT NULL DEFAULT 0 CHECK (unit_cost   >= 0),
    selling_price   NUMERIC(15,2)   NOT NULL DEFAULT 0 CHECK (selling_price >= 0),
    -- Số ngày bảo quản được tính từ ngày nhập kho, dùng để tính hạn khi tạo lô hàng
    shelf_life_days INTEGER         NOT NULL CHECK (shelf_life_days > 0),
    -- Ngưỡng tồn kho để sinh cảnh báo tự động
    min_stock       NUMERIC(15,3)   NOT NULL DEFAULT 0 CHECK (min_stock >= 0),
    max_stock       NUMERIC(15,3)   CHECK (max_stock IS NULL OR max_stock > 0),
    -- Sản phẩm có hạn sử dụng ngắn: đồ án tập trung vào nhóm này (hạn < 90 ngày)
    is_perishable   BOOLEAN         NOT NULL DEFAULT TRUE,
    -- Tồn kho bắt đầu dưới ngưỡng này sẽ sinh cảnh báo "tồn kho thấp"
    reorder_point   NUMERIC(15,3)   CHECK (reorder_point IS NULL OR reorder_point >= 0),
    supplier        VARCHAR(200),
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_stock_range CHECK (max_stock IS NULL OR min_stock <= max_stock)
);

COMMENT ON TABLE  products                  IS 'Thông tin sản phẩm — thuộc tính bất biến theo lô hàng';
COMMENT ON COLUMN products.product_id       IS 'Khoá chính, tự sinh';
COMMENT ON COLUMN products.product_code     IS 'Mã sản phẩm (SKU), duy nhất, ví dụ: SP0001';
COMMENT ON COLUMN products.product_name     IS 'Tên sản phẩm';
COMMENT ON COLUMN products.category_id      IS 'Nhóm sản phẩm';
COMMENT ON COLUMN products.unit             IS 'Đơn vị tính: cái, kg, lít, hộp, chai, thùng';
COMMENT ON COLUMN products.unit_cost        IS 'Giá nhập / giá vốn (VNĐ)';
COMMENT ON COLUMN products.selling_price    IS 'Giá bán lẻ (VNĐ)';
COMMENT ON COLUMN products.shelf_life_days  IS 'Số ngày bảo quản tính từ ngày nhập, dùng tính hạn sử dụng của lô hàng';
COMMENT ON COLUMN products.min_stock        IS 'Tồn kho tối thiểu — dưới mức này sẽ sinh cảnh báo';
COMMENT ON COLUMN products.max_stock        IS 'Tồn kho tối đa — vượt mức này sẽ sinh cảnh báo nhập dư';
COMMENT ON COLUMN products.is_perishable    IS 'TRUE = thực phẩm có hạn sử dụng ngắn (nhóm trọng tâm của đồ án)';
COMMENT ON COLUMN products.reorder_point    IS 'Điểm đặt lại — gợi ý nhập hàng khi tồn kho chạm ngưỡng này';
COMMENT ON COLUMN products.supplier         IS 'Nhà cung cấp mặc định';

CREATE INDEX idx_products_category_id ON products(category_id);
CREATE INDEX idx_products_is_active    ON products(is_active);
CREATE INDEX idx_products_product_name ON products(product_name);


-- =============================================================================
--  BẢNG 5: inventory — Tồn kho hiện tại theo lô hàng
-- -----------------------------------------------------------------------------
--  Mỗi dòng = MỘT LÔ HÀNG của MỘT SẢN PHẨM tại MỘT CỬA HÀNG.
--  Ràng buộc UNIQUE (store_id, product_id, expiry_date) cho phép cùng một sản
--  phẩm có nhiều lô với hạn sử dụng khác nhau — điều kiện cần để quản lý
--  hạn sử dụng và áp dụng nguyên tắc FIFO (xuất lô hết hạn sớm trước).
--
--  Quan hệ: inventory là bảng "ảnh chụp" trạng thái hiện tại, được cập nhật từ
--  inventory_transactions. Đây là dữ liệu phục vụ DASHBOARD và CẢNH BÁO.
-- =============================================================================
CREATE TABLE inventory (
    inventory_id   BIGSERIAL       PRIMARY KEY,
    store_id       INTEGER         NOT NULL REFERENCES stores(store_id)   ON DELETE CASCADE,
    product_id     INTEGER         NOT NULL REFERENCES products(product_id) ON DELETE RESTRICT,
    expiry_date    DATE,
    quantity       NUMERIC(15,3)   NOT NULL DEFAULT 0 CHECK (quantity >= 0),
    -- Ngày nhập lô hàng này vào kho, dùng để thống kê tồn đọng
    received_date  DATE            NOT NULL DEFAULT CURRENT_DATE,
    batch_code     VARCHAR(50),
    created_at     TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_inventory_store_product_expiry UNIQUE (store_id, product_id, expiry_date)
);

COMMENT ON TABLE  inventory               IS 'Tồn kho hiện tại, theo từng lô hàng của từng cửa hàng';
COMMENT ON COLUMN inventory.inventory_id   IS 'Khoá chính, tự sinh';
COMMENT ON COLUMN inventory.expiry_date    IS 'Ngày hết hạn của LÔ HÀNG này — dùng cho cảnh báo và xuất FIFO';
COMMENT ON COLUMN inventory.quantity       IS 'Số lượng đang tồn trong lô, không âm';
COMMENT ON COLUMN inventory.received_date  IS 'Ngày nhập lô hàng vào kho, dùng thống kê hàng tồn đọng';
COMMENT ON COLUMN inventory.batch_code     IS 'Mã lô hàng theo nhà cung cấp, nếu có';

-- Chỉ mục phục vụ truy vấn cảnh báo hết hạn (lọc theo ngày hết hạn)
CREATE INDEX idx_inventory_product_id  ON inventory(product_id);
CREATE INDEX idx_inventory_store_id    ON inventory(store_id);
CREATE INDEX idx_inventory_expiry_date ON inventory(expiry_date);
-- Chỉ mục phục vụ truy vấn "sắp hết hạn trong N ngày"
CREATE INDEX idx_inventory_expiry_store ON inventory(expiry_date, store_id) WHERE quantity > 0;


-- =============================================================================
--  BẢNG 6: inventory_transactions — Lịch sử nhập / xuất kho
-- -----------------------------------------------------------------------------
--  ★ ĐÂY LÀ BẢNG QUAN TRỌNG NHẤT ĐỐI VỚI MÔ HÌNH DỰ BÁO ★
--  Chứa dữ liệu chuỗi thời gian đầu vào cho ARIMA / Prophet / XGBoost.
--
--  Ghi chú kỹ thuật quan trọng — HIỆN TƯỢNG "CENSORED DEMAND":
--  Khi sản phẩm hết hàng, doanh số ghi nhận được sẽ bằng 0 dù khách hàng
--  vẫn muốn mua. Nếu đưa dữ liệu này vào mô hình dự báo, mô hình sẽ học
--  nhầm "bán ít = nhu cầu thấp" và dự báo thấp hơn thực tế ở các kỳ sau.
--  Cần phát hiện các ngày bị censored để hiệu chỉnh trước khi huấn luyện.
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

    -- Chống giao dịch trùng lặp: cùng một đơn hàng không được xuất cùng lô 2 lần
    CONSTRAINT uq_transactions_reference UNIQUE (reference_type, reference_id, product_id, expiry_date)
);

COMMENT ON TABLE  inventory_transactions                     IS 'Lịch sử giao dịch nhập/xuất kho — nguồn dữ liệu chính cho mô hình dự báo nhu cầu';
COMMENT ON COLUMN inventory_transactions.transaction_id     IS 'Khoá chính, tự sinh';
COMMENT ON COLUMN inventory_transactions.expiry_date        IS 'Hạn sử dụng của lô hàng tại thời điểm giao dịch';
COMMENT ON COLUMN inventory_transactions.transaction_type   IS 'import (nhập), export (xuất bán), adjustment (điều chỉnh kiểm kê), disposal (tiêu hủy hết hạn)';
COMMENT ON COLUMN inventory_transactions.quantity           IS 'Số lượng giao dịch, luôn dương — loại giao dịch quyết định chiều';
COMMENT ON COLUMN inventory_transactions.reference_type     IS 'Nguồn phát sinh: manual (nhập tay), order (từ đơn hàng), import_excel (từ file Excel)';
COMMENT ON COLUMN inventory_transactions.reference_id       IS 'Khoá tham chiếu tới bản ghi gốc trong orders nếu reference_type = order';
COMMENT ON COLUMN inventory_transactions.transaction_date   IS 'Thời điểm phát sinh giao dịch — cột thời gian quan trọng nhất cho dự báo';
COMMENT ON COLUMN inventory_transactions.note               IS 'Ghi chú, ví dụ lý do tiêu hủy hết hạn';

-- ===== CHỈ MỤC PHỤC VỤ DỰ BÁO (tối ưu truy vấn theo sản phẩm + thời gian) =====
CREATE INDEX idx_transactions_product_date ON inventory_transactions(product_id, transaction_date);
CREATE INDEX idx_transactions_store_date   ON inventory_transactions(store_id, transaction_date);
CREATE INDEX idx_transactions_date          ON inventory_transactions(transaction_date);
CREATE INDEX idx_transactions_type_date     ON inventory_transactions(transaction_type, transaction_date);


-- =============================================================================
--  BẢNG 7: orders — Đơn hàng
-- -----------------------------------------------------------------------------
--  order_type phân biệt đơn BÁN ra (sale) và đơn NHẬP vào (purchase).
--  Gộp chung một bảng giúp thống kê luồng hàng đối xứng hai chiều.
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

COMMENT ON TABLE  orders               IS 'Đơn hàng bán ra (sale) và đơn nhập hàng (purchase)';
COMMENT ON COLUMN orders.order_code     IS 'Mã đơn hàng, duy nhất';
COMMENT ON COLUMN orders.order_type     IS 'sale = bán ra, purchase = nhập vào kho';
COMMENT ON COLUMN orders.status         IS 'pending = đang xử lý, completed = hoàn tất, cancelled = đã huỷ';
COMMENT ON COLUMN orders.total_amount   IS 'Tổng tiền sau giảm giá (VNĐ)';
COMMENT ON COLUMN orders.total_quantity IS 'Tổng số lượng các mặt hàng trong đơn';

CREATE INDEX idx_orders_store_date  ON orders(store_id, order_date);
CREATE INDEX idx_orders_date        ON orders(order_date);
CREATE INDEX idx_orders_type_date   ON orders(order_type, order_date, status);


-- =============================================================================
--  BẢNG 8: order_items — Chi tiết đơn hàng
-- -----------------------------------------------------------------------------
--  line_total dùng GENERATED ALWAYS AS ... STORED: giá trị được PostgreSQL tự
--  tính, không thể sửa tay → không bao giờ xảy ra sai lệch do lỗi tính tay.
--  (Yêu cầu PostgreSQL 12 trở lên.)
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

    -- Một sản phẩm chỉ xuất hiện 1 lần trong cùng một đơn
    CONSTRAINT uq_order_items_order_product UNIQUE (order_id, product_id)
);

COMMENT ON TABLE  order_items                  IS 'Chi tiết từng mặt hàng trong đơn';
COMMENT ON COLUMN order_items.line_total       IS 'Thành tiền = số lượng × đơn giá × (1 - % giảm giá), tự động tính';
COMMENT ON COLUMN order_items.discount_percent IS 'Phần trăm giảm giá từ 0 đến 100';
COMMENT ON COLUMN order_items.unit_cost        IS 'Giá vốn tại thời điểm bán, dùng tính lợi nhuận gộp';

CREATE INDEX idx_order_items_order_id   ON order_items(order_id);
CREATE INDEX idx_order_items_product_id ON order_items(product_id);


-- =============================================================================
--  BẢNG 9: forecasts — Kết quả dự báo nhu cầu
-- -----------------------------------------------------------------------------
--  Lưu kết quả dự báo của TỪNG MÔ HÌNH để so sánh công bằng trên cùng một
--  tập dữ liệu kiểm tra — nguyên tắc bắt buộc khi đánh giá mô hình dự báo.
--
--  Ghi chú thiết kế: khuyến nghị "gợi ý nhập hàng" (recommended_import_qty)
--  được tính ngoài mô hình dự báo, dựa trên: nhu cầu dự báo − tồn kho hiện tại
--  + tồn kho an toàn, đồng thời xét hạn sử dụng để không gợi ý nhập hàng có
--  hạn sử dụng quá ngắn. Xem tài liệu thiết kế thuật toán.
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

    -- Một sản phẩm tại một cửa hàng chỉ có 1 kết quả cho mỗi ngày dự báo
    -- và mỗi mô hình → tránh trùng khi chạy lại
    CONSTRAINT uq_forecasts_unique UNIQUE (store_id, product_id, model_name, forecast_date)
);

COMMENT ON TABLE  forecasts                          IS 'Kết quả dự báo nhu cầu theo từng mô hình';
COMMENT ON COLUMN forecasts.model_name               IS 'Mô hình dự báo: prophet, xgboost, arima, moving_average, naive';
COMMENT ON COLUMN forecasts.forecast_date            IS 'Ngày được dự báo (nằm ở tương lai so với thời điểm huấn luyện)';
COMMENT ON COLUMN forecasts.horizon_days             IS 'Số ngày dự trước tính từ thời điểm huấn luyện';
COMMENT ON COLUMN forecasts.predicted_quantity       IS 'Số lượng dự báo bán ra';
COMMENT ON COLUMN forecasts.lower_bound              IS 'Cận dưới khoảng tin cậy, dùng tính tồn kho an toàn theo phương pháp tin cậy';
COMMENT ON COLUMN forecasts.upper_bound              IS 'Cận trên khoảng tin cậy';
COMMENT ON COLUMN forecasts.recommended_import_qty   IS 'Gợi ý số lượng nhập hàng, tính từ dự báo và tồn kho hiện tại';
COMMENT ON COLUMN forecasts.rmse                     IS 'Sai số căn bậc hai trung bình — chỉ số đánh giá chính';
COMMENT ON COLUMN forecasts.mae                      IS 'Sai số tuyệt đối trung bình';
COMMENT ON COLUMN forecasts.mape                     IS 'Sai số phần trăm trung bình — dễ diễn giải cho người quản lý';
COMMENT ON COLUMN forecasts.trained_at               IS 'Thời điểm chạy mô hình, dùng để biết kết quả có còn giá trị không';

CREATE INDEX idx_forecasts_product_date  ON forecasts(product_id, forecast_date);
CREATE INDEX idx_forecasts_store_date    ON forecasts(store_id, forecast_date);
CREATE INDEX idx_forecasts_model         ON forecasts(model_name);


-- =============================================================================
--  BẢNG 10: alerts — Cảnh báo
-- -----------------------------------------------------------------------------
--  alert_type bao gồm cả cảnh báo theo mô hình (forecast_anomaly) lẫn cảnh báo
--  theo quy tắc nghiệp vụ. Đây là bảng trung tâm cho tính năng real-time
--  qua WebSocket: mỗi khi có bản ghi mới, backend đẩy thông báo tới frontend.
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

    -- Không thể vừa đã đóng vừa chưa đóng cùng lúc
    CONSTRAINT chk_alert_resolved_at CHECK (
        (is_resolved AND resolved_at IS NOT NULL) OR
        (NOT is_resolved AND resolved_at IS NULL)
    )
);

COMMENT ON TABLE  alerts                     IS 'Cảnh báo hệ thống: hết hạn, tồn kho bất thường, sai lệch dự báo';
COMMENT ON COLUMN alerts.alert_type          IS 'expiring_soon (sắp hết hạn), expired (đã hết hạn), low_stock (tồn thấp), over_stock (tồn cao), forecast_anomaly (bất thường dự báo)';
COMMENT ON COLUMN alerts.severity            IS 'Mức độ nghiêm trọng: low, medium, high, critical';
COMMENT ON COLUMN alerts.current_stock       IS 'Tồn kho hiện tại tại thời điểm sinh cảnh báo';
COMMENT ON COLUMN alerts.threshold_value     IS 'Ngưỡng đã vượt, giúp hiểu vì sao sinh cảnh báo';
COMMENT ON COLUMN alerts.is_read             IS 'Người dùng đã xem chưa';
COMMENT ON COLUMN alerts.is_resolved         IS 'Đã xử lý xong chưa';
COMMENT ON COLUMN alerts.resolved_at         IS 'Thời điểm đóng cảnh báo';

-- Chỉ mục phục vụ truy vấn cảnh báo chưa đọc (tính năng real-time)
CREATE INDEX idx_alerts_unread    ON alerts(store_id, created_at DESC) WHERE is_read = FALSE;
CREATE INDEX idx_alerts_product   ON alerts(product_id);
CREATE INDEX idx_alerts_type_date ON alerts(alert_type, created_at DESC);


-- =============================================================================
--  TRIGGER — Tự động cập nhật updated_at
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
--  HÀM NGHIỆP VỤ — Sinh cảnh báo tự động
-- -----------------------------------------------------------------------------
--  Đây là hàm minh hoạ cơ chế cảnh báo của giai đoạn 1. Trong hệ thống thật,
--  backend sẽ gọi hàm này theo lịch (cron job) mỗi ngày, hoặc gọi trực tiếp
--  sau mỗi giao dịch nhập/xuất.
--
--  Cảnh báo được sinh theo 4 quy tắc:
--    1. Hết hạn       — ngày hết hạn < hôm nay
--    2. Sắp hết hạn  — còn <= 3 ngày và còn tồn kho
--    3. Tồn kho thấp  — tổng tồn < min_stock
--    4. Tồn kho cao  — tổng tồn > max_stock
--
--  Điều kiện chống trùng: chỉ sinh cảnh báo chưa được xử lý (is_resolved =
--  FALSE) của cùng loại và cùng sản phẩm.
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
    -- 1 & 2. CẢNH BÁO HẾT HẠN ------------------------------------------------
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
        p.product_name || ' — ' ||
            CASE WHEN i.expiry_date < v_today
                 THEN 'ĐÃ HẾT HẠN từ ' || TO_CHAR(i.expiry_date, 'DD/MM/YYYY')
                 ELSE 'SẮP HẾT HẠN ngày ' || TO_CHAR(i.expiry_date, 'DD/MM/YYYY') END,
        'Lô hàng còn ' || i.quantity || ' ' || p.unit ||
            '. Cần xử lý trước ngày ' || TO_CHAR(i.expiry_date, 'DD/MM/YYYY') || '.',
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

    -- 3. CẢNH BÁO TỒN KHO THẤP ------------------------------------------------
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
        p.product_name || ' — TỒN KHO THẤP',
        'Tồn kho hiện tại ' || SUM(i.quantity) || ' ' || p.unit ||
            ', thấp hơn ngưỡng tối thiểu ' || p.min_stock || ' ' || p.unit || '.',
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

    -- 4. CẢNH BÁO TỒN KHO CAO (nguy cơ nhập dư) ---------------------------------
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
        p.product_name || ' — TỒN KHO CAO',
        'Tồn kho hiện tại ' || SUM(i.quantity) || ' ' || p.unit ||
            ', vượt ngưỡng tối đa ' || p.max_stock || ' ' || p.unit ||
            '. Cần xem xét giảm lượng nhập.',
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
    'Sinh cảnh báo tự động: hết hạn, sắp hết hạn, tồn kho thấp, tồn kho cao. Trả về số cảnh báo đã tạo.';


-- =============================================================================
--  VIEW — TRUY VẤN PHỤC VỤ GIAO DIỆN VÀ MÔ HÌNH DỰ BÁO
-- =============================================================================

-- View 1: Doanh thu bán ra theo ngày — NGUỒN DỮ LIỆU CHÍNH CHO MÔ HÌNH DỰ BÁO.
-- Lưu ý: chỉ tính đơn completed, và GHI NHẬN rõ trường is_censored.
-- Nếu ngày nào tồn kho = 0 thì doanh số ghi nhận được không phản ánh nhu cầu
-- thực — cần dùng cờ is_censored để hiệu chỉnh trước khi huấn luyện mô hình.
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

COMMENT ON VIEW v_daily_sales IS 'Doanh thu và số lượng bán ra theo ngày — dữ liệu đầu vào cho mô hình dự báo nhu cầu';


-- View 2: Tồn kho dưới ngưỡng tối thiểu — cho biểu đồ cảnh báo
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

COMMENT ON VIEW v_low_stock IS 'Sản phẩm có tồn kho thấp hơn ngưỡng tối thiểu, kèm số lượng thiếu';


-- View 3: Lô hàng sắp hết hạn — cho tính năng cảnh báo, dùng định kỳ
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

COMMENT ON VIEW v_expiring_inventory IS 'Các lô hàng còn tồn và hết hạn trong vòng 30 ngày, kèm mức độ cảnh báo';


-- View 4: Tổng hợp tồn kho theo sản phẩm — cho dashboard
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

COMMENT ON VIEW v_product_stock_summary IS 'Tổng hợp tồn kho, giá trị tồn kho và lợi nhuận gộp tiềm năng theo sản phẩm';


COMMIT;


-- =============================================================================
--  KIỂM TRA SAU KHI TẠO
-- =============================================================================
\echo '--- Danh sách bảng đã tạo ---'
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_type = 'BASE TABLE'
ORDER BY table_name;

\echo '--- Số lượng bảng (kỳ vọng: 10) ---'
SELECT COUNT(*) AS total_tables
FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';

\echo '--- Kiểm tra khoá ngoại ---'
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

\echo '--- Tạo schema thành công! Bước tiếp theo: chạy database/02-seed/seed-data.sql ---'

-- =============================================================================
--  GHI CHÚ KỸ THUẬT
-- =============================================================================
--
--  1. VỀ CENSORED DEMAND (hiện tượng quan trọng nhất khi dự báo bán lẻ):
--     View v_daily_sales chỉ ghi nhận doanh số thực tế. Khi sản phẩm hết hàng,
--     doanh số = 0 dù khách vẫn có nhu cầu. Khi huấn luyện mô hình cần:
--       - Bổ sung lịch mua hàng (purchases) để xác định ngày nào bị hết hàng
--       - Hiệu chỉnh doanh số các ngày trước đó bằng một ước lượng nhu cầu
--       - Hoặc dùng giá trị tồn kho 0 làm cờ đánh dấu ngày bị censored
--
--  2. VỀ FIFO VÀ HẠN SỬ DỤNG:
--     Ràng buộc UNIQUE (store_id, product_id, expiry_date) cho phép theo dõi
--     nhiều lô cùng sản phẩm. Khi xuất hàng, nghiệp vụ chuẩn là xuất lô có
--     expiry_date sớm nhất trước để giảm thiểu lãng phịch.
--
--  3. VỀ CỘNG CHỈ MỤC:
--     Các view đã tạo đều có thể gắn chỉ mục để tăng tốc truy vấn:
--       CREATE INDEX idx_v_daily_sales ON v_daily_sales(product_id, sale_date);
--     Hiện chưa tạo vì kích thước bảng giao dịch còn nhỏ, sẽ đánh giá lại
--     sau khi có dữ liệu thực tế.
--
--  4. VỀ MIGRATION:
--     Thay đổi lược đồ sau này cần tạo file trong database/03-migrations/
--     theo thứ tự 01_, 02_, 03_... KHÔNG sửa trực tiếp file này.
-- =============================================================================
