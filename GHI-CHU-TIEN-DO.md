# Ghi chú tiến độ làm việc

> **Cập nhật:** 02/10/2026
> **Repo:** https://github.com/toan151007/supply-chain-spoilage-predictor
> **Giai đoạn:** Tuần 1 (05/10 – 16/10/2026)

---

## 1. Trạng thái tổng quan

| Hạng mục | Trạng thái | Ghi chú |
|----------|-------------|---------|
| Cấu trúc thư mục | ✅ Xong | 8 thư mục gốc + 30+ thư mục con |
| AGENTS.md | ✅ Xong | Tech stack, quy tắc, môi trường, tiến độ |
| T1 — README.md | ✅ Xong | 11 mục, commit `31df9f7` |
| T3 — Kiến trúc hệ thống | ✅ Xong | 4 sơ đồ Mermaid, commit `31df9f7` |
| T4.1 — Chương 1 | ✅ Xong | ~2.050 từ, 6 mục, commit `f55dce4` |
| T4.2 — Chương 2 | ✅ Xong | ~2.500 từ, 6 mục, commit `40020ca` |
| D1 — SQL Schema | ✅ Xong | 10 bảng, test thật, commit `ea9e96e` |
| Fix encoding SQL | ✅ Xong | Thuần ASCII, commit `48f4b4b` |
| i18n | ✅ Xong | `vi.json`, commit `9372a0d` |
| Quy tắc SQL | ✅ Xong | 6 quy tắc, commit `aaec0c6` |
| Dataset Kaggle | ✅ Đã tải | `datasets/raw/train.csv`, không commit |
| D2 — Seed data | ✅ Xong | categories 8, stores 10, products 50, users 3 |
| D3 — Import Kaggle | ✅ Xong | 3.650 orders + 182.500 order_items (năm 2017) |
| D4 — Seed inventory | ✅ Xong | 1.330 lô · 11.412 giao dịch · 518 cảnh báo |
| B1/B2 — Backend | ⬜ Chưa làm | FastAPI + kết nối DB |
| T2 — README con | ⬜ Chưa làm | |
| Frontend React | ⬜ Chưa làm | |
| AI Model | ⬜ Chưa làm | |

---

## 2. Lịch sử commit

```
aaec0c6  docs(agents): Add mandatory SQL rules
cebd8e7  fix(sql): Join stores in v_daily_sales
9372a0d  feat(i18n): Store i18n keys, add vi.json
48f4b4b  fix(sql): Convert SQL comments to English
ea9e96e  D1: Add PostgreSQL schema with 10 tables
40020ca  T4.2: Chapter 2
f55dce4  T4.1: Chapter 1
8245924  docs: progress notes
31df9f7  T1+T3: README + architecture
```

---

## 3. File đã tạo

| File | Mô tả |
|------|-------|
| `README.md` | Tài liệu chính dự án (11 mục) |
| `AGENTS.md` | Hướng dẫn AI + tiến độ |
| `GHI-CHU-TIEN-DO.md` | File này |
| `docs/03-thiet-ke/kien-truc-he-thong.md` | Kiến trúc, Use Case, Sequence, module, API, DB schema |
| `docs/02-bao-cao/chuong-1-tong-quan.md` | Chương 1 — Tổng quan đề tài |
| `docs/02-bao-cao/chuong-2-co-so-ly-thuyet.md` | Chương 2 — Cơ sở lý thuyết |
| `docs/05-tham-khao/giai-thich-comment-sql.md` | Đối chiếu comment SQL Anh ↔ Việt (20 mục) |
| `database/01-schema/02-create-tables.sql` | Schema 10 bảng + 6 trigger + 2 hàm + 4 view |
| `backend/app/i18n/vi.json` | Bản dịch thông báo cảnh báo (9 khóa) |

---

## 4. Quyết định thiết kế đã chốt

> **Không đổi các mục dưới đây** — sẽ phải sửa cả Chương 1 và Chương 2.

| Quyết định | Lý do |
|------------|-------|
| **10 bảng** (không có bảng `sales`) | Đã thêm `stores` để hỗ trợ chuỗi nhiều chi nhánh |
| **Dữ liệu bán hàng nằm ở `orders` + `order_items`** | Thuật ngữ "sales" trong tài liệu = `orders` + `order_items` trong schema |
| **`expiry_date` ở `inventory` + `inventory_transactions`** | Hạn sử dụng thuộc về *lô hàng tại cửa hàng*, không phải thuộc tính sản phẩm |
| **`CHECK` thay vì PG `ENUM`** | Dễ migrate, tương thích SQLAlchemy ORM |
| **`NUMERIC` cho mọi số lượng, `TIMESTAMPTZ` cho mọi thời gian** | Tránh sai số làm lệch tồn kho, tránh lệch múi giờ |
| **SQL giữ ASCII, tiếng Việt qua i18n key** | `psql -f` chạy được trên Windows; dễ thêm ngôn ngữ |
| Prophet = cơ sở, XGBoost = chính, ARIMA + trung bình động = đối chứng | Chương 2 đã phân tích chi tiết |
| **KHÔNG dùng LSTM** trong hệ thống | Dữ liệu quy mô nhỏ, chỉ trình bày lý thuyết |
| AI Agent dùng **grounding** | Lấy context từ DB → giảm tình trạng mô hình "bịa" số liệu |
| **KHÔNG commit file CSV 17MB** | Giữ repo nhẹ, tránh giới hạn 100MB của GitHub |

---

## 5. Môi trường đã kiểm chứng

| Thành phần | Thông tin |
|------------|-----------|
| Python | 3.14.7 · pip 26.2.1 |
| pandas | 3.0.6 |
| numpy | 2.5.3 |
| SQLAlchemy | 2.1.2 |
| psycopg2-binary | 2.9.13 |
| Node.js | v24.15.0 · npm 11.12.1 |
| PostgreSQL | 18.6 · service `postgresql-x64-18` · port 5432 |
| statsmodels | 0.15.0 (ARIMA) |
| scikit-learn | 1.9.1 |
| XGBoost | 3.4.1 |
| Prophet | 1.4.0 (kèm CmdStan 2.37.0) |
| Database | `spoilage_predictor` · 10 bảng |
| Xác thực | `scram-sha-256` |

✅ Python 3.14.7 chạy được đủ 3 mô hình — **không cần lùi phiên bản**.
**Còn thiếu:** `fastapi`, `uvicorn`, `pydantic` (cho backend B1).

**Dữ liệu trong DB (03/10/2026):** categories 8 · stores 10 · products 50 · users 3 · **orders 18.260** · **order_items 912.999** (2013–2017) · inventory 1.330 · inventory_transactions 11.412 · alerts 518 · **forecasts 0 (đang xây)**

🔒 **Mật khẩu database nằm trong `.env` cục bộ — KHÔNG ghi vào repo này.**

---

## 6. Dataset Kaggle

| Mục | Nội dung |
|-----|----------|
| Nguồn | Walmart Store Sales - Time Series Forecasting |
| Link | https://www.kaggle.com/competitions/demand-forecasting-kernels-only |
| File | `datasets/raw/train.csv` — 913.000 dòng dữ liệu (913.001 dòng gồm header) |
| Cột | `date, store, item, sales` — **không có cột giá** |
| Kích thước | 50 items (id 1–50), 10 stores (id 1–10) |
| Giai đoạn | 2013-01-01 → 2017-12-31 (test set bắt đầu 2018-01-01) |
| Trong git | ❌ Không commit — đã thêm `datasets/raw/*.csv` vào `.gitignore` |

---

## 7. Kết quả test D1 (đã xác minh)

Schema chạy sạch trên PostgreSQL 18.6:

| Kiểm tra | Kết quả |
|----------|---------|
| Số bảng | 10/10 ✓ |
| Khoá ngoại | 16 quan hệ ✓ |
| Encoding | 0 ký tự non-ASCII, không BOM ✓ |
| Cột GENERATED `line_total` | `2.5 × 35000 × 0.9 = 78750.00` ✓ |
| View `v_daily_sales` | Trả đúng `store_code`, `store_name`, `product_name` ✓ |
| Hàm `fn_generate_inventory_alerts()` | Sinh 2 cảnh báo đúng loại ✓ |
| Chống trùng (gọi lần 2) | 0 dòng ✓ |
| 3 view còn lại | Trả dữ liệu đúng ✓ |

Dữ liệu test đã `TRUNCATE`, DB sẵn sàng cho seed.

---

## 8. Việc còn lại

| Mã | Task | Ưu tiên |
|----|------|---------|
| ~~D2~~ | ✅ Seed: categories 8, stores 10, products 50, users 3 | Xong |
| ~~D3~~ | ✅ Import Kaggle 2017 → 3.650 orders + 182.500 order_items | Xong |
| **D4** | Seed `inventory` + `inventory_transactions` | ✅ Xong — xem mục 8d |
| D5 | Chạy lại `fn_generate_inventory_alerts()` | ✅ Xong (đã gọi trong seed-inventory.sql) |
| **M1** | Train 3 mô hình (Prophet / XGBoost / ARIMA) — 100 cặp | 🔴 Đang làm |
| **M2** | Dự báo 30 ngày + ghi vào bảng `forecasts` | 🔴 Chờ M1 |
| B1 | Setup backend FastAPI | 🟡 TB |
| B2 | Kết nối backend với database (SQLAlchemy) | 🟡 TB |
| T2 | README con cho từng thư mục | 🟢 Thấp |
| F1 | Setup Frontend React | 🟢 Thấp |
| M1 | Huấn luyện AI Model | 🟢 Thấp |

### Thứ tự seed + import (đã chốt)

```
1. categories  (8 nhóm)
2. products    (50 sản phẩm, id 1-50  ← khớp Kaggle item)
3. stores      (10 cửa hàng, id 1-10  ← khớp Kaggle store)
        ↓
4. Import Kaggle 2017 → orders + order_items
        ↓
5. inventory + inventory_transactions + users (seed)
        ↓
6. forecasts + alerts (chạy hàm sinh cảnh báo)
```

**Bắt buộc:** seed `products` và `stores` **trước**, vì `order_items.product_id` và `orders.store_id` là khoá ngoại — import trước sẽ vi phạm ràng buộc toàn vẹn.

---

## 8b. Chi tiết import dataset (D3)

**Script:** `scripts/import_kaggle.py`

```bash
python scripts/import_kaggle.py --year 2017 --dry-run   # xem trước
python scripts/import_kaggle.py --year 2017             # import thật
python scripts/import_kaggle.py --year 2016 --unit-price 25000
```

| Thông số | Giá trị |
|----------|---------|
| Nguồn | `datasets/raw/train.csv` (913.000 dòng, 2013-01-01 → 2017-12-31) |
| Lọc | Năm 2017 → 182.500 dòng |
| `orders` | 3.650 (mỗi cặp ngày × cửa hàng = 1 đơn) |
| `order_items` | 182.500 |
| `order_code` | `ORD-2017-000001` … `ORD-2017-003650` |
| Tổng số lượng | 10.733.740 |
| Độ phủ | 50 sản phẩm · 10 cửa hàng · 365 ngày |
| **Đối chiếu CSV** | ✅ Khớp chính xác 182.500 dòng / 10.733.740 |
| **Tổng doanh thu** | **317.233.060.000 VND** ⚠️ *từ giá mô phỏng, không phải số liệu thật* |

### ⚠️ Giá là MÔ PHỎNG — bắt buộc nêu trong Chương 4

Dataset Kaggle **chỉ có số lượng, không có cột giá**. Script tự gán giá theo nhóm hàng để dashboard doanh thu chạy được:

| Nhóm hàng | `category_id` | Giá mô phỏng |
|-----------|---------------|--------------|
| Đồ uống | 3 | 15.000đ |
| Rau củ, trái cây | 2 (id 1–6) | 20.000đ |
| Bánh kẹo | 4 | 25.000đ |
| Tạp hóa / cá nhân / trẻ em | 5, 6, 7 | 30.000đ |
| Sữa, phô mai | 8 | 35.000đ |
| Thịt, cá, trứng | 2 (id 7–10) | 80.000đ |

`category_id = 2` chứa cả rau củ lẫn thịt cá → tách nhỏ theo `product_id`.

**Khi viết báo cáo phải ghi rõ:**
1. Dataset gốc là của **Walmart (Hoa Kỳ)**, không phải Việt Nam
2. Con số doanh thu 317 tỷ VND là **tính từ giả định mô phỏng**, không phải doanh thu thật
3. Giá chỉ phục vụ **demo giao diện**, mô hình dự báo chỉ dùng `quantity` nên không phụ thuộc giá

**Cách ánh xạ:** `products.product_id` 1–50 ← Kaggle `item`; `stores.store_id` 1–10 ← Kaggle `store`. Seed data dùng **id tường minh** nên không cần bảng mapping.

**Kết quả chạy:** `orders` và `order_items` nằm trong cùng transaction (`engine.begin()`) — nếu lỗi giữa chừng thì rollback hết, không để lại dữ liệu nửa vời.

---

## 8c. ⚠️ Lỗi đã gặp — đừng lặp lại

| Lỗi | Nguyên nhân | Cách xử lý |
|-----|-------------|-------------|
| `column p.store_code does not exist` | Trong view, `p` là alias của `products` nhưng `store_code` thuộc bảng `stores` | Thêm `JOIN stores s` và dùng `s.store_code` |
| Seed chạy xong nhưng DB vẫn rỗng | **Thiếu `COMMIT;`** — query kiểm tra nằm trong transaction nên thấy dữ liệu, nhưng `psql` thoát là rollback | Luôn kết thúc file SQL bằng `COMMIT;` |
| `UnicodeEncodeError: charmap` | Console Windows dùng cp1252, không in được ký tự tiếng Việt trong đường dẫn `Đồ án TN` | Thêm `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` |
| `ResourceClosedError` khi `RETURNING` | SQLAlchemy 2.x không hỗ trợ `RETURNING` với bulk insert | Insert không `RETURNING`, rồi `SELECT` lại theo `order_code` (UNIQUE) để lấy `order_id` |
| `KeyError: 1` | `code_to_id` khoá theo `order_code` (string) nhưng code truy cập bằng `_tmp_key` (int) | Thêm bảng trung gian `key_to_code` |
| `pip list` bỏ sót thư viện | Lọc bằng `Select-String` chỉ trả về một phần output | Kiểm tra bằng `python -c "import X; print(X.__version__)"` |
| Doanh thu báo **15.861 tỷ** thay vì 317 tỷ | `SUM(orders.total_amount)` chạy trên `JOIN order_items` — mỗi đơn có ~50 dòng chi tiết nên tổng bị nhân 50 lần | Tính từ `SUM(order_items.line_total)`, hoặc query `orders` riêng không join |
| `syntax error at or near "TRUE"` | `CROSS JOIN LATERAL (...) ON TRUE` — `CROSS JOIN` không nhận mệnh đề `ON` | Bỏ `ON TRUE` |
| `syntax error at or near "CASE"` | Lateral subquery phải có `SELECT` bao quanh, không thể để `CASE` trần | Viết `CROSS JOIN LATERAL (SELECT CASE ... END AS x)` |
| `duplicate key ... uq_inventory_store_product_expiry` | `LEAST(offset, shelf_life_days)` làm cả 3 lô của một cặp trùng ngày hết hạn | Suy `offset` trực tiếp từ `batch_no` để luôn khác nhau |
| `duplicate key ... uq_transactions_reference` | `import` và `disposal` cùng dùng `reference_type='manual'` + `reference_id=inventory_id` | Dùng `inventory_id` âm cho `disposal` để tách không gian khoá |
| 383 cảnh báo `over_stock` thay vì ~51 | `(p*17 + s*37) % 100` không phân bố đều, **và** lượng bình thường 30–600 đã vượt `max_stock` 30–300 | Dùng `md5` cho bucket + tính lượng bình thường từ `max_stock`/`min_stock` |

---

## 8d. Chi tiết seed inventory (D4)

**File:** `database/02-seed/seed-inventory.sql` (chạy **sau** `seed-data.sql`)

```powershell
psql -U postgres -d spoilage_predictor -v ON_ERROR_STOP=1 -f database/02-seed/seed-inventory.sql
```

### Kết quả

| Bảng | Số dòng |
|------|---------|
| `inventory` | **1.330** |
| `inventory_transactions` | **11.412** (import 1.330 · export 10.000 · disposal 82) |
| `alerts` | **518** |

### Kịch bản đã tạo có chủ đích

| Kịch bản | Tỷ lệ | Thực tế | Mục đích |
|----------|--------|----------|----------|
| Lô đã hết hạn | ~5% | **6,2%** (82 lô) | Cảnh báo `expired` |
| Lô sắp hết hạn | ~15% | **24,7%** (328 lô) | Cảnh báo `expiring_soon` |
| Tồn kho thấp | ~8% cặp | **57 cảnh báo** | Cảnh báo `low_stock` |
| Tồn kho cao | ~8% cặp | **51 cảnh báo** | Cảnh báo `over_stock` |

⚠️ **Vì sao "sắp hết hạn" là 24,7% chứ không phải 15%?** Vì sản phẩm hạn ngắn (thịt gà 2 ngày, rau muống 3 ngày) **về mặt vật lý không thể** có hạn sử dụng xa hơn 7 ngày. Kịch bản "bình thường" của chúng rơi vào khoảng ≤7 ngày một cách tự nhiên. Đây là hệ quả đúng với thực tế, không phải lỗi.

### Cảnh báo sinh ra

| Loại | Mức độ | Số lượng |
|------|--------|----------|
| `expired` | critical | 82 |
| `expiring_soon` | high | 116 |
| `expiring_soon` | medium | 212 |
| `low_stock` | high | 57 |
| `over_stock` | medium | 51 |

Cột `title` chứa đúng **key i18n**: `alert.title.EXPIRED`, `alert.title.EXPIRING_SOON`, `alert.title.LOW_STOCK`, `alert.title.OVER_STOCK`.

### ⚠️ Dữ liệu MÔ PHỎNG — không phải lịch sử thật

`inventory_transactions` ở đây là **dữ liệu demo tự sinh**, KHÔNG phải lịch sử kho thật, và **không liên quan đến doanh số Kaggle**. Lịch sử bán hàng thật nằm ở `orders` + `order_items`.

**Mô hình dự báo phải lấy dữ liệu từ `v_daily_sales`** (đọc `orders`/`order_items`), không dùng bảng này.

### Nguyên tắc thiết kế

| Nguyên tắc | Giải thích |
|------------|------------|
| Không dùng `random()` | Mọi giá trị suy ra từ `md5(product_id, store_id, batch_no)` → chạy lại cho kết quả giống hệt |
| Số lô theo hạn sử dụng | Hạn ≤3 ngày → 1 lô · ≤10 ngày → 2 lô · còn lại → 3 lô. Cửa hàng không giữ 3 lô rau muống cùng hạn |
| Offset hết hạn theo `batch_no` | `-1,-2,-3` hoặc `1,2,3` hoặc `shelf-1,shelf-2,shelf-3` → luôn khác nhau, tránh vi phạm `UNIQUE (store_id, product_id, expiry_date)` |
| Kịch bản quyết ở mức **cặp** (sản phẩm × cửa hàng) | Quy tắc cảnh báo so sánh **TỔNG** tồn kho với `min_stock`/`max_stock`. Nếu tính ở mức lô thì 3 lô bình thường luôn vượt ngưỡng và không cảnh báo nào bắn |
| Lượng bình thường bám `max_stock` | `q = max(45% × max_stock, 150% × min_stock) / số lô`. Dùng khoảng ngẫu nhiên phẳng (10–200/lô) sẽ cho tổng 30–600, vượt `max_stock` (30–300) ở hầu hết cặp → 383 cảnh báo `over_stock` thay vì 51 |
| `disposal` dùng `inventory_id` âm | Tách không gian khoá khỏi giao dịch `import` (cùng `reference_type='manual'`) |

---

## 8e. Fix mâu thuẫn "nguồn dữ liệu dự báo"

**Vấn đề:** Comment gốc trong schema mô tả `inventory_transactions` là *"bảng quan trọng nhất cho mô hình dự báo"* và *"nguồn dữ liệu chính cho mô hình dự báo"*. Điều này **sai** sau quyết định Hướng B.

**Đã sửa:**

| Đối tượng | Trước | Sau |
|-----------|-------|-----|
| `inventory_transactions` | *"Stock import/export history - main data source for the demand forecasting model"* | *"Stock movement audit trail - used for stock analysis, expiry alerts and FIFO. NOT the demand forecasting input."* |
| `v_daily_sales` | *"input data for the demand forecasting model"* | *"PRIMARY data source for the demand forecasting model... Built from orders + order_items"* |

**Files đã sửa:**

| File | Nội dung sửa |
|------|--------------|
| `database/01-schema/02-create-tables.sql` | Header bảng 6 + 2 `COMMENT ON` + comment chỉ mục |
| `docs/05-tham-khao/giai-thich-comment-sql.md` | Bảng dịch mục 9 + `v_daily_sales` + thêm mục 0 giải thích |
| `database/03-migrations/004-fix-comments.sql` | **Mới** — migration chỉ chứa `COMMENT ON` |

### ⚠️ Vì sao tạo migration thay vì chạy lại schema

`01-schema/02-create-tables.sql` bắt đầu bằng `DROP TABLE ... CASCADE`. Chạy lại sẽ **xóa toàn bộ dữ liệu** đã seed và import. Migration 004 chỉ chứa `COMMENT ON` — thuần metadata, không thể mất dữ liệu.

**Đã kiểm chứng số dòng trước / sau migration — không đổi:**

```
Trước: inventory=1330 trans=11412 orders=3650 items=182500 products=50 alerts=518
Sau:  inventory=1330 trans=11412 orders=3650 items=182500 products=50 alerts=518
```

Backup trước khi làm: `pg_dump` ra thư mục temp (14,7 MB), không đưa vào repo.

### Chương 2 không cần sửa

Đã tìm toàn bộ Chương 2 (439 dòng): `inventory_transactions` → **0 lần**, `sales` → **0 lần**. Chương 2 là tài liệu lý thuyết, không nhắc tên bảng.

### Bảng phân công vai trò (nhớ để viết Chương 3/4)

| Đối tượng | Vai trò |
|-----------|---------|
| `orders` + `order_items` | Lịch sử bán hàng thật |
| **`v_daily_sales`** | **Đầu vào DUY NHẤT cho mô hình dự báo** |
| `inventory` | Tồn kho hiện tại theo lô |
| `inventory_transactions` | Nhật ký biến động — phân tích tồn kho, cảnh báo hết hạn, FIFO. **KHÔNG** dùng để dự báo |

---

## 8f. Chọn 10 sản phẩm huấn luyện (đã chốt)

`product_id`: **[45, 8, 15, 13, 25, 11, 28, 48, 38, 18]**

### ⚠️ Lỗi tôi đã mắc phải và cách sửa

Tôi từng đề xuất 3 sản phẩm bổ sung là **13, 25, 22** mà **không hề kiểm tra** xem chúng có thực sự nằm trong top HS_tuần của nhóm Beverages hay không. Khi chạy `scripts/confirm_products.py` mới phát hiện:

| Đề xuất của tôi | HS_tuần | Hạng thật |
|-----------------|----------|-----------|
| 13 | 1,971 | hạng 3 ✅ đúng |
| 25 | 1,955 | hạng 4 ❌ |
| 22 | 1,919 | **hạng 10/11** ❌ sai rõ ràng |

**Bài học:** đề xuất phải kèm bằng chứng kiểm chứng, không được dựa vào cảm tính.

### Kết luận điều tra mùa vụ

Tiêu chí "hệ số biến động mùa vụ" **không dùng được** để chọn sản phẩm:

| Mức đo | Hệ số | Độ rộng giữa 50 sản phẩm |
|--------|-------|--------------------------|
| Theo tháng | 1,85 – 1,95 | **0,098** → không phân biệt được |
| Theo tuần | 1,88 – 2,03 | 0,153 → phân biệt rất yếu |
| Theo ngày trong tuần | 1,52 | yếu hơn mùa vụ tháng |

**Lý do:** mùa vụ Walmart chạy theo thời tiết và ngày lễ quốc gia, tác động **đồng đều lên mọi mặt hàng**. Không sản phẩm nào "mùa vụ riêng" hơn sản phẩm khác.

### Tiêu chí thay thế đã dùng

1. Loại sản phẩm doanh số năm < 1.000
2. Chọn sản phẩm doanh số cao nhất của **từng nhóm** → đủ 7/7 nhóm hàng
3. Bổ sung để đủ 10, ưu tiên doanh số cao

Lý do bỏ tiêu chí HS_tuần: chênh lệch HS giữa các sản phẩm **< 4%**, trong khi chênh lệch doanh số lên tới **3 lần** (105k vs 346k). Doanh số quan trọng hơn nhiều.

### Độ phủ dữ liệu — rất tốt

| Kiểm tra | Kết quả |
|----------|---------|
| Số cặp (sản phẩm × cửa hàng) | **100 / 100** đủ |
| Số ngày mỗi cặp | **365 / 365** — không thiếu ngày nào |
| Lượng nhỏ nhất 1 cặp | 14.759 sản phẩm/năm |
| Ngày bán = 0 | **0** → không có censored demand |

### ⚠️ Censored demand — cần nêu rõ trong Chương 4

Chương 1 và 2 trình bày censored demand như vấn đề **lý thuyết**. Dữ liệu Kaggle **không có** hiện tượng này (0 ngày bán = 0).

**Cách trình bày trong Chương 4:** *"Trong dữ liệu thực tế, không xảy ra censored demand. Đây là hạn chế của dataset Kaggle so với dữ liệu bán lẻ thực tế, nơi hiện tượng này có thể xảy ra."*

**Không sửa Chương 1, 2** — đó là nội dung lý thuyết chung, đúng và cần giữ.

### Files liên quan

| File | Vai trò |
|------|---------|
| `scripts/check_ml_env.py` | Kiểm tra môi trường ML |
| `scripts/select_products.py` | Chọn theo HS mùa vụ (tiêu chí ban đầu — không dùng) |
| `scripts/investigate_selection.py` | Điều tra vì sao tiêu chí không phân biệt được |
| `scripts/selection_options.py` | Tính 2 phương án chọn |
| `scripts/confirm_products.py` | Kiểm chứng danh sách cuối + độ phủ dữ liệu |

---

## 8g. Công việc ngày 03/10/2026

### 1. Import lại dataset Kaggle — 5 năm (2013–2017)

Trước đó chỉ import năm 2017 (365 ngày). Vì Prophet cảnh báo *"Yearly seasonality is enabled with less than 730 days"*, đã import lại **toàn bộ 5 năm**.

**Cách chạy:**
```powershell
python scripts/import_kaggle.py --all-years
```

| Chỉ số | CSV | Database |
|--------|-----|----------|
| Số dòng | 912.999 (sales > 0) | **912.999** ✅ |
| Tổng số lượng | 47.704.512 | **47.704.512** ✅ |
| Số ngày | 1.826 | **1.826** ✅ |
| Cửa hàng / sản phẩm | 10 / 50 | **10 / 50** ✅ |
| `orders` | — | 18.260 |
| Doanh thu (giá giả lập) | — | 1.409.611.790.000 VND |

**Lỗi gặp phải:** bảng `order_items` có ràng buộc `CHECK (quantity > 0)`, nhưng CSV có **1 dòng** năm 2014 với `sales = 0` (product 4, store 6, ngày 15/01/2014). Đã **bỏ dòng đó** thay vì nới ràng buộc — vì `sales = 0` nghĩa là hôm đó không bán được mặt hàng đó, không phải lỗi dữ liệu. Script giờ in rõ số dòng bỏ qua.

Hệ quả: cặp (product 4, store 6) thiếu 1 ngày trong chuỗi. Đã xử lý bằng cách reindex (mục 2).

### 2. Sửa `train_models.py` cho dữ liệu 5 năm

| Thay đổi | Chi tiết |
|----------|----------|
| Đọc dữ liệu | Toàn bộ 2013–2017 thay vì chỉ 2017 |
| **Reindex chuỗi** | Đủ 1.826 ngày liên tục, ngày thiếu điền **0**. Đây có thể là ngày không bán được mặt hàng → là trường hợp censored demand |
| Tách tập | Theo **mốc ngày `2017-10-01`** (không dùng 80/20): train 1.734 ngày · test 92 ngày |
| Tham số Prophet | `PROPHET_PARAMS` tách thành hằng số ở đầu file |

**Log mỗi cặp:** in số ngày có `y = 0` và số ngày bị điền 0, để báo cáo trung thực.

### 3. Kiểm chứng giả thuyết mùa vụ năm — KẾT QUẢ MẠNH NHẤT

Đây là phát hiện quan trọng nhất của ngày 03/10.

| Mô hình | RMSE với 1 năm | RMSE với 5 năm | Cải thiện |
|---------|----------------|----------------|-----------|
| **Prophet** | 23,20 | **9,98** | **−57%** |
| XGBoost | 16,47 | 10,91 | −34% |
| ARIMA | 19,36 | 18,36 | −5% |

**Thứ hạng đã đảo ngược:**

| | 1 năm | 5 năm |
|---|-------|-------|
| Thứ nhất | XGBoost (16,47) | **Prophet (9,98)** |
| Thứ hai | ARIMA (19,36) | XGBoost (10,91) |
| Thứ ba | Prophet (23,20) | ARIMA (18,36) |

→ Prophet đi từ **hạng 3** lên **hạng 1** chỉ nhờ thêm dữ liệu, **không đổi tham số**.

Nếu không kiểm tra cảnh báo của Prophet và cứ giữ 1 năm, đồ án sẽ kết luận sai rằng Prophet không phù hợp với bài toán này.

### 4. Tune lại Prophet trên 5 năm

**Cách chạy:** `python ai-model/scripts/tune_prophet.py --product 15 --store 1` (18,5 giây)

| Cách chọn | cps | mode | yearly | RMSE_val | RMSE_test |
|-----------|-----|------|--------|----------|-----------|
| **Theo validation (đúng)** | **0,01** | **multiplicative** | **20** | **10,49** | **10,23** |
| Theo test (rò rỉ dữ liệu) | 0,5 | additive | True/10 | 11,47 | 9,76 |
| Bộ đã tune trên 1 năm | 0,01 | additive | 20 | 10,60 | 9,92 |

**Đã chọn theo validation.** Không chọn theo test dù cho RMSE tốt hơn 0,47 — chọn bằng tập đánh giá là rò rỉ dữ liệu, con số báo cáo sẽ không còn trung thực.

#### Prophet đã bám đảo tham số khi đủ dữ liệu

| Mức | 1 năm | 5 năm |
|-----|-------|-------|
| RMSE thấp nhất | 23,20 | 9,76 |
| RMSE cao nhất | 243,27 | 10,51 |
| **Độ biến động** | **10,5 lần** | **chỉ 8%** |

`changepoint_prior_scale = 0.5` từng gây RMSE 243,27, giờ chỉ 9,76. Dữ liệu dài giúp xu hướng được ước lượng tốt hơn.

### 5. Files đã tạo / sửa

| File | Nội dung |
|------|----------|
| `ai-model/scripts/train_models.py` | Hỗ trợ 5 năm, reindex, tách theo mốc ngày, CSV phẳng |
| `ai-model/scripts/tune_prophet.py` | Grid search 18 bộ, tách rõ validation vs test |
| `scripts/import_kaggle.py` | Thêm cờ `--all-years` |
| `ai-model/outputs/prophet_tuning_p15_s1.csv` | 18 bộ trên **1 năm** (đối chiếu) |
| `ai-model/outputs/prophet_tuning_5y_p15_s1.csv` | 18 bộ trên **5 năm** |
| `ai-model/outputs/model_metrics_p15_s1.csv` | Kết quả test 1 cặp |

### 6. Bài học quan trọng

1. **Prophet cần ≥ 2 năm dữ liệu để ước lượng mùa vụ năm.** Chỉ có 1 năm thì mô hình không biết mùa vụ lặp lại thế nào — đây là nguyên nhân gốc khiến Prophet kém hơn, **không phải do tham số**.
2. **Dữ liệu dài làm mô hình bám đảo hơn.** Biến động RMSE giữa các bộ tham số giảm từ 10,5 lần xuống 8%.
3. **Chọn tham số theo validation, không theo test.** Dù chọn theo test cho số đẹp hơn, đó là rò rỉ dữ liệu.
4. **`yearly_seasonality=True` chính là `fourier_order=10`.** 18 lần chạy chỉ cho 12 kết quả khác nhau — xác nhận bằng dữ liệu, không phải giả định.
5. **Bảo vệ sự toàn vẹn dữ liệu thay vì nới ràng buộc.** 1 dòng `sales = 0` vi phạm `CHECK (quantity > 0)` → bỏ dòng, không đổi schema.

### 7. Trạng thái hiện tại — DỪNG LẠI

| Việc | Trạng thái |
|------|------------|
| Import 5 năm | ✅ Xong |
| Sửa script cho 5 năm | ✅ Xong |
| Tune Prophet trên 5 năm | ✅ Xong |
| Test 1 cặp | ✅ Xong |
| **Chạy 100 cặp** | ⏸ **CHỜ DUYỆT** |
| **Dự báo 30 ngày (01/01–30/01/2018)** | ⏸ Chờ |
| **Ghi vào bảng `forecasts`** | ⏸ Chờ |
| Tài liệu đánh giá model | ⏸ Chờ |

Ước tính chạy 100 cặp: **~9 phút** (5,4 giây/cặp).

---

## 9. ⚠️ Việc cần tra cứu / xác minh

Không gấp, nhưng **bắt buộc làm trước khi nộp báo cáo**:

- [ ] **Đối chiếu trích dẫn Chương 2 [5]–[8]** với bản gốc: số tạp, số trang, năm
- [ ] **Mục 2.4** hiện là "hướng nghiên cứu" chưa gắn bài báo cụ thể
- [ ] **Số liệu lãng phịch thực phẩm Việt Nam** — đang để `(cần bổ sung)`
- [ ] **Tên trường / khoa** trong Chương 1 và phần tác giả
- [ ] **Khả năng cung cấp dữ liệu thực tế** — hiện đang dùng dataset Kaggle (Mỹ), cần ghi rõ trong Chương 1
- [ ] **Danh mục tài liệu tham khảo đầy đủ** ở phần cuối báo cáo
- [x] **Cân nhắc sửa Chương 2** — ✅ Đã kiểm tra: Chương 2 **không nhắc tên bảng nào** (0 lần `inventory_transactions`, 0 lần `sales`), nên không cần sửa. Mâu thuẫn thật nằm ở comment SQL, đã sửa qua migration 004 — xem mục 8e

---

## 10. Cần quyết định (chưa làm)

| Việc | Vấn đề |
|------|--------|
| **Thuật ngữ trong Chương 2** | Tài liệu nhắc bảng `sales`, schema dùng `orders` + `order_items`. Cần sửa Chương 2 cho nhất quán, hoặc thêm bảng `sales` |
| ~~`unit_price = 0` trong import~~ | ✅ **Đã xử lý** — chuyển sang gán giá mô phỏng theo nhóm hàng (mục 8b) |
| **`docs/03-thiet-ke/kien-truc-he-thong.md` mục 7** | Đang ghi 9 bảng, chưa có `stores`, còn ghi `products` có `expiry_date` → lệch với schema hiện tại |

---

## 11. Lệnh thường dùng

```powershell
# Git (PowerShell KHÔNG hỗ trợ &&)
git status --short; git add <file>; git commit -m "msg"; git push

# Database
$env:PGPASSWORD = "<mat khau trong .env>"
psql -U postgres -h localhost -c "CREATE DATABASE spoilage_predictor;"
psql -U postgres -h localhost -d spoilage_predictor -v ON_ERROR_STOP=1 -f database/01-schema/02-create-tables.sql

# Kiểm tra dữ liệu
psql -U postgres -h localhost -d spoilage_predictor -c "SELECT count(*) FROM orders;"

# Xoá dữ liệu test (pgAdmin giữ session thì không DROP được)
psql -U postgres -h localhost -d spoilage_predictor -c "TRUNCATE alerts, forecasts, order_items, orders, inventory_transactions, inventory, products, categories, users, stores RESTART IDENTITY CASCADE;"

# Backend
cd backend; uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend; npm run dev
```

---

## 12. Quy tắc bắt buộc

**SQL** (xem `AGENTS.md:46-53`):
1. Kiểm tra cột tồn tại trong `CREATE TABLE` trước khi viết INDEX/VIEW/FUNCTION
2. Không tham chiếu cột không tồn tại
3. **Phải test `psql -f` trước khi commit**
4. Lỗi thì sửa ngay, không để sang task khác
5. File SQL giữ ASCII
6. Tiếng Việt trong SQL → dùng i18n key

**Chung:**
7. KHÔNG dùng PHP, ASP.NET hoặc framework ngoài danh sách trong AGENTS.md
8. KHÔNG sửa `config.py`, `.env` mà không hỏi trước
9. Mọi API có prefix `/api/v1/`
10. Mọi truy vấn DB qua ORM — không raw SQL trong routers
11. File Python: `snake_case` · Component React: `PascalCase` · Comment tiếng Việt
12. Trước khi commit chạy `git status`
13. 🔒 Không ghi mật khẩu vào bất kỳ file nào trong repo

---

*Phiên sau: đọc `AGENTS.md` + file này, chạy `git status`, rồi làm D2 (seed data).*
