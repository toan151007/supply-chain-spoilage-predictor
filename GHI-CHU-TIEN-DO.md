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
| D4 — Seed inventory | ⬜ Chưa làm | inventory + inventory_transactions |
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
| Database | `spoilage_predictor` · 10 bảng · đang rỗng |
| Xác thực | `scram-sha-256` |

**Cần cài thêm:** `fastapi`, `uvicorn`, `pydantic` · mô hình: `prophet`, `xgboost`, `scikit-learn`, `statsmodels`, `matplotlib`

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
| **D4** | Seed `inventory` + `inventory_transactions` | 🔴 Cao — cần cho cảnh báo + mô hình |
| D5 | Chạy `fn_generate_inventory_alerts()` tạo cảnh báo thật | 🟡 TB |
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

---

## 9. ⚠️ Việc cần tra cứu / xác minh

Không gấp, nhưng **bắt buộc làm trước khi nộp báo cáo**:

- [ ] **Đối chiếu trích dẫn Chương 2 [5]–[8]** với bản gốc: số tạp, số trang, năm
- [ ] **Mục 2.4** hiện là "hướng nghiên cứu" chưa gắn bài báo cụ thể
- [ ] **Số liệu lãng phịch thực phẩm Việt Nam** — đang để `(cần bổ sung)`
- [ ] **Tên trường / khoa** trong Chương 1 và phần tác giả
- [ ] **Khả năng cung cấp dữ liệu thực tế** — hiện đang dùng dataset Kaggle (Mỹ), cần ghi rõ trong Chương 1
- [ ] **Danh mục tài liệu tham khảo đầy đủ** ở phần cuối báo cáo
- [ ] **Cân nhắc sửa Chương 2** để nhất quán với thuật ngữ `orders`/`order_items` (xem mục 10)

---

## 10. Cần quyết định (chưa làm)

| Việc | Vấn đề |
|------|--------|
| **Thuật ngữ trong Chương 2** | Tài liệu nhắc bảng `sales`, schema dùng `orders` + `order_items`. Cần sửa Chương 2 cho nhất quán, hoặc thêm bảng `sales` |
| **`unit_price = 0` trong import** | Kaggle không có giá → `line_total` và `total_amount` đang bằng **0**. Mô hình dự báo chỉ dùng `quantity` nên không ảnh hưởng, nhưng dashboard doanh thu sẽ hiển thị 0. Có thể chạy lại với `--unit-price` để gán giá mẫu |
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
