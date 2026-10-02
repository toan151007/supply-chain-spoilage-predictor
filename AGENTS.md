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
- Chạy backend: `uvicorn app.main:app --reload --port 8000`
- Cài đặt frontend: `cd frontend && npm install`
- Chạy frontend: `npm run dev` (cổng 3000)
- Chạy database: `psql -U postgres -d spoilage_predictor`
- Import SQL schema: `psql -U postgres -d spoilage_predictor -f database/01-schema/02-create-tables.sql`
- Chạy AI model: `cd ai-model && jupyter notebook`

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
| Node.js | v24.15.0 (npm 11.12.1) |
| PostgreSQL | 18.6 · service `postgresql-x64-18` · port 5432 |
| Database | `spoilage_predictor` · 10 bảng đã tạo · đang rỗng |
| Xác thực | `scram-sha-256` · mật khẩu nằm trong `.env` cục bộ, KHÔNG commit |

| statsmodels | 0.15.0 (ARIMA) |
| scikit-learn | 1.9.1 |
| XGBoost | 3.4.1 |
| Prophet | 1.4.0 (kèm CmdStan 2.37.0) |

✅ **Python 3.14.7 chạy được đủ 3 mô hình — KHÔNG cần lùi phiên bản.**
Còn thiếu: `fastapi`, `uvicorn`, `pydantic` (cho backend B1).

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
- [ ] M1: Train 3 mô hình (Prophet / XGBoost / ARIMA) cho 100 cặp
- [ ] M2: Dự báo 30 ngày + ghi vào bảng `forecasts`
- [ ] B1: Setup backend FastAPI
- [ ] B2: Kết nối backend với database
- [ ] T2: README con cho từng thư mục
- [ ] Setup Frontend React
- [ ] Tích hợp AI Model
