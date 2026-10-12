# AGENTS.md — Supply Chain Spoilage Predictor

## Project Overview

Nền tảng Quản trị Chuỗi cung ứng Chống lãng phí cho chuỗi cửa hàng bán lẻ/F&B.
Mục tiêu: Dự báo nhu cầu, tối ưu nhập hàng, giảm lãng phí thực phẩm.

## Tech Stack

- Frontend: React.js + Vite + Tailwind CSS
- Backend: Python FastAPI (hoặc Node.js/Express)
- Database: PostgreSQL
- AI/ML: Prophet, XGBoost, ARIMA (Python)
- Real-time: WebSocket
- AI Agent: Gemini API (chatbot hỏi đáp kho)

## Commands

- Cài đặt backend: `pip install -r backend/requirements.txt`
- Chạy backend: `cd backend; uvicorn app.main:app --reload --port 8000`
- Test backend: mở `http://localhost:8000/docs`
- Cài đặt frontend: `cd frontend && npm install`
- Chạy frontend: `npm run dev` (cổng 3000)
- Chạy database: `psql -U postgres -d spoilage_predictor`
- Import SQL schema: `psql -U postgres -d spoilage_predictor -f database/01-schema/02-create-tables.sql`
- Chạy AI model: `cd ai-model && jupyter notebook`

> ⚠️ `cd backend` là **bắt buộc** khi chạy uvicorn — các module import
> theo đường dẫn tuyệt đối `from app.config import settings`.
> Nếu chạy từ thư mục gốc sẽ báo `ModuleNotFoundError: No module named 'app'`.

## Project Structure

- /backend/ FastAPI server (models, routers, services)
- /frontend/ React app (components, pages, services)
- /ai-model/ Jupyter notebooks + Python models
- /database/ SQL schema, seed, queries
- /docs/ Tài liệu đồ án (báo cáo, thiết kế, timeline)
- /datasets/ Dữ liệu mẫu (raw, processed)
- /tests/ Unit tests

## Rules (BẮT BUỘC TUÂN THỦ)

- KHÔNG dùng PHP, ASP.NET, hay bất kỳ framework nào ngoài danh sách trên.
- KHÔNG sửa file cấu hình (config.py, .env) mà không hỏi trước.
- Mọi API phải có prefix `/api/v1/`.
- Mọi truy vấn database phải qua ORM, KHÔNG viết raw SQL trong routers.
- Đặt tên file Python: snake_case. Tên React component: PascalCase.
- **Comment trong code Python dùng tiếng Anh KHÔNG DẤU** (tương thích console Windows cp1252). Tài liệu `.md` và file SQL vẫn dùng tiếng Việt / ASCII theo quy tắc riêng.
- Trước khi commit, chạy `git status` để kiểm tra.

## SQL Rules (BẮT BUỘC TUÂN THỦ)

- Trước khi viết INDEX / VIEW / FUNCTION, phải kiểm tra cột đã tồn tại trong CREATE TABLE chưa.
- KHÔNG tham chiếu cột không tồn tại. Chỉ dùng cột của bảng trong đúng JOIN đó.
- Sau khi viết file SQL, PHẢI tự test bằng `psql -f file.sql` trước khi commit.
- Nếu có lỗi, sửa ngay, không để lỗi sang task khác.
- File SQL giữ ASCII (comment tiếng Anh) để chạy được trên Windows PowerShell.
- Muốn thêm tiếng Việt vào SQL thì dùng cơ chế i18n: lưu KEY, dịch ở `backend/app/i18n/vi.json`.

## Môi trường phát triển (đã kiểm chứng 02/10/2026)

| Thành phần | Phiên bản / thông tin |
|-----------|----------------------|
| Python | 3.14.7 (pip 26.2.1) |
| pandas | 3.0.6 |
| numpy | 2.5.3 |
| SQLAlchemy | 2.1.2 |
| psycopg2-binary | 2.9.13 |
| FastAPI | 0.143.0 |
| uvicorn | 0.54.0 (`[standard]` — kèm websockets cho realtime) |
| pydantic | 2.14.1 |
| pydantic-settings | 2.15.0 |
| Node.js | v24.15.0 (npm 11.12.1) |
| PostgreSQL | 18.6 · service `postgresql-x64-18` · port 5432 |
| Database | `spoilage_predictor` · 10 bảng · **đã có dữ liệu** (912.999 `order_items` · 3.000 `forecasts`) |
| Xác thực | `scram-sha-256` · mật khẩu nằm trong `.env` cục bộ, KHÔNG commit |

| statsmodels | 0.15.0 (ARIMA) |
| scikit-learn | 1.9.1 |
| XGBoost | 3.4.1 |
| Prophet | 1.4.0 (kèm CmdStan 2.37.0) |

✅ **Python 3.14.7 chạy được đủ 3 mô hình — KHÔNG cần lùi phiên bản.**
✅ Backend B1 đã cài đủ `fastapi`, `uvicorn`, `pydantic` (12/10/2026).

Kiểm tra lại môi trường ML: `python scripts/check_ml_env.py`

## Dataset Kaggle

- **Nguồn:** Walmart Store Sales - Time Series Forecasting
- **Link:** https://www.kaggle.com/competitions/demand-forecasting-kernels-only
- **File:** `datasets/raw/train.csv` (913.000 dòng dữ liệu), `test.csv`, `sample_submission.csv`
- **Cột:** `date, store, item, sales` — KHÔNG có cột giá
- **Phạm vi:** 50 items (id 1–50), 10 stores (id 1–10), giai đoạn 2013-01-01 → 2017-12-31
- **KHÔNG commit CSV** (17MB vượt ngân sách repo). Đã thêm vào `.gitignore`

## Quyết định thiết kế đã chốt

- **10 bảng:** users, stores, categories, products, inventory, inventory_transactions, orders, order_items, forecasts, alerts
- **SQL giữ ASCII**, tiếng Việt dùng i18n key → `backend/app/i18n/vi.json`
- **Dữ liệu Kaggle nạp vào `orders` + `order_items`**, KHÔNG tạo bảng `sales` riêng
- **Giá trong DB là MÔ PHỎNG theo nhóm hàng** — Kaggle không có cột giá. Chỉ dùng để demo dashboard doanh thu. **Không trình bày như số liệu thật.** Mô hình dự báo chỉ dùng `quantity` nên không ảnh hưởng kết quả.
- **Nguồn dữ liệu dự báo:** `v_daily_sales` (view, dựng từ `orders` + `order_items`). `inventory_transactions` CHỈ dùng cho phân tích tồn kho, cảnh báo hết hạn, FIFO — **KHÔNG** phải đầu vào dự báo.
- **Thuật ngữ:** bảng "sales" trong tài liệu = `orders` + `order_items` trong schema
- **KHÔNG chạy lại `01-schema/02-create-tables.sql` khi DB đã có dữ liệu** — file đó có `DROP TABLE ... CASCADE`. Dùng file trong `database/03-migrations/`.
- **Prophet** = mô hình cơ sở, **XGBoost** = mô hình chính, **ARIMA + trung bình động** = đối chứng
- **KHÔNG dùng LSTM** trong hệ thống (chỉ trình bày lý thuyết — dữ liệu quá nhỏ)
- **`expiry_date`** đặt ở `inventory` + `inventory_transactions`, không đặt ở `products`
- **CHECK constraint** thay vì PostgreSQL `ENUM` (dễ migrate, tương thích SQLAlchemy)

## Cấu hình mô hình dự báo (đã chốt 03/10/2026)

| Mục | Giá trị |
|-----|---------|
| Dữ liệu | **5 năm 2013–2017** · 912.999 dòng · 1.826 ngày · 10 cửa hàng · 50 sản phẩm |
| Chia tập | Theo **mốc ngày `2017-10-01`** (không dùng 80/20) — train 1.734 ngày · test 92 ngày |
| Chuỗi thời gian | Reindex đủ 1.826 ngày, ngày thiếu điền **0** |
| Prophet | `changepoint_prior_scale=0.01`, `seasonality_mode='multiplicative'`, `yearly_seasonality=20` |
| Ngày lễ | Bộ ngày lễ **Hoa Kỳ** (dùng chung Prophet + XGBoost để so sánh công bằng) |
| Đặc trưng XGBoost | `lag_1..7`, `lag_14`, `lag_28`, `roll_mean_7/28`, `dow`, `month`, `is_weekend`, `trend`, `is_holiday` |
| Chọn tham số | **Theo validation**, không theo test (tránh rò rỉ dữ liệu) |

### Kết quả đánh giá 100 cặp (đã chạy đầy đủ 03/10/2026)

| Mô hình | RMSE | MAE | MAPE | Số cặp thắng |
|---------|------|-----|------|--------------|
| **Prophet** | **9,97** | **7,94** | **10,43%** | **97 / 100** |
| XGBoost | 10,98 | 8,77 | 11,69% | 3 / 100 |
| ARIMA | 20,20 | 16,44 | 23,77% | 0 / 100 |

**Prophet là mô hình chính** (không phải XGBoost như Chương 2 dự kiến).
XGBoost chỉ thắng 3 cặp: (45,2), (13,7), (28,4) — ở 59 cặp chênh lệch < 1,0 RMSE.
Chi tiết: `docs/05-tham-khao/ket-qua-danh-gia-model.md`

## ⚠️ Bài học quan trọng (nhớ khi làm tiếp)

1. **Prophet cần ≥ 2 năm dữ liệu để ước lượng mùa vụ năm.** Với 1 năm, Prophet báo *"Yearly seasonality is enabled with less than 730 days"* và RMSE 23,20. Thêm 4 năm dữ liệu → RMSE **9,97** (−57%), và đi từ **hạng 3 lên hạng 1** (đã xác nhận trên 100 cặp). Nguyên nhân khiến Prophet kém là **thiếu dữ liệu**, không phải tham số.
2. **Dữ liệu dài làm mô hình bám đảo hơn.** Biến động RMSE giữa các bộ tham số giảm từ **10,5 lần** (1 năm) xuống **8%** (5 năm).
3. **Chọn tham số theo validation, không theo test.** Tune trên test cho RMSE thấp hơn 0,47 nhưng đó là rò rỉ dữ liệu — con số báo cáo sẽ không còn trung thực.
4. **`yearly_seasonality=True` chính là `fourier_order=10`.** 18 lần chạy chỉ cho 12 kết quả khác nhau (đã xác nhận bằng dữ liệu).
5. **Bảo vệ toàn vẹn dữ liệu thay vì nới ràng buộc.** 1 dòng `sales = 0` vi phạm `CHECK (quantity > 0)` → bỏ dòng, **không** sửa schema.
6. **Reindex chuỗi thời gian trước khi train.** View `v_daily_sales` chỉ có dòng cho ngày **có phát sinh giao dịch**. Cặp (product 4, store 6) thiếu ngày 15/01/2014 vì dòng `sales = 0` đã bị bỏ. Phải `reindex` về đủ 1.826 ngày và điền **0** — nếu không, các hàm lag/rolling sẽ lệch ngày và mô hình học sai. Đây cũng là nơi hiện tượng **censored demand** xuất hiện trong thực tế.
7. **Tách tập theo mốc ngày, không dùng 80/20 cố định.** Với dữ liệu nhiều năm, 80/20 không bảo đảm test rơi vào một mùa cụ thể. Mốc `2017-10-01` giúp test rơi vào Q4 — dễ giải thích và đúng nghiệp vụ.

## 10 sản phẩm dùng để huấn luyện mô hình (đã chốt 02/10/2026)

`product_id`: **[45, 8, 15, 13, 25, 11, 28, 48, 38, 18]**

| # | product_id | Sản phẩm | Nhóm | Doanh số 2017 | BQ/ngày |
|---|-----------|----------|------|---------------|---------|
| 1 | 45 | Khan uot tre em | Baby Care | 331.783 | 909,0 |
| 2 | 8 | Thit bo | Fresh Food | 316.911 | 868,2 |
| 3 | 15 | Ca phe sua dinh huong | Beverages | 361.586 | 990,6 |
| 4 | 13 | Nuoc sui 330ml | Beverages | 346.565 | 949,5 |
| 5 | 25 | Ruou dua co | Beverages | 330.786 | 906,3 |
| 6 | 11 | Nuoc loc 500ml | Beverages | 286.882 | 785,7 |
| 7 | 28 | Keo mut | Snacks | 360.768 | 988,4 |
| 8 | 48 | Kem danh rang | Personal Care | 211.365 | 579,1 |
| 9 | 38 | Sua tam the | Household | 331.005 | 906,9 |
| 10 | 18 | Sua chua 500g | Dairy | 346.448 | 949,2 |

**Đủ 7/7 nhóm hàng · 100 cặp (sản phẩm × cửa hàng) · mỗi cặp đủ 365 ngày.**

> **Nguồn số liệu:** cột "Doanh số 2017" lấy từ `SUM(order_items.quantity)` trong DB
> (điều kiện `order_date` từ 2017-01-01 đến trước 2018-01-01), đã đối chiếu khớp
> **từng dòng** với `SUM(sales)` trong `datasets/raw/train.csv`.
> Cột "BQ/ngày" là doanh số chia 365, làm tròn 1 chữ số thập phân — nên nhân ngược
> có thể lệch vài đơn vị so với doanh số gốc, đó là sai số làm tròn, không phải sai số liệu.
>
> Đã kiểm chứng lại toàn bộ 10 dòng ngày 12/10/2026 — **10/10 khớp tuyệt đối** giữa CSV và DB.

### ⚠️ Về hiện tượng censored demand

Chương 1 và Chương 2 trình bày censored demand như một vấn đề **lý thuyết**. **Dữ liệu Kaggle không có hiện tượng này** — đã kiểm tra, có **0 ngày** bán bằng 0 sản phẩm.

Khi viết Chương 4 phải ghi rõ: *"Trong dữ liệu thực tế, không xảy ra censored demand. Đây là hạn chế của dataset Kaggle so với dữ liệu bán lẻ thực tế, nơi hiện tượng này có thể xảy ra."*

Không sửa Chương 1, 2 — đó là nội dung lý thuyết chung, đúng và cần giữ.

### ⚠️ Về mùa vụ

Mua vụ của Walmart **tác động đồng đều lên mọi mặt hàng**:

| Mức | Hệ số biến động | Nhận xét |
|------|------------------|----------|
| Theo tháng (cả 50 sản phẩm) | 1,85 – 1,95 (rộng 0,098) | **Không phân biệt được sản phẩm nào** |
| Theo tuần | 1,88 – 2,03 (rộng 0,153) | Phân biệt rất yếu |
| Theo ngày trong tuần | 1,52 | Yếu hơn mùa vụ tháng |
| Theo tháng (toàn hệ thống) | 1,90 · tháng 7 cao nhất, tháng 1 thấp nhất | |

Vì vậy **không dùng được** tiêu chí "hệ số biến động mùa vụ" để chọn sản phẩm. Đã chọn theo **doanh số năm + đa dạng 7 nhóm hàng**.

## Known Issues & Gotchas

- Token Antigravity có giới hạn → cần commit thường xuyên.
- Khi chuyển sang Cursor/OpenCode, PHẢI yêu cầu AI đọc file AGENTS.md trước.
- WebSocket cần bật CORS cho frontend localhost:3000.
- **Không có bảng `sales`.** Dữ liệu bán hàng nằm ở `orders` + `order_items`.
- Không ghi mật khẩu database vào bất kỳ file nào trong repo.
- PowerShell máy này KHÔNG hỗ trợ `&&` — dùng `;`.
- pgAdmin giữ session thì `DROP DATABASE` bị lỗi → dùng `TRUNCATE`.
- **`max_stock` trong seed data KHÔNG cùng thang đo với Kaggle.** Seed đặt `max_stock` 48–300, nhưng nhu cầu thực tế 861–2.793/ngày → `max_stock` chỉ bằng **0,5–3 ngày bán**. Hệ quả: **100/100 cặp bị `max_stock` chặn** khi tính `recommended_import_qty` (nhu cầu thuần 232.397 → đề xuất sau cap chỉ 7.286). Đây là hạn chế dữ liệu, KHÔNG phải lỗi mô hình. Khi viết báo cáo phải nêu rõ.
- **pandas 3.0**: `pd.DataFrame({"ds": <DataFrame>})` sẽ báo `ValueError: If using all scalar values, you must pass an index` — phải truyền **Series** (`df["sale_date"]`).
- **FastAPI 0.143 đổi cách `include_router`:** `app.routes` giờ chứa một đối tượng `_IncludedRouter` thay vì flatten từng endpoint vào danh sách. **ĐỪNG kiểm tra `app.routes` để xác nhận router đã đăng ký** — hãy gọi thật qua HTTP (`Invoke-WebRequest http://localhost:8000/health`).
- **Chạy uvicorn phải `cd backend` trước.** Module import theo đường dẫn tuyệt đối `from app.config import settings`; chạy từ thư mục gốc sẽ báo `ModuleNotFoundError: No module named 'app'`.
- **File `.env` đã tạo ở thư mục gốc** (có trong `.gitignore`) — backend **và script AI/ML** (`import_kaggle.py`, `train_models.py`, `forecast_next_month.py`) đều đọc từ đó. **KHÔNG chuyển `.env` sang `backend/`** sẽ làm hỏng script AI/ML. Mẫu cấu hình cho người clone repo: `backend/.env.example`.
- **`CORS_ORIGINS` phải khai báo kiểu `str` + property, KHÔNG dùng `list[str]`.** Biến môi trường luôn là chuỗi; khai báo `list[str]` khiến pydantic chỉ chấp nhận JSON (`["http://..."]`) và báo `ValidationError: Input should be a valid list` khi ai đó viết dạng dấu phẩy — **đúng dạng `backend/.env.example` đang dùng**. Trong `main.py` dùng property **`settings.cors_origins_list`**.
  - `@field_validator(mode="before")` **không cứu được** lỗi này — validator không can thiệp được vào env source của pydantic-settings.
  - Hành vi khi `CORS_ORIGINS=` rỗng: trả `[]` (fail-closed, chặn mọi origin). Muốn dùng mặc định thì **xoá hẳn dòng** khỏi `.env`, đừng để trống.
- Console Windows dùng cp1252 — khi in chuỗi có dấu tiếng Việt ra terminal sẽ báo `UnicodeEncodeError: charmap`. Thêm `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`.
- **Cột NUMERIC trả về `Decimal`, không phải `float`.** Khi so sánh/tính toán phải ép `float(...)` cả hai vế, nếu không sẽ nhận `TypeError: unsupported operand type(s) for -: 'float' and 'decimal.Decimal'`.
- **`order_items.line_total` là GENERATED COLUMN** → model dùng `Computed(..., persisted=True)`. **Không được gán giá trị** cho cột này khi INSERT/UPDATE, DB tự tính: `round(quantity * unit_price * (1 - discount_percent/100), 2)`.
- **`categories` có quan hệ tự tham chiếu** (`parent_category_id` → chính nó). Bắt buộc chỉ rõ `remote_side` và `foreign_keys` ở cả hai chiều, nếu không SQLAlchemy sẽ không xác định được quan hệ cha/con.
- **Tên nhóm hàng trong DB là tiếng Anh** (`Food`, `Fresh Food`, `Beverages`…), khác với tên tiếng Việt trong tài liệu. Khi viết test đừng đoán tên — query `categories` trước.
- **Sequence ID có thể trôi khỏi dữ liệu** — đã gặp và đã sửa bằng migration 005. Nguyên nhân: `TRUNCATE ... RESTART IDENTITY` rồi import lại bằng `COPY`/insert **chỉ định khóa chính** → PostgreSQL **không** tự đẩy sequence lên. Mọi `INSERT` sau đó đụng `duplicate key ... already exists`. Chạy `database/03-migrations/005-fix-sequences.sql` sau khi import dữ liệu hàng loạt. Triệu chứng: `products_product_id_seq.last_value = 2` trong khi `MAX(product_id) = 50`.
- **Sau `db.commit()`, lỗi phát sinh ở `db.refresh()` không rollback được** — dữ liệu đã ghi vĩnh viễn. Đã gặp: `NameError` ở `db.refresh()` làm POST trả 500 nhưng bản ghi vẫn được tạo. Nếu test thất bại, **kiểm tra dữ liệu thừa** trước khi chạy lại.
- **Cổng 8000 dễ bị chiếm bởi server cũ** — `Kill-Process` trước khi start lại, nếu không sẽ báo `[winerror 10048] only one usage of each socket address` và test vẫn chạy vào code cũ.
- **FastAPI khớp route THEO THỨ TỰ khai báo.** Path đặc biệt phải khai báo trước path có tham số: `GET /alerts/unread` **trước** `GET /alerts/{alert_id}`. Nếu đảo, `alert_id: int` sẽ cố parse chuỗi `"unread"` và trả 422 thay vì vào handler. Tương tự `/forecasts/latest` và `/inventory/expiring`.
- **`alerts` có CHECK `chk_alert_resolved_at`**: `resolved_at` phải khác NULL **khi và chỉ khi** `is_resolved = TRUE`. Khi update phải gán **cả hai cùng lúc** — set riêng cờ sẽ bị DB từ chối với `IntegrityError` khó hiểu.
- **View `v_expiring_inventory` giới hạn cứng 30 ngày** — trong `WHERE` của nó: `expiry_date <= CURRENT_DATE + 30`. API `/dashboard/expiring` vì thế chặn `days > 30` bằng 422 thay vì âm thầm trả về kết quả không đổi.
- **Không đọc view bằng `text()` / raw SQL.** Dùng `Table("v_x", Base.metadata, autoload_with=engine)` trong `backend/app/models/views.py` — SQLAlchemy Core reflection, vẫn là `select()`/`group_by()` nên không vi phạm quy tắc "mọi truy vấn qua ORM".
- **`SUM(orders.total_amount)` phải đếm trên bảng `orders` đơn lẻ** — cộng cột này sau `JOIN order_items` sẽ nhân lên ~50 lần vì mỗi đơn có ~50 dòng chi tiết (18.260 × 50 ≈ 913.000). Xem GHI-CHU-TIEN-DO.md mục 8c.
- **`date_trunc` + filter năm:** `period=year` + `year=2017` cho ra **1** điểm (cả năm gộp 1 bucket), không phải 5. Bỏ filter `year` mới được 5 điểm cho 5 năm dữ liệu.
- **Session dùng `autoflush=False`** (`app/database.py`). Viết xong rồi mới `SELECT` sẽ **không thấy** thay đổi chưa commit. Mọi chỗ tính tổng (`SUM`) phải `db.flush()` trước, nếu không tổng sẽ được tính từ trạng thái cũ.
- **`db.flush()` phải nằm TRONG `try` bắt `IntegrityError`.** `flush()` mới là chỗ thực sự phát `INSERT`/`UPDATE`, nên vi phạm UNIQUE nổ ra ở đây chứ không ở `commit()`. Đặt ngoài `try` thì client nhận **500** thay vì **409**. Đã gặp đúng lỗi này 3 chỗ ở B6.
- **`orders.total_amount` / `total_quantity` là cột thường, KHÔNG phải generated column.** Không có gì trong DB tự đồng bộ chúng với `order_items` — chính API phải tính lại bằng `SUM(line_total)` và `SUM(quantity)` sau **mỗi** lần thêm/sửa/xoá dòng hàng. Sửa thiếu bước này là header đơn lệch với dòng của nó ngay lần ghi đầu tiên.
- **`order_date` là `timestamptz` nhưng dữ liệu nhập theo mốc giờ địa phương +07:00.** `2017-01-01T00:00:00+07:00` = `2016-12-31T17:00:00Z`. Lọc `from_date`/`to_date` bằng mốc **UTC** sẽ **cắt mất 10 đơn** của ngày 01/01 (đúng 1 đơn/cửa hàng). Lọc năm 2017 bằng UTC ra 3.640, bằng +07:00 ra đúng 3.650.
- **`order_items` có UNIQUE `(order_id, product_id)`.** Thêm lại sản phẩm đã có trong đơn → **409**. Trong `POST /orders`, trùng `product_id` ngay trong payload bị chặn sớm bằng `field_validator` → 422 nêu tên sản phẩm, thay vì để DB trả `IntegrityError` chung chung.
- **`order_date` mặc định phải là timezone-aware.** Cột là `timestamptz`; truyền `datetime.now()` (naive) sẽ bị PostgreSQL từ chối: *"timestamp with time zone cannot be used with naive datetime"*. Dùng `datetime.now(timezone.utc)`.
- **Schema KHÔNG đặt `extra="forbid"`** (đã chốt 12/10/2026). Field lạ trong body sẽ bị **bỏ qua âm thầm**, không báo 422. Quyết định giữ nguyên để nhất quán toàn hệ thống. **Hệ quả: gõ sai chính tả tên field (vd `quantitiy`) sẽ không bị phát hiện — phải test kỹ ở tầng frontend.**
- **`python-multipart` là BẮT BUỘC, không phải tuỳ chọn.** FastAPI khai báo `UploadFile`/`File(...)` mà thiếu nó thì router **lỗi ngay lúc import**, không phải lúc chạy. Đã thêm vào `backend/requirements.txt`.
- **File `.xlsx` thực chất là file ZIP** (bắt đầu bằng `PK\x03\x04`). Kiểm tra 4 byte đầu giúp bắt lỗi "đổi tên `.csv` nhưng nội dung vẫn là Excel" và trả **400 kèm hướng dẫn**, thay vì để pandas ném `UnicodeDecodeError` khó hiểu.
- **Chiến lược import: `rollback` (mặc định) hoặc `skip`** qua query param `on_error`. Validate **toàn bộ** trước rồi mới ghi — nếu ghi từng dòng thì không có "trạng thái chưa ghi" nào để so sánh, và file hỏng ở dòng 9.001 sẽ để lại 9.000 dòng.
- **Validator phải trả về `(values, error)` — nếu `error` là `None` thì `values` BẮT BUỘC khác `None`.** Đã vi phạm đúng điều này ở B7: trả `(None, None)` cho `order_code` trùng → `None` lọt vào writer → **500**. Giờ có chặn phòng thủ trong `_run_import`.
- **`inventory` UNIQUE `(store_id, product_id, expiry_date)`** và **`products.order_code`/`product_code` UNIQUE.** Phải kiểm tra trùng **cả trong file lẫn với DB**. Trùng với DB → **409** + không ghi gì. Trùng trong file → báo lỗi theo dòng.
- **Cleanup trong script test phải xoá theo KHÓA CHÍNH (`= ANY(:ids)`), KHÔNG dùng `WHERE ... LIKE 'prefix%'`.** `LIKE` **không khớp `NULL`**, nên bản ghi không có cột chuỗi (vd lô hàng nhập không có `batch_code`) sẽ lọt khỏi cleanup — mà kiểm tra "còn sót dữ liệu test không" cũng viết bằng `LIKE` nên **báo PASS sai**. Bài học từ B7: dùng `created_ids` mà server đã trả về, rồi xác minh lại bằng `count(*) WHERE id > <mốc seed>`.
- **`v_daily_sales` có `GROUP BY store_id, order_date, product_id` là THỪA — quyết định KHÔNG sửa view (chốt 12/10/2026).** Vì `order_items` UNIQUE `(order_id, product_id)` nên mỗi cặp đơn/sản phẩm chỉ có **đúng 1** dòng — `SUM()` chỉ có thể trả về chính dòng đó. Đọc view tốn một `Sort` + `GroupAggregate` trên 912.999 dòng mà **không đổi kết quả**. Đo: **1.606 ms qua view vs 680 ms join thẳng `order_items`**, tổng tiền khớp từng cent cho cả 7 nhóm. **Lý do không sửa:** đổi view = đổi schema cần migration, đã có workaround, chỉ 2 endpoint bị ảnh hưởng. → **Endpoint cần chi tiết dòng hàng thì join thẳng `order_items`, đừng đọc view.**
- **Báo cáo nhóm hàng PHẢI dùng `SUM(OrderItem.line_total)`**, không tự tính lại `quantity * unit_price * (1-discount/100)` — để DB tự tính bằng generated column.
- **Khi lọc theo ngày trên `orders` (timestamptz), dựng mốc bằng `VN_TZ = +07:00`, không dùng UTC.** Endpoint B8 khai báo param là `date` (không phải `datetime`) và tự dựng mốc giữa nửa đêm giờ địa phương — nhờ vậy chuỗi `2017-01-01T00:00:00Z` bị **422** thay vì âm thầm cắt mất 10 đơn.
- **⛔ `forecast-vs-actual` KHÔNG tính được MAPE — hạn chế dữ liệu (chốt 12/10/2026).** `forecasts` chỉ phủ **2018-01-01 → 2018-01-30**, còn dữ liệu bán hàng kết thúc **2017-12-31** → **hai khoảng không giao nhau**, `matched_rows = 0`. API trả `mape: null` kèm `message` giải thích, **không** báo số sai. **Khi viết Chương 4 PHẢI nêu rõ điều này — KHÔNG được trình bày như đã đo được độ chính xác trên dữ liệu thật.** Số RMSE/MAE/MAPE 9,97 ở bảng đánh giá 100 cặp là đo trên tập **test nội bộ** của mô hình, là con số khác và không thay thế cho kiểm chứng ngoài mẫu.
### ⚠️ Ba đặc tính dữ liệu phải nhớ khi viết test hoặc báo cáo

| # | Vấn đề | Hệ quả |
|---|--------|--------|
| 1 | **SP 13, 28, 45 chỉ có dự báo cho 9/10 cửa hàng** (270 dòng) — 7 sản phẩm còn lại đủ 300 | Tổng 2.910 dòng prophet **không** chia hết cho 10. Đừng đoán `2910/10`. Cũng đừng giả định mọi cặp (SP × CH) đều có dự báo. |
| 2 | **Category "Food" (id 1) không có sản phẩm nào** | Không có doanh thu → inner join loại khỏi kết quả. DB có **8** nhóm nhưng `/dashboard/revenue-by-category` trả **7**. Đây là đúng, không phải thiếu dữ liệu. |
| 3 | **`avg_order_value` chia cho SỐ ĐƠN, không chia số dòng hàng** | Một đơn có 50 dòng vẫn là **một** lần mua. Chia cho 50 sẽ thấp hơn thực tế 50 lần. Cột `orders.total_amount` đã là tổng của dòng hàng rồi. |

### ⚠️ Ghi chú B8 — đo độ chính xác dự báo trên dữ liệu thật

- **`forecast-vs-actual` chưa đo được MAPE**: `forecasts` phủ 2018-01-01→01-30, dữ liệu bán hàng kết thúc 2017-12-31 → **không giao nhau**, `matched_rows = 0`. API trả `mape: null` + `message` giải thích, **không** báo số bịa.
- **RMSE/MAE/MAPE 9,97 trong bảng đánh giá 100 cặp là đo trên tập test nội bộ của mô hình**, không phải kiểm chứng ngoài mẫu. Khi viết Chương 4 phải phân biệt rõ hai thứ này.
- Logic ghép trong `forecast-vs-actual` đã viết đúng và sẽ chạy được ngay khi có dữ liệu thực tế cho tháng 1/2018.

### ⛔ Ghi chú B8 — sửa hay không sửa view `v_daily_sales`

**Quyết định: KHÔNG sửa view.** Đổi view = đổi schema cần migration; đã có workaround (join thẳng `order_items`); chỉ 2 endpoint bị ảnh hưởng.

`v_daily_sales` có `GROUP BY store_id, order_date, product_id` là **thừa** vì `order_items` UNIQUE `(order_id, product_id)` — mỗi cặp chỉ có đúng 1 dòng. Đọc view tốn `Sort` + `GroupAggregate` trên 912.999 dòng mà **không đổi kết quả** (đo: 1.606 ms qua view vs 680 ms join thẳng, tổng tiền khớp từng cent cả 7 nhóm).

→ **Endpoint cần chi tiết dòng hàng thì join thẳng `order_items`, đừng đọc view.** Ghi nhớ khi viết endpoint mới.

- **Đơn `completed`/`cancelled` bị khóa 2 chiều.** Không sửa được header, không sửa/xoá được dòng hàng. `completed` **không** quay lại `pending` được (cần bút toán bù trừ chứ không phải đảo trạng thái); `cancelled` thì quay lại `pending` được. **Hệ quả thực tế: không có đường qua API để dọn dữ liệu test của một đơn đã `completed`** — phải xoá bằng SQL.
- **`passlib` KHÔNG dùng được với `bcrypt` 5.0** (đã thử 12/10/2026). passlib 1.7.4 đọc `bcrypt.__about__.__version__` — thuộc tính đã bị xoá từ bcrypt 4.1+. Nó **nuốt** lỗi `AttributeError` rồi báo sai hoàn toàn: *"password cannot be longer than 72 bytes"* cho một mật khẩu **7 byte**. Thông báo đó sẽ khiến người đọc đi tìm một lỗi không tồn tại. → Dùng thư viện `bcrypt` trực tiếp (`app/security.py`).
- **JWT PHẢI có claim `type` (`access` / `refresh`).** Thiếu nó thì access token chạy được ở endpoint refresh và ngược lại — vô nghĩa hoá việc có hai vòng đời token. `decode_token()` kiểm tra claim này.
- **Logout dùng denylist trong RAM** (`jti` → hết hạn), **KHÔNG lưu trong DB.** Hệ quả phải nói rõ: **restart server là mọi token đã logout sống lại.** Chấp nhận được với 1 tiến trình dev; với nhiều tiến trình thì phải chuyển sang Redis hoặc bảng DB.
- **3 user seed ban đầu có `password_hash` = chuỗi placeholder 29 ký tự**, không phải hash → **không mật khẩu nào đăng nhập được**. Đã chạy `scripts/reset_user_passwords.py` để đặt hash bcrypt thật: `owner/Owner@2026`, `manager/Manager@2026`, `staff/Staff@2026` (**chỉ dùng khi phát triển**).
- **`users.role` là `owner | manager | staff`** — KHÔNG có `admin`. CHECK constraint trong DB là nguồn sự thật.
- **Đã bảo vệ 28 endpoint ghi (POST/PUT/DELETE)**. Endpoint GET vẫn mở. Chính sách: sản phẩm · cửa hàng · nhóm · dự báo · import · `DELETE alerts` → **owner+manager**; tồn kho · đơn hàng · trạng thái cảnh báo → **mọi user đã đăng nhập**.
- **Query param phải khớp TÊN mà client gửi.** FastAPI **bỏ qua âm thầm** query param lạ. Đã dính: khai báo `fmt` nhưng spec/client gửi `format` → cả 3 định dạng đều trả CSV, `?format=bogus` vẫn 200. Sửa bằng `Query(..., alias="format")`. Kiểm bằng cách gửi giá trị sai và xem có 422 không.
- **PDF giới hạn 1.000 dòng (`MAX_PDF_ROWS`), CSV/XLSX 50.000.** reportlab vẽ **mỗi ô** bằng `Paragraph` để xuống dòng — đắt gấp ~100 lần so với chuỗi thường: báo cáo lãng phí mất 77 giây cho ~700 dòng, báo cáo bán hàng **timeout quá 120 giây**. Trang PDF có ghi rõ đã cắt và gợi ý dùng CSV/XLSX.
- **`group_by=day` phải gom theo ngày, KHÔNG gom thêm theo cửa hàng/nhóm hàng.** Bản đầu gom cả 3 chiều → 1.826 × 10 × 8 = **146.080 dòng**, file 3 MB, 24 giây. Sửa còn **1.826 dòng**, 91 KB, 4 giây.
- **Mốc "30 ngày gần nhất" phải neo vào ngày CÓ DỮ LIỆU, không phải `CURRENT_DATE`.** Và **phải lọc `status='completed' AND order_type='sale'`** — chỉ cần một đơn nháp tạo "hôm nay" cũng kéo mốc về hiện tại và **làm mọi số bán hàng về 0**. Đã dính lỗi này ở B10.
- **Không đọc tuple kết quả query bằng chỉ số vị trí.** Ở B10 đã đọc nhầm `row[10]` (unit_cost) thay cho `row[11]` (total_value), báo giá trị lô sai 350 lần mà không báo lỗi. Đã chuyển sang **unpack theo tên**.

## ⛔ Quyết định đã chốt 03/10/2026 — KHÔNG sửa, ghi chú vào Chương 4

### 1. KHÔNG sửa Chương 2. Giữ nguyên "XGBoost = mô hình chính"

Chương 2 là cơ sở lý thuyết, trình bày cả 5 mô hình, chỉ **kỳ vọng** XGBoost là mô hình chính. Kết quả thực nghiệm ở Chương 4: **Prophet thắng 97/100 cặp**, đảo ngược dự kiến.

**Khi viết Chương 4, phải trình bày đúng như sau:**
- Nêu rõ đây là **kết quả thực nghiệm đảo ngược kỳ vọng ban đầu** — không giấu, không sửa lại giả định
- Giải thích cơ chế: XGBoost dựa trên `lag_1..lag_28`, mạnh ở chế độ one-step nhưng **suy giảm khi dự báo 30 ngày liên tục** (phải đệ quy, sai lệch tích luỹ). Prophet vốn là mô hình đa bước và có `yearly_seasonality` sẵn
- Dẫn chiếu lợi thế của cách trình bày này: dự đoán ban đầu khác kết quả thực tế → **thể hiện quá trình nghiên cứu khoa học**, đúng như GVHD đánh giá cao
- **KHÔNG sửa Chương 2.** Chương 2 là lý thuyết chung, không sai — sai ở chỗ dự đoán mô hình nào sẽ thắng, và điều đó chính là giá trị của phần thực nghiệm

### 2. KHÔNG sửa `max_stock` trong seed data

`max_stock` trong seed được đặt **độc lập với doanh số Kaggle** (48–300), trong khi nhu cầu thực tế là 861–2.793/ngày. Hệ quả: **100/100 cặp bị cap** khi tính `recommended_import_qty` (nhu cầu thuần 232.397 → đề xuất sau cap 7.286).

**Đây là hạn chế của dữ liệu, KHÔNG phải lỗi đồ án.** Sửa `max_stock` sẽ phải seed lại `inventory` — tốn thời gian, không đáng.

**Khi viết Chương 4, phải nêu rõ:**
- Con số `recommended_import_qty` trong DB bị nén bởi `max_stock`, **không phản ánh đúng nhu cầu dự báo**
- Cột `raw_need` trong `ai-model/outputs/forecast_summary_30d.csv` giữ lại nhu cầu chưa cap để đối chiếu
- Nếu không nói rõ, người đọc sẽ hiểu nhầm rằng mô hình dự báo thiếu chính xác

## Current Progress

- [x] Cấu trúc thư mục — 8 thư mục gốc + 30+ thư mục con (commit `31df9f7`)
- [x] T1: README.md chính, 11 mục (commit `31df9f7`)
- [x] T3: Sơ đồ kiến trúc hệ thống, 4 sơ đồ Mermaid (commit `31df9f7`)
- [x] T4.1: Chương 1 — Tổng quan đề tài (commit `f55dce4`)
- [x] T4.2: Chương 2 — Cơ sở lý thuyết (commit `40020ca`)
- [x] Ghi chú tiến độ — GHI-CHU-TIEN-DO.md (commit `8245924`)
- [x] D1: SQL Schema 10 bảng — đã test thật, 10/10 bảng + 16 khoá ngoại (commit `ea9e96e`)
- [x] Fix encoding SQL — comment sang tiếng Anh, thuần ASCII (commit `48f4b4b`)
- [x] i18n — SQL lưu key, tạo `backend/app/i18n/vi.json` (commit `9372a0d`)
- [x] Quy tắc SQL bắt buộc trong AGENTS.md (commit `aaec0c6`)
- [x] Tải dataset Kaggle về `datasets/raw/` (không commit — có trong .gitignore)
- [x] D2: Seed data — categories 8, stores 10, products 50, users 3 (đã test `psql -f`)
- [x] D3: Import Kaggle 2017 → 3.650 orders + 182.500 order_items (giá MÔ PHỎNG theo nhóm hàng)
- [x] D4: Seed inventory (1.330 lô) + transactions (11.412) + alerts (518) — đã test `psql -f`
- [x] Sửa comment SQL sai về nguồn dữ liệu dự báo (migration 004) — dữ liệu không đổi
- [x] Chọn 10 sản phẩm huấn luyện (điều tra lại tiêu chí mùa vụ — không dùng được)
- [x] M0: Import lại dataset Kaggle **5 năm** (2013–2017) — 912.999 dòng, 1.826 ngày
- [x] M0: Tune Prophet trên 5 năm → `cps=0.01, multiplicative, yearly=20`
- [x] M0: Test 1 cặp — Prophet RMSE 9,98 (thắng), XGBoost 10,91, ARIMA 18,36
- [x] M1: Chạy **100 cặp** trong 13,2 phút — Prophet RMSE 9,97 (thắng 97/100)
- [x] M2: Dự báo 30 ngày (01/01–30/01/2018) → **3.000 dòng** trong bảng `forecasts`
- [x] M3: `docs/05-tham-khao/ket-qua-danh-gia-model.md`
- [x] B1: Setup backend FastAPI — config/database/main + CORS + 3 endpoint health, test thật `localhost:8000/docs` (đã chụp màn hình)
- [x] B2: 10 ORM models trong `app/models/` — test thật 947.590 dòng qua ORM, relationship OK
- [x] B3: CRUD products `/api/v1/products` — 5 endpoint + Pydantic schemas, test 27/27 pass
- [x] B4: CRUD stores · categories · inventory + read-only forecasts · alerts — 37 operation, test toàn bộ pass
- [x] B5: API dashboard tổng hợp — 6 endpoint, test toàn bộ pass, mọi số đối chiếu khớp DB/CSV
- [x] B6: API bán hàng — orders (7 endpoint) + order-items (5 endpoint), 155 check PASS
- [x] B7: API import Excel/CSV — 3 endpoint upload + 2 endpoint template, 115 check PASS
- [x] B8: API dashboard nâng cao — 6 endpoint (doanh thu theo CH/nhóm · top CH · giá trị tồn kho · lãng phí · forecast-vs-actual), 121 check PASS
- [x] B10: API đề xuất nhập hàng — 3 endpoint (import · expiring · slow-moving)
- [x] B11: API xuất báo cáo — 4 endpoint × 3 định dạng (CSV · XLSX · PDF)
- [x] B12: Authentication JWT — login · refresh · me · logout + bảo vệ **28** endpoint ghi
- [ ] F1: Setup Frontend React
- [ ] T2: README con cho từng thư mục
- [ ] Tích hợp AI Model
