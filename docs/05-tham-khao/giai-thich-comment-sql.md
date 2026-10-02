# Giải thích comment trong file SQL Schema

> **File SQL:** `database/01-schema/02-create-tables.sql`
> **Mục đích:** File SQL dùng comment **tiếng Anh** để tránh lỗi encoding khi chạy `psql` trên Windows PowerShell. Tài liệu này giữ lại **nghĩa tiếng Việt** của toàn bộ comment, dùng khi viết báo cáo đồ án hoặc khi cần tra cứu.
> **Ngày cập nhật:** 02/10/2026

---

## 0. Lưu ý quan trọng về nguồn dữ liệu dự báo

Bảng này từng mô tả `inventory_transactions` là *"bảng quan trọng nhất đối với mô hình dự báo"*. **Điều đó đã sai và đã được sửa** (migration `004-fix-comments.sql`).

| Bảng / view | Vai trò thực tế |
|--------------|-----------------|
| `orders` + `order_items` | **Lịch sử bán hàng thật** — nguồn dữ liệu gốc |
| `v_daily_sales` (view) | **Đầu vào duy nhất cho mô hình dự báo** ARIMA / Prophet / XGBoost |
| `inventory` | Tồn kho hiện tại theo lô hàng |
| `inventory_transactions` | Nhật ký truy vết biến động tồn kho — dùng cho **phân tích tồn kho**, cảnh báo hết hạn, chọn lô FIFO. **KHÔNG** phải đầu vào dự báo |

Lý do tách bạch: nếu doanh số nằm ở cả hai nơi, hệ thống sẽ có **hai nguồn sự thật** cho cùng một khái niệm và rất dễ lệch nhau.

---

## 1. Vì sao comment lại dùng tiếng Anh?
Khi chạy file `.sql` chứa ký tự tiếng Việt trên Windows, `psql` có thể báo lỗi do bảng mã ký tự (character encoding) của console không khớp với file. Ba cách xử lý:

| Cách | Hiệu quả | Ghi chú |
|------|----------|---------|
| Chuyển comment sang tiếng Anh | ✅ Chắc chắn | **Đã áp dụng** — file thuần ASCII, không thể lỗi encoding |
| Đặt biến môi trường `PGCLIENTENCODING=UTF8` | ⚠️ Tùy | Chạy được nhưng phụ thuộc thiết lập máy |
| Đổi code page: `chcp 65001` | ⚠️ Tùy | Chỉ áp dụng cho console, không áp dụng khi chạy tự động |

Nếu sau này cần thêm nội dung tiếng Việt vào file SQL, chạy lệnh sau trước:

```powershell
$env:PGCLIENTENCODING = "UTF8"
psql -U postgres -d spoilage_predictor -f database/01-schema/02-create-tables.sql
```

> **Lưu ý quan trọng:** Chuỗi `message` và `title` trong hàm `fn_generate_inventory_alerts()` cũng đã chuyển sang tiếng Anh. Đây là **thông báo hiển thị cho người dùng cuối** trong giao diện. Khi phát triển frontend, cần đưa các thông báo này về tiếng Việt (xem mục 9 bên dưới).

---

## 2. Comment phần đầu file

| Comment tiếng Anh | Nghĩa tiếng Việt |
|-------------------|------------------|
| `PROJECT: SUPPLY CHAIN SPOILAGE PREDICTOR` | Đề tài: Nền tảng Quản trị Chuỗi cung ứng Chống lãng phí |
| `Retail / F&B chain management platform` | Nền tảng quản trị chuỗi cửa hàng bán lẻ / F&B |
| `TASK: Create database schema - 10 tables` | Nhiệm vụ: Tạo lược đồ cơ sở dữ liệu — 10 bảng |
| `NORMAL: 3NF` | Chuẩn hoá: 3NF (dạng chuẩn thứ ba) |
| `DATABASE: PostgreSQL 13 or later` | Cơ sở dữ liệu: PostgreSQL 13 trở lên |
| `USAGE` | Cách sử dụng |
| `ENCODING NOTE` | Lưu ý về encoding ký tự |
| `This file uses ASCII characters only (English comments) so it runs without errors on Windows PowerShell / cmd` | File này chỉ dùng ký tự ASCII (comment tiếng Anh) để chạy không lỗi trên Windows PowerShell / cmd |
| `If Vietnamese text is added later, run psql with:` | Nếu sau này thêm nội dung tiếng Việt, chạy psql với: |

### 2.1. Các ghi chú thiết kế (DESIGN NOTES)

| Comment tiếng Anh | Nghĩa tiếng Việt |
|-------------------|------------------|
| `1. CHECK constraints are used instead of PostgreSQL ENUM types.` | 1. Dùng ràng buộc CHECK thay cho kiểu ENUM của PostgreSQL. |
| `ENUM is hard to extend (adding a value needs ALTER TYPE) and does not work well with SQLAlchemy ORM during migrations.` | ENUM rất khó mở rộng (thêm giá trị mới phải dùng ALTER TYPE) và không tương thích tốt với SQLAlchemy ORM khi migrate. |
| `2. All quantity columns use NUMERIC, never FLOAT/DOUBLE PRECISION.` | 2. Mọi cột số lượng dùng NUMERIC, tuyệt đối không dùng FLOAT/DOUBLE PRECISION. |
| `Float rounding errors would corrupt stock levels, which is especially dangerous for products sold by weight or volume (kg, litre).` | Sai số làm tròn của float sẽ làm sai lệch tồn kho, đặc biệt nguy hiểm với sản phẩm bán theo khối lượng hoặc thể tích (kg, lít). |
| `3. All timestamp columns use TIMESTAMPTZ to avoid timezone drift.` | 3. Mọi cột thời gian dùng TIMESTAMPTZ để tránh lệch múi giờ. |
| `4. expiry_date lives in inventory and inventory_transactions, NOT in products.` | 4. `expiry_date` nằm ở bảng inventory và inventory_transactions, KHÔNG nằm ở products. |
| `Expiry belongs to a specific BATCH in a specific STORE, it is not a fixed attribute of the product itself.` | Hạn sử dụng thuộc về một LÔ HÀNG cụ thể tại một CỬA HÀNG cụ thể, không phải thuộc tính bất biến của sản phẩm. |

### 2.2. Các dòng khác

| Comment tiếng Anh | Nghĩa tiếng Việt |
|-------------------|------------------|
| `Extension used to generate primary key values` | Extension dùng để sinh giá trị khoá chính |
| `Drop old tables so this script can be re-run many times (WARNING: data loss)` | Xoá các bảng cũ để script có thể chạy lại nhiều lần (CẢNH BÁO: mất dữ liệu) |
| `SHARED FUNCTION` | Hàm dùng chung |

---

## 3. Hàm `fn_update_updated_at()`

| Comment tiếng Anh | Nghĩa tiếng Việt |
|-------------------|------------------|
| `Auto-update the updated_at field on every row change.` | Tự động cập nhật trường `updated_at` mỗi khi dữ liệu thay đổi. |
| `Needed for the project because it allows tracing "who edited stock and when".` | Cần thiết cho đồ án vì cho phép truy vết "ai sửa tồn kho vào lúc mấy giờ". |

---

## 4. Bảng 1 — `stores` (Cửa hàng / Chi nhánh)

| Comment tiếng Anh | Nghĩa tiếng Việt |
|-------------------|------------------|
| `TABLE 1: stores - Shops / Branches` | BẢNG 1: stores — Cửa hàng / Chi nhánh |
| `The project targets a chain of retail shops, so this table is the root entity for all business data in the system.` | Đề tài hướng tới chuỗi cửa hàng bán lẻ, nên bảng này là thực thể gốc cho toàn bộ dữ liệu nghiệp vụ trong hệ thống. |

| Đối tượng | Comment tiếng Anh | Nghĩa tiếng Việt |
|-----------|-------------------|------------------|
| Bảng | `Shop / branch in the retail or F&B chain` | Cửa hàng / chi nhánh trong chuỗi bán lẻ hoặc F&B |
| `store_id` | `Primary key, auto generated` | Khoá chính, tự sinh |
| `store_code` | `Unique shop code, example: CH01, CH02` | Mã cửa hàng, duy nhất, ví dụ: CH01, CH02 |
| `store_name` | `Shop name shown on the user interface` | Tên cửa hàng hiển thị trên giao diện người dùng |
| `store_type` | `Shop type: convenience_store, restaurant, warehouse` | Loại cửa hàng: cửa hàng tiện lợi, nhà hàng, kho hàng |
| `opening_date` | `Date the shop started operating` | Ngày bắt đầu hoạt động |
| `is_active` | `TRUE = operating, FALSE = closed` | TRUE = đang hoạt động, FALSE = đã ngừng |

---

## 5. Bảng 2 — `users` (Người dùng hệ thống)

| Comment tiếng Anh | Nghĩa tiếng Việt |
|-------------------|------------------|
| `TABLE 2: users - System accounts` | BẢNG 2: users — Tài khoản người dùng hệ thống |
| `store_id NULL means the user manages the whole system (chain owner) and can see data from all branches.` | `store_id` NULL nghĩa là người dùng quản lý toàn hệ thống (chủ chuỗi) và có thể xem dữ liệu của tất cả các chi nhánh. |

| Đối tượng | Comment tiếng Anh | Nghĩa tiếng Việt |
|-----------|-------------------|------------------|
| Bảng | `System user accounts` | Tài khoản người dùng hệ thống |
| `user_id` | `Primary key, auto generated` | Khoá chính, tự sinh |
| `username` | `Login name, unique` | Tên đăng nhập, duy nhất |
| `password_hash` | `Password hashed with bcrypt - NEVER store plain text` | Mật khẩu đã băm bằng bcrypt — TUYỆT ĐỐI KHÔNG lưu dạng chữ thường |
| `role` | `Role: owner (chain owner), manager (stock manager), staff (employee)` | Vai trò: owner (chủ chuỗi), manager (quản lý kho), staff (nhân viên) |
| `store_id` | `Working branch, NULL if manages the whole system` | Chi nhánh làm việc, NULL nếu quản lý toàn hệ thống |

---

## 6. Bảng 3 — `categories` (Phân loại sản phẩm)

| Comment tiếng Anh | Nghĩa tiếng Việt |
|-------------------|------------------|
| `TABLE 3: categories - Product categories` | BẢNG 3: categories — Nhóm phân loại sản phẩm |
| `Self-referencing foreign key (parent_category_id) supports multi-level categories, example: Food > Beverages > Soft drinks.` | Khoá ngoại tự tham chiếu (`parent_category_id`) hỗ trợ phân loại nhiều cấp, ví dụ: Thực phẩm > Đồ uống > Nước giải khát. |

| Đối tượng | Comment tiếng Anh | Nghĩa tiếng Việt |
|-----------|-------------------|------------------|
| Bảng | `Product category groups, supports multi-level grouping` | Nhóm phân loại sản phẩm, hỗ trợ phân loại nhiều cấp |
| `category_id` | `Primary key, auto generated` | Khoá chính, tự sinh |
| `category_name` | `Category name, unique` | Tên nhóm, duy nhất |
| `parent_category_id` | `Parent category, NULL if top level` | Nhóm cha, NULL nếu là nhóm cấp cao nhất |

---

## 7. Bảng 4 — `products` (Sản phẩm)

| Comment tiếng Anh | Nghĩa tiếng Việt |
|-------------------|------------------|
| `TABLE 4: products - Products` | BẢNG 4: products — Sản phẩm |
| `This table stores FIXED product attributes (not batch specific).` | Bảng này lưu thuộc tính CỐ ĐỊNH của sản phẩm (không phụ thuộc lô hàng). |
| `There is no expiry_date here because expiry belongs to a batch - see the inventory table.` | Không có `expiry_date` ở đây vì hạn sử dụng thuộc về lô hàng — xem bảng inventory. |
| `Units: retail and F&B sell by piece, kg, box, litre, bottle.` | Đơn vị tính: bán lẻ và F&B bán theo cái, kg, hộp, lít, chai. |
| `Quantities use NUMERIC so fractional sales by kg or litre are supported.` | Số lượng dùng NUMERIC nên hỗ trợ bán lẻ theo kg hoặc lít với số thập phân. |
| `Shelf life in days counted from the received date, used to calculate the expiry date when a batch is created` | Số ngày bảo quản tính từ ngày nhập, dùng để tính hạn sử dụng khi tạo lô hàng |
| `Stock thresholds used to generate automatic alerts` | Ngưỡng tồn kho dùng để sinh cảnh báo tự động |
| `Short shelf life product: the project focuses on these (under 90 days)` | Sản phẩm hạn sử dụng ngắn: đồ án tập trung vào nhóm này (dưới 90 ngày) |
| `Stock level below this triggers a reorder suggestion` | Tồn kho dưới mức này sẽ kích hoạt gợi ý đặt lại hàng |

| Đối tượng | Comment tiếng Anh | Nghĩa tiếng Việt |
|-----------|-------------------|------------------|
| Bảng | `Product information - fixed attributes, not batch specific` | Thông tin sản phẩm — thuộc tính cố định, không phụ thuộc lô hàng |
| `product_id` | `Primary key, auto generated` | Khoá chính, tự sinh |
| `product_code` | `Unique product code (SKU), example: SP0001` | Mã sản phẩm (SKU) duy nhất, ví dụ: SP0001 |
| `product_name` | `Product name` | Tên sản phẩm |
| `category_id` | `Product category` | Nhóm sản phẩm |
| `unit` | `Unit of measure: piece, kg, litre, box, bottle, carton` | Đơn vị tính: cái, kg, lít, hộp, chai, thùng |
| `unit_cost` | `Purchase cost / cost of goods (VND)` | Giá nhập / giá vốn (VNĐ) |
| `selling_price` | `Retail selling price (VND)` | Giá bán lẻ (VNĐ) |
| `shelf_life_days` | `Days the product keeps after receiving, used to set batch expiry date` | Số ngày sản phẩm giữ được sau khi nhập, dùng để đặt hạn cho lô hàng |
| `min_stock` | `Minimum stock level - below this an alert is raised` | Tồn kho tối thiểu — dưới mức này sẽ sinh cảnh báo |
| `max_stock` | `Maximum stock level - above this an overstock alert is raised` | Tồn kho tối đa — vượt mức này sẽ sinh cảnh báo tồn cao |
| `is_perishable` | `TRUE = short shelf life food, the main focus of this project` | TRUE = thực phẩm hạn ngắn, là trọng tâm của đồ án |
| `reorder_point` | `Reorder point - suggests importing stock when reached` | Điểm đặt lại — gợi ý nhập hàng khi tồn kho chạm ngưỡng này |
| `supplier` | `Default supplier` | Nhà cung cấp mặc định |

---

## 8. Bảng 5 — `inventory` (Tồn kho theo lô hàng)

| Comment tiếng Anh | Nghĩa tiếng Việt |
|-------------------|------------------|
| `TABLE 5: inventory - Current stock per batch` | BẢNG 5: inventory — Tồn kho hiện tại theo lô hàng |
| `Each row = ONE BATCH of ONE PRODUCT in ONE SHOP.` | Mỗi dòng = MỘT LÔ HÀNG của MỘT SẢN PHẨM tại MỘT CỬA HÀNG. |
| `UNIQUE (store_id, product_id, expiry_date) allows the same product to have several batches with different expiry dates.` | Ràng buộc UNIQUE `(store_id, product_id, expiry_date)` cho phép cùng một sản phẩm có nhiều lô với hạn sử dụng khác nhau. |
| `This is required to manage expiry tracking and apply FIFO (sell the earliest expiry batch first).` | Điều này cần thiết để quản lý hạn sử dụng và áp dụng nguyên tắc FIFO (xuất lô hết hạn sớm trước). |
| `Relationship: inventory is the CURRENT snapshot, updated from inventory_transactions.` | Quan hệ dữ liệu: inventory là ảnh chụp trạng thái HIỆN TẠI, được cập nhật từ inventory_transactions. |
| `This data feeds the DASHBOARD and ALERTS.` | Dữ liệu này phục vụ DASHBOARD và CẢNH BÁO. |
| `Date this batch was received, used to report slow moving stock` | Ngày nhập lô hàng này vào kho, dùng để thống kê hàng tồn đọng |
| `Index serving expiry alert queries (filter by expiry date)` | Chỉ mục phục vụ truy vấn cảnh báo hết hạn (lọc theo ngày hết hạn) |
| `Index serving the query "expiring within N days"` | Chỉ mục phục vụ truy vấn "sắp hết hạn trong N ngày" |

| Đối tượng | Comment tiếng Anh | Nghĩa tiếng Việt |
|-----------|-------------------|------------------|
| Bảng | `Current stock, per batch, per shop` | Tồn kho hiện tại, theo từng lô hàng, theo từng cửa hàng |
| `inventory_id` | `Primary key, auto generated` | Khoá chính, tự sinh |
| `expiry_date` | `Expiry date of THIS batch - used for alerts and FIFO ordering` | Ngày hết hạn của LÔ HÀNG NÀY — dùng cho cảnh báo và thứ tự xuất FIFO |
| `quantity` | `Quantity remaining in this batch, never negative` | Số lượng còn lại trong lô này, không âm |
| `received_date` | `Date the batch was received, used to report slow moving stock` | Ngày nhập lô hàng vào kho, dùng thống kê hàng tồn đọng |
| `batch_code` | `Supplier batch code, optional` | Mã lô hàng theo nhà cung cấp, không bắt buộc |

---

## 9. Bảng 6 — `inventory_transactions` (Lịch sử nhập/xuất kho)

| Comment tiếng Anh | Nghĩa tiếng Việt |
|-------------------|------------------|
| `TABLE 6: inventory_transactions - Stock movement history` | BẢNG 6: inventory_transactions — Lịch sử giao dịch nhập/xuất kho |
| `ROLE IN THIS PROJECT - READ THIS BEFORE USING THE TABLE:` | VAI TRÒ TRONG DỰ ÁN — ĐỌC MỤC NÀY TRƯỚC KHI DÙNG BẢNG: |
| `This table is the audit trail for stock movements. It feeds:` | Bảng này là nhật ký truy vết các biến động tồn kho. Nó phục vụ: |
| `- stock analysis (which product moved how much, when)` | − Phân tích tồn kho (sản phẩm nào biến động bao nhiêu, khi nào) |
| `- expiry alerts (v_expiring_inventory, fn_generate_inventory_alerts)` | − Cảnh báo hết hạn (`v_expiring_inventory`, `fn_generate_inventory_alerts`) |
| `- FIFO batch selection when exporting goods` | − Chọn lô hàng theo nguyên tắc FIFO khi xuất hàng |
| `- spoilage statistics (disposal movements)` | − Thống kê lãng phịch (các giao dịch tiêu hủy) |
| `It is NOT the source for demand forecasting.` | Nó **KHÔNG** phải nguồn dữ liệu cho bài toán dự báo nhu cầu. |
| `The forecasting input is v_daily_sales, which is built from orders + order_items.` | Đầu vào cho mô hình dự báo là view `v_daily_sales`, được xây dựng từ `orders` + `order_items`. |
| `Sales and stock movements are deliberately kept apart so that one source of truth exists for "what was sold".` | Doanh số và biến động tồn kho được tách bạch có chủ đích, để tồn tại **một nguồn sự thật duy nhất** cho câu hỏi "đã bán được gì". |
| `Critical technical note - CENSORED DEMAND (applies to the forecasting input, i.e. orders/order_items):` | Lưu ý kỹ thuật quan trọng — HIỆN TƯỢNG CENSORED DEMAND (áp dụng cho đầu vào dự báo, tức `orders`/`order_items`): |
| `When a product runs out of stock, recorded sales become 0 even though customers still wanted to buy.` | Khi sản phẩm hết hàng, doanh số ghi nhận được sẽ bằng 0 dù khách hàng vẫn muốn mua. |
| `If this data is fed to a forecasting model, the model learns the wrong relation "low sales = low demand" and will under-forecast in later periods.` | Nếu đưa dữ liệu này vào mô hình dự báo, mô hình sẽ học nhầm mối quan hệ "bán ít = nhu cầu thấp" và dự báo thấp hơn thực tế ở các kỳ sau. |
| `Those days must be detected and corrected before training.` | Phải phát hiện và hiệu chỉnh các ngày này trước khi huấn luyện. |
| `Prevent duplicate movements: the same order cannot export the same batch twice` | Chống giao dịch trùng lặp: cùng một đơn hàng không được xuất cùng lô 2 lần |
| `INDEXES FOR STOCK ANALYSIS (not used by the forecasting model)` | CHỈ MỤC PHỤC VỤ PHÂN TÍCH TỒN KHO (không dùng cho mô hình dự báo) |

| Đối tượng | Comment tiếng Anh | Nghĩa tiếng Việt |
|-----------|-------------------|------------------|
| Bảng | `Stock movement audit trail - used for stock analysis, expiry alerts and FIFO. NOT the demand forecasting input.` | Nhật ký truy vết biến động tồn kho — dùng cho phân tích tồn kho, cảnh báo hết hạn và FIFO. **KHÔNG** phải đầu vào cho mô hình dự báo nhu cầu. |
| `transaction_id` | `Primary key, auto generated` | Khoá chính, tự sinh |
| `expiry_date` | `Expiry date of the batch at the time of the movement` | Hạn sử dụng của lô hàng tại thời điểm giao dịch |
| `transaction_type` | `import, export (sale), adjustment (stocktake), disposal (spoilage write-off)` | nhập, xuất (bán), điều chỉnh (kiểm kê), tiêu hủy (hết hạn) |
| `quantity` | `Movement quantity, always positive - direction is decided by transaction_type` | Số lượng giao dịch, luôn dương — chiều giao dịch do `transaction_type` quyết định |
| `reference_type` | `Origin of the record: manual, order, import_excel` | Nguồn phát sinh bản ghi: nhập tay, từ đơn hàng, từ file Excel |
| `reference_id` | `Reference key to the source record in orders when reference_type = order` | Khoá tham chiếu tới bản ghi gốc trong bảng orders khi `reference_type = order` |
| `transaction_date` | `When the movement happened - the most important column for forecasting` | Thời điểm phát sinh giao dịch — cột quan trọng nhất cho dự báo |
| `note` | `Note, for example the reason a batch was written off` | Ghi chú, ví dụ lý do tiêu hủy một lô hàng |

---

## 10. Bảng 7 — `orders` (Đơn hàng)

| Comment tiếng Anh | Nghĩa tiếng Việt |
|-------------------|------------------|
| `TABLE 7: orders - Orders` | BẢNG 7: orders — Đơn hàng |
| `order_type distinguishes SALE orders from PURCHASE orders.` | `order_type` phân biệt đơn BÁN ra và đơn NHẬP vào. |
| `Keeping both in one table allows symmetric two-way stock flow reporting.` | Gộp cả hai vào một bảng giúp thống kê luồng hàng đối xứng hai chiều. |

| Đối tượng | Comment tiếng Anh | Nghĩa tiếng Việt |
|-----------|-------------------|------------------|
| Bảng | `Sales orders (sale) and purchase orders (purchase)` | Đơn hàng bán ra (sale) và đơn nhập hàng (purchase) |
| `order_code` | `Unique order code` | Mã đơn hàng, duy nhất |
| `order_type` | `sale = sold to customer, purchase = purchased into stock` | sale = bán ra cho khách, purchase = nhập vào kho |
| `status` | `pending, completed, or cancelled` | đang xử lý, đã hoàn tất, đã huỷ |
| `total_amount` | `Total amount after discount (VND)` | Tổng tiền sau giảm giá (VNĐ) |
| `total_quantity` | `Total quantity of all items in the order` | Tổng số lượng các mặt hàng trong đơn |

---

## 11. Bảng 8 — `order_items` (Chi tiết đơn hàng)

| Comment tiếng Anh | Nghĩa tiếng Việt |
|-------------------|------------------|
| `TABLE 8: order_items - Order line items` | BẢNG 8: order_items — Chi tiết mặt hàng trong đơn |
| `line_total uses GENERATED ALWAYS AS ... STORED: PostgreSQL computes it, it cannot be edited by hand, so it can never drift due to a manual calculation mistake.` | `line_total` dùng `GENERATED ALWAYS AS ... STORED`: PostgreSQL tự tính, không thể sửa tay, nên không bao giờ sai lệch do lỗi tính tay. |
| `(Requires PostgreSQL 12 or later.)` | (Yêu cầu PostgreSQL 12 trở lên.) |
| `A product appears at most once in the same order` | Một sản phẩm chỉ xuất hiện tối đa một lần trong cùng một đơn |

| Đối tượng | Comment tiếng Anh | Nghĩa tiếng Việt |
|-----------|-------------------|------------------|
| Bảng | `Line items of each order` | Chi tiết từng mặt hàng trong đơn |
| `line_total` | `Line amount = quantity * unit price * (1 - discount %), auto computed` | Thành tiền = số lượng × đơn giá × (1 − % giảm giá), tự động tính |
| `discount_percent` | `Discount percentage from 0 to 100` | Phần trăm giảm giá từ 0 đến 100 |
| `unit_cost` | `Cost at time of sale, used for gross margin` | Giá vốn tại thời điểm bán, dùng tính lợi nhuận gộp |

---

## 12. Bảng 9 — `forecasts` (Kết quả dự báo)

| Comment tiếng Anh | Nghĩa tiếng Việt |
|-------------------|------------------|
| `TABLE 9: forecasts - Demand forecast results` | BẢNG 9: forecasts — Kết quả dự báo nhu cầu |
| `Stores results of EACH model so they can be compared fairly on the same test set - this is mandatory when evaluating forecasting models.` | Lưu kết quả của TỪNG mô hình để so sánh công bằng trên cùng một tập kiểm tra — đây là điều bắt buộc khi đánh giá mô hình dự báo. |
| `Design note: the recommended import quantity is calculated outside the forecasting model, from: predicted demand - current stock + safety stock, while also checking expiry dates so we never suggest importing goods with a shelf life that is too short.` | Ghi chú thiết kế: gợi ý số lượng nhập hàng được tính bên ngoài mô hình dự báo, theo công thức: nhu cầu dự báo − tồn kho hiện tại + tồn kho an toàn, đồng thời xét hạn sử dụng để không gợi ý nhập hàng có hạn quá ngắn. |
| `See the algorithm design document.` | Xem tài liệu thiết kế thuật toán. |
| `One result per product, shop, model and forecast date prevents duplicates when the job re-runs` | Mỗi sản phẩm tại một cửa hàng chỉ có một kết quả cho mỗi ngày dự báo và mỗi mô hình — tránh trùng khi chạy lại |

| Đối tượng | Comment tiếng Anh | Nghĩa tiếng Việt |
|-----------|-------------------|------------------|
| Bảng | `Demand forecast results per model` | Kết quả dự báo nhu cầu theo từng mô hình |
| `model_name` | `Model: prophet, xgboost, arima, moving_average, naive` | Mô hình: Prophet, XGBoost, ARIMA, trung bình động, nguyên bản |
| `forecast_date` | `The predicted date (in the future relative to training time)` | Ngày được dự báo (nằm ở tương lai so với thời điểm huấn luyện) |
| `horizon_days` | `Days predicted ahead from the training time` | Số ngày dự trước tính từ thời điểm huấn luyện |
| `predicted_quantity` | `Predicted quantity sold` | Số lượng dự báo bán ra |
| `lower_bound` | `Lower confidence bound, used for safety stock calculation` | Cận dưới khoảng tin cậy, dùng tính tồn kho an toàn |
| `upper_bound` | `Upper confidence bound` | Cận trên khoảng tin cậy |
| `recommended_import_qty` | `Suggested import quantity, derived from the forecast and current stock` | Gợi ý số lượng nhập hàng, tính từ dự báo và tồn kho hiện tại |
| `rmse` | `Root mean squared error - main accuracy metric` | Sai số căn bậc hai trung bình — chỉ số đánh giá chính |
| `mae` | `Mean absolute error` | Sai số tuyệt đối trung bình |
| `mape` | `Mean absolute percentage error - easiest metric to explain to managers` | Sai số phần trăm trung bình — dễ diễn giải nhất cho người quản lý |
| `trained_at` | `When the model was run, to check if the result is still valid` | Thời điểm chạy mô hình, dùng để biết kết quả có còn giá trị không |

---

## 13. Bảng 10 — `alerts` (Cảnh báo)

| Comment tiếng Anh | Nghĩa tiếng Việt |
|-------------------|------------------|
| `TABLE 10: alerts - Alerts` | BẢNG 10: alerts — Cảnh báo |
| `alert_type covers both rule based alerts and model based alerts.` | `alert_type` bao gồm cả cảnh báo theo quy tắc nghiệp vụ lẫn cảnh báo theo mô hình. |
| `This is the central table for the WebSocket real-time feature: whenever a row is inserted, the backend pushes it to the frontend.` | Đây là bảng trung tâm cho tính năng real-time qua WebSocket: mỗi khi có bản ghi mới, backend đẩy thông báo tới frontend. |
| `An alert cannot be closed and unresolved at the same time` | Một cảnh báo không thể vừa đã đóng vừa chưa đóng cùng lúc |
| `Index serving unread alert queries (the real-time feature)` | Chỉ mục phục vụ truy vấn cảnh báo chưa đọc (tính năng real-time) |

| Đối tượng | Comment tiếng Anh | Nghĩa tiếng Việt |
|-----------|-------------------|------------------|
| Bảng | `System alerts: expiry, abnormal stock, forecast deviation` | Cảnh báo hệ thống: hết hạn, tồn kho bất thường, sai lệch dự báo |
| `alert_type` | `expiring_soon, expired, low_stock, over_stock, forecast_anomaly` | sắp hết hạn, đã hết hạn, tồn kho thấp, tồn kho cao, bất thường dự báo |
| `severity` | `Severity level: low, medium, high, critical` | Mức độ nghiêm trọng: thấp, trung bình, cao, nghiêm trọng |
| `current_stock` | `Stock level at the moment the alert was created` | Tồn kho hiện tại tại thời điểm sinh cảnh báo |
| `threshold_value` | `Threshold that was crossed, explains why the alert fired` | Ngưỡng đã vượt, giúp hiểu vì sao sinh cảnh báo |
| `is_read` | `Has the user read this alert` | Người dùng đã xem cảnh báo này chưa |
| `is_resolved` | `Has the issue been handled` | Vấn đề đã được xử lý xong chưa |
| `resolved_at` | `When the alert was closed` | Thời điểm đóng cảnh báo |

---

## 14. Trigger

| Comment tiếng Anh | Nghĩa tiếng Việt |
|-------------------|------------------|
| `TRIGGERS - Auto update updated_at` | TRIGGER — Tự động cập nhật `updated_at` |

---

## 15. Hàm `fn_generate_inventory_alerts()` (Sinh cảnh báo tự động)

| Comment tiếng Anh | Nghĩa tiếng Việt |
|-------------------|------------------|
| `BUSINESS FUNCTION - Automatic alert generation` | HÀM NGHIỆP VỤ — Sinh cảnh báo tự động |
| `This function demonstrates the alert mechanism of phase 1.` | Hàm này minh hoạ cơ chế cảnh báo của giai đoạn 1. |
| `In the real system the backend calls it on a schedule (cron job) each day, or directly after every import/export transaction.` | Trong hệ thống thật, backend sẽ gọi hàm này theo lịch (cron job) mỗi ngày, hoặc gọi trực tiếp sau mỗi giao dịch nhập/xuất. |
| `Alerts are generated by 4 rules:` | Cảnh báo được sinh theo 4 quy tắc: |
| `1. Expired - expiry date is earlier than today` | 1. Hết hạn — ngày hết hạn sớm hơn hôm nay |
| `2. Expiring soon - expires within <= 3 days and stock remains` | 2. Sắp hết hạn — còn ≤ 3 ngày và vẫn còn tồn kho |
| `3. Low stock - total stock < min_stock` | 3. Tồn kho thấp — tổng tồn < `min_stock` |
| `4. Overstock - total stock > max_stock` | 4. Tồn kho cao — tổng tồn > `max_stock` |
| `Duplicate guard: an alert is only created when there is no unresolved alert of the same type for the same product.` | Chống trùng: chỉ tạo cảnh báo khi không có cảnh báo chưa xử lý cùng loại của cùng sản phẩm đó. |
| `1 & 2. EXPIRY ALERTS` | 1 và 2. CẢNH BÁO HẾT HẠN |
| `3. LOW STOCK ALERTS` | 3. CẢNH BÁO TỒN KHO THẤP |
| `4. OVERSTOCK ALERTS (risk of over-ordering)` | 4. CẢNH BÁO TỒN KHO CAO (nguy cơ nhập dư) |
| *(comment của hàm)* `Generate automatic alerts: expired, expiring soon, low stock, overstock. Returns the number of alerts created.` | Sinh cảnh báo tự động: hết hạn, sắp hết hạn, tồn kho thấp, tồn kho cao. Trả về số cảnh báo đã tạo. |

---

## 16. View

| Comment tiếng Anh | Nghĩa tiếng Việt |
|-------------------|------------------|
| `VIEWS - QUERIES FOR THE USER INTERFACE AND FORECASTING MODEL` | VIEW — TRUY VẤN PHỤC VỤ GIAO DIỆN VÀ MÔ HÌNH DỰ BÁO |
| `View 1: Daily sales - MAIN DATA SOURCE FOR THE FORECASTING MODEL.` | View 1: Doanh thu bán ra theo ngày — NGUỒN DỮ LIỆU CHÍNH CHO MÔ HÌNH DỰ BÁO. |
| `Note: only completed orders are counted, and censored days must be tracked.` | Lưu ý: chỉ tính đơn đã hoàn tất, và phải theo dõi các ngày bị censored. |
| `If stock is 0 on a day, recorded sales do NOT reflect real demand - use the censored flag to correct the data before training the model.` | Nếu tồn kho bằng 0 trong ngày, doanh số ghi nhận KHÔNG phản ánh nhu cầu thực — dùng cờ censored để hiệu chỉnh dữ liệu trước khi huấn luyện. |
| `View 2: Stock below the minimum level - for the alert chart` | View 2: Tồn kho dưới ngưỡng tối thiểu — cho biểu đồ cảnh báo |
| `View 3: Batches expiring soon - for the alert feature, run on a schedule` | View 3: Lô hàng sắp hết hạn — cho tính năng cảnh báo, chạy định kỳ |
| `View 4: Stock summary per product - for the dashboard` | View 4: Tổng hợp tồn kho theo sản phẩm — cho dashboard |

| Đối tượng | Comment tiếng Anh | Nghĩa tiếng Việt |
|-----------|-------------------|------------------|
| `v_daily_sales` | `Daily quantity and revenue per product/shop - PRIMARY data source for the demand forecasting model (ARIMA / Prophet / XGBoost). Built from orders + order_items.` | Số lượng và doanh thu bán ra theo ngày, theo từng sản phẩm và cửa hàng — **nguồn dữ liệu chính** cho mô hình dự báo nhu cầu (ARIMA / Prophet / XGBoost). Được xây dựng từ `orders` + `order_items`. |
| `v_low_stock` | `Products with stock below the minimum level, with the shortage quantity` | Sản phẩm có tồn kho thấp hơn ngưỡng tối thiểu, kèm số lượng thiếu |
| `v_expiring_inventory` | `Batches still in stock expiring within 30 days, with alert severity` | Các lô hàng còn tồn và hết hạn trong vòng 30 ngày, kèm mức độ cảnh báo |
| `v_product_stock_summary` | `Stock, stock value and potential gross profit summary per product` | Tổng hợp tồn kho, giá trị tồn kho và lợi nhuận gộp tiềm năng theo sản phẩm |

---

## 17. Kiểm tra sau khi tạo

| Comment tiếng Anh | Nghĩa tiếng Việt |
|-------------------|------------------|
| `POST-CREATE VERIFICATION` | KIỂM TRA SAU KHI TẠO |
| `Tables created` | Danh sách bảng đã tạo |
| `Table count (expected: 10)` | Số lượng bảng (kỳ vọng: 10) |
| `Foreign key check` | Kiểm tra khoá ngoại |
| `Schema created successfully. Next step: run database/02-seed/seed-data.sql` | Tạo schema thành công! Bước tiếp theo: chạy `database/02-seed/seed-data.sql` |

---

## 18. Ghi chú kỹ thuật cuối file

| Comment tiếng Anh | Nghĩa tiếng Việt |
|-------------------|------------------|
| `TECHNICAL NOTES` | GHI CHÚ KỸ THUẬT |
| `1. CENSORED DEMAND (the most important issue when forecasting retail):` | 1. CENSORED DEMAND (vấn đề quan trọng nhất khi dự báo bán lẻ): |
| `View v_daily_sales only records actual sales. When a product is out of stock, sales are 0 even though customers still had demand.` | View `v_daily_sales` chỉ ghi nhận doanh số thực tế. Khi sản phẩm hết hàng, doanh số bằng 0 dù khách hàng vẫn có nhu cầu. |
| `When training a model you must:` | Khi huấn luyện mô hình cần: |
| `- Use purchase orders to detect which days were out of stock` | − Dùng đơn nhập hàng để xác định ngày nào bị hết hàng |
| `- Correct sales on preceding days with an estimated demand figure` | − Hiệu chỉnh doanh số các ngày trước đó bằng một ước lượng nhu cầu |
| `- Or treat zero stock as a censored flag for that day` | − Hoặc dùng tồn kho bằng 0 làm cờ đánh dấu ngày bị censored |
| `2. FIFO AND EXPIRY:` | 2. FIFO VÀ HẠN SỬ DỤNG: |
| `UNIQUE (store_id, product_id, expiry_date) allows tracking several batches of the same product.` | Ràng buộc UNIQUE `(store_id, product_id, expiry_date)` cho phép theo dõi nhiều lô của cùng một sản phẩm. |
| `The standard business rule when exporting is to take the batch with the earliest expiry date first to minimise spoilage.` | Quy tắc nghiệp vụ chuẩn khi xuất hàng là lấy lô có hạn sử dụng sớm nhất trước để giảm thiểu lãng phịch. |
| `3. VIEW INDEXES:` | 3. CHỈ MỤC CHO VIEW: |
| `The views can be indexed for faster queries:` | Có thể tạo chỉ mục cho view để truy vấn nhanh hơn: |
| `Not created yet because the transaction table is still small. Re-evaluate once real data is available.` | Hiện chưa tạo vì bảng giao dịch còn nhỏ. Đánh giá lại khi có dữ liệu thực tế. |
| `4. MIGRATION:` | 4. MIGRATION: |
| `Future schema changes must go in database/03-migrations/ with ordered names 01_, 02_, 03_... Do NOT edit this file directly after release.` | Thay đổi lược đồ sau này cần tạo file trong `database/03-migrations/` theo thứ tự 01_, 02_, 03_... KHÔNG sửa trực tiếp file này sau khi phát hành. |

---

## 19. ⚠️ Cần đưa về tiếng Việt khi phát triển frontend

Các chuỗi sau trong hàm `fn_generate_inventory_alerts()` là **thông báo hiển thị cho người dùng cuối**, hiện đang là tiếng Anh. Khi làm giao diện, cần chuyển về tiếng Việt (hoặc tách ra file i18n riêng):

| Chuỗi tiếng Anh hiện tại | Nghĩa tiếng Việt |
|--------------------------|------------------|
| `EXPIRED since DD/MM/YYYY` | ĐÃ HẾT HẠN từ DD/MM/YYYY |
| `EXPIRING on DD/MM/YYYY` | SẮP HẾT HẠN ngày DD/MM/YYYY |
| `Batch remaining X unit. Handle before DD/MM/YYYY.` | Lô hàng còn X đơn vị. Cần xử lý trước ngày DD/MM/YYYY. |
| `LOW STOCK` | TỒN KHO THẤP |
| `Current stock X, below minimum level Y.` | Tồn kho hiện tại X, thấp hơn ngưỡng tối thiểu Y. |
| `OVERSTOCK` | TỒN KHO CAO |
| `Above maximum level Y. Consider reducing the next import.` | Vượt ngưỡng tối đa Y. Cần xem xét giảm lượng nhập lần sau. |

**Khuyến nghị:** Khi phát triển frontend, nên đưa toàn bộ thông báo sang một file i18n (ví dụ `backend/app/i18n/vi.json`) để có thể đa ngôn ngữ mà không phải sửa SQL. Như vậy file SQL luôn giữ được dạng ASCII an toàn.

---

## 20. Cách dùng tài liệu này

Khi cần giải thích một cấu trúc trong báo cáo đồ án (Chương 3 — Thiết kế cơ sở dữ liệu), tra cứu nhanh:

| Cần tìm | Xem mục |
|---------|---------|
| Nghĩa của một cột trong `products` | Mục 7 |
| Nghĩa của một cột trong `inventory` | Mục 8 |
| Nghĩa của một cột trong `inventory_transactions` | Mục 9 |
| Tại sao `products` không có `expiry_date` | Mục 2.1, mục 7 |
| Quy tắc sinh cảnh báo | Mục 15 |
| Vì sao dùng NUMERIC không dùng FLOAT | Mục 2.1 |
| Hiện tượng censored demand | Mục 9, mục 18 |
