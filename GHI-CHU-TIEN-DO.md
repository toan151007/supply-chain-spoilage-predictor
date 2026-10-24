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
| **M1 — Train 100 cặp** | ✅ Xong | Prophet thắng 97/100 · RMSE 9,97 · 13,2 phút · commit `47b4775` |
| **M2 — Dự báo 30 ngày** | ✅ Xong | 3.000 dòng trong bảng `forecasts` |
| **M3 — Tài liệu đánh giá** | ✅ Xong | `docs/05-tham-khao/ket-qua-danh-gia-model.md` |
| **Quyết định Chương 4** | ✅ Xong | Giữ nguyên Chương 2 + `max_stock`, ghi chú hạn chế — mục 8j |
| **B1 — Setup FastAPI** | ✅ Xong | config · database · main · CORS · health — mục 8k |
| **B2 — ORM models** | ✅ Xong | 10 model · test 947.590 dòng · mục 8l |
| **B3 — CRUD products API** | ✅ Xong | 5 endpoint · test 27/27 · mục 8m |
| **B4 — CRUD 5 bảng còn lại** | ✅ Xong | 37 operation · test pass · mục 8n |
| **Migration 005** | ✅ Xong | Sửa 4 sequence trôi · mục 8m |
| **CONTEXT-SUMMARY** | ✅ Xong | `docs/04-timeline/CONTEXT-SUMMARY.md` · commit `8e60e09` |
| B5 — Endpoint dashboard | ⬜ Chưa làm | Tiếp theo |
| T2 — README con | ⬜ Chưa làm | |
| Frontend React | ⬜ Chưa làm | |
| AI Model | ✅ Xong | M1 100 cặp · M2 3.000 dòng forecasts · M3 tài liệu |

---

## 2. Lịch sử commit

```
4a744ac  fix: CORS_ORIGINS parse trong config.py
3fac6b8  feat(backend): them .env.example, /api/v1/health, ho tro CORS 2 dinh dang
0ca104d  feat(backend): setup FastAPI - config, database, CORS, health check
8e60e09  docs: them CONTEXT-SUMMARY tom tat toan bo du an
7a95bbf  docs: cap nhat quyet dinh ve Chuong 2 + max_stock
47b4775  feat(ai): chay 100 cap, du bao 30 ngay, danh gia 3 mo hinh
8e392c6  docs: cap nhat tien do truoc khi ket thuc session
f46e479  docs: cap nhat tien do ngay 03/10/2026
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
| `docs/04-timeline/CONTEXT-SUMMARY.md` | Tóm tắt toàn bộ dự án — đọc file này trước khi chuyển máy |
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
| ~~M1~~ | Train 3 mô hình — 100 cặp | ✅ Xong — xem mục 8i |
| ~~M2~~ | Dự báo 30 ngày + ghi bảng `forecasts` | ✅ Xong 3.000 dòng — xem mục 8i |
| ~~M3~~ | Tài liệu đánh giá mô hình | ✅ Xong — xem mục 8i |
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

## 8i. Hoàn thành M1 + M2 + M3 (03/10/2026 — phiên sau)

### M1 — Chạy 100 cặp ✅

**Lệnh:** `python ai-model/scripts/train_models.py --all` → **13,2 phút** (ước tính ban đầu 9 phút)

**Sửa trước khi chạy:** `train_models.py` còn để `seasonality_mode="additive"` — lệch với config đã chốt trong AGENTS.md. Đã sửa thành `multiplicative`. Cũng xóa biến chết `TRAIN_RATIO = 0.8` và viết lại docstring cho đúng (5 năm, mốc `2017-10-01`, 15 đặc trưng).

**Kết quả — KHÔNG cặp nào lỗi, không có cột NaN:**

| Mô hình | RMSE | MAE | MAPE | RMSE min | RMSE max | SD |
|---------|------|-----|------|----------|----------|-----|
| **Prophet** | **9,97** | **7,94** | **10,43%** | 6,62 | 12,81 | 1,43 |
| XGBoost | 10,98 | 8,77 | 11,69% | 7,39 | 15,14 | 1,70 |
| ARIMA | 20,20 | 16,44 | 23,77% | 9,94 | 35,84 | 4,96 |

**Số cặp thắng: Prophet 97 · XGBoost 3 · ARIMA 0**

3 cặp XGBoost thắng: `(45,2)` · `(13,7)` · `(28,4)`

#### 🔴 Kết quả đảo ngược kỳ vọng của Chương 2

Chương 2 chốt **XGBoost = mô hình chính**. Kết quả thực tế: **Prophet thắng áp đảo 97/100**.

| | Chương 2 dự kiến | Thực tế 100 cặp |
|---|------------------|-----------------|
| Mô hình chính | XGBoost | **Prophet** |
| Đối chứng | Prophet, ARIMA | XGBoost, ARIMA |

**Lý do:** XGBoost dựa trên `lag_1..lag_28`, rất mạnh ở chế độ one-step nhưng khi dự báo 30 ngày liên tục phải đệ quy → sai lệch tích luỹ. Prophet vốn là mô hình đa bước, có `yearly_seasonality` sẵn.

Chênh lệch trung bình chỉ **1,02 RMSE**; ở **59/100 cặp** chênh lệch < 1,0 — tức dưới 1 sản phẩm/ngày trên quy mô bán ~1.000/ngày. Không đủ bù để bác bỏ Prophet.

→ **Cần sửa Chương 2 mục phân vai trò mô hình**, hoặc giữ nguyên và giải thích rõ ở Chương 4 rằng kết quả thực nghiệm đã đảo ngược dự kiến ban đầu.

### M2 — Dự báo 30 ngày + ghi bảng `forecasts` ✅

**Script mới:** `ai-model/scripts/forecast_next_month.py`

```powershell
python ai-model/scripts/forecast_next_month.py --dry-run   # xem trước, không ghi
python ai-model/scripts/forecast_next_month.py --replace   # xóa dữ liệu cũ rồi ghi
```

**Kết quả:** **3.000 dòng** trong bảng `forecasts` = 100 cặp × 30 ngày · 01/01/2018 → 30/01/2018 · horizon 1→30

| model_name | Số dòng |
|-----------|---------|
| prophet | 2.910 |
| xgboost | 90 |

Thời gian: 1,7 phút.

**Chỉ ghi model tốt nhất mỗi cặp** → 100 × 30 = 3.000, không phải 9.000 (9.000 sẽ là ghi cả 3 model cho mỗi cặp).

#### Lỗi đã gặp

| Lỗi | Nguyên nhân | Cách xử |
|-----|-------------|----------|
| `ValueError: If using all scalar values, you must pass an index` (97/100 cặp fail) | `pd.DataFrame({"ds": future_dates})` — truyền **cả DataFrame** vào dict. pandas 3.0 coi đây là giá trị scalar | Truyền **Series**: `pd.DataFrame({"ds": future_dates["sale_date"]})` |

Lưu ý: `train_models.py` dùng `future["sale_date"]` (Series) nên chạy được. Chỉ script M2 mắc lỗi này.

#### ⚠️ `recommended_import_qty` bị `max_stock` chặn 100/100 cặp

| Chỉ số | Giá trị |
|--------|---------|
| Tổng nhu cầu dự báo 30 ngày | 191.582 |
| Tổng tồn kho hiện tại | 11.304 |
| **Tổng nhu cầu thuần** (chưa cap) | **232.397** |
| **Tổng đề xuất nhập** (sau cap) | **7.286** |

**Nguyên nhân:** seed data đặt `max_stock` trong khoảng **48–300**, nhưng nhu cầu thực tế của Kaggle là **861–2.793/ngày**. Tức `max_stock` chỉ tương đương **0,5–3 ngày bán**.

**Đây là hạn chế của dữ liệu seed, KHÔNG phải lỗi mô hình dự báo.** Seed `inventory` được thiết kế như tồn kho cửa hàng nhỏ, không cùng thang đo với doanh thu Walmart.

→ Đã thêm cột `raw_need` (nhu cầu chưa cap) vào `forecast_summary_30d.csv` để lưu vết. **Khi viết báo cáo phải nêu rõ hạn chế này**, nếu không số liệu `recommended_import_qty` sẽ gây hiểu nhầm là mô hình dự báo thiếu.

#### Công thức `recommended_import_qty`

```
ngày d : MAX(0, nhu_cầu_tích_luỹ(d) + tồn_kho_an_toàn − tồn_hiện_tại)
         MIN( với max_stock − tồn_hiện_tại )         ← chặn trên
         MIN( với nhu_cầu_trong_hạn_sử_dụng )      ← chặn hạn

tồn_kho_an_toàn = Σ (upper_bound − predicted) trên 30 ngày
```

Khoảng tin cậy 95%: Prophet lấy trực tiếp `yhat_lower/upper`; XGBoost dùng `±1,96 × RMSE(tap train)`; ARIMA dùng `±1,96 × σ(resid)`.

**XGBoost dự báo ĐỆ QUY** — ngày N+1 dùng giá trị *dự báo* của ngày N cho đặc trưng lag. Dùng số thực tương lai sẽ là rò rỉ dữ liệu, RMSE đẹp giả.

### M3 — Tài liệu đánh giá mô hình ✅

**File:** `docs/05-tham-khao/ket-qua-danh-gia-model.md`

Nội dung: phương pháp (time-series split theo mốc ngày, chọn tham số theo validation) · bảng so sánh 3 mô hình · số cặp thắng · 3 insight chính · hạn chế.

**3 insight chính:**
1. **Độ dài chuỗi quyết định thứ hạng, không phải thuật toán** — Prophet hạng 3 → hạng 1 nhờ thêm 4 năm dữ liệu, không đổi tham số
2. **ARIMA không phù hợp khi chuỗi có mùa vụ mạnh** — `seasonal_order=(0,0,0,0)` không mô hình hóa được mùa vụ năm, RMSE gấp 2,02 lần
3. **XGBoost có lợi thế ở chuỗi ngắn nhưng suy giảm khi dự báo xa** — đệ quy 30 ngày làm sai lệch tích luỹ

### Bảng dữ liệu sau M2

| Bảng | Số dòng |
|------|---------|
| categories | 8 |
| stores | 10 |
| products | 50 |
| users | 3 |
| orders | 18.260 |
| order_items | 912.999 |
| inventory | 1.330 |
| inventory_transactions | 11.412 |
| alerts | 518 |
| **forecasts** | **3.000** ← mới |

---

## 8r. B8 — API Dashboard nâng cao (12/10/2026) ✅

### Files đã tạo / sửa — 5 file

| File | Nội dung |
|------|----------|
| `backend/app/routers/dashboard_advanced_router.py` | 6 endpoint dưới `/api/v1/dashboard` |
| `backend/app/schemas/dashboard_advanced_schema.py` | 8 schema |
| `backend/app/main.py` | Include router (giữ nguyên router B5) |
| `backend/app/schemas/__init__.py` | Export 8 schema |
| `backend/test_b8_dashboard_advanced.py` | 121 check — **read-only, không có cleanup** |

### 6 endpoint

| Endpoint | Trả về |
|----------|--------|
| `/dashboard/revenue-by-store` | `store_id` · `store_code` · `store_name` · `total_revenue` · `total_orders` · `total_quantity` · `avg_order_value` |
| `/dashboard/revenue-by-category` | `category_id` · `category_name` · `total_revenue` · `total_quantity` · `product_count` |
| `/dashboard/top-stores?limit=5` | Cùng cấu trúc, sắp theo doanh thu |
| `/dashboard/inventory-value` | `total_items` · `total_batches` · `total_value` · `expiring_value` |
| `/dashboard/waste-analysis` | Tổng hợp lãng phí (+ chi tiết từng lô nếu `include_batches`) |
| `/dashboard/forecast-vs-actual` | `matched_rows` · `accuracy` (MAPE/MAE/RMSE/bias) · `comparison` |

### 🔴 Phát hiện quan trọng: `v_daily_sales` có `GROUP BY` thừa

Endpoint chạy lần đầu: **`revenue-by-category` mất 8.616 ms**. Tôi tưởng do 912.999 dòng, nên chạy `EXPLAIN ANALYZE`.

Kết quả: PostgreSQL báo **Execution Time chỉ 1.606 ms**, nhưng client chờ **8.6 giây**. Và cùng một câu SQL đó chạy qua `psql` chỉ 1.6 giây.

Đọc định nghĩa view ra mới thấy nguyên nhân thật:

```sql
GROUP BY o.store_id, ..., oi.product_id, ..., o.order_date
```

Nhưng `order_items` có **UNIQUE `(order_id, product_id)`** — mỗi cặp đơn/sản phẩm chỉ có **đúng một** dòng. `SUM(oi.quantity)` và `SUM(oi.line_total)` chỉ có thể trả về chính dòng đó.

**→ `GROUP BY` đó không bao giờ gộp được gì, nhưng bắt PostgreSQL sort + GroupAggregate trên 912.999 dòng mỗi lần đọc.**

Kiểm chứng bằng cách bỏ `GROUP BY` thừa:

| Cách | Execution Time | Kết quả |
|------|----------------|---------|
| Qua `v_daily_sales` | 1.606 ms | — |
| Join thẳng `order_items` | **680 ms** | **khớp từng cent, cả 7 nhóm** |

Tôi đã đối chiếu từng nhóm hàng giữa hai cách — `458860820000.00 = 458860820000.00`, `189764730000.00 = 189764730000.00`… **7/7 khớp tuyệt đối.**

→ Hai endpoint B8 (`revenue-by-category`, `forecast-vs-actual`) đã **bỏ qua view, join thẳng**. Đây cũng là bài học áp dụng được cho **B5** (`/revenue`, `/top-products` cũng đọc view này).

**Không sửa view** vì đó là thay đổi schema, cần bạn quyết định. Báo cáo tại đây.

### 🔴 Lỗi SQLAlchemy — `missing FROM-clause entry for table "order_items"`

Sau khi tối ưu, `forecast-vs-actual` trả **500**:

```python
# SAI:
on_match = (Order.store_id == Forecast.store_id) \
         & (OrderItem.product_id == Forecast.product_id) \
         & (Order.order_date.cast(Date) == Forecast.forecast_date)
.select_from(Forecast).join(Order, on_match).join(OrderItem, ...)
```

`on_match` nhắc tới `OrderItem.product_id` **trong khi `OrderItem` chưa có trong FROM** — SQLAlchemy không biết lấy nó ở đâu.

→ Tách thành hai điều kiện riêng, mỗi bảng vào lúc nó được join:

```python
on_order = (Order.store_id == Forecast.store_id) \
         & (Order.order_date.cast(Date) == Forecast.forecast_date)
on_line  = (OrderItem.order_id == Order.order_id) \
         & (OrderItem.product_id == Forecast.product_id)
.select_from(Forecast).join(Order, on_order).join(OrderItem, on_line)
```

### Tối ưu thứ 2 — kẹp cửa sổ thực tế vào cửa sổ dự báo

`forecast-vs-actual` còn một vấn đề: nó đếm `actual_rows` trên **toàn bộ** `v_daily_sales` khi không có filter ngày — tức quét 912.999 dòng để đếm những thứ **vốn không thể khớp** với dự báo.

Sửa: **kẹp** khoảng ngày thực tế vào khoảng mà `forecasts` thật sự phủ. Với dữ liệu hiện tại, cửa sổ thực tế thu hẹp còn 2018-01-01 → 2018-01-30, đúng vùng **không có** đơn nào → index lookup trả về 0 dòng ngay.

Ngoài ra con số `actual_rows` trong response cũng chính xác hơn: đếm doanh số ngoài tầm dự báo là vô nghĩa.

**Kết quả: 6.464 ms → 84 ms (nhanh hơn 77 lần).**

### Hiệu năng (đo 5 lần mỗi endpoint)

| Endpoint | Trước | Sau |
|----------|-------|-----|
| `revenue-by-store` | 29 ms | **20 ms** |
| `top-stores?limit=5` | 56 ms | **73 ms** |
| `inventory-value` | 50 ms | **69 ms** |
| `waste-analysis` | 53 ms | **83 ms** |
| `forecast-vs-actual` | **6.464 ms** | **84 ms** ✅ |
| `revenue-by-category` | **8.616 ms** | **4.087 ms** ✅ |

### ⚠️ `revenue-by-category` vẫn nặng khi không lọc ngày

| Truy vấn | Thời gian |
|----------|-----------|
| Không filter (toàn bộ 5 năm) | **3.995 ms** |
| Filter 1 năm (2017) | **414 ms** |
| Filter 1 tháng (2017-06) | **39 ms** |

PostgreSQL tự báo mất **653 ms** cho bản không filter. Nhưng client chờ **4 giây**.

Tôi đã kiểm tra kỹ: đây **không phải** lỗi SQLAlchemy — chạy bằng `psycopg2` thuần trên **cùng connection** vẫn ra 6–8 giây, trong khi `EXPLAIN` của chính DB báo 653 ms. Tỉ lệ ~6x này **nhất quán** ở cả hai endpoint, nên nó là đặc tính của môi trường (máy Windows + PostgreSQL local), không phải của câu truy vấn.

Kết luận: gọn nhất trong điều kiện hiện tại là **680 ms DB / ~4 giây thực tế** cho bản tổng hợp toàn bộ lịch sử. Muốn nhanh hơn nữa thì phải thêm index hoặc biến view thành materialized view — **cần bạn quyết định**.

Trong thực tế dashboard luôn có khoảng ngày, nên 39–414 ms là con số đáng quan tâm.

### ⛔ `forecast-vs-actual` KHÔNG tính được MAPE — hạn chế dữ liệu

| | Từ | Đến |
|---|---|---|
| `forecasts` (prophet) | **2018-01-01** | **2018-01-30** |
| `v_daily_sales` | 2013-01-01 | **2017-12-31** |

**Hai khoảng không giao nhau.** Không có ngày nào có cả dự báo lẫn thực tế → `matched_rows = 0`.

API xử lý thành thật: `mape: null`, `mae: null`, `rmse: null`, kèm `message` giải thích đầy đủ — **không** báo một con số MAPE bịa ra.

```
matched_rows = 0 · mape = null
"The table holds 2910 forecast row(s) and 0 actual row(s) within the
forecast window, but they cover different periods. Stored forecasts run
from 2018-01-01 to 2018-01-30 while sales data ends 2017-12-31, so
accuracy cannot be measured until actual sales exist for the forecast
horizon."
```

Logic ghép đã viết đúng và sẽ chạy được ngay khi có dữ liệu thực tế cho tháng 1/2018. **Khi viết Chương 4 phải nói rõ điều này**, không được trình bày như đã đo được độ chính xác trên dữ liệu thật.

### Ba phát hiện thêm về dữ liệu

**1. Số dự báo không đều** — SP 13, 28, 45 chỉ có dự báo cho **9/10 cửa hàng**:

| Sản phẩm | Số dòng dự báo |
|----------|----------------|
| 8, 11, 15, 18, 25, 38, 48 | 300 (10 CH × 30 ngày) |
| **13, 28, 45** | **270 (9 CH × 30 ngày)** |

Tổng 2.910 **không** chia hết cho 10. Tôi đã đoán nhầm 291 (trung bình) và test bắt được.

**2. Category "Food" (id 1) không có sản phẩm nào** → không có doanh thu → inner join loại khỏi kết quả. DB có 8 nhóm, endpoint trả **7**.

**3. `avg_order_value` phải chia cho SỐ ĐƠN, không chia cho số dòng hàng.** Một đơn có 50 dòng vẫn là **một** lần mua; chia cho 50 sẽ thấp hơn thực tế 50 lần. Đã kiểm chứng `avg_order_value` > `total_revenue / (orders × 10)`.

### Thiết kế filter ngày — chặn sẵn bẫy timezone

Các endpoint nhận param kiểu **`date`**, không phải `datetime`. Hệ quả:

| Input | Kết quả |
|---|---|
| `?from_date=2017-01-01&to_date=2017-12-31` | 200 · **3.650 đơn** ✅ |
| `?from_date=2017-01-01T00:00:00Z&...` | **422** ← bị chặn ngay |

Bên trong, mốc được dựng bằng `VN_TZ = +07:00` đúng như cách dữ liệu được lưu. Mốc trên dùng **`<` với nửa đêm ngày kế tiếp** nên không phải xử lý `23:59:59.999999`.

Đã kiểm chứng: 1 ngày → 10 đơn · tháng 1/2017 → 310 đơn · năm 2017 → 3.650 đơn.

### Ước lượng lãng phí — cố tình lấy **trường hợp xấu nhất**

`estimated_waste_value = expired_value + expiring_value`, tức giả định **mọi** lô sắp hết hạn cũng mất trắng. Lãng phí thật sẽ thấp hơn.

Báo cáo con số lạc quan ở đây sẽ **đánh giá thấp rủi ro vận hành**. Đã ghi rõ trong docstring.

Giá trị tính theo `products.unit_cost` (giá vốn), không phải `selling_price` — vì câu hỏi là "hàng này còn giá trị bao nhiêu với chúng ta", và cùng cơ sở đó dùng cho ước lượng lãng phí.

Đã kiểm chứng `expired_batches` của B8 **khớp** `/dashboard/expiring?days=0` của B5 (444 lô).

### Kết quả test — 121 check, ALL PASS

| Nhóm | Đã kiểm |
|------|---------|
| `revenue-by-store` | 10 CH · tổng khớp DB · từng CH khớp DB · sắp xếp · 2017/1 ngày/1 tháng · mở đầu-cuối · năm không có dữ liệu · 7 edge case |
| `top-stores` | limit 1/3/5/10 · khớp `revenue-by-store` · tổng khớp · filter ngày · 4 edge case |
| `revenue-by-category` | 7 nhóm · tổng khớp view · từng nhóm khớp DB · 2017 · năm rỗng · from>to |
| `inventory-value` | tổng khớp DB · **khớp `/overview` của B5** · `expiring_value` khớp view 30 ngày · `include_empty` |
| `waste-analysis` | mọi trường · khớp DB · **khớp B5 `/expiring?days=0`** · `include_batches` · `limit` · 2 edge case |
| `forecast-vs-actual` | khoảng không giao nhau · `matched=0` · `mape=null` · message giải thích · model khác · product/store filter · 2 edge case |
| Cuối buổi | 5 bảng về đúng baseline — **B8 read-only, không ghi gì** |

### Sai lầm của tôi — 3 kỳ vọng test sai

| Tôi kỳ vọng | Thực tế đúng |
|-------------|--------------|
| Mốc UTC trả 200 | **422** — và đó là điểm tốt: chặn được bẫy timezone |
| 8 nhóm hàng | **7** — "Food" không có sản phẩm |
| SP15 có 291 dòng dự báo | **300** — 291 là trung bình bịa ra |

### Sai lầm khác

Tôi chạy `python -c "..."` với heredoc để profile, PowerShell **bóp méo dấu nháy** làm Python báo `SyntaxError` 2 lần. Đã chuyển sang file `.py` tạm. (Đây là lần thứ 3 trong phiên — nên nhớ luôn viết file thay vì `python -c` khi cần dấu nháy phức tạp.)

### Việc tiếp theo — F1

Setup Frontend React + Vite + Tailwind. CORS đã bật sẵn cho `localhost:3000` và `:5173`.

---

## 8q. B7 — API Import Excel/CSV (12/10/2026) ✅

### ⚠️ Phải cài thêm 3 thư viện — đã tự quyết, cần bạn xác nhận

Bắt buộc phải có để làm được B7, **không cài thì router không chạy được**:

| Thư viện | Vì sao BẮT BUỘC | Đã cài |
|----------|-----------------|--------|
| `python-multipart==0.0.32` | FastAPI khai báo `UploadFile`/`File(...)` mà thiếu nó sẽ **lỗi ngay lúc import** | ✅ |
| `openpyxl==3.1.5` | engine đọc `.xlsx` cho `pandas.read_excel()` | ✅ |
| `pandas==3.0.6` | đọc CSV/Excel trong router | ✅ (đã có sẵn, **thiếu trong `requirements.txt`** — đã bổ sung) |

Đã thêm cả 3 vào `backend/requirements.txt` kèm giải thích. Không có gì bị xoá hay thay đổi.

### Files đã tạo / sửa — 6 file

| File | Nội dung |
|------|----------|
| `backend/app/routers/import_router.py` | 5 endpoint |
| `backend/app/import_specs.py` | **Mới** — hợp đồng cột của 3 loại import + dữ liệu mẫu |
| `backend/app/schemas/import_schema.py` | `ImportResult` · `RowError` · `TemplateInfo` |
| `backend/app/main.py` | Include `import_router` |
| `backend/app/schemas/__init__.py` | Export 5 schema |
| `backend/requirements.txt` | + `python-multipart` · `openpyxl` · `pandas` |

### Tách `import_specs.py` riêng — để hợp đồng cột không trôi

Router **kiểm tra đúng những gì `import_specs.py` khai báo**, và endpoint template **phát ra đúng những header đó**. Hai bên không thể lệch nhau vì cùng đọc một nguồn.

| Loại | Cột bắt buộc |
|------|--------------|
| products | `product_code` `product_name` `category_id` `unit` `unit_cost` `selling_price` `shelf_life_days` |
| inventory | `product_id` `store_id` `quantity` `expiry_date` |
| sales | `order_date` `store_id` `product_id` `quantity` `unit_price` |

### 5 endpoint

| Method | Path |
|--------|------|
| POST | `/api/v1/import/products` · `/inventory` · `/sales` |
| GET | `/api/v1/import/template/{type}?fmt=csv\|xlsx` |
| GET | `/api/v1/import/types` |

### 🔴 Lỗi thật — validator trả `(None, None)` → 500

Đây là lỗi nghiêm trọng nhất của B7. Trong `_validate_sales` tôi viết:

```python
if order_code in seen_codes:
    return None, None     # ← TƯỞNG là "không có lỗi"
```

Nhưng hợp đồng của vòng lặc gọi là:

```python
values, error = validator(...)
if error: ...   # báo lỗi
else:    clean_rows.append(values)   # ← append None !
```

`error = None` nên nó **không báo lỗi**, mà `None` lọt thẳng vào danh sách dòng hợp lệ. Tới `_write_sales` thì `row["order_code"]` với `row = None` → **500**.

Chuyện đáng nói: đó là **ý định của tôi sai ngay từ đầu**. `order_code` trùng **không phải lỗi** — đó chính là cách biểu diễn một đơn nhiều dòng hàng. Tôi viết nhánh "trả về sớm" rồi quên xoá.

→ Sửa: bỏ nhánh sớm, để dòng đi tiếp và gom ở `_write_sales`.

**Ngoài ra** đã thêm chặn phòng thủ trong `_run_import`: nếu `error is None` mà `values is None` thì trả 500 kèm message nói rõ đây là bug — thay vì để lỗi lan xuống tầng dưới thành `TypeError` khó đoán.

### Ràng buộc an toàn khi đọc file

| Kiểm tra | Kết quả | Mã |
|----------|---------|-----|
| Đuôi file không hỗ trợ | "Unsupported file type '.txt'. Allowed: .csv, .xlsx" | 400 |
| File rỗng | "Uploaded file is empty" | 400 |
| Tên `.csv` nhưng là Excel | "File is named .csv but its bytes are an Excel (.xlsx) workbook…" | 400 |
| Tên `.xlsx` nhưng là CSV | "File is named .xlsx but is not an Excel workbook." | 400 |
| `.xlsx` hỏng | "Could not read the file: BadZipFile…" | 400 |
| Chỉ có header, không có dòng | "File has headers but no data rows." | 422 |
| Quá 20.000 dòng | "File has 20001 rows; the limit is 20000." | 422 |
| Quá 10 MB | "File too large. Maximum is 10 MB." | 400 |

**Kiểm tra 4 byte đầu** (`PK\x03\x04`) là mấu chốt: `.xlsx` thật ra là file ZIP. Không có bước này thì lỗi "đổi tên `.csv` nhưng nội dung vẫn là Excel" sẽ nổ ra thành `UnicodeDecodeError` từ pandas — người dùng không hiểu phải làm gì.

### Chiến lược transaction — `rollback` (mặc định) vs `skip`

| `on_error` | 4 dòng, 1 dòng sai | Ghi được |
|------------|-------------------|----------|
| `rollback` (mặc định) | `error_rows=3`, `created_ids=[]` | **0 dòng** |
| `skip` | `success_rows=2`, `error_rows=1` | **2 dòng** |

Đã kiểm chứng `rollback` thật sự không ghi gì: sản phẩm ở dòng 1 (dòng hợp lệ) của file có dòng sai vẫn **không tồn tại** sau khi import.

**Vì sao validate hết rồi mới ghi:** nếu ghi từng dòng thì không có "trạng thái chưa ghi" để so sánh. File hỏng ở dòng 9.001 sẩy lại 9.000 dòng, và lần import sau lại trùng rồi hỏng tiếp.

### Import sales — gom dòng theo `order_code`

| File | Kết quả |
|------|---------|
| 2 dòng, cùng `order_code` | **1 đơn**, 2 dòng chi tiết |
| 2 dòng, `order_code` rỗng | **2 đơn** riêng |

Đã kiểm chứng công thức `line_total` từ dữ liệu import:

```
5 × 15.000, giảm 0%   =  75.000
2 × 25.000, giảm 10%  =  45.000
total_amount           = 120.000   ✅ khớp
total_quantity         =       7   ✅ khớp
```

Dòng hàng được ghi **không có** `line_total` — GENERATED COLUMN, DB tự tính. Tổng đơn tính lại bằng `SUM` y hệt router orders (kèm `db.flush()` vì session `autoflush=False`).

### Kiểm tra trùng — cả trong file lẫn với DB

| Tình huống | Kết quả |
|------------|---------|
| `product_code` trùng **trong file** | 200 + báo lỗi theo dòng, rollback không ghi |
| `product_code` trùng **DB** | **409** + không ghi gì |
| Lot `(store, product, expiry)` trùng **trong file** | 200 + báo lỗi theo dòng |
| Lot trùng **DB** | **409** + không ghi gì |
| `order_code` trùng **DB** | **409** + không ghi gì |

Kiểm tra DB dùng **1 query** cho cả file (`WHERE code IN (...)`), không query từng dòng.

### Sai lầm của tôi — 3 kỳ vọng test sai

Lần chạy đầu có 6 FAIL, **lỗi ở test, không ở API**:

| Tôi kỳ vọng | Thực tế đúng |
|-------------|--------------|
| Bỏ cột cuối → 422 | **200** — cột cuối là `supplier`/`received_date`/`customer_name`, đều **không bắt buộc**. Phải bỏ cột bắt buộc thì mới 422 |
| Cột tên sai (`category_id_x`) → chấp nhận | **422** — tên cột cũng phải khớp chính xác |

Nhưng lần này lỗi test **có hậu quả thật**: vì 200 nên nó đã **tạo 1 sản phẩm rác** (`product_code = "1"`) mà tiền tố `IMPT-` không bắt được. Đã phát hiện và xoá.

### 🔴 Lỗi cleanup — `LIKE` không khớp `NULL`

Sau khi tất cả PASS, kiểm tra baseline thấy `inventory = 1331` thay vì 1330.

Lý do: test "chỉ dùng cột bắt buộc" tạo lô hàng **không có `batch_code`** → giá trị `NULL`. Cleanup chạy:

```sql
DELETE FROM inventory WHERE batch_code LIKE 'IMPT-%'
```

**`NULL LIKE 'IMPT-%'` không bao giờ đúng.** Dòng đó lọt khỏi cleanup và mọi kiểm tra vẫn báo PASS vì nó chỉ xoá theo tiền tố.

→ Sửa: cleanup xoá **theo khóa chính** (`= ANY(%s)`) dùng `created_ids` mà server đã trả về, cộng một vòng quét dự phòng. Giờ xác minh 4 bảng về đúng baseline.

**Bài học:** kiểm tra baseline cuối buổi là bắt buộc — không có nó thì lỗi cleanup sẽ âm thầm tích luỹ qua nhiều lần chạy.

### Kết quả test — 115 check, ALL PASS

| Nhóm | Đã kiểm |
|------|---------|
| Template | 3 loại × 2 định dạng · header đúng · xlsx là ZIP · đọc lại được · 404 · 422 |
| `/import/types` | 3 loại · mô tả đầy đủ |
| products happy | CSV 3 dòng · XLSX 1 dòng · trả `created_ids` |
| products lỗi | 3 dòng sai (FK, giá âm, shelf_life=0) · rollback không ghi · `skip` ghi 2 |
| products UNIQUE | trùng trong file · trùng DB → 409 |
| inventory | happy · **5** case validation · trùng lot trong file · trùng DB → 409 |
| sales | gom đơn · không `order_code` · `line_total` + tổng đơn khớp công thức · **9** case validation · trùng DB → 409 · rollback |
| Thiếu cột | bỏ cột bắt buộc → 422 (3 loại) · đổi tên cột → 422 (3 loại) · **chỉ dùng cột bắt buộc → 200** |
| Sai định dạng | `.txt` · rỗng · `.csv` hóa `.xlsx` · `.xlsx` hóa CSV · xlsx hỏng |
| Giới hạn | >20.000 dòng → 422 · >10 MB → 400 · `on_error` sai → 422 |
| Tiếng Việt | tên có dấu giữ nguyên sau vòng import |
| Cleanup | 4 bảng về đúng baseline, 0 dòng sót |

### Sai lầm khác

- Trong lúc chạy `python -c "..."` để kiểm thư viện, PowerShell **bóp méo dấu nháy** trong heredoc làm Python báo `SyntaxError` hai lần. Đã chuyển sang viết file `.py` tạm rồi chạy.
- Lỗi `UnicodeEncodeError` khi in tiếng Việt ra console (cp1252) — đã thêm `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` vào script, giống các script trước.

### Việc tiếp theo — F1

Setup Frontend React + Vite + Tailwind. CORS đã bật sẵn cho `localhost:3000` và `:5173`.

---

## 8p. B6 — API bán hàng: orders + order-items (12/10/2026) ✅

### Files đã tạo / sửa — 5 file

| File | Nội dung |
|------|----------|
| `backend/app/schemas/order_schema.py` | `OrderCreate` · `Update` · `Read` · `Detail` · `StatusUpdate` · `OrderItemInput` |
| `backend/app/schemas/order_item_schema.py` | `OrderItemCreate` · `Update` · `Read` |
| `backend/app/routers/order_router.py` | 7 endpoint `/api/v1/orders` |
| `backend/app/routers/order_item_router.py` | 5 endpoint `/api/v1/order-items` |
| `backend/app/main.py` + `schemas/__init__.py` | Include 2 router · export 12 schema |

### 12 endpoint

| Method | Path | Việc |
|--------|------|------|
| GET | `/api/v1/orders` | List + phân trang + filter |
| GET | `/api/v1/orders/{id}` | Chi tiết kèm items |
| GET | `/api/v1/orders/{id}/items` | Chỉ items của đơn |
| POST | `/api/v1/orders` | Tạo đơn kèm items |
| PUT | `/api/v1/orders/{id}` | Sửa header đơn |
| PUT | `/api/v1/orders/{id}/status` | Đổi trạng thái |
| DELETE | `/api/v1/orders/{id}` | Xoá (chỉ khi không còn dòng) |
| GET | `/api/v1/order-items` | List + filter |
| GET | `/api/v1/order-items/{id}` | Chi tiết 1 dòng |
| POST | `/api/v1/order-items` | Thêm dòng vào đơn |
| PUT | `/api/v1/order-items/{id}` | Sửa dòng |
| DELETE | `/api/v1/order-items/{id}` | Xoá dòng |

### 🔴 Lỗi thật tìm ra khi test — `autoflush=False` (quan trọng nhất của B6)

`app/database.py` khai báo `sessionmaker(autoflush=False)`. Tôi viết `_recalculate_order_totals()` chạy `SELECT SUM(line_total)` để cập nhật `orders.total_amount` — **nhưng không `flush()` trước**.

Kết quả: `SUM` nhìn thấy trạng thái **cũ**, nên thêm dòng hàng vào đơn xong thì `total_amount` **không đổi**:

```
POST /order-items thêm 45.00  →  total_amount vẫn 140.0 (đáng lẽ 185.0)
PUT  /order-items/{id}         →  total_amount vẫn 185.0 (đáng lẽ 235.0)
DELETE /order-items/{id}       →  OK (vì chỗ này tôi có flush tay)
```

Cái thú vị là **DELETE chạy đúng** vì tôi đã viết `db.flush()` tay ở chỗ xoá — nhưng quên ở POST và PUT. Đủ để hỏng âm thầm, không báo lỗi.

→ Sửa: `db.flush()` ở đầu `_recalculate_order_totals()` của **cả hai** router.

### 🔴 Lỗi thật thứ 2 — `flush()` nằm ngoài `try` → 500 thay vì 409

Sau khi thêm `flush()` thì phát sinh lỗi mới: `flush()` **mới là chỗ thực sự phát `INSERT`**, nên vi phạm UNIQUE nổ ra ở đó chứ không ở `commit()`.

```python
db.add(order)
db.flush()          # ← UniqueViolation nổ ra ở ĐÂY, ngoài try
try:
    db.commit()    # ← không bao giờ kịp chạy tới khi lỗi xảy ra
except IntegrityError:
    ...             # ← handler không bao giờ được gọi
```

Triệu chứng: `POST /orders` với `order_code` trùng trả **500 Internal Server Error** thay vì 409.

Đã gặp đúng lỗi này ở **3 chỗ**: 1 trong `order_router`, 2 trong `order_item_router`. Đã sửa cả 3 — mọi thứ có thể ném `IntegrityError` phải nằm trong `try`.

### 🔴 Lỗi thật thứ 3 — mốc thời gian UTC cắt mất 10 đơn

`order_date` là `timestamptz`, nhưng dữ liệu được nhập theo **mốc giờ địa phương +07:00**:

```
order_id 1 → 2013-01-01 00:00:00+07   (tức 2012-12-31 17:00:00 UTC)
```

Nên lọc năm 2017 ra hai kết quả khác nhau:

| Khoảng lọc | Kết quả | Đúng? |
|-------------|---------|-------|
| `2017-01-01T00:00:00Z` → `2017-12-31T23:59:59Z` | 3.640 | ❌ thiếu 10 |
| `2017-01-01T00:00:00+07:00` → `2017-12-31T23:59:59+07:00` | **3.650** | ✅ |

Thiếu đúng **10 đơn** — là 10 đơn ngày 01/01 (1 đơn/cửa hàng × 10 cửa hàng), vì `00:00+07:00` rơi vào `31/12` theo UTC.

Đây là đặc tính thật của dữ liệu, không phải lỗi API. Đã ghi chú vào test và AGENTS.md.

### GENERATED COLUMN `line_total` — kiểm chứng đầy đủ

| Cách kiểm | Kết quả |
|-----------|---------|
| Client gửi `line_total: 999999` | Bị Pydantic bỏ qua, **DB tự tính** ra giá trị đúng |
| `10 × 5, không giảm` | `50.00` ✅ |
| `4 × 25, giảm 10%` | `90.00` ✅ |
| `6 × 10, giảm 25%` | `45.00` ✅ |
| `8 × 3, giảm 50%` | `12.00` ✅ |
| `2 × 50, giảm 100%` | `0.00` ✅ (giảm trọn vẹn) |
| `27 × 20000` (dữ liệu seed) | `540.000.00` ✅ |

`line_total` **không xuất hiện** trong bất kỳ schema ghi nào. Chỉ đọc, và luôn đọc bằng `db.refresh()` sau khi commit.

### Nghiệp vụ vòng đời đơn hàng

| Từ → Đến | Kết quả | Lý do |
|----------|---------|-------|
| pending → completed | ✅ 200 | Đường đi bình thường |
| pending → cancelled | ✅ 200 | Huỷ đơn nhập nhầm |
| pending → pending | ✅ 200 | Idempotent, là no-op |
| cancelled → pending | ✅ 200 | Mở lại đơn huỷ nhầm |
| cancelled → completed | ❌ 409 | Đã huỷ thì không hoàn tất |
| **completed → bất cứ** | ❌ 409 | Đơn đã xuất hoá đơn, kho đã dịch chuyển — cần bút toán bù trừ chứ không đảo trạng thái |

Giữ nguyên trạng thái hiện tại luôn trả 200 (cùng hợp đồng idempotent với `PUT /alerts/{id}/read`).

**Chỉ đơn `pending` mới sửa được** (header lẫn dòng hàng).

### Xoá đơn — chặn cascade có chủ đích

FK `order_items.order_id` là `ON DELETE CASCADE` (đã kiểm trong `pg_constraint`: `confdeltype = 'c'`). PostgreSQL sẵn sàng xoá luôn 50 dòng theo đơn.

API **cố tình chặn**, trả 409. Lý do: mất 50 dòng bằng một nhấn chuột nhầm thì không khôi phục lại được qua API.

→ **Hệ quả thực tế:** đơn `completed` là **điểm cuối** — không xoá được dòng (đơn đã khoá), không xoá được đơn (còn dòng). **Không tồn tại đường thoát qua API.** Script test vì thế phải dọn bằng SQL, giới hạn theo tiền tố `order_code LIKE 'T-B6%'`.

### Chống N+1

| Endpoint | Số query |
|----------|----------|
| `GET /orders` | 3 (đếm + trang + **1** GROUP BY tính `line_count`/`total_items` cho cả trang) |
| `GET /orders/{id}` | 2 (đơn + 1 query lấy product stub cho 50 dòng) |
| `GET /orders/{id}/items` | 3 (đơn + dòng + 1 query product stub) |
| `GET /order-items` | 3 (đếm + trang + 1 query product stub) |

Nếu chạm `line.product` trong vòng lặp thì đơn 50 dòng sẽ tốn **50** query. Gom `product_id` distinct rồi `IN (...)` giữ ở 1.

### Kết quả test — 155 check, ALL PASS

| Nhóm | Đã kiểm |
|------|---------|
| `GET /orders` | phân trang · sắp xếp DESC + tie-break · store/type/status · date range · 11 edge case 422 |
| `GET /orders/{id}` | 404 · 422 · 50 dòng · `total_amount` khớp tổng `line_total` |
| `GET /orders/{id}/items` | 404 · số dòng khớp detail |
| `POST /orders` | happy path · `line_total` client bị bỏ · **17** case validation |
| `POST /orders` UNIQUE | `order_code` trùng → 409 |
| `POST /order-items` | happy path · trùng sản phẩm → 409 · 6 case 422 |
| `PUT /order-items/{id}` | đổi qty/giá/giảm giá · đổi `product_id` (200 và 409) · body rỗng · 404 |
| `PUT /orders/{id}` | sửa từng field · 409 khi đã chốt · store/user sai → 422 · 404 |
| `PUT /orders/{id}/status` | đủ 6 tổ hợp chuyển trạng thái · 422 · 404 |
| `DELETE /order-items/{id}` | 204 · tổng về 0 · xoá 2 lần → 404 |
| `DELETE /orders/{id}` | 409 khi còn dòng · 204 khi rỗng · 404 |
| Sau cleanup | `orders` về **18.260** · `order_items` về **912.999** |

### Sai lầm của tôi — 6 kỳ vọng test sai (API đúng)

Lần chạy đầu có FAIL mà **lỗi ở test, không ở API**:

| Tôi kỳ vọng | Thực tế đúng |
|-------------|--------------|
| `store_id=1` → 3.650 đơn | **1.826** — 18.260 đơn ÷ 10 cửa hàng |
| năm 2017 (mốc UTC) → 3.650 | **3.640** — xem mục mốc thời gian ở trên |
| `store_id=1` trong order-items → 182.600 | **91.300** — 912.999 ÷ 10 |
| `field lạ` → 422 | **200** — không schema nào trong dự án đặt `extra="forbid"` |
| tổng dữ liệu "không đổi" | Kiểm **trước** cleanup nên tất nhiên khác — đã chuyển kiểm **sau** cleanup |
| `order_code` cố định cho mọi đơn test | UNIQUE nên lần 2 trở đi trả 409 — đã thêm đếm tăng dần |

Lần này tôi **không** sửa API cho khớp kỳ vọng sai; tôi hỏi DB rồi sửa test.

### Về `extra="forbid"` — để nguyên theo quy ước chung

Gửi field lạ (`{"khong_ton_tai": 1}`) được **200 và bị bỏ qua**. Đây là hành vi của **toàn bộ** API hiện tại — không schema nào đặt `extra="forbid"`.

Chỉ riêng orders mà đặt thì phần còn lại (products, stores, categories...) sẽ trả lỗi khác kiểu → API không nhất quán. Nên tôi giữ nguyên và **ghi chú lại** để bạn quyết định có muốn bật `extra="forbid"` cho **tất cả** schema không.

Rủi ro thật: gõ sai chính tả (`"quantitiy"`) sẽ bị bỏ qua âm thầm thay vì báo lỗi.

### Sai lầm khác — 3 lần làm rò dữ liệu test vào DB

- Dùng `Select-Object -First 60` để cắt output → **giết tiến trình Python giữa chừng**, nên `cleanup()` không bao giờ chạy. Lần đầu sót **5 đơn**.
- Lần sau sót **2 đơn** vì đơn đã `completed` không xoá được qua API.
- Lần sau sót **1 đơn** vì `order_code` của test trùng test (`ORD-TEST-DUP`) nằm ngoài tiền tố `T-B6%` mà cleanup quét.

Đã sửa: chuyển output vào file thay vì pipe, và dọn bằng SQL giới hạn theo `order_code LIKE 'T-B6%'`. Xác minh lại sau mỗi lần: **18.260 / 912.999**.

### Việc tiếp theo — F1

Setup Frontend React + Vite + Tailwind. CORS đã bật sẵn cho `localhost:3000` và `:5173`.

---

## 8o. B5 — API Dashboard tổng hợp (12/10/2026) ✅

### Files đã tạo / sửa — 5 file

| File | Nội dung |
|------|----------|
| `backend/app/schemas/dashboard_schema.py` | 9 schema (6 response chính + `RevenuePoint` · `SeverityCount` · `TypeCount`) |
| `backend/app/routers/dashboard_router.py` | 6 endpoint tổng hợp |
| `backend/app/models/views.py` | **Mới** — reflection 4 view bằng SQLAlchemy Core |
| `backend/app/schemas/__init__.py` | Export thêm 9 schema |
| `backend/app/main.py` | Include `dashboard_router` |

### Đọc view mà không dùng raw SQL

Yêu cầu là "dùng view có sẵn", nhưng quy tắc dự án cấm raw SQL trong routers. Giải pháp: **SQLAlchemy Core reflection**.

```python
v_low_stock = Table("v_low_stock", Base.metadata, autoload_with=engine)
```

Vẫn dùng `select()` / `where()` / `group_by()` / `order_by()` như bình thường — không có chuỗi SQL nào. Reflection đọc cấu trúc cột từ catalogue nên tự cập nhật nếu view trong DB thay đổi.

**Đã kiểm chứng:** `v_low_stock` 9 cột · `v_expiring_inventory` 13 · `v_product_stock_summary` 11 · `v_daily_sales` 13.

### Ràng buộc phát hiện khi đọc view — `v_expiring_inventory` giới hạn 30 ngày

```sql
WHERE i.quantity > 0 AND i.expiry_date IS NOT NULL
  AND i.expiry_date <= (CURRENT_DATE + 30)
```

Cứng 30 ngày. Nếu API cho `days=90` sẽ âm thầm trả đúng kết quả của `days=30` — người dùng tưởng đang xem 90 ngày.

→ Đã chặn `days` tối đa 30, trả **422** nếu vượt. Docstring ghi rõ giới hạn.

### Đối chiếu số liệu — khớp tuyệt đối với DB và CSV

| Kiểm tra | API trả về | DB / CSV |
|----------|-------------|----------|
| Doanh thu 5 năm | 1.409.611.790.000 | ✅ |
| Doanh thu 2017 | 317.233.060.000 | ✅ |
| Số đơn 2017 | 3.650 | ✅ |
| SP15 cả 5 năm | 1.607.442 | ✅ |
| SP15 doanh thu | 24.111.630.000 | ✅ |
| **SP15 năm 2017** | **361.586** | ✅ **khớp CSV gốc** |
| Low stock `threshold=20` | 21 dòng | ✅ |
| Low stock `threshold=0` | 57 dòng | ✅ |
| Expiring `days=7` | 474 lô | ✅ |
| Expiring `days=0` | 444 lô | ✅ |
| Expiring `days=30` | 564 lô (hết view) | ✅ |
| `by_severity` cộng lại | 518 = `total` | ✅ |

### ❌ SAI LẦM CỦA TÔI — báo nhầm AGENTS.md là có số liệu sai

Ban đầu tôi báo: *"Kiểm tra SP15 năm 2017 cho kết quả 361.586, khác với 331.783 đang ghi trong AGENTS.md → AGENTS.md SAI."*

**Kết luận đó SAI.** AGENTS.md không sai gì cả.

| | Số tôi báo là của SP15 | Thực tế thuộc về |
|---|---|---|
| **331.783** | tôi gán cho product 15 | **product 45** — hàng #1 của bảng |
| **361.586** | tôi nghĩ là số đúng | **product 15** — và AGENTS.md đã ghi đúng số này |

**Nguyên nhân:** khi quét bảng 10 dòng tôi đã đọc lệch hàng — lấy số của dòng #1 rồi gán cho dòng #3. Hai số trùng nhau làm lỗi này càng dễ xảy ra.

**Bằng chứng bảng trên đĩa luôn đúng từ đầu:**

```
$ git log -L 154,154:AGENTS.md
10d69f0 2026-10-02 docs: chot danh sach 10 san pham huyen luyen + ghi chu censored demand
+| 3 | 15 | Ca phe sua dinh huong | Beverages | 361.586 | 990,6 |
```

Commit `10d69f0` (02/10/2026) — commit **tạo ra** bảng — đã viết `361.586` ngay từ dòng đầu tiên. Không có lần nào sai.

**Đã kiểm chứng lại toàn bộ 10 dòng (12/10/2026)** bằng script so 3 nguồn:

| product_id | CSV gốc | DB | AGENTS.md | Chênh lệch |
|-----------|---------|-----|-----------|-----------|
| 45 | 331.783 | 331.783 | 331.783 | 0 ✅ |
| 8 | 316.911 | 316.911 | 316.911 | 0 ✅ |
| 15 | 361.586 | 361.586 | 361.586 | 0 ✅ |
| 13 | 346.565 | 346.565 | 346.565 | 0 ✅ |
| 25 | 330.786 | 330.786 | 330.786 | 0 ✅ |
| 11 | 286.882 | 286.882 | 286.882 | 0 ✅ |
| 28 | 360.768 | 360.768 | 360.768 | 0 ✅ |
| 48 | 211.365 | 211.365 | 211.365 | 0 ✅ |
| 38 | 331.005 | 331.005 | 331.005 | 0 ✅ |
| 18 | 346.448 | 346.448 | 346.448 | 0 ✅ |

**CSV == DB == AGENTS.md cho cả 10/10 sản phẩm. Không có số liệu nào cần sửa.**

Mỗi sản phẩm đều có đúng **3.650 dòng CSV** năm 2017 (10 cửa hàng × 365 ngày) — khớp hoàn toàn.

#### Về cột "BQ/ngày" — chênh nhẹ là do làm tròn, không phải lỗi

Script cũng báo "KHÔNG khớp" khi so `BQ/ngày × 365` với doanh số gốc. Đây là **sai số làm tròn** ở 1 chữ số thập phân, chênh tối đa ~100 đơn vị (0,03%), không phải số liệu sai:

| product | Doanh số | BQ/ngày | BQ × 365 | Lệch |
|---------|----------|---------|----------|------|
| 45 | 331.783 | 909,0 | 331.785 | 2 |
| 8 | 316.911 | 868,2 | 316.893 | 18 |
| 25 | 330.786 | 906,3 | 330.800 | 14 |
| 13 | 346.565 | 949,5 | 346.568 | 3 |

Riêng product 15: `361.586 / 365 = 990,6` → `990,6 × 365 = 361.569`, lệch 17. Nhất quán với 9 sản phẩm còn lại.

→ Đã ghi chú giải thích điều này vào AGENTS.md để lần đọc sau không báo nhầm nữa.

### Bài học

Vạch nhóm số liệu trong bảng có nhiều dòng, phải **đối chiếu bằng script theo `product_id` chứ không đọc bằng mắt rồi đối chiếu bằng trí nhớ.** Ở đây tôi đã "đối chiếu" bằng cách nhớ số đã đọc ở phiên trước — rồi gán nhầm sang dòng khác.

Đáng lẽ phải chạy script ngay từ đầu thay vì báo cáo rồi mới kiểm.

### Sai lầm của tôi — 3 kỳ vọng test sai (API đúng)

Lần chạy test đầu có 3 "FAIL" mà **lỗi ở test, không ở API**:

| Kỳ vọng sai | Thực tế đúng |
|---|---|
| `period=year&year=2017` → 5 điểm | **1** điểm — `date_trunc('year')` gộp cả năm thành 1 bucket. Bỏ filter `year` mới được 5 |
| `period=month&year=2017` → 60 điểm | **12** điểm — 12 tháng trong năm |
| SP15 năm 2017 = 290.419 | **361.586** (đã kiểm chứng từ CSV) |

Ngoài ra tôi đọc nhầm thứ tự cột CSV (`date,store,item,sales` → `item` là index **2**, không phải 1) nên kết luận nhầm "0 dòng dữ liệu". Đã sửa và đối chiếu lại.

### Hiệu năng — đo 20 lần mỗi endpoint

| Endpoint | Thời gian |
|----------|-----------|
| `low-stock?threshold=20` | 13 ms |
| `revenue?period=month&year=2017` | 17 ms |
| `alerts-summary` | 23 ms |
| `expiring?days=7` (474 lô, 118 KB) | 68 ms |
| `overview` | 137 ms |
| `top-products?limit=10` | 222–350 ms |

`top-products` chậm nhất vì `order_items` có **912.999 dòng** — JOIN + GROUP BY chạy trong PostgreSQL, Python chỉ nhận 10 dòng kết quả.

### Tránh N+1 query

| Endpoint | Số query |
|----------|----------|
| `overview` | 6 aggregate nhỏ, index-only scan |
| `alerts-summary` | 3 |
| `revenue` · `top-products` · `low-stock` · `expiring` | 1 mỗi cái |

Không endpoint nào lặp truy vấn theo từng dòng.

### Bucket rỗng bị bỏ qua, không điền 0

`/revenue` chỉ trả bucket có đơn hàng. Điền 0 cho bucket rỗng sẽ khiến biểu đồ hiện một tuần bằng phẳng — trông như có dữ liệu nhưng thực ra là "không bán được gì". Thiếu dữ liệu nên nhìn ra là thiếu dữ liệu.

### Kết quả test — toàn bộ PASS

| Nhóm | Số check | Đã kiểm |
|------|----------|----------|
| `overview` | 8 | happy path + đối chiếu DB |
| `revenue` | 28 | 4 period × year có/không filter · năm không có dữ liệu · `period` sai · `year` không phải số · ngoài khoảng |
| `top-products` | 16 | limit 10/50/100 · sắp xếp · filter store/year · limit 0/-5/101/không phải số |
| `low-stock` | 12 | threshold 0/20/100/10000/-1 · filter store · sắp xếp shortage |
| `expiring` | 17 | days 0/7/30/-1/31/không phải số · filter store+product · store không tồn tại · severity hợp lệ |
| `alerts-summary` | 13 | tổng · unread · unresolved · critical · 4 mức độ · thứ tự · tổng khớp · filter store |

**Dữ liệu sau test:** không đổi (dashboard chỉ đọc).

### Sai lầm khác

Sai ký tự đường dẫn `Đồ án TN` → tạo nhầm thư mục `Ēồ án TN` ngoài workspace (lần thứ 2 trong ngày). Đã xoá ngay và kiểm tra Desktop.

### Việc tiếp theo — F1

Setup Frontend React + Vite + Tailwind. CORS đã bật sẵn cho `localhost:3000` và `:5173`.

---

## 8n. B4 — API CRUD 5 bảng còn lại (12/10/2026) ✅

### Files đã tạo / sửa — 14 file

| File | Nội dung |
|------|----------|
| `backend/app/schemas/common.py` | Generic `Page[T]` + `Message` |
| `backend/app/schemas/store_schema.py` | `StoreBase` · `Create` · `Update` · `Read` · `Brief` |
| `backend/app/schemas/category_schema.py` | `CategoryBase` · `Create` · `Update` · `Read` |
| `backend/app/schemas/inventory_schema.py` | `InventoryBase` · `Create` · `Update` · `Read` · `ExpiringBatch` · `ExpiringReport` |
| `backend/app/schemas/forecast_schema.py` | `ForecastRead` · `LatestForecast` |
| `backend/app/schemas/alert_schema.py` | `AlertRead` · `AlertPage` · `MarkReadRequest` · `ResolveRequest` |
| `backend/app/schemas/__init__.py` | Export 31 schema |
| `backend/app/schemas/product_schema.py` | **Sửa** — dùng `Page[ProductRead]` chung, bỏ class `ProductPage` riêng |
| `backend/app/routers/store_router.py` | 5 endpoint |
| `backend/app/routers/category_router.py` | 5 endpoint |
| `backend/app/routers/inventory_router.py` | 6 endpoint |
| `backend/app/routers/forecast_router.py` | 5 endpoint (read-only) |
| `backend/app/routers/alert_router.py` | 8 endpoint |
| `backend/app/main.py` | Include 7 router |

**Tổng: 37 operation · 22 path · 32 schema.**

### Quyết định phạm vi (đã hỏi và chốt)

`forecasts` và `alerts` **không có POST/PUT tạo mới**:

| Bảng | Lý do |
|------|-------|
| `forecasts` | 3.000 dòng do M2 sinh ra bằng model tốt nhất từng cặp — tạo tay sẽ làm sai lệch dữ liệu đánh giá mô hình ở Chương 4 |
| `alerts` | Sinh từ hàm DB `fn_generate_inventory_alerts()` |

Cả hai vẫn có DELETE (không bảng nào tham chiếu tới chúng); alerts có thao tác trạng thái `read` / `resolve`.

### Ràng buộc nghiệp vụ đã xử lý

| Vấn đề | Xử lý |
|--------|-------|
| Xoá `stores` có đơn hàng | 409 + gợi ý `is_active = false` (FK `orders` RESTRICT) |
| Xoá `categories` còn nhóm con | 409 kèm số lượng — FK `SET NULL` sẽ làm nhóm con **bật lên 1 cấp**, hiếm khi là ý muốn người dùng |
| Xoá `categories` còn sản phẩm | 409 kèm số lượng (FK `products` RESTRICT) |
| Nhóm hàng làm cha của chính nó | 422 — DB **chấp nhận** nhưng tạo vòng lặp làm hỏng cây |
| Nhóm hàng chuyển dưới nhóm cháu | 422 — sẽ **cắt rời** cả nhánh khỏi gốc. Duyệt cây bằng BFS, không dùng CTE đệ quy |
| `alerts` CHECK `resolved_at` | Router gán `is_resolved` **và** `resolved_at` cùng lúc — set riêng sẽ bị DB từ chối với `IntegrityError` khó hiểu |
| `DELETE /forecasts` không có filter | 422 — bắt buộc có ít nhất 1 filter để 1 request gõ nhầm không xoá sạch 3.000 dòng |

### ⚠️ FastAPI khớp route THEO THỨ TỰ

Path đặc biệt phải khai báo **trước** path có tham số:

```python
# ĐÚNG
@router.get("/unread")        # trước
@router.get("/{alert_id}")    # sau

# SAI → alert_id: int không parse được "unread" → trả 422
@router.get("/{alert_id}")
@router.get("/unread")
```

Áp dụng cho: `/alerts/unread` · `/forecasts/latest` · `/inventory/expiring`.

### `/forecasts/latest` — sửa sau khi test phát hiện doc sai code

Bản đầu docstring ghi "tổng nhu cầu cả 30 ngày" và trả `total_predicted` + `days_ahead`. **Test cho thấy hành vi thật chỉ trả ngày mới nhất** (`days_ahead = 1`) → **doc sai với code**.

Đã sửa cho khớp:

| Trước | Sau |
|-------|-----|
| `total_predicted` | **`predicted_quantity`** (giá trị ngày mới nhất) |
| `days_ahead` (luôn = 1) | Bỏ — gây hiểu nhầm |
| — | Bổ sung `lower_bound` / `upper_bound` |
| "tổng 30 ngày" | "**KHÔNG phải** tổng 30 ngày" |
| Gom nhóm theo cặp | Nhiều model cùng ngày → chọn model **RMSE thấp nhất** (row không có RMSE không thắng row có RMSE) |

**Đã cross-check:** giá trị từ `/forecasts/latest` khớp chính xác dòng tương ứng trong `GET /forecasts?forecast_date=2018-01-30`.

### Endpoint `/inventory/expiring`

```
GET /api/v1/inventory/expiring?days=7&include_expired=true
```

| Quyết định | Lý do |
|------------|-------|
| Chỉ lô `quantity > 0` | Lô rỗng không thể hỏng, chỉ làm nhiễu báo cáo |
| `include_expired` mặc định **true** | Lô đã hết hạn là việc khẩn cấp nhất — ẩn đi là sai |
| `days_left` âm = đã hết hạn | Frontend tô màu khác nhau cho "đã hết hạn" và "sắp hết hạn" |

**Kết quả thật (12/10/2026):** `days=7` → **474 lô** (gồm đã hết hạn) · `include_expired=false` → **30 lô**.

### `alerts.title` chứa i18n key

Giá trị trả về là `alert.title.EXPIRED`, **không phải** text hiển thị. Dịch ở `backend/app/i18n/vi.json`. Lưu key trong DB giúp đổi ngôn ngữ mà không phải sửa dữ liệu.

### Kết quả test — toàn bộ PASS

| Nhóm | Số check | Kết quả |
|------|----------|---------|
| Stores | 14 | ✅ 200 · 201 · 409 trùng code · 422 sai `store_type` · 409 xoá có đơn |
| Categories | 15 | ✅ 8 nhóm · 5 gốc · Food có 3 con · 422 tự làm cha · 422 làm cha của cháu · 409 còn con |
| Inventory | 16 | ✅ 1.330 lô · `/expiring` 474 → 30 · 409 trùng bộ 3 khoá · 422 store/sản phẩm sai · 422 số lượng âm |
| Forecasts | 14 | ✅ 3.000 dòng · 150 trang · lọc theo model · 422 model lạ · 422 xoá không filter · `/latest` 100 cặp |
| Alerts | 22 | ✅ 518 · lọc type/severity · 422 giá trị lạ · `/unread` · `/unread-count` · đọc idempotent · resolve gán `resolved_at` · reopen xoá `resolved_at` |

**Trạng thái cuối — dữ liệu về đúng nguyên trạng:** stores 10 · categories 8 · inventory 1.330 · forecasts 3.000 · alerts 518 · products 50.

### ⚠️ Test làm bẩn dữ liệu — đã khôi phục

Test `/read` và `/resolve` đổi cờ thật trên `alert_id = 1` → `unread` giảm 518 → 517. Đã khôi phục:

```sql
UPDATE alerts SET is_read = FALSE, is_resolved = FALSE, resolved_at = NULL;
```

Đã thêm bước khôi phục **vào cuối file test** để chạy lại nhiều lần vẫn giữ dữ liệu sạch.

> **Bài học (nhắc lại từ B3):** endpoint đổi trạng thái ghi vào DB thật. Test phải có cleanup, nếu không chạy 2 lần sẽ cho kết quả sai.

### Sai lầm của tôi trong lúc làm — đã sửa hết

| Sai lầm | Xử lý |
|---------|-------|
| Gõ sai ký tự trong đường dẫn `Đồ án TN` → tạo nhầm thư mục `Ēồ án TN` ngoài workspace | Xoá ngay, xác minh Desktop chỉ còn `Đồ án TN` |
| Import `ProductBrief` nhưng class trong file tên `CategoryBrief` | Tạo `ProductBrief` thật trong `product_schema.py` |
| Định nghĩa `CategoryBrief` ở cả 2 file | Xoá bản trùng trong `category_schema.py` |
| Viết `HTTP_422_UNPROCESSABLE_CONTENT if (HTTP_422 := 422) else 422` | Thay bằng hằng số rõ ràng |
| Để lại dòng vô nghĩa `alert = ... if False else None` | Xoá |

### Không chụp được màn hình Swagger UI

`browser.screenshot` báo *"needs a visible tab"* — cửa sổ desktop không hiển thị. Đã xác minh thay bằng cách đọc `openapi.json`: **OpenAPI 3.1.0 · 22 path · 37 operation · 32 schema**, tất cả path đúng như thiết kế.

### Việc tiếp theo — B5

Endpoint dashboard tổng hợp cho trang chủ frontend: tổng doanh thu · tổng tồn kho · số cảnh báo theo mức độ · sản phẩm sắp hết hạn.

---

## 8m. B3 — API CRUD Products (12/10/2026) ✅

### Files đã tạo

| File | Nội dung |
|------|----------|
| `backend/app/schemas/product_schema.py` | 6 Pydantic schema |
| `backend/app/schemas/__init__.py` | Export schemas |
| `backend/app/routers/product_router.py` | 5 endpoint CRUD |
| `backend/app/main.py` | Thêm `include_router(product_router.router, prefix="/api/v1")` |
| `database/03-migrations/005-fix-sequences.sql` | **Mới** — sửa bug sequence (xem mục bên dưới) |

### 5 endpoint

| Method | Path | Chức năng |
|--------|------|-----------|
| GET | `/api/v1/products` | Danh sách + phân trang + lọc + tìm kiếm |
| GET | `/api/v1/products/{id}` | Chi tiết |
| POST | `/api/v1/products` | Tạo mới |
| PUT | `/api/v1/products/{id}` | Cập nhật một phần |
| DELETE | `/api/v1/products/{id}` | Xoá (409 nếu đã có lịch sử) |

**Quyết định thiết kế:**

| Quyết định | Lý do |
|------------|-------|
| Phân trang mặc định 20, tối đa 100 | `joinedload(Product.category)` chạy cho mỗi dòng — trả 1000 dòng sẽ nặng |
| Response trả **object** `{total, page, page_size, pages, items}` | Frontend cần tổng số bản ghi để vẽ phân trang, không cần gọi thêm API đếm |
| `PUT` dùng `exclude_unset=True` | Cho phép gửi một phần; trường không gửi giữ nguyên, không phải ghi `null` |
| Validator `max_stock >= min_stock` trong Pydantic | Chặn ở tầng schema với thông báo rõ tên trường, thay vì để `IntegrityError` lọt lên thành 500 |
| DELETE trả **409** kèm gợi ý | FK `ON DELETE RESTRICT` — đúng nghiệp vụ, lịch sử bán hàng không được xoá âm thầm |

### 🐛 Bug nghiêm trọng tìm ra khi test POST — bug sequence

**Triệu chứng:** POST trả 409 ngay lần đầu, dù `SP-TEST-9999` chắc chắn chưa tồn tại.

**Debug trực tiếp:**

```
LOI: IntegrityError
ORIG: duplicate key value violates unique constraint "products_pkey"
DETAIL: Key (product_id)=(2) already exists.
```

**Đối chiếu:**

| Đối tượng | Giá trị |
|---|---|
| `products_product_id_seq.last_value` | **2** |
| `MAX(products.product_id)` | **50** |

**Nguyên nhân:** trước đây đã `TRUNCATE ... RESTART IDENTITY` rồi import lại dữ liệu 5 năm bằng insert **chỉ định `product_id` từ Kaggle**. PostgreSQL **không tự đẩy sequence** khi insert có giá trị khóa chính tường minh. Sequence bị bỏ lại ở giá trị 2.

**Hệ quả:** mọi `INSERT` mới sẽ lấy id 2, 3, 4… đã tồn tại → **luôn lỗi**. API tạo sản phẩm không thể hoạt động.

#### Cách sửa — migration 005

Tạo `database/03-migrations/005-fix-sequences.sql` dùng `DO` block + `setval()`, **kiểm tra tất cả 10 bảng** chứ không chỉ `products`:

| Bảng | seq trước | max | Kết quả |
|------|-----------|-----|---------|
| `users` | 1 | 3 | **FIXED** |
| `stores` | 1 | 10 | **FIXED** |
| `categories` | 1 | 8 | **FIXED** |
| `products` | 2 | 50 | **FIXED** |
| `inventory` | 1330 | 1330 | ok |
| `inventory_transactions` | 11412 | 11412 | ok |
| `orders` | 18260 | 18260 | ok |
| `order_items` | — | — | không có sequence (BIGSERIAL) |
| `forecasts` | 3000 | 3000 | ok |
| `alerts` | 518 | 518 | ok |

→ **4 sequence sai.** 5 bảng còn lại đã đúng sẵn (vì seed dùng sequence tự sinh).

**Đã kiểm chứng:**
- File thuần ASCII (0 byte > 127)
- Backup 65 MB trước khi chạy
- **Idempotent**: chạy lần 2 fix 0 sequence, không báo lỗi
- Số dòng 10 bảng **không đổi** sau migration

→ **Bài học:** sau mỗi lần import dữ liệu hàng loạt bằng insert chỉ định khóa chính, **phải chạy migration 005**. Đã ghi vào AGENTS.md.

### Lỗi của tôi trong lúc làm (đã sửa, đã báo)

| Lỗi | Nguyên nhân | Hậu quả |
|---|---|---|
| `NameError: name 'product' is not defined` tại `db.refresh()` | Rút gọn dòng `Product(**...)` thành `db.add(Product(...))` nhưng dòng `db.refresh(product)` vẫn còn | **POST trả 500 nhưng bản ghi ĐÃ được commit** → còn 51 sản phẩm trong DB |
| `[winerror 10048] only one usage of each socket address` | Server cũ chưa chết, server mới không bind được | Test chạy vào **code cũ** |
| `Total: 51` trong lần chạy test sau | Hệ quả của lỗi `NameError` ở trên | Phải `DELETE` bản ghi thừa |

**Bài học quan trọng:** lỗi xảy ra **sau `db.commit()`** thì **không rollback được** — dữ liệu đã ghi vĩnh viễn. Log server cho thấy rõ:

```
POST /api/v1/products  → 500 Internal Server Error   (NameError)
POST /api/v1/products  → 409 Conflict                (đã tạo xong trong lần trước)
```

Nếu test fail, **phải kiểm tra dữ liệu thừa** trước khi chạy lại — không phải chỉ sửa code.

### Kết quả test cuối — 27/27 PASS

| Nhóm | Kiểm tra | Kết quả |
|------|----------|---------|
| **GET list** | 200 · total=50 · pages=3 · 20 item/trang | ✅ |
| | Trang 3 (trang cuối) → 10 item | ✅ |
| | Lọc `category_id=3` → 11 SP, tất cả đều đúng category | ✅ |
| | Tìm `search=kem` → `Kem chong nang`, `Kem danh rang` | ✅ |
| | Lọc `is_active=false` → 0 | ✅ |
| **GET detail** | 200 · SP0045 · han=730 ngày · Baby Care | ✅ |
| | ID không tồn tại → 404 | ✅ |
| **POST** | 201 · tạo được · `is_perishable` mặc định `true` | ✅ |
| | Trùng `product_code` → 409 | ✅ |
| | `category_id=999` → 422 | ✅ |
| | `max_stock < min_stock` → 422 | ✅ |
| **PUT** | 200 · đổi `selling_price` + `supplier` | ✅ |
| | Trường không gửi → giữ nguyên | ✅ |
| | Body rỗng `{}` → 200, không đổi gì | ✅ |
| | Đổi sang `product_code` đã có → 409 | ✅ |
| **DELETE** | Sản phẩm mới → 204, body rỗng | ✅ |
| | Xoá xong → GET trả 404 | ✅ |
| | Sản phẩm 45 (đã có lịch sử) → **409** kèm gợi ý dùng `is_active=false` | ✅ |
| | SP45 vẫn còn sau khi DELETE thất bại | ✅ |
| **Cuối** | Tổng sản phẩm quay về **50** | ✅ |

Dữ liệu 10 bảng sau test **không đổi** (912.999 order_items · 18.260 orders · 50 products · …).

### Sửa warning deprecation

Starlette đã đổi `HTTP_422_UNPROCESSABLE_ENTITY` → `HTTP_422_UNPROCESSABLE_CONTENT`. Log hiện:

```
StarletteDeprecationWarning: 'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated.
```

Đã dùng hằng `HTTP_422_UNPROCESSABLE_CONTENT = 422` trong router. Chạy lại → log sạch, không còn warning.

### Đã chụp màn hình Swagger UI

`http://localhost:8000/docs` hiển thị đủ:
- Nhóm `health`: 3 endpoint
- Nhóm `products`: 5 endpoint (GET / POST / GET-id / PUT / DELETE với màu đúng phương thức)
- Nhóm `Schemas`: `CategoryBrief` · `ProductCreate` · `ProductPage` · `ProductRead` · `ProductUpdate` · `HTTPValidationError` · `ValidationError`

### Việc tiếp theo — B4

CRUD cho `stores` · `categories` · `inventory` · `forecasts` · `alerts`. Cùng pattern: schema Pydantic + router ORM + `Depends(get_db)`.

---

## 8l. B2 — Viết SQLAlchemy Models (12/10/2026) ✅

### Files đã tạo — 11 file

| File | Bảng | Số cột |
|------|------|--------|
| `backend/app/models/store.py` | `stores` | 10 |
| `backend/app/models/category.py` | `categories` | 6 |
| `backend/app/models/user.py` | `users` | 10 |
| `backend/app/models/product.py` | `products` | 14 |
| `backend/app/models/inventory.py` | `inventory` | 9 |
| `backend/app/models/inventory_transaction.py` | `inventory_transactions` | 13 |
| `backend/app/models/order.py` | `orders` | 12 |
| `backend/app/models/order_item.py` | `order_items` | 9 |
| `backend/app/models/forecast.py` | `forecasts` | 14 |
| `backend/app/models/alert.py` | `alerts` | 13 |
| `backend/app/models/__init__.py` | — | Export 10 model + `Base` |

Dùng SQLAlchemy 2.x hiện đại: `Mapped[]` + `mapped_column()` (không dùng `Column()` kiểu cũ).

### 3 điểm kỹ thuật bắt buộc xử lý riêng

#### 1. `order_items.line_total` là GENERATED COLUMN

Trong DB:

```sql
line_total numeric(18,2) generated always as
  (round(quantity * unit_price * (1::numeric - discount_percent / 100::numeric), 2)) stored
```

**Không map như cột thường.** Phải dùng:

```python
line_total: Mapped[float] = mapped_column(
    Numeric(18, 2),
    Computed("round(quantity * unit_price * (1::numeric - discount_percent / 100::numeric), 2)",
             persisted=True),
)
```

Nếu gán giá trị tay → PostgreSQL báo lỗi *"cannot update a generated column"*. Đây là ưu điểm: không thể nào tính tay sai lệch với công thức.

**Đã kiểm chứng:** `quantity=13.000 × unit_price=20000.00 × (1 − 0/100)` → DB trả `260000.00`, tính tay ra `260000.0` → **KHỚP**.

#### 2. `categories` tự tham chiếu

`parent_category_id` trỏ về chính bảng `categories`. Phải chỉ rõ `remote_side` ở chiều "cha", nếu không SQLAlchemy không biết đâu là cha:

```python
parent: Mapped["Category | None"] = relationship(
    "Category", back_populates="children",
    remote_side="Category.category_id",       # BẮT BUỘC
    foreign_keys=[parent_category_id],
)
children: Mapped[list["Category"]] = relationship(
    "Category", back_populates="parent",
    foreign_keys=[parent_category_id],
)
```

**Đã kiểm chứng:** `Food` có 3 nhóm con — `Fresh Food` (10 sản phẩm), `Beverages` (11), `Snacks` (10). `Food` bản thân có 0 sản phẩm vì sản phẩm được gán vào nhóm con.

#### 3. Cột `NUMERIC` trả về `Decimal`

Không phải `float`. Khi tính toán phải ép kiểu:

```python
TypeError: unsupported operand type(s) for -: 'float' and 'decimal.Decimal'
```

Đã gặp lỗi này khi viết script kiểm tra. Sửa bằng cách ép `float()` **cả hai vế** trước khi trừ.

### Kết quả test — 10/10 bảng đọc qua ORM

| Bảng | Số dòng | | Bảng | Số dòng |
|------|----------|---|------|----------|
| `order_items` | 912.999 | | `inventory` | 1.330 |
| `orders` | 18.260 | | `inventory_transactions` | 11.412 |
| `forecasts` | 3.000 | | `alerts` | 518 |
| `products` | 50 | | `stores` | 10 |
| `categories` | 8 | | `users` | 3 |
| | | | **TỔNG** | **947.590** |

**Đối chiếu `pg_stat_user_tables` — khớp tuyệt đối 10/10 bảng.** Không sửa schema DB, chỉ đọc.

### Test relationship (Bước 5)

`Order → store` (JOIN tự động, không viết SQL):

| order_code | store_name | total_amount | status |
|------------|-----------|--------------|--------|
| ORD-2013-000001 | Cửa hàng tiện lợi Q.3 | 37.390.000,00 | completed |
| ORD-2013-000002 | Cửa hàng tiện lợi Bình Thành | 51.260.000,00 | completed |
| ORD-2013-000003 | Cửa hàng tiện lợi Thủ Đức | 46.990.000,00 | completed |
| ORD-2013-000004 | Cửa hàng tiện lợi Tân Bình | 40.190.000,00 | completed |
| ORD-2013-000005 | Cửa hàng tiện lợi Hai Bà Trưng | 30.535.000,00 | completed |

Quan hệ nhiều tầng `Order → items → product` cũng chạy:

```
ORD-2013-000001 có 50 dòng chi tiết
  Rau muống tươi   x13.000 =    260.000,00
  Rau cải thường   x33.000 =    660.000,00
  Khoai lang       x15.000 =    300.000,00
```

Quan hệ ngược từ `Store`: `CH01` có 1 user · 133 lô tồn kho · 48 cảnh báo · 300 dự báo.

### Lỗi của tôi trong lúc test (đã sửa, không ảnh hưởng model)

| Lỗi | Nguyên nhân |
|---|---|
| `TypeError: unsupported operand type(s) for -: 'float' and 'decimal.Decimal'` | Ép `float()` một vế trong script test |
| `AttributeError: 'NoneType' object has no attribute 'products'` | Đoán tên nhóm hàng là `"Drinks"` — nhưng DB dùng **tiếng Anh** (`Food`, `Fresh Food`, `Beverages`). Phải query `categories` trước, không đoán |

### ✅ Quyết định ngôn ngữ comment trong code (12/10/2026)

**GIỮ TIẾNG ANH KHÔNG DẤU cho toàn bộ code Python.**

Trước đây rule 11 ghi "comment tiếng Việt", mâu thuẫn với thực tế đang làm. Đã chốt lại:

| Nhóm file | Ngôn ngữ comment | Lý do |
|-----------|------------------|-------|
| **Code Python** (`.py`) | **Tiếng Anh không dấu** | Console Windows cp1252 không in được tiếng Việt có dấu → gây `UnicodeEncodeError` khi hiện traceback hoặc log ra terminal |
| **Tài liệu `.md`** | Tiếng Việt có dấu | Không chạy qua console, GitHub render UTF-8 bình thường |
| **File SQL** | ASCII tiếng Anh | Quy tắc riêng — `psql -f` trên Windows PowerShell |

**Lý do chọn:**

1. Console cp1252 không hỗ trợ tiếng Việt — đã gặp `UnicodeEncodeError: 'charmap' codec` nhiều lần trong quá trình làm
2. 11 file models + 4 file Python trước đó đã dùng tiếng Anh không dấu — sửa ngược lại tốn công và gây thiếu nhất quán
3. Chuẩn quốc tế — dự án thật đều comment tiếng Anh
4. Thể hiện hiểu đúng giới hạn môi trường, là điểm cộng khi bảo vệ đồ án

→ **Không sửa 11 file models + 4 file Python cũ** — chúng vốn đã đúng chuẩn mới.

### Ghi chú thêm — `updated_at` không cần set trong Python

Bảng có trigger `trg_*_updated BEFORE UPDATE ... EXECUTE FUNCTION fn_update_updated_at()`. DB tự cập nhật `updated_at` khi UPDATE, không cần gán tay trong ORM (không dùng `onupdate=`).

### Việc tiếp theo — B3

Tạo endpoint nghiệp vụ dưới prefix `/api/v1/`: sản phẩm · tồn kho · dự báo · cảnh báo. Dùng `Depends(get_db)`. **Không viết raw SQL trong routers.**

---

## 8k. B1 — Setup backend FastAPI (12/10/2026) ✅

### Cài thư viện

```powershell
pip install fastapi "uvicorn[standard]" pydantic pydantic-settings sqlalchemy psycopg2-binary
```

`sqlalchemy` và `psycopg2-binary` đã có sẵn. Phiên bản sau khi cài:

| Thư viện | Phiên bản |
|----------|-----------|
| FastAPI | 0.143.0 |
| uvicorn | 0.54.0 (`[standard]` — kèm websockets cho realtime) |
| pydantic | 2.14.1 |
| pydantic-settings | 2.15.0 |
| SQLAlchemy | 2.1.2 (có sẵn) |
| psycopg2-binary | 2.9.13 (có sẵn) |

### Files đã tạo

| File | Vai trò |
|------|--------|
| `backend/requirements.txt` | 7 thư viện, ghim phiên bản |
| `backend/app/config.py` | Đọc `.env` qua pydantic-settings · `@lru_cache` · property `database_url` |
| `backend/app/database.py` | `create_engine` + `SessionLocal` + `Base(DeclarativeBase)` + `get_db()` + `check_database()` |
| `backend/app/main.py` | Khởi tạo FastAPI + CORS middleware + gắn router |
| `backend/app/routers/health.py` | 2 endpoint health check |
| `backend/app/__init__.py` | Package marker |
| `backend/app/routers/__init__.py` | Package marker |

### Endpoint (đều test thật qua HTTP)

| Endpoint | Kết quả test |
|----------|-------------|
| `GET /` | 200 OK |
| `GET /health` | 200 OK — `{"status":"ok"}` |
| `GET /health/database` | 200 OK — `"connected": true` |
| `GET /docs` | 200 OK — Swagger UI render bình thường |
| `GET /redoc` | 200 OK |
| `GET /openapi.json` | 200 OK — OpenAPI 3.1.0, 2 paths |

**CORS đã test:** header `Access-Control-Allow-Origin: http://localhost:3000` trả về đúng; preflight `OPTIONS` trả `200` với `Allow-Methods: DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT, QUERY`.

### Endpoint nào KHÔNG có tiền tố `/api/v1/`?

`/health` và `/health/database` **cố ý không** dùng tiền tố — chúng thuộc hạ tầng (kiểm tra server), không phải API nghiệp vụ.

Mọi API nghiệp vụ từ B3 trở đi **bắt buộc** dùng `settings.API_V1_PREFIX` = `/api/v1`.

### Đã tạo file `.env` ở thư mục gốc

`.env` đã có sẵn trong `.gitignore` (`git check-ignore -v .env` xác nhận). Nội dung:

```
DB_USER / DB_PASSWORD / DB_HOST / DB_PORT / DB_NAME
CORS_ORIGINS=["http://localhost:3000", ...]
```

**Xác minh:** backend chạy được mà **không cần** set `$env:DB_PASSWORD` — đã test bằng cách xoá biến môi trường rồi khởi động uvicorn, kết quả `"connected": true`.

### Lỗi / bất ngờ đã gặp

| Vấn đề | Giải thích | Xử lý |
|---------|-----------|-------|
| `app.routes` không liệt kê `/health` | **FastAPI 0.143 đổi cách `include_router`** — giờ tạo đối tượng `_IncludedRouter` thay vì flatten endpoint vào `app.routes` | **ĐỪNG kiểm tra `app.routes`** để xác nhận router. Gọi thật qua HTTP mới đáng tin |
| `ModuleNotFoundError: No module named 'app'` | Chạy `python -c "from app.main import ..."` từ thư mục gốc | Phải `cd backend` trước — module import tuyệt đối `from app.config import settings` |
| `UnicodeEncodeError: 'charmap' codec` | In `repr(module)` có đường dẫn tiếng Việt ra console cp1252 | `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` hoặc set `$env:PYTHONIOENCODING="utf-8"` |

### Cải thiện trong lúc làm

`check_database()` ban đầu trả `bool`. Đã đổi thành trả `(bool, str | None)`:

- Trả **tên lớp exception** (`OperationalError`, `InterfaceError`…) để chẩn đoán được
- **KHÔNG** trả `str(exc)` — message psycopg2 có thể chứa thông tin kết nối nhạy cảm, không nên đưa vào HTTP response

Test với mật khẩu sai (port 8001):

```json
{"status":"degraded","database":{"host":"localhost","port":5432,
 "database":"spoilage_predictor","connected":false,"error":"OperationalError"}}
```

Đồng thời `GET /health` vẫn trả `"status":"ok"` — server không crash khi DB hỏng, phù hợp thiết kế health check.

### Đã sửa trong AGENTS.md

- Bảng môi trường: thêm FastAPI/uvicorn/pydantic/pydantic-settings
- Sửa "Database đang rỗng" → "**đã có dữ liệu** (912.999 `order_items` · 3.000 `forecasts`)"
- Bỏ dòng "Còn thiếu: fastapi, uvicorn, pydantic"
- Thêm gotcha: `_IncludedRouter`, `cd backend`, `.env`, console cp1252

### Bổ sung lần 2 (12/10/2026) — chỉnh theo yêu cầu mới

B1 đã xong ở commit `0ca104d`. Lần này chỉ bổ sung 4 điểm còn thiếu:

| Việc | Kết quả |
|------|---------|
| Tạo `backend/.env.example` | ✅ Mới — mẫu cấu hình, `DB_PASSWORD=your_password_here` (không phải mật khẩu thật) |
| Thêm `GET /api/v1/health` | ✅ Mới — giữ cả `/health` cho hạ tầng |
| Thêm key `"message"` cho `GET /` | ✅ Mới — `{"message": "API dang chay", ...}` |
| Chụp m��nh `/docs` | ✅ Xong — Swagger UI hiển thị đủ 3 endpoint |

**Quyết định đã chốt khi hỏi lại:**

| Câu hỏi | Quyết định | Lý do |
|---------|-----------|-------|
| Vị trí `.env` thật | **Giữ ở thư mục gốc** | Script AI/ML cũng đọc từ đó — chuyển đi sẽ phá vỡ |
| Endpoint health | **Cả hai** `/health` và `/api/v1/health` | Tuân thủ quy tắc tiền tố mà vẫn giữ được endpoint uptime check |
| Response `GET /` | **Thêm key `message`, giữ thông tin khác** | Không mất link `/docs` và `/health` |

#### Lỗi thật: `CORS_ORIGINS` dạng dấu phẩy sẽ gây lỗi cho người clone repo

`backend/.env.example` dùng dạng thân thiện:

```
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

Nhưng `config.py` khai báo `CORS_ORIGINS: list[str]`. Biến môi trường **luôn là chuỗi**, pydantic-settings chỉ đọc chuỗi đó theo **dạng JSON** → sẽ báo:

```
ValidationError: Input should be a valid list [type=list_type]
```

Nghĩa là **file `.env.example` sẽ làm hỏng người dùng khác sau khi copy**, dù file mẫu trông đúng.

**Đã thử 2 hướng:**

| Hướng | Kết quả |
|-------|---------|
| `@field_validator(mode="before")` | ❌ **Không hoạt động** — validator không can thiệp được vào env source của pydantic-settings, vẫn `ValidationError` |
| Khai báo `str` + `property` tách thủ công | ✅ **Chạy đúng** |

Cách đã dùng trong `config.py`:

```python
CORS_ORIGINS: str = ",".join(DEFAULT_CORS_ORIGINS)

@property
def cors_origins(self) -> list[str]:
    raw = self.CORS_ORIGINS.strip()
    if raw.startswith("["):
        try:  # thu doc dang JSON truoc
            import json
            parsed = json.loads(raw)
            ...
        except (ValueError, TypeError):
            pass
    return [item.strip() for item in raw.split(",") if item.strip()]
```

**Test 4 trường hợp — tất cả đúng:**

| Input | Kết quả |
|-------|---------|
| `http://a:3000,http://b:5173` (dấu phẩy) | `['http://a:3000', 'http://b:5173']` |
| `["http://a:3000","http://b:5173"]` (JSON) | `['http://a:3000', 'http://b:5173']` |
| `http://a:3000` (một giá trị) | `['http://a:3000']` |
| `""` (rỗng) | `[]` |
| Không cấu hình (xoá dòng khỏi `.env`) | 4 origin mặc định |

⚠️ **Phân biệt quan trọng — rỗng KHÁC không cấu hình:**

| Trong `.env` | `cors_origins_list` | Hậu quả |
|---|---|---|
| `CORS_ORIGINS=` (để trống) | `[]` | **Fail-closed** — chặn MỌI origin, frontend sẽ báo lỗi CORS |
| Xoá hẳn dòng | 4 origin mặc định | Dùng `localhost:3000` / `:5173` |

Rỗng là fail-closed là đúng về mặt bảo mật, nhưng dễ gây khó chẩn đoán. Muốn dùng mặc định thì **xoá hẳn dòng**, đừng để trống.

### Chỉnh tên property + sửa comment sai trong `.env.example`

| Việc | Trước | Sau |
|------|-------|-----|
| Tên property | `settings.cors_origins` | **`settings.cors_origins_list`** (khớp yêu cầu) |
| `main.py` | `allow_origins=settings.cors_origins` | `allow_origins=settings.cors_origins_list` |
| Comment `.env.example` | *"Phải là JSON hợp lệ vì config.py đọc vào biến kiểu list"* — **SAI, đã lỗi thời** | Ghi rõ hỗ trợ cả 2 định dạng, trỏ tới property |

### Test backend sau khi sửa — 4/4 endpoint 200 OK

| Endpoint | Kết quả |
|----------|---------|
| `GET /` | 200 — `{"message":"API dang chay", ...}` |
| `GET /api/v1/health` | 200 — `{"status":"ok"}` |
| `GET /health` | 200 — `{"status":"ok"}` |
| `GET /health/database` | 200 — `"connected": true` |

**CORS header:**

| Origin gửi lên | Header trả về |
|----------------|---------------|
| `http://localhost:3000` | `http://localhost:3000` ✅ |
| `http://localhost:5173` | `http://localhost:5173` ✅ |
| `http://evil.com` | *(rỗng)* — bị chặn đúng ✅ |

Test origin lạ bị chặn xác nhận cấu hình CORS **không bật `allow_origins=["*"]`** — không mở cho tất cả.

### Kết quả test cuối — 6/6 endpoint 200 OK

| Endpoint | Kết quả |
|----------|---------|
| `GET /` | 200 — `{"message":"API dang chay", ...}` |
| `GET /api/v1/health` | 200 — `{"status":"ok"}` |
| `GET /health` | 200 — `{"status":"ok"}` |
| `GET /health/database` | 200 — `"connected": true` |
| `GET /docs` | 200 — Swagger UI, 3 endpoint hiển thị đúng |
| `GET /openapi.json` | 200 — 3 paths: `/health`, `/health/database`, `/api/v1/health` |

### Việc tiếp theo — B2

Viết ORM models trong `backend/app/models/` cho 10 bảng, kế thừa `Base` từ `app/database.py`. Sau đó B3 mới tạo endpoint nghiệp vụ dưới `/api/v1/`.

---

## 8j. ⛔ Quyết định 03/10/2026 — viết Chương 4 thế nào

Hai vấn đề phát hiện sau M1/M2 đã được quyết định: **giữ nguyên dữ liệu và tài liệu, ghi chú vào Chương 4.**

### Quyết định 1 — KHÔNG sửa Chương 2

Chương 2 chốt **XGBoost = mô hình chính**. Kết quả thực nghiệm: **Prophet thắng 97/100 cặp**.

| | |
|---|---|
| Chương 2 (lý thuyết) | XGBoost là mô hình chính — **giữ nguyên** |
| Chương 4 (thực nghiệm) | Trình bày kết quả thật: Prophet thắng |

**Lý do không sửa Chương 2:**

| # | Lý do |
|---|-------|
| 1 | Chương 2 là cơ sở lý thuyết — trình bày cả 5 mô hình, **không cần chốt** model nào là chính |
| 2 | Chương 4 là kết quả thực nghiệm — nói đúng điều thực nghiệm cho thấy |
| 3 | Dự đoán ban đầu ≠ kết quả thực tế → **thể hiện quá trình nghiên cứu khoa học** |
| 4 | GVHD đánh giá cao sự trung thực |

**Cách viết ở Chương 4 — phải nêu 3 điều:**

1. **Nêu rõ đảo ngược kỳ vọng.** Đừng lấp đầy bằng cách sửa giả định ban đầu — đó là giấu dấu vết nghiên cứu.
2. **Giải thích cơ chế, không chỉ nêu kết quả:**

   | Mô hình | Đặc điểm | Hệ quả khi dự báo 30 ngày |
   |---------|-----------|---------------------------|
   | XGBoost | Phụ thuộc `lag_1..lag_28` | Phải **đệ quy** — dùng giá trị dự báo ngày trước cho ngày sau → sai lệch tích luỹ dần |
   | Prophet | Mô hình **đa bước** sẵn có | Không gặp hạn chế này |

   Ngoài ra XGBoost chỉ thắng 3/100 cặp, và ở **59 cặp chênh lệch < 1,0 RMSE** — tức dưới 1 sản phẩm/ngày trên quy mô bán ~1.000/ngày, không có ý nghĩa nghiệp vụ.
3. **Kết luận:** triển khai Prophet làm mô hình chính.

### Quyết định 2 — KHÔNG sửa `max_stock` trong seed

| | |
|---|---|
| `max_stock` trong seed | 48 – 300 (đặt **độc lập** với doanh số Kaggle) |
| Nhu cầu thực tế | 861 – 2.793 / ngày |
| → `max_stock` tương đương | **0,5 – 3 ngày bán** |
| Hệ quả | **100/100 cặp bị cap** |
| Tổng nhu cầu thuần | 232.397 |
| Tổng đề xuất nhập sau cap | 7.286 |

**Đây là hạn chế của dữ liệu, KHÔNG phải lỗi đồ án.** Sửa `max_stock` phải seed lại `inventory` — tốn thời gian, không đáng.

**Cách viết ở Chương 4 — phải nêu rõ:**
- `recommended_import_qty` trong DB **bị nén bởi `max_stock`, không phản ánh đúng nhu cầu dự báo**
- Cột `raw_need` trong `ai-model/outputs/forecast_summary_30d.csv` giữ nhu cầu chưa cap để đối chiếu
- **Nếu không nói rõ, người đọc sẽ hiểu nhầm rằng mô hình dự báo thiếu chính xác**

---

## 8h. Kết thúc phiên làm việc 03/10/2026 (phiên trước)

### Trạng thái Git

| Mục | Kết quả |
|-----|---------|
| Commit cuối | `f46e479` — "docs: cap nhat tien do ngay 03/10/2026" |
| Working tree | Sạch, khớp 100% với `origin/main` |
| Số commit từ đầu dự án | 13 |

### Kiểm tra bảo toàn dữ liệu

| Bảng | Số dòng |
|------|---------|
| `categories` | 8 |
| `stores` | 10 |
| `products` | 50 |
| `users` | 3 |
| `orders` | 18.260 |
| `order_items` | 912.999 |
| `inventory` | 1.330 |
| `inventory_transactions` | 11.412 |
| `alerts` | 518 |
| `forecasts` | **0** ← đang chờ chạy 100 cặp |

### Đã làm trong phiên 03/10

1. Import lại dataset Kaggle **5 năm** (2013–2017) — 912.999 dòng, đối chiếu khớp tuyệt đối với CSV
2. Sửa `train_models.py`: reindex 1.826 ngày, tách tập theo mốc `2017-10-01`, CSV phẳng
3. Tune Prophet trên 5 năm → `cps=0.01, multiplicative, yearly=20`
4. Kiểm chứng giả thuyết: Prophet RMSE **23,20 → 9,98** (−57%), từ hạng 3 lên hạng 1

### Việc tiếp theo (chờ duyệt)

| Mã | Việc | Ước lượng |
|----|------|-----------|
| M1 | Chạy 100 cặp (10 sản phẩm × 10 cửa hàng) | ~9 phút |
| M2 | Dự báo 30 ngày 01/01–30/01/2018 + tính `recommended_import_qty` + ghi bảng `forecasts` | ~3 phút |
| M3 | Tạo `docs/05-tham-khao/ket-qua-danh-gia-model.md` | ~10 phút |
| B1 | Setup backend FastAPI (cần cài `fastapi`, `uvicorn`, `pydantic`) | |

**Sau khi M1–M3 xong**, có thể viết Chương 3 và Chương 4 của báo cáo.

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
| ~~**Thuật ngữ trong Chương 2**~~ | ✅ **Đã xử lý** — Chương 2 **không nhắc tên bảng nào** (0 lần `inventory_transactions`, 0 lần `sales`). Vấn đề thật nằm ở comment SQL, đã sửa qua migration 004. Xem mục 8e |
| ~~`unit_price = 0` trong import~~ | ✅ **Đã xử lý** — chuyển sang gán giá mô phỏng theo nhóm hàng (mục 8b) |
| ~~**Vai trò mô hình (XGBoost vs Prophet)**~~ | ✅ **Đã xử lý** — giữ nguyên Chương 2, giải thích ở Chương 4. Xem mục 8j |
| ~~**`max_stock` không khớp thang đo Kaggle**~~ | ✅ **Đã xử lý** — giữ nguyên seed, ghi chú hạn chế ở Chương 4. Xem mục 8j |
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

# Backend — PHẢI cd backend trước
cd backend; python -m uvicorn app.main:app --reload --port 8000
# Test: http://localhost:8000/docs

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
11. File Python: `snake_case` · Component React: `PascalCase` · **Comment code Python dùng tiếng Anh không dấu** (tương thích cp1252 — quyết định 12/10/2026). Tài liệu `.md` và SQL giữ tiếng Việt / ASCII theo quy tắc riêng
12. Trước khi commit chạy `git status`
13. 🔒 Không ghi mật khẩu vào bất kỳ file nào trong repo

---

## 13. Việc còn lại (cập nhật sau B4 — 12/10/2026)

| Mã | Việc | Ưu tiên |
|----|------|---------|
| **B5** | Endpoint dashboard tổng hợp (doanh thu · tồn kho · cảnh báo) | 🔴 Tiếp theo |
| **F1** | Setup Frontend React | 🟡 Sau B5 |
| T4.3 | Viết Chương 3 — Thiết kế hệ thống | 🟡 |
| T4.4 | Viết Chương 4 — Thực nghiệm (**đọc mục 8j trước khi viết**) | 🟡 |
| T2 | README con cho từng thư mục | 🟢 |

**Chưa có Chương 3 và Chương 4.** Đã đủ căn cứ: M1–M3 + backend FastAPI + 10 ORM model + **37 API endpoint**.

**Khi viết Chương 4, BẮT BUỘC đọc mục 8j** — đã có 2 quyết định không sửa dữ liệu/tài liệu mà chỉ ghi chú.

**Ngôn ngữ comment code Python:** ✅ đã chốt — **tiếng Anh không dấu**. Xem mục 8l.

**Sau khi import dữ liệu hàng loạt:** chạy `database/03-migrations/005-fix-sequences.sql`. Xem mục 8m.

---

## 8s. B10 + B11 + B12 (12/10/2026) — Phiên gộp 3 task backend

### Kết quả

| Task | Nội dung | Kết quả |
|------|----------|---------|
| **B10** | `recommendation_router.py` — 3 endpoint (import · expiring · slow-moving) | PASS |
| **B11** | `report_router.py` — 4 endpoint × 3 định dạng (CSV · XLSX · PDF) | PASS |
| **B12** | `auth_router.py` + `security.py` + `dependencies.py` — login · refresh · me · logout · change-password, bảo vệ **28** endpoint ghi | PASS |

**Bộ test mới:** `backend/test_b10_b11_b12.py` — **190 check PASS**.
Chạy lại toàn bộ: **B6 155 OK · B7 115 OK · B8 121 OK · B10/11/12 190 OK**.

---

### Sai lầm của tôi trong phiên này (ghi lại để không lặp lại)

| # | Sai lầm | Cách phát hiện | Sửa |
|---|---------|----------------|-----|
| 1 | Dùng `__import__("app.models", fromlist=[...])` thay cho import bình thường trong `recommendation_router.py` và `report_router.py` — 4 chỗ | Đọc lại code sau khi viết | Thay bằng import thật ở đầu file |
| 2 | Viết script tự động chèn `dependencies=[...]` vào decorator — làm **hỏng cú pháp** 2 lần: lần 1 sinh `",,"`, lần 2 sinh `"))"`; lần đầu còn **treo vô hạn** vì decorator 1 dòng làm cursor không tiến | `python -c "from app.main import app"` báo SyntaxError | Bỏ script, viết lại chèn trực tiếp trước `)` + **compile từng file sau khi sửa, rollback nếu fail** |
| 3 | **Query param `fmt` trong khi client gửi `format`** → cả 3 định dạng đều trả CSV, `?format=bogus` vẫn 200 | So magic bytes: cả 3 đều là BOM UTF-8 | `Query(..., alias="format")`. Kiểm bằng cách gửi giá trị sai và xem có 422 không |
| 4 | `group_by=day` vẫn gom thêm theo **cửa hàng + nhóm hàng** → 146.080 dòng, file 3 MB, 24 giây | So số dòng với `count(DISTINCT order_date)` | Bỏ `extra`, chỉ gom theo bucket. Còn **1.826 dòng / 91 KB / 4 giây** |
| 5 | PDF không giới hạn số dòng → báo cáo lãng phí **77 giây** cho ~700 dòng, báo cáo bán hàng **timeout > 120 giây** | Đo thời gian từng định dạng | `MAX_PDF_ROWS = 1.000`, in rõ trên trang PDF là đã cắt |
| 6 | `refresh` **bắt buộc** có header → client gửi refresh token trong body bị 401 `Not authenticated` trước khi đọc body | Test trường hợp body-only | `get_current_active_refresh_token` trả `None` khi thiếu header |
| 7 | Đọc `row[10]` (unit_cost) thay cho `row[11]` (total_value) trong `recommend_expiring` → **báo giá trị lô sai 350 lần**, không báo lỗi | Test kiểm tra thứ tự sắp xếp phát hiện đảo chiều giá trị | Chuyển sang **unpack tuple theo tên** |
| 8 | `_data_anchor_date` lấy `max(order_date)` **không lọc trạng thái** → chỉ cần một đơn nháp tạo "hôm nay" là **mọi số bán hàng trong khuyến nghị về 0** | Test tạo đơn nháp rồi so với SQL | Lọc `status='completed' AND order_type='sale'` |
| 9 | Test tự viết sai: SQL cửa sổ 30 ngày lấy `< db_last` (bỏ mất ngày cuối), so `limit` mặc định 200 với số dòng DB, header tra cứu sai hoa/thường | 4 lần FAIL lần đầu | Sửa test, không sửa API — **phải phân biệt bug API với bug test** |

> Điểm chung của #3, #7, #8: **API trả 200 với dữ liệu sai** và chẳng báo lỗi nào.
> Chỉ khi đối chiếu với SQL thật mới thấy. Đây là lý do mọi check trong bộ test
> đều so với SQL chứ không so với chính API.

---

### Thư viện: KHÔNG dùng passlib

Task yêu cầu `passlib[bcrypt]`. Đã thử và **hỏng thật** với `bcrypt 5.0.0`:

```
passlib 1.7.4 → đọc bcrypt.__about__.__version__  (xoá từ bcrypt 4.1+)
→ nuốt AttributeError
→ báo: ValueError: password cannot be longer than 72 bytes
```

Mật khẩu thử nghiệm dài **7 byte** — thông báo hoàn toàn bịa, và sẽ dẫn người đọc
đi tìm một lỗi không tồn tại. → Dùng thư viện `bcrypt` trực tiếp
(`app/security.py`). Đã ghi rõ trong `requirements.txt`.

---

### Phát hiện về dữ liệu mới

| Vấn đề | Ảnh hưởng |
|--------|-----------|
| **3 user seed có `password_hash` là placeholder 29 ký tự**, không phải hash | **Không tài khoản nào đăng nhập được.** Đã chạy `scripts/reset_user_passwords.py` đặt hash bcrypt thật (`owner`/`manager`/`staff` — mật khẩu phát triển, xem `backend/.env.example`) |
| **`users.role` là `owner \| manager \| staff`** — KHÔNG có `admin` như task mô tả | CHECK constraint trong DB là nguồn sự thật. Đã dùng đúng 3 role này |
| **`slow-moving` trả 0 dòng với ngưỡng mặc định** | **Đúng, không phải lỗi.** Mọi sản phẩm bán 300–1.500 đơn vị/30 ngày, không có hàng bán chậm. Test chạy nghịch đảo ngưỡng để kiểm chứng logic vẫn đúng |
| **Chỉ có dự báo cho 100 cặp SP × CH** | `/recommendations/import` chỉ trả các cặp có dự báo, không phải 500 cặp |

---

### Quyết định thiết kế cần nêu trong báo cáo

1. **`recommended_import_qty` bị nén bởi `max_stock`** — tồn kho seed chỉ 0,5–3 ngày bán
   trong khi dự báo 30 ngày tới ~2.700. Con số **đúng thuật toán, không hành động được
   thực tế**. Mỗi dòng `reason` đã tự nhắc lại điều này.
2. **Đề xuất nhập hàng là THỰC NGHIỆM** — `forecasts` phủ 01/2018, dữ liệu bán hàng
   kết thúc 31/12/2017. Không có thực tế nào để kiểm chứng.
3. **Logout không bền vững** — denylist trong RAM, **restart là token sống lại**.
   Chấp nhận với 1 tiếng trình dev; nhiều tiếng trình thì phải dùng Redis/bảng DB.
4. **Giá trong báo cáo là MÔ PHỎNG** (Kaggle không có cột giá) — giữ nguyên cảnh báo
   cũ, không trình bày như doanh thu thật.

---

### Test thay đổi (B12 bắt buộc token cho endpoint ghi)

`backend/test_support.py` mới — chứa `login()` + `check()`/`ok()` dùng chung.
`test_b6_orders.py` và `test_b7_import.py` đã cập nhật để gửi
`Authorization: Bearer ...` cho POST/PUT/DELETE.

> Nếu sau này thêm endpoint ghi mà quên bảo vệ, hãy kiểm tra bằng cách gọi
> **không có token** và xem có 401 không — đừng chỉ nhìn vào code.

---

---

## 8t. CHUYỂN DATABASE SANG SQL SERVER — BƯỚC 1, 2 & 3 (24/10/2026)

### Bối cảnh

GVHD **bắt buộc** dùng SQL Server (giữ backend FastAPI) và yêu cầu
**100% thao tác dữ liệu qua Stored Procedure**. Toàn bộ quyết định PostgreSQL
trước đây (ORM, `v_daily_sales` bản PostgreSQL, sequence, migration 005…) chỉ còn
giá trị tham khảo.

| Mục | Giá trị |
|-----|---------|
| SQL Server | 2025 Express · `17.0.1000.7` |
| Instance | `LAPTOP-I39E3UT2\SQLEXPRESS` |
| Database | `spoilage_predictor` (đã nạp lại đầy đủ dữ liệu ở Bước 3) |
| Xác thực | SQL Server Authentication (`sa`) — mật khẩu chỉ trong `.env` |
| Driver | `pyodbc 5.3.0` + ODBC Driver 18 for SQL Server |

### Đã làm trong phiên này

| Bước | Nội dung | Trạng thái |
|------|----------|-----------|
| 1 | Cập nhật `AGENTS.md` (tech stack, commands, rules, SQL rules, môi trường, Known Issues, Current Progress) và file này | Xong |
| 2 | Tạo `database/HUONG-DAN-CHAY-SSMS.md` chứa **toàn bộ T-SQL** để copy/paste trên SSMS | Xong |
| 3 | Đổi `config.py` / `database.py` sang pyodbc + chuyển router sang Stored Procedure + nạp lại dữ liệu | Xong (xem mục dưới) |

### Nội dung file `HUONG-DAN-CHAY-SSMS.md`

| Phần | Số lượng | Ghi chú |
|------|----------|---------|
| Bảng | **10** | `stores, users, categories, products, inventory, inventory_transactions, orders, order_items, forecasts, alerts` |
| Index | 27 | gồm 2 filtered unique index thay cho UNIQUE + NULL của PostgreSQL |
| Trigger | 6 | tự cập nhật `updated_at` |
| View | 4 | `v_daily_sales`, `v_low_stock`, `v_expiring_inventory`, `v_product_stock_summary` |
| Stored Procedure | **49** | CRUD + nghiệp vụ, tất cả có `TRY...CATCH` + `TRANSACTION` |

### Danh sách Stored Procedure (49)

| Nhóm | Procedure |
|------|-----------|
| Products (5) | `sp_Products_List/Get/Create/Update/Delete` |
| Stores (5) | `sp_Stores_List/Get/Create/Update/Delete` |
| Categories (5) | `sp_Categories_List/Get/Create/Update/Delete` |
| Inventory (6) | `sp_Inventory_List/ListExpiring/Get/Create/Update/Delete` |
| Orders (6) | `sp_Orders_List/Get/Create/Update/UpdateStatus/Delete` |
| Order items (5) | `sp_OrderItems_List/Get/Create/Update/Delete` |
| Forecasts (5) | `sp_Forecasts_List/Get/Latest/Delete/DeleteByFilter` |
| Alerts (7) | `sp_Alerts_List/Get/UnreadCount/MarkRead/MarkAllRead/Resolve/Delete` |
| Users (3) | `sp_Users_GetByUsername/GetById/ChangePassword` |
| Nghiệp vụ (2) | `sp_Alerts_Generate`, `sp_Orders_RecalculateTotals` |

### Khác biệt kỹ thuật so với PostgreSQL (phải nhớ)

| # | PostgreSQL | SQL Server | Cách xử lý |
|---|-----------|-----------|-----------|
| 1 | `SERIAL` / `BIGSERIAL` | `IDENTITY(1,1)` | Dùng `SCOPE_IDENTITY()` để lấy id |
| 2 | `TIMESTAMPTZ` | `DATETIME2(7)` | Lưu giờ địa phương; seed dùng mốc ngày |
| 3 | `NUMERIC` | `DECIMAL` | Giữ nguyên độ chính xác |
| 4 | `TEXT` | `NVARCHAR(MAX)` | Hỗ trợ tiếng Việt |
| 5 | `BOOLEAN` | `BIT` | 0/1 |
| 6 | UNIQUE cho phép nhiều NULL | UNIQUE coi NULL là trùng | **Filtered unique index** `WHERE ... IS NOT NULL` |
| 7 | `ON DELETE SET NULL` trên cây tự tham chiếu | Báo lỗi 1785 | Procedure tự set NULL cho con rồi xoá |
| 8 | Generated column `line_total` | Computed column `PERSISTED` | Không được gán khi INSERT/UPDATE |
| 9 | `RETURNING` | `OUTPUT` / `SCOPE_IDENTITY()` | Procedure trả result set sau khi ghi |
| 10 | `ILIKE` | Collation mặc định không phân biệt hoa/thường | Dùng `LIKE` |
| 11 | `date_trunc` | `DATEPART` / `CAST(... AS DATE)` | View đã viết lại |
| 12 | `ISODOW` | `DATEPART(WEEKDAY)` phụ thuộc `DATEFIRST` | Tính bằng `DATEDIFF(DAY,'1900-01-01',...) % 7 + 1` |

### Mã lỗi nghiệp vụ (router map sang HTTP ở Bước 3)

| Mã | Ý nghĩa | HTTP |
|----|---------|------|
| 50001 | NOT_FOUND | 404 |
| 50002 | DUPLICATE | 409 |
| 50003 | REFERENCED (còn dữ liệu con) | 409 |
| 50004 | INVALID_STATE (trạng thái không cho phép) | 409 |
| 50005 | INVALID_INPUT | 422 |

### Đã test thật trên SQL Server (không chỉ đọc code)

Chạy trên database tạm `spoilage_tsql_test` (đã drop sau khi test):

- DDL: **10 bảng · 4 view · 6 trigger · 27 index** — không lỗi.
- Procedure: **49/49 tạo thành công**.
- Smoke test: tạo cửa hàng, nhóm cha/con, sản phẩm, tồn kho, đơn hàng 2 dòng,
  cập nhật/xoá dòng hàng, đổi trạng thái, sinh cảnh báo, đọc 4 view.
- Các ràng buộc **chặn đúng**: vòng lặp nhóm hàng, trùng `product_code`,
  trùng dòng hàng trong đơn, `completed → pending`, xoá sản phẩm/cửa hàng còn lịch sử.
  (Xoá đơn hàng **được phép** và xoá kèm dòng hàng trong cùng transaction — xem Bước 3.)
- Tổng đơn khớp lại sau mỗi lần thêm/sửa/xoá dòng hàng.

### Bước 3 — đã hoàn tất (24/10/2026)

| Hạng mục | Kết quả |
|----------|---------|
| `backend/app/config.py` | `DB_DRIVER`, `DB_HOST = LAPTOP-I39E3UT2\SQLEXPRESS`, `DB_PORT = 1433`, `DB_USER = sa`; `database_url` dựng qua `odbc_connect` (host có dấu `\` nên không dùng dạng `user:pass@host`) |
| `backend/app/database.py` | Engine `mssql+pyodbc` với `autocommit=True`; `DbSession` bọc pyodbc raw connection (`call/scalar/rows/one/commit/rollback/close`); `map_sqlserver_error()` map 50001–50005 + 2601/2627/547 |
| `backend/app/sp_helpers.py` | Gắn object lồng `store` / `product` / `category`, ép `BIT` → `bool`, `Decimal` → `float` |
| 18 router | Gọi `db.call("sp_...", {...})` — **không còn ORM, không còn raw SQL** trong router |
| Migration `010` | Thêm **25 Stored Procedure** cho dashboard, dashboard nâng cao, đề xuất nhập hàng, báo cáo, import (dùng `OPENJSON`) + sửa `sp_Orders_Delete` xoá kèm dòng hàng |
| Tổng Stored Procedure | **74** (49 CRUD/nghiệp vụ + 25 phân tích/báo cáo/import) |
| Dữ liệu nạp lại | 8 nhóm · 10 cửa hàng · 50 sản phẩm · 3 user · **18.260 đơn / 912.999 dòng hàng** · 1.330 lô tồn kho · 1.596 giao dịch kho · 2.820 dự báo · 492 cảnh báo |
| Công cụ nạp | `scripts/convert_seed_to_sqlserver.py` + `database/02-seed/seed-sqlserver.sql` + `scripts/load_sqlserver_data.py` |

### Vì sao KHÔNG dùng SQLAlchemy Session cho Stored Procedure

`Session` không có `nextset()`, và procedure tự `COMMIT` transaction ngầm của pyodbc
gây lỗi `266 Transaction count after EXECUTE indicates a mismatching number`.
Vì vậy `DbSession` giữ **raw pyodbc connection** lấy từ `engine.raw_connection()`,
engine đặt `autocommit=True` để procedure tự quản lý transaction của nó.

### Đã test thật ở Bước 3 (qua HTTP, không chỉ đọc code)

- `scripts/smoke_test_api.py`: **48/48 check PASS** — health, auth (login/me), mọi nhóm
  GET (products, stores, categories, inventory, forecasts, alerts, orders, order-items),
  toàn bộ dashboard + dashboard nâng cao, 3 recommendation, 4 báo cáo × 3 định dạng
  (CSV/XLSX/PDF), import template, và các case lỗi 404/409/422/401.
- `scripts/smoke_test_writes.py`: **29/29 check PASS** — tạo/sửa/xoá sản phẩm,
  trùng `product_code` → 409, `staff` tạo sản phẩm → 403, tồn kho + trùng lô → 409,
  đơn hàng 2 dòng (tổng tiền khớp công thức), trùng `order_code` → 409,
  `completed` bị khoá sửa và không quay lại `pending` → 409,
  đọc/giải quyết/mở lại cảnh báo, xoá đơn `pending` → 204,
  import CSV sản phẩm (2 dòng) + xoá sạch dữ liệu test.
- `python -c "import app.main"` sạch, không còn cảnh báo `HTTP_422_UNPROCESSABLE_ENTITY`.

### Ghi chú còn lại cho Chương 4 / phiên sau

1. `forecasts` nạp **2.820** dòng (94 cặp × 30 ngày) vì file `forecast_summary_30d.csv`
   hiện có 94 cặp prophet, không phải 100. Khi viết báo cáo dùng đúng số trong DB.
2. `sp_Orders_Delete` đã đổi sang **xoá dòng hàng trước rồi xoá đơn** trong cùng
   transaction (khôi phục hành vi `ON DELETE CASCADE` của PostgreSQL). File
   `HUONG-DAN-CHAY-SSMS.md` cũng đã cập nhật theo.
3. Xoá tay dữ liệu test: đơn `completed` không xoá được qua API (đúng thiết kế) —
   dùng SQL trực tiếp như đã làm với các đơn `SMOKE-%`.

---

*Bước 3 xong. Phiên sau: **F1 — Setup Frontend React** (phân quyền owner/manager vs staff,
Dark Mode, Responsive).*

## 8u. F1 — SETUP FRONTEND REACT + TAILWIND (24/10/2026)

### Công nghệ đã cài

| Thành phần | Phiên bản | Ghi chú |
|-----------|-----------|---------|
| Vite | 8.3.5 | Scaffold `react` (React 19), dev server cổng **3000** |
| React | 19.3.1 | `BrowserRouter` + React Router 7 |
| Tailwind CSS | 3.4.17 | `darkMode: 'class'`, PostCSS + Autoprefixer |
| React Router DOM | 7.18.4 | Route lồng nhau, `ProtectedRoute`, `NavLink` |
| Axios | 1.20.0 | Instance dùng chung + interceptor token/refresh |
| Recharts | 3.10.1 | Biểu đồ dashboard |

### Cấu trúc frontend

| Đường dẫn | Nội dung |
|-----------|----------|
| `frontend/vite.config.js` | Proxy `/api` → `http://localhost:8000`, cổng 3000 |
| `frontend/tailwind.config.js` | `darkMode: 'class'`, bảng màu `brand` (emerald), animation |
| `frontend/src/services/api.js` | Axios `baseURL: /api/v1`; tự gắn Bearer; refresh token một lần cho cả loạt 401 |
| `frontend/src/contexts/AuthContext.jsx` | Lưu phiên (`scsp_access_token`, `scsp_refresh_token`, `scsp_user`); `isAdmin` = owner/manager |
| `frontend/src/contexts/ThemeContext.jsx` | Sáng/Tối, lưu `scsp_theme`; mặc định theo `prefers-color-scheme` |
| `frontend/src/components/layout/` | `Layout`, `Sidebar` (drawer mobile), `Header`, `ProtectedRoute` |
| `frontend/src/pages/LoginPage.jsx` | Đăng nhập thật qua `/api/v1/auth/login` + tài khoản dùng thử |
| `frontend/src/pages/DashboardPage.jsx` | Mockup UI: 4 KPI, biểu đồ doanh thu, top sản phẩm, cảnh báo, lô cận hạn |
| `frontend/src/pages/ProductsPage.jsx` | **Gọi API thật** `GET /api/v1/products`: tìm kiếm, lọc trạng thái, phân trang |

### Phân quyền / Dark Mode / Responsive

- `owner` + `manager`: thấy đầy đủ menu (kể cả nhóm Phân tích) và nút **Thêm / Sửa / Xoá**.
- `staff`: menu Phân tích bị ẩn; cột thao tác và nút thêm sản phẩm không render.
- Backend vẫn là nơi quyết định cuối cùng (`require_role`), frontend chỉ ẩn/hiện.
- Dark Mode: nút ở Header và trang Login; class `dark` gắn trên `<html>`; script trong
  `index.html` áp dụng theme trước khi React mount để không bị nháy sáng.
- Responsive: sidebar cố định từ `lg`, dưới `lg` là drawer + backdrop + nút hamburger;
  bảng sản phẩm cuộn ngang, KPI dùng grid 1 → 2 → 4 cột.

### Đã kiểm chứng

| Kiểm tra | Kết quả |
|----------|---------|
| `npm run build` | Thành công (732 kB JS / 32 kB CSS, gzip 221 kB / 6 kB) |
| `GET http://localhost:3000/` | 200 — Vite dev server chạy |
| Login qua proxy `POST /api/v1/auth/login` | 200 — `owner` / `Chu chuoi` |
| `GET /api/v1/products?page=1&page_size=3` qua proxy | 200 — `total=50`, trả đúng 3 dòng kèm `category` |

### Ghi chú cho phiên sau

- Dashboard đang dùng **số liệu minh hoạ** (có badge "Số liệu minh hoạ giao diện"),
  chưa nối `/dashboard/overview`.
- Nút Thêm/Sửa/Xoá sản phẩm mới chỉ hiện theo quyền và báo "sẽ nối ở bước sau";
  CRUD thật + các trang Tồn kho / Đơn hàng / Dự báo / Cảnh báo / Báo cáo còn lại.
- Các trang "Sắp" trong sidebar là chỗ đặt trước, chưa có route.

---

*F1 xong. Bước tiếp theo: nối Dashboard với API thật và hoàn thiện CRUD sản phẩm.*

## 8v. F2 — HOÀN THIỆN CÁC TRANG GIAO DIỆN CÒN LẠI (24/10/2026)

### Đã thêm

| Trang | API gọi | Tính năng |
|-------|---------|-----------|
| `InventoryPage` | `/inventory`, `/inventory/expiring` | Tab "Tất cả lô hàng" / "Hàng sắp hết hạn", bộ lọc ngày (3/7/14/30), badge tình trạng hạn sử dụng |
| `OrdersPage` | `/orders`, `/orders/{id}` | Lọc theo loại/trạng thái, nút "Tạo đơn mới" (owner/manager), modal xem chi tiết đơn hàng |
| `AlertsPage` | `/alerts`, `/alerts/unread`, `PUT /alerts/{id}/read` | Lọc theo mức độ, tab "Chỉ chưa đọc"/"Tất cả", nút "Đánh dấu đã đọc" |
| `ForecastsPage` | `/forecasts/latest` | Bảng dự báo mới nhất theo cặp SP×CH, biểu đồ top 10, thông tin mô hình Prophet |
| `CategoriesPage` | `/categories` | Hiển thị dạng cây (nhóm cha/con), CRUD (owner/manager) — nối ở bước sau |
| `StoresPage` | `/stores` | Bảng cửa hàng, CRUD (owner/manager) — nối ở bước sau |

### Cập nhật layout

- `Sidebar`: thêm menu Kho hàng, Bán hàng, Cảnh báo, Dự báo nhu cầu, Nhóm hàng, Cửa hàng
- `Header`: cập nhật tiêu đề trang
- `App.jsx`: thêm routes cho các trang mới

### Kiểm chứng

| Kiểm tra | Kết quả |
|----------|---------|
| `npm run build` (frontend) | Thành công (673 modules transformed) |
| Phân quyền | Nút thêm/xóa/đánh dấu chỉ hiện theo role (owner/manager/staff) |
| Dark Mode / Responsive | Áp dụng cho toàn bộ trang mới |

---

*F2 xong. Bước tiếp theo: nối Dashboard với API thật và hoàn thiện CRUD sản phẩm/nhóm hàng/cửa hàng.*

\
## 8w. I1 � T�CH H?P AI CHATBOT V� REALTIME WEBSOCKET (24/10/2026)

### Backend

| Th�nh ph?n | M� t? |
|------------|-------|
| google-generativeai | Th�m v�o equirements.txt; c?u h�nh GEMINI_API_KEY, GEMINI_MODEL trong .env/config.py |
| POST /api/v1/chat | Nh?n c�u h?i, x�y d?ng ng? c?nh t? t?n kho/don h�ng/c?nh b�o/d? b�o qua Stored Procedure, g?i k�m Gemini d? tr? l?i d?a tr�n d? li?u th?t (fallback hi?n th? ng? c?nh n?u chua c� API key) |
| WebSocket /ws/alerts | Endpoint realtime; ConnectionManager broadcast tin nh?n |
| Broadcast c?nh b�o | Khi resolve/x�a c?nh b�o, backend push lert_updated/lert_deleted qua WebSocket |

### Frontend

| Th�nh ph?n | M� t? |
|------------|-------|
| Chatbot.jsx | Bong b�ng chat n?i g�c ph?i, hi?n th? tin nh?n ngu?i d�ng/AI, loading, quick questions, h? tr? Dark Mode |
| RealtimeAlerts.jsx | L?ng nghe WebSocket, hi?n th? toast th�ng b�o realtime g�c tr�i kh�ng c?n reload |
| T�ch h?p App.jsx | Th�m Chatbot v� RealtimeAlerts to�n c?c cho user d� dang nh?p |

### Ki?m ch?ng

| Ki?m tra | K?t qu? |
|----------|---------|
| 
pm run build (frontend) | Th�nh c�ng (675 modules transformed) |
| Endpoint chat (Swagger) | C� s?n POST /api/v1/chat |
| WebSocket | Endpoint ws://localhost:8000/ws/alerts ho?t d?ng |

---

*I1 xong. Bu?c ti?p theo: t�ch h?p AI Model v� ho�n thi?n CRUD.*\
\
## 8x. FIX � TH�M N�T QUAY L?I CHO C�C TRANG CON (24/10/2026)

- Th�m BackButton component d�ng 
avigate(-1)`n- �p d?ng cho: S?n ph?m, Kho h�ng, �on h�ng, C?nh b�o, D? b�o, Nh�m h�ng, C?a h�ng
- H? tr? Dark Mode v� Responsive
- Build frontend th�nh c�ng\
