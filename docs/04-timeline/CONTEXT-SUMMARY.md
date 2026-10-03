# Tóm tắt toàn bộ dự án — Context Summary

> **Cập nhật:** 03/10/2026 · commit `7a95bbf`
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

### 2.2 Database — 10 bảng

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

### 2.3 AI/ML — kết quả M1 + M2 + M3

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

### 2.4 10 sản phẩm dùng để huấn luyện

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

**Không có task nào đang dở dang.** Đã hoàn thành trọn M1 + M2 + M3 và dừng tại mốc chờ duyệt.

### Trạng thái Git

| Mục | Trạng thái |
|-----|-----------|
| Commit cuối | `7a95bbf` — docs: cap nhat quyet dinh ve Chuong 2 + max_stock |
| Working tree | Sạch, khớp 100% với `origin/main` |
| Số commit từ đầu dự án | 23 |

Lịch sử commit gần đây:

```
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
| **B1** | Setup backend FastAPI | 🔴 Tiếp theo | Cần cài `fastapi`, `uvicorn`, `pydantic` |
| **B2** | Kết nối backend với database qua SQLAlchemy ORM | 🔴 Sau B1 | Mọi API prefix `/api/v1/` |
| T4.3 | Viết Chương 3 — Thiết kế hệ thống | 🟡 TB | Cần kết quả M1–M3 làm căn cứ |
| T4.4 | Viết Chương 4 — Thực nghiệm | 🟡 TB | **BẮT BUỘC đọc mục 8j GHI-CHU-TIEN-DO.md trước** |
| F1 | Setup Frontend React | 🟢 Thấp | |
| T2 | README con cho từng thư mục | 🟢 Thấp | |

**Chưa có Chương 3 và Chương 4.** Sau khi B1–B2 xong sẽ đủ căn cứ viết 2 chương này.

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
| 5 | File Python: `snake_case` · Component React: `PascalCase` · Comment tiếng Việt |
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

# Backend
cd backend; uvicorn app.main:app --reload --port 8000

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
| Thiếu thư viện cho backend | Cài `fastapi`, `uvicorn`, `pydantic` (cho B1) |

---

## Tài liệu liên quan

| File | Vai trò |
|------|---------|
| `AGENTS.md` | Hướng dẫn AI: tech stack, quy tắc, môi trường, quyết định, tiến độ chi tiết |
| `GHI-CHU-TIEN-DO.md` | Ghi chú tiến độ chi tiết theo từng phiên, lịch sử lỗi, phân tích |
| `README.md` | Tài liệu chính dự án |
| `docs/04-timeline/CONTEXT-SUMMARY.md` | File này — bản tóm tắt ngắn |

**Khi chuyển sang máy hoặc AI mới:** đọc file này → đọc `AGENTS.md` → chạy `git status`.