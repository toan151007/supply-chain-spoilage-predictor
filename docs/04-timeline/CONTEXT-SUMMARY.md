# Tóm tắt toàn bộ dự án — Context Summary

> **Cập nhật:** 12/10/2026 · commit `8e60e09`
> **Repo:** https://github.com/toan151007/supply-chain-spoilage-predictor
> **Giai đoạn:** Tuần 1 (05/10 – 16/10/2026)
> **Ghi chú:** file này là bản tóm tắt ngắn của toàn bộ dự án. Khi chuyển sang máy/AI mới, đọc file này trước, sau đó đọc `AGENTS.md` và `GHI-CHU-TIEN-DO.md` nếu cần chi tiết.

---

## 1. Dự án làm gì

### Tên dự án

**Supply Chain Spoilage Predictor** — Nền tảng Quản trị Chuỗi cung ứng Chống lãng phịch

### Mục tiêu

Dự báo nhu cầu · tối ưu nhập hàng · giảm lãng phí thực phẩm cho chuỗi cửa hàng bán lẻ / F&B.

Hệ thống gồm 4 thành phần chính:

| Thành phần | Vai trò |
|------------|----------|
| **Dự báo nhu cầu** | Dùng mô hình thống kê dự báo số lượng bán theo từng cặp sản phẩm × cửa hàng |
| **Gợi ý nhập hàng** | Tính lượng nhập đề xuất dựa trên nhu cầu dự báo, tồn kho hiện tại và tồn kho an toàn |
| **Cảnh báo hết hạn** | Phát hiện lô hàng sắp/đã hết hạn, tồn kho thấp, tồn kho cao |
| **AI Agent hỏi đáp kho** | Chatbot trả lời câu hỏi nghiệp vụ, có grounding từ database |

### Tech stack đã chốt

| Lớp | Công nghệ |
|-----|-----------|
| Frontend | React.js + Vite + Tailwind CSS · WebSocket · chatbot Gemini API |
| Backend | Python FastAPI · SQLAlchemy ORM |
| Database | PostgreSQL 18.6 · 10 bảng · CHECK constraint thay vì ENUM |
| AI/ML | Prophet (chính) · XGBoost · ARIMA + trung bình động (đối chứng) · Python 3.14.7 |
| Dữ liệu | Kaggle — Walmart Store Sales, 2013–2017 · 912.999 dòng |

**Quyết định quan trọng:** KHÔNG dùng LSTM. Chỉ trình bày lý thuyết — quy mô dữ liệu không đủ cho mạng nơ-ron hội quy.

---

## 2. Đã xong gì

### 2.1 Tài liệu

| Mã | Nội dung | Trạng thái |
|-----|----------|------------|
| T1 | `README.md` — 11 mục | ✅ commit `31df9f7` |
| T3 | `docs/03-thiet-ke/kien-truc-he-thong.md` — 4 sơ đồ Mermaid | ✅ commit `31df9f7` |
| T4.1 | `docs/02-bao-cao/chuong-1-tong-quan.md` — ~2.050 từ, 6 mục | ✅ commit `f55dce4` |
| T4.2 | `docs/02-bao-cao/chuong-2-co-so-ly-thuyet.md` — ~2.500 từ, 6 mục | ✅ commit `40020ca` |
| M3 | `docs/05-tham-khao/ket-qua-danh-gia-model.md` | ✅ commit `47b4775` |
| — | `docs/05-tham-khao/giai-thich-comment-sql.md` — đối chiếu comment SQL Anh ↔ Việt | ✅ |
| — | `backend/app/i18n/vi.json` — 9 khóa thông báo cảnh báo | ✅ commit `9372a0d` |

### 2.2 Backend FastAPI (B1 — 12/10/2026)

| File | Vai trò |
|------|---------|
| `backend/requirements.txt` | 7 thư viện, ghim phiên bản |
| `backend/.env.example` | **File mẫu** — hướng dẫn clone repo. KHÔNG chứa mật khẩu thật |
| `backend/app/config.py` | Đọc `.env` qua pydantic-settings · `@lru_cache` · `cors_origins` tách 2 kiểu |
| `backend/app/database.py` | `create_engine` + `SessionLocal` + `Base` + `get_db()` + `check_database()` |
| `backend/app/main.py` | Khởi tạo FastAPI + CORS + gắn 2 router |
| `backend/app/routers/health.py` | 3 endpoint health check |

### 2.3 Backend ORM Models (B2 — 12/10/2026)

11 file trong `backend/app/models/` — mỗi bảng 1 file + `__init__.py` export tất cả.

| File | Bảng |
|------|------|
| `store.py` | `stores` |
| `category.py` | `categories` |
| `user.py` | `users` |
| `product.py` | `products` |
| `inventory.py` | `inventory` |
| `inventory_transaction.py` | `inventory_transactions` |
| `order.py` | `orders` |
| `order_item.py` | `order_items` |
| `forecast.py` | `forecasts` |
| `alert.py` | `alerts` |

**3 điểm kỹ thuật xử lý đặc biệt:**

| Vấn đề | Cách xử lý |
|---|---|
| `order_items.line_total` là GENERATED ALWAYS AS ... STORED | `Computed(..., persisted=True)` — DB tự tính, **không gán tay** |
| `categories.parent_category_id` tự tham chiếu | `remote_side` + `foreign_keys` ở cả 2 chiều `parent`/`children` |
| Cột `NUMERIC` | Trả về `Decimal` trong Python — ép `float()` khi tính toán |

**Đã test thật** — đọc 947.590 dòng qua ORM, khớp 100% với `pg_stat_user_tables`:

| Bảng | Số dòng | Bảng | Số dòng |
|------|----------|------|----------|
| `order_items` | 912.999 | `inventory` | 1.330 |
| `orders` | 18.260 | `inventory_transactions` | 11.412 |
| `forecasts` | 3.000 | `alerts` | 518 |
| `products` | 50 | `stores` | 10 |
| `categories` | 8 | `users` | 3 |

Relationship đã kiểm chứng: `Order → store`, `Order → items → product`, `Store → {users, inventory, alerts, forecasts}`, `Category → products` + tự tham chiếu (Food có 3 nhóm con).

### 2.4 API nghiệp vụ — CRUD Products (B3 — 12/10/2026)

| File | Vai trò |
|------|---------|
| `backend/app/schemas/product_schema.py` | 6 Pydantic schema: `ProductBase` · `Create` · `Update` · `Read` · `Page` · `CategoryBrief` |
| `backend/app/routers/product_router.py` | 5 endpoint, tất cả truy vấn qua ORM |

| Endpoint | Chức năng |
|----------|-----------|
| `GET /api/v1/products` | Danh sách có phân trang + lọc `category_id` · `is_active` · tìm kiếm `search` |
| `GET /api/v1/products/{id}` | Chi tiết 1 sản phẩm (kèm category) |
| `POST /api/v1/products` | Tạo mới |
| `PUT /api/v1/products/{id}` | Cập nhật một phần (`exclude_unset=True`) |
| `DELETE /api/v1/products/{id}` | Xoá — trả **409** nếu sản phẩm đã có lịch sử |

**Xử lý lỗi chuẩn:**

| Tình huống | HTTP |
|------------|------|
| Không tìm thấy | 404 |
| `product_code`/`product_name` trùng | 409 |
| `category_id` không tồn tại | 422 |
| `max_stock < min_stock` | 422 (validator Python, chặn trước khi ghi DB) |
| Xoá sản phẩm đã có đơn hàng / tồn kho / dự báo | 409 kèm gợi ý dùng `is_active = false` |

Phân trang mặc định 20/trang, tối đa 100. Response trả **object** `{total, page, page_size, pages, items}` thay vì list thuần, để frontend biết tổng số bản ghi mà không cần gọi thêm.

**Đã test thật: 27/27 pass** (tạo sản phẩm thử rồi xoá, dữ liệu về nguyên 50 sản phẩm).

### 2.5 API nghiệp vụ — CRUD 5 bảng còn lại (B4 — 12/10/2026)

**Tổng: 37 operation · 22 path · 32 schema** (tính cả B3).

| Router | Số endpoint | Ghi chú |
|--------|-------------|---------|
| `store_router.py` | 5 | Xoá cửa hàng có đơn → **409** (`orders` FK RESTRICT) |
| `category_router.py` | 5 | Chặn tạo vòng lặp cha–con; xoá nhóm còn nhóm con → **409** |
| `inventory_router.py` | 6 | `GET /expiring?days=N` — lô sắp hết hạn, chỉ lô `quantity > 0` |
| `forecast_router.py` | 5 | **Không có POST/PUT** — dữ liệu do M2 sinh ra |
| `alert_router.py` | 8 | `PUT /{id}/read` · `PUT /{id}/resolve` · `GET /unread` · `GET /unread-count` |

**Schema dùng chung:** `schemas/common.py` định nghĩa generic `Page[T]` → mọi endpoint list trả cùng cấu trúc `{total, page, page_size, pages, items}`.

**Ràng buộc nghiệp vụ đã xử lý:**

| Vấn đề | Xử lý |
|--------|-------|
| Xoá `stores` có đơn hàng | 409 kèm gợi ý dùng `is_active = false` |
| Xoá `categories` còn sản phẩm hoặc nhóm con | 409 kèm số lượng tham chiếu |
| Làm nhóm hàng thành cha của chính nó / của nhóm cháu | 422 — chặn ở tầng app vì DB sẽ chấp nhận và làm hỏng cây |
| `alerts` CHECK `resolved_at` phải khớp `is_resolved` | Router gán **cả hai** cùng lúc — set riêng sẽ bị DB từ chối |
| Xoá sạch 3.000 dòng forecasts do gõ nhầm | `DELETE /forecasts` **bắt buộc** có ít nhất 1 filter, không có → 422 |

**`/forecasts/latest`** trả **dòng mới nhất** (30/01/2018) cho mỗi cặp sản phẩm × cửa hàng — 100 dòng, **không phải** tổng 30 ngày. Khi một cặp có nhiều mô hình cùng ngày, chọn mô hình có **RMSE thấp nhất**. Đã cross-check giá trị khớp với dòng tương ứng trong `GET /forecasts`.

**`/alerts` `title` chứa i18n key** (`alert.title.EXPIRED`), không phải text hiển thị — dịch ở `backend/app/i18n/vi.json`.

### 2.6 API Dashboard tổng hợp (B5 — 12/10/2026)

6 endpoint dưới `/api/v1/dashboard`. **Mọi số liệu đã đối chiếu với DB và file CSV gốc.**

| Endpoint | Nguồn | Kết quả thật |
|----------|-------|---------------|
| `/overview` | `orders` + `products` + `stores` + view tồn kho + `alerts` | 18.260 đơn · 50 SP · 10 CH · doanh thu 1.409.611.790.000 · tồn kho 1.542.170.700 · 518 cảnh báo |
| `/revenue?period=&year=` | `orders` + `date_trunc` | day 365 · week 53 · month 12 · year 1 điểm/năm |
| `/top-products?limit=` | `order_items` + `orders` + `products` | SP0015 dẫn đầu 1.607.442 sản phẩm |
| `/low-stock?threshold=` | view `v_low_stock` | 57 cặp · `threshold=20` → 21 |
| `/expiring?days=` | view `v_expiring_inventory` | `days=0` → 444 · `days=7` → 474 · `days=30` → 564 |
| `/alerts-summary` | `alerts` | 518 · theo loại và theo mức độ |

**Đối chiếu số liệu — khớp tuyệt đối:**

| Kiểm tra | API | DB / CSV |
|----------|-----|----------|
| Doanh thu 5 năm | 1.409.611.790.000 | ✅ |
| Doanh thu 2017 / số đơn | 317.233.060.000 / 3.650 | ✅ |
| SP15 năm 2017 | 361.586 | ✅ **khớp CSV gốc** |
| SP15 cả 5 năm | 1.607.442 | ✅ |
| Low stock `threshold=20` | 21 | ✅ |
| Expiring `days=7` | 474 | ✅ |
| Tổng `by_severity` = `total` | 518 | ✅ |

**Hiệu năng (đo 20 lần):**

| Endpoint | Thời gian |
|----------|-----------|
| `low-stock` | 13 ms |
| `revenue` | 17 ms |
| `alerts-summary` | 23 ms |
| `expiring?days=7` | 68 ms |
| `overview` | 137 ms |
| `top-products` | 222–350 ms (trên 912.999 dòng) |

**Cách đọc view:** `backend/app/models/views.py` dùng SQLAlchemy Core reflection (`Table(..., autoload_with=engine)`) cho 4 view — vẫn là `select()`/`group_by()`, **không** raw SQL.

**Ràng buộc phát hiện khi đọc view:** `v_expiring_inventory` có `WHERE expiry_date <= CURRENT_DATE + 30`. API chặn `days > 30` bằng 422 thay vì âm thầm trả kết quả không đổi.

> ⚠️ `total_revenue` và `total_inventory_value` dùng **giá MÔ PHỎNG** — không phải doanh thu thật.

**Endpoint hiện có:**

| Endpoint | Mục đích | Tiền tố |
|----------|----------|---------|
| `GET /` | Hướng dẫn nhanh (`"message": "API dang chay"`) | — |
| `GET /health` | Kiểm tra server còn sống | hạ tầng |
| `GET /health/database` | Kiểm tra kết nối PostgreSQL | hạ tầng |
| `GET /api/v1/health` | Trùng nội dung `/health`, có tiền tố theo quy tắc dự án | `/api/v1/` |
| `GET /docs` · `/redoc` · `/openapi.json` | Tài liệu API | — |

**Đã test thật** — 6/6 endpoint trả `200 OK`, DB `"connected": true`, CORS trả đúng header cho cả `:3000` và `:5173`. Đã chụp màn hình Swagger UI xác nhận 3 endpoint hiện đúng.

Phiên bản: FastAPI 0.143.0 · uvicorn 0.54.0 · pydantic 2.14.1 · pydantic-settings 2.15.0.

### 2.7 API bán hàng — orders + order-items (B6 — 12/10/2026)

12 endpoint dưới `/api/v1/orders` và `/api/v1/order-items`. **155 check test, tất cả PASS.**

| Method | Path |
|--------|------|
| GET | `/orders` · `/orders/{id}` · `/orders/{id}/items` · `/order-items` · `/order-items/{id}` |
| POST | `/orders` (kèm items) · `/order-items` |
| PUT | `/orders/{id}` · `/orders/{id}/status` · `/order-items/{id}` |
| DELETE | `/orders/{id}` · `/order-items/{id}` |

**Ba điều DB không tự lo, phải do API đảm nhiệm:**

1. **`orders.total_amount` / `total_quantity` là cột thường**, không có trigger nào đồng bộ với `order_items`. Mỗi lần thêm/sửa/xoá dòng đều phải tính lại bằng `SUM(line_total)` và `SUM(quantity)`.
2. **Session chạy `autoflush=False`** → phải `db.flush()` trước mỗi `SUM`, nếu không tổng tính từ trạng thái cũ.
3. **`flush()` phải nằm trong `try` bắt `IntegrityError`** — `flush()` mới là chỗ phát `INSERT`, đặt ngoài `try` thì lỗi UNIQUE thành **500** thay vì **409**.

**`line_total` là GENERATED COLUMN** — không có trong schema ghi nào, chỉ đọc qua `db.refresh()`. Client gửi lên bị bỏ qua, DB tự tính. Đã kiểm 6 trường hợp, gồm giảm 100% → `0.00`.

**Mốc thời gian — dữ liệu ở +07:00, không phải UTC:**

| Khoảng `from_date`→`to_date` | Số đơn 2017 |
|------------------------------|------------|
| `2017-01-01T00:00:00Z` → `2017-12-31T23:59:59Z` | 3.640 ❌ |
| `2017-01-01T00:00:00+07:00` → `2017-12-31T23:59:59+07:00` | **3.650** ✅ |

Mốc UTC cắt mất 10 đơn của ngày 01/01 (1 đơn/cửa hàng × 10).

**Vòng đời đơn hàng:**

| Từ → Đến | Kết quả |
|----------|---------|
| pending → completed / cancelled | ✅ |
| cancelled → pending (mở lại) | ✅ |
| trùng trạng thái hiện tại | ✅ idempotent |
| completed → bất cứ | ❌ 409 |

Chỉ đơn `pending` sửa được. Xoá đơn còn dòng → **409** (FK là `ON DELETE CASCADE` nhưng API cố tình chặn). Thêm sản phẩm đã có trong đơn → **409** (UNIQUE `(order_id, product_id)`).

**Hệ quả cần nhớ:** đơn `completed` là điểm cuối — không API nào xoá được. Dọn dữ liệu test phải dùng SQL.

**Số liệu tham chiếu:** 18.260 đơn · 912.999 dòng · 1.826 đơn/cửa hàng · 91.300 dòng/cửa hàng · mỗi đơn 50 dòng.

### 2.8 API Import Excel/CSV (B7 — 12/10/2026)

5 endpoint. **115 check test, tất cả PASS.** Đã cài thêm `python-multipart` + `openpyxl` + `pandas` vào `backend/requirements.txt`.

| Method | Path |
|--------|------|
| POST | `/api/v1/import/products` · `/inventory` · `/sales` |
| GET | `/api/v1/import/template/{type}?fmt=csv\|xlsx` |
| GET | `/api/v1/import/types` |

**Chiến lược transaction — query param `on_error`:**

| Giá trị | 4 dòng, 1 sai | Ghi được |
|---------|---------------|----------|
| `rollback` (mặc định) | báo lỗi từng dòng | **0 dòng** |
| `skip` | báo lỗi, import phần tốt | **2 dòng** |

Validate **toàn bộ trước**, ghi **sau**. Ghi từng dòng thì không có trạng thái "chưa ghi" để so sánh, và file hỏng ở dòng 9.001 sẽ để lại 9.000 dòng.

**Ràng buộc đọc file:**

| Tình huống | Mã |
|------------|-----|
| Đuôi không hỗ trợ (`.txt`) · file rỗng · quá 10 MB | 400 |
| `.csv` tên nhưng nội dung là Excel · `.xlsx` hỏng | 400 |
| Thiếu cột bắt buộc · đổi tên cột · >20.000 dòng · chỉ có header | 422 |
| `product_code` / lot / `order_code` trùng **DB** | 409, không ghi gì |
| Trùng **trong file** | 200 + báo lỗi theo dòng |

**`inventory` UNIQUE `(store_id, product_id, expiry_date)`** — phải kiểm trùng cả trong file lẫn với DB.

**Import sales gom dòng theo `order_code`:** 2 dòng cùng mã → 1 đơn 2 dòng chi tiết; không có mã → mỗi dòng 1 đơn riêng. `line_total` do DB tính, tổng đơn tính lại bằng `SUM`.

### 2.9 API Dashboard nâng cao (B8 — 12/10/2026)

6 endpoint bổ sung dưới `/api/v1/dashboard`. **121 check test, tất cả PASS. Read-only — không ghi gì vào DB.**

| Endpoint | Nội dung |
|----------|----------|
| `/revenue-by-store` | Doanh thu + số đơn + `avg_order_value` từng cửa hàng |
| `/revenue-by-category` | Doanh thu + số lượng + số SP từng nhóm hàng |
| `/top-stores?limit=5` | Xếp hạng cửa hàng theo doanh thu |
| `/inventory-value` | `total_value` (theo `unit_cost`) + `expiring_value` |
| `/waste-analysis` | Lô hết hạn / sắp hết hạn / ước lượng lãng phí |
| `/forecast-vs-actual` | MAPE/MAE/RMSE/bias của dự báo |

**Phát hiện quan trọng về view:** `v_daily_sales` có `GROUP BY store_id, order_date, product_id` là **vô nghĩa** — vì `order_items` UNIQUE `(order_id, product_id)` nên mỗi cặp chỉ có đúng 1 dòng. Đo được: **1.606 ms qua view vs 680 ms join thẳng**, kết quả khớp từng cent. B8 đã bỏ qua view.

| Endpoint | Trước | Sau |
|----------|-------|-----|
| `forecast-vs-actual` | 6.464 ms | **84 ms** |
| `revenue-by-category` | 8.616 ms | **4.087 ms** |
| `revenue-by-store` | 29 ms | 20 ms |

**⛔ `forecast-vs-actual` chưa tính được MAPE.** `forecasts` phủ 2018-01-01→01-30, dữ liệu bán hàng kết thúc 2017-12-31 → **không giao nhau**. API trả `mape: null` + `message` giải thích, không báo số bịa. **Phải nêu rõ khi viết Chương 4.**

**Filter ngày dùng kiểu `date`** (không phải `datetime`) và mốc dựng bằng `+07:00` — nên `?from_date=2017-01-01T00:00:00Z` bị **422** thay vì cắt mất 10 đơn.

**Lưu ý dữ liệu:** SP 13/28/45 chỉ có dự báo 9/10 cửa hàng; category "Food" không có sản phẩm nên không xuất hiện (7/8 nhóm).

### 2.10 Database — 10 bảng

Số dòng thực tế trong DB `spoilage_predictor`:

| Bảng | Số dòng | Mô tả |
|------|----------|-------|
| `categories` | 8 | Nhóm hàng |
| `stores` | 10 | Cửa hàng |
| `products` | 50 | Sản phẩm |
| `users` | 3 | Người dùng |
| `orders` | 18.260 | Đơn hàng (Kaggle 2013–2017) |
| `order_items` | 912.999 | Chi tiết đơn hàng |
| `inventory` | 1.330 | Tồn kho theo lô |
| `inventory_transactions` | 11.412 | Nhật ký biến động kho |
| `alerts` | 518 | Cảnh báo |
| `forecasts` | 3.000 | Kết quả dự báo (tạo ở M2) |

**Không có bảng `sales`.** Dữ liệu bán hàng nằm ở `orders` + `order_items`. Thuật ngữ "sales" trong tài liệu = hai bảng này trong schema.

Các thành phần khác: 6 trigger · 2 hàm · 4 view · 16 khóa ngoại.

### 2.11 AI/ML — kết quả M1 + M2 + M3

#### M1 — Đánh giá 3 mô hình trên 100 cặp (10 sản phẩm × 10 cửa hàng)

| Mô hình | RMSE | MAE | MAPE | Số cặp thắng |
|---------|------|-----|------|--------------|
| **Prophet** | **9,97** | **7,94** | **10,43%** | **97 / 100** |
| XGBoost | 10,98 | 8,77 | 11,69% | 3 / 100 |
| ARIMA | 20,20 | 16,44 | 23,77% | 0 / 100 |

XGBoost chỉ thắng 3 cặp: `(45,2)` · `(13,7)` · `(28,4)`. Ở 59 cặp chênh lệch < 1,0 RMSE — dưới 1 sản phẩm/ngày trên quy mô bán ~1.000/ngày.

#### M2 — Dự báo 30 ngày (01/01/2018 – 30/01/2018)

**3.000 dòng** trong bảng `forecasts` (100 cặp × 30 ngày, chỉ ghi model tốt nhất mỗi cặp).

| model_name | Số dòng |
|-----------|---------|
| prophet | 2.910 |
| xgboost | 90 |

#### M3 — Tài liệu đánh giá

`docs/05-tham-khao/ket-qua-danh-gia-model.md` — phương pháp đánh giá, bảng so sánh, 3 insight chính, các hạn chế.

### 2.12 10 sản phẩm dùng để huấn luyện

Đủ **7/7 nhóm hàng** · 100 cặp (sản phẩm × cửa hàng) · mỗi cặp đủ 365 ngày.

`product_id`: **[45, 8, 15, 13, 25, 11, 28, 48, 38, 18]**

| # | product_id | Sản phẩm | Nhóm hàng |
|---|-----------|----------|-----------|
| 1 | 45 | Khăn ướt trẻ em | Baby Care |
| 2 | 8 | Thịt bò | Fresh Food |
| 3 | 15 | Cà phê sữa đinh hương | Beverages |
| 4 | 13 | Nước suối 330ml | Beverages |
| 5 | 25 | Rượu dừa cơ | Beverages |
| 6 | 11 | Nước lọc 500ml | Beverages |
| 7 | 28 | Kẹo mút | Snacks |
| 8 | 48 | Kem đánh răng | Personal Care |
| 9 | 38 | Sữa tắm thể | Household |
| 10 | 18 | Sữa chua 500g | Dairy |

Tiêu chí chọn: doanh số năm cao nhất của **từng nhóm hàng**. **KHÔNG** dùng tiêu chí "hệ số biến động mùa vụ" — đã điều tra và chứng minh tiêu chí này không phân biệt được sản phẩm nào.

---

## 3. Đang làm gì

### Task đang dở

**Không có task nào đang dở dang.** B1 vừa hoàn thành xong, dừng tại mốc chờ duyệt.

### Trạng thái Git

| Mục | Trạng thái |
|-----|-----------|
| Commit cuối | `8e60e09` — docs: them CONTEXT-SUMMARY tom tat toan bo du an |
| Working tree | Sạch, khớp 100% với `origin/main` |
| Số commit từ đầu dự án | 24 |

Lịch sử commit gần đây:

```
8e60e09  docs: them CONTEXT-SUMMARY tom tat toan bo du an
7a95bbf  docs: cap nhat quyet dinh ve Chuong 2 + max_stock
47b4775  feat(ai): chay 100 cap, du bao 30 ngay, danh gia 3 mo hinh
8e392c6  docs: cap nhat tien do truoc khi ket thuc session
f46e479  docs: cap nhat tien do ngay 03/10/2026
aaec0c6  docs(agents): Add mandatory SQL rules
ea9e96e  D1: Add PostgreSQL schema with 10 tables
40020ca  T4.2: Chapter 2
f55dce4  T4.1: Chapter 1
31df9f7  T1+T3: README + architecture
```

---

## 4. Task tiếp theo

| Mã | Việc | Ưu tiên | Ghi chú |
|----|------|---------|---------|
| **F1** | Setup Frontend React + Vite + Tailwind | 🔴 Tiếp theo | CORS đã bật cho `:3000` và `:5173` |
| T4.3 | Viết Chương 3 — Thiết kế hệ thống | 🟡 TB | Cần kết quả M1–M3 làm căn cứ |
| T4.4 | Viết Chương 4 — Thực nghiệm | 🟡 TB | **BẮT BUỘC đọc mục 8j GHI-CHU-TIEN-DO.md trước** |
| T2 | README con cho từng thư mục | 🟢 Thấp | |

**Chưa có Chương 3 và Chương 4.** Đã đủ căn cứ từ M1–M3 + kiến trúc backend.

Còn 1 việc tồn đọng: `docs/03-thiet-ke/kien-truc-he-thong.md` mục 7 còn ghi 9 bảng (thiếu `stores`) và ghi `products` có `expiry_date` → lệch schema hiện tại.

---

## 5. Cảnh báo cần nhớ

### 5.1 Quy tắc bắt buộc (chung)

| # | Quy tắc |
|---|---------|
| 1 | KHÔNG dùng PHP, ASP.NET hoặc framework ngoài danh sách trong AGENTS.md |
| 2 | KHÔNG sửa `config.py`, `.env` mà không hỏi trước |
| 3 | Mọi API có prefix `/api/v1/` |
| 4 | Mọi truy vấn DB qua ORM — **không raw SQL trong routers** |
| 5 | File Python: `snake_case` · Component React: `PascalCase` · **Comment code Python dùng tiếng Anh không dấu** (tương thích cp1252). Tài liệu `.md` và SQL giữ tiếng Việt / ASCII |
| 6 | Trước khi commit chạy `git status` |
| 7 | 🔒 Không ghi mật khẩu vào bất kỳ file nào trong repo |
| 8 | Token Antigravity có giới hạn → **cần commit thường xuyên** |

### 5.2 SQL Rules

1. Kiểm tra cột đã tồn tại trong `CREATE TABLE` trước khi viết INDEX/VIEW/FUNCTION
2. KHÔNG tham chiếu cột không tồn tại — chỉ dùng cột của bảng trong đúng JOIN đó
3. **PHẢI test `psql -f file.sql` trước khi commit**
4. Lỗi thì sửa ngay, không để sang task khác
5. File SQL giữ **ASCII** (comment tiếng Anh) để chạy được trên Windows PowerShell
6. Tiếng Việt trong SQL → dùng **i18n key**, dịch ở `backend/app/i18n/vi.json`

⚠️ **KHÔNG chạy lại `database/01-schema/02-create-tables.sql`** khi DB đã có dữ liệu — file đó có `DROP TABLE ... CASCADE`. Dùng file trong `database/03-migrations/`.

### 5.3 Quyết định KHÔNG sửa

| # | Quyết định | Lý do |
|---|-----------|-------|
| 1 | **KHÔNG sửa Chương 2** | Chương 2 là cơ sở lý thuyết, chỉ *kỳ vọng* XGBoost là mô hình chính. Chương 4 trình bày kết quả thực: **Prophet thắng 97/100**. Dự đoán ≠ kết quả thực thể hiện **quá trình nghiên cứu khoa học** |
| 2 | **KHÔNG sửa `max_stock` trong seed** | Seed đặt `max_stock` 48–300 **độc lập với doanh số Kaggle** (thực tế 861–2.793/ngày) → 100/100 cặp bị cap khi tính `recommended_import_qty`. Đây là **hạn chế dữ liệu, không phải lỗi đồ án** |
| 3 | **Comment code Python dùng tiếng Anh không dấu** (chốt 12/10/2026) | Console Windows cp1252 không in được tiếng Việt có dấu → `UnicodeEncodeError`. Đồng nhất với 15 file Python đã viết · chuẩn quốc tế · thể hiện hiểu giới hạn môi trường. **Tài liệu `.md` và SQL giữ tiếng Việt / ASCII** theo quy tắc riêng |

→ **Khi viết Chương 4, phải trình bày cả 2 điểm này.** Chi tiết ở mục 8j `GHI-CHU-TIEN-DO.md`.

### 5.4 Bài học kỹ thuật

| # | Bài học |
|---|---------|
| 1 | **Prophet cần ≥ 2 năm dữ liệu** để ước lượng mùa vụ năm. 1 năm → RMSE 23,20; 5 năm → **9,97** (−57%), từ hạng 3 lên hạng 1. Nguyên nhân khiến Prophet kém là **thiếu dữ liệu, không phải tham số** |
| 2 | **Dữ liệu dài làm mô hình bám đảo hơn** — biến động RMSE giữa các bộ tham số giảm từ 10,5 lần (1 năm) xuống 8% (5 năm) |
| 3 | **Chọn tham số theo validation, KHÔNG theo test.** Tune trên test cho RMSE thấp hơn 0,47 nhưng đó là rò rỉ dữ liệu — con số báo cáo sẽ không còn trung thực |
| 4 | **Reindex chuỗi thời gian trước khi train.** View `v_daily_sales` chỉ có dòng cho ngày có giao dịch. Phải reindex đủ 1.826 ngày, ngày thiếu điền **0** — nếu không, hàm lag/rolling lệch ngày và mô hình học sai |
| 5 | **Tách tập theo mốc ngày `2017-10-01`, KHÔNG dùng 80/20.** 80/20 không bảo đảm test rơi vào một mùa cụ thể. Mốc cố định giúp test rơi vào Q4 — dễ giải thích và đúng nghiệp vụ |
| 6 | **`yearly_seasonality=True` chính là `fourier_order=10`.** 18 lần chạy chỉ cho 12 kết quả khác nhau |
| 7 | **Bảo vệ toàn vẹn dữ liệu thay vì nới ràng buộc.** 1 dòng `sales = 0` vi phạm `CHECK (quantity > 0)` → bỏ dòng, không sửa schema |
| 8 | **XGBoost phải dự báo đệ quy khi dự báo nhiều ngày.** Ngày N+1 dùng giá trị *dự báo* của ngày N cho đặc trưng lag. Dùng số thực tương lai → rò rỉ dữ liệu |
| 9 | **pandas 3.0**: `pd.DataFrame({"ds": <DataFrame>})` sẽ báo `ValueError: If using all scalar values, you must pass an index` — phải truyền **Series** |

### 5.5 Dữ liệu cần lưu ý

| # | Vấn đề | Xử lý |
|---|--------|-------|
| 1 | **Giá trong DB là MÔ PHỎNG** — Kaggle chỉ có cột `sales`, không có giá. Giá gán theo nhóm hàng chỉ để demo dashboard doanh thu | Mô hình chỉ dùng `quantity` nên không ảnh hưởng. **Không trình bày con số doanh thu như số liệu thật** |
| 2 | **Dataset là của Walmart (Hoa Kỳ)**, không phải Việt Nam | Ghi rõ trong Chương 1 |
| 3 | **Không có censored demand** — đã kiểm tra, 0 ngày bán bằng 0 | Chương 1–2 trình bày censored demand như vấn đề *lý thuyết*. Chương 4 phải nêu đây là **hạn chế của dataset Kaggle**. Không sửa Chương 1, 2 |
| 4 | **Mùa vụ không phân biệt được giữa các sản phẩm** — hệ số biến động theo tháng chỉ 1,85–1,95 (độ rộng 0,098) | Walmart mùa vụ theo thời tiết + ngày lễ, tác động đồng đều mọi mặt hàng |
| 5 | **`inventory_transactions` KHÔNG phải đầu vào dự báo** | Chỉ dùng cho phân tích tồn kho, cảnh báo hết hạn, FIFO. Đầu vào dự báo duy nhất là **`v_daily_sales`** (dựng từ `orders` + `order_items`) |
| 6 | **CSV 17MB không được commit** | Đã thêm `datasets/raw/*.csv` vào `.gitignore` |

### 5.6 Lỗi đã gặp — đừng lặp lại

| Lỗi | Nguyên nhân | Cách xử |
|-----|-------------|----------|
| `column p.store_code does not exist` | Trong view, `p` là alias của `products` nhưng `store_code` thuộc `stores` | Thêm `JOIN stores s` và dùng `s.store_code` |
| Seed chạy xong nhưng DB rỗng | Thiếu `COMMIT;` | Luôn kết thúc file SQL bằng `COMMIT;` |
| `UnicodeEncodeError: charmap` | Console Windows cp1252, không in tiếng Việt trong đường dẫn `Đồ án TN` | Thêm `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` |
| `ResourceClosedError` khi `RETURNING` | SQLAlchemy 2.x không hỗ trợ `RETURNING` với bulk insert | Insert không `RETURNING`, rồi `SELECT` lại theo `order_code` (UNIQUE) |
| Doanh thu báo 15.861 tỷ thay vì 317 tỷ | `SUM(orders.total_amount)` chạy trên `JOIN order_items` — mỗi đơn ~50 dòng nên nhân 50 lần | Tính từ `SUM(order_items.line_total)` |
| `duplicate key ... uq_inventory_store_product_expiry` | `LEAST(offset, shelf_life_days)` làm 3 lô của một cặp trùng ngày hết hạn | Suy `offset` trực tiếp từ `batch_no` |
| 383 cảnh báo `over_stock` thay vì ~51 | `(p*17+s*37)%100` không phân bố đều, và lượng bình thường 30–600 đã vượt `max_stock` 30–300 | Dùng `md5` cho bucket + tính lượng từ `max_stock`/`min_stock` |
| `ValueError: If using all scalar values...` (pandas 3.0) | Truyền cả DataFrame vào `pd.DataFrame({...})` | Truyền Series: `df["sale_date"]` |

### 5.7 Lệnh thường dùng

```powershell
# Git (PowerShell KHÔNG hỗ trợ &&)
git status --short; git add <file>; git commit -m "msg"; git push

# Database
$env:PGPASSWORD = "<mật khẩu trong .env>"
psql -U postgres -h localhost -d spoilage_predictor -v ON_ERROR_STOP=1 -f database/02-seed/seed-inventory.sql

# Kiểm tra dữ liệu
psql -U postgres -h localhost -d spoilage_predictor -c "SELECT count(*) FROM forecasts;"

# Xoá dữ liệu test (pgAdmin giữ session thì không DROP được)
psql -U postgres -h localhost -d spoilage_predictor -c "TRUNCATE alerts, forecasts, order_items, orders, inventory_transactions, inventory, products, categories, users, stores RESTART IDENTITY CASCADE;"

# ML
python scripts/check_ml_env.py
python ai-model/scripts/train_models.py --all
python ai-model/scripts/forecast_next_month.py --replace

# Backend — PHẢI cd backend trước
cd backend; python -m uvicorn app.main:app --reload --port 8000
# Test: http://localhost:8000/docs

# Frontend
cd frontend; npm run dev
```

### 5.8 Gotchas môi trường

| Vấn đề | Xử lý |
|--------|-------|
| PowerShell **KHÔNG hỗ trợ `&&`** | Dùng `;` |
| pgAdmin giữ session → `DROP DATABASE` bị lỗi | Dùng `TRUNCATE` |
| `.env` có thể chưa tồn tại | Tạo file `.env` ở thư mục gốc (đã có trong `.gitignore`) hoặc set `$env:DB_PASSWORD` |
| Python 3.14.7 chạy được đủ 3 mô hình | ✅ **KHÔNG cần lùi phiên bản** |
| ✅ Đã cài đủ thư viện backend | FastAPI · uvicorn · pydantic · pydantic-settings (12/10/2026) |
| **Chạy uvicorn phải `cd backend` trước** | Module import tuyệt đối `from app.config import settings`. Chạy từ thư mục gốc → `ModuleNotFoundError: No module named 'app'` |
| **FastAPI 0.143 đổi `include_router`** | `app.routes` chứa `_IncludedRouter` thay vì flatten endpoint. **Đừng kiểm tra `app.routes`** để xác nhận router — hãy gọi thật qua HTTP |
| File `.env` đã tạo ở **thư mục gốc** | Có trong `.gitignore` · backend **và script AI/ML** đều đọc từ đó → KHÔNG chuyển sang `backend/` sẽ phá vỡ script. Mẫu cấu hình cho người clone: `backend/.env.example` |
| **`CORS_ORIGINS` nhận cả 2 kiểu viết** | `CORS_ORIGINS=http://a:3000,http://b:5173` (dấu phẩy) **hoặc** `CORS_ORIGINS=["http://a:3000"]` (JSON). Dùng property **`settings.cors_origins_list`**. Khai báo `list[str]` chỉ chấp nhận JSON và sẽ báo `ValidationError` với dạng dấu phẩy — tức làm hỏng chính file `.env.example` của repo |
| **`CORS_ORIGINS=` rỗng → `[]`** | Fail-closed, chặn mọi origin. Muốn dùng 4 origin mặc định thì **xoá hẳn dòng** khỏi `.env`, đừng để trống |
| **Sequence ID trôi khỏi dữ liệu** | `TRUNCATE ... RESTART IDENTITY` rồi import lại bằng insert **chỉ định khóa chính** → PostgreSQL không tự đẩy sequence. Mọi INSERT sau đó đụng `duplicate key ... already exists`. Đã gặp với `products` (seq=2 vs max=50) → **đã sửa bằng `database/03-migrations/005-fix-sequences.sql`** (4 sequence sai: `users` `stores` `categories` `products`). Chạy file này sau mỗi lần import dữ liệu hàng loạt |
| **Lỗi sau `db.commit()` không rollback được** | `NameError` ở `db.refresh()` làm POST trả 500 nhưng bản ghi **đã được tạo**. Nếu test fail, kiểm tra dữ liệu thừa trước khi chạy lại |
| **Cổng 8000 dễ bị chiếm** | `Kill-Process` trước khi start lại, nếu không sẽ báo `[winerror 10048]` và test vẫn chạy vào code cũ |
| **FastAPI khớp route theo thứ tự khai báo** | Path đặc biệt phải khai **trước** path có tham số: `/alerts/unread` trước `/alerts/{alert_id}`, `/forecasts/latest` trước `/forecasts/{id}`, `/inventory/expiring` trước `/inventory/{id}`. Đảo thứ tự → `int` không parse được chuỗi → 422 |
| **`alerts.resolved_at` phải khớp `is_resolved`** | CHECK `chk_alert_resolved_at` yêu cầu `resolved_at` khác NULL khi và chỉ khi `is_resolved = TRUE`. Phải gán **cả hai cùng lúc** |
| Console Windows cp1252 | In chuỗi tiếng Việt ra terminal → `UnicodeEncodeError: charmap`. Thêm `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` |

---

## Tài liệu liên quan

| File | Vai trò |
|------|---------|
| `AGENTS.md` | Hướng dẫn AI: tech stack, quy tắc, môi trường, quyết định, tiến độ chi tiết |
| `GHI-CHU-TIEN-DO.md` | Ghi chú tiến độ chi tiết theo từng phiên, lịch sử lỗi, phân tích |
| `README.md` | Tài liệu chính dự án |
| `docs/04-timeline/CONTEXT-SUMMARY.md` | File này — bản tóm tắt ngắn |

**Khi chuyển sang máy hoặc AI mới:** đọc file này → đọc `AGENTS.md` → chạy `git status`.