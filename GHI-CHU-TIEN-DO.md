# Ghi chú tiến độ làm việc

> **Ngày cập nhật:** 30/09/2026
> **Giai đoạn:** Ngày 5/10 – 6/10 (tương ứng ngày 5 và ngày 6 trong timeline dự án)
> **Repo:** https://github.com/toan151007/supply-chain-spoilage-predictor

---

## 1. Trạng thái tổng quan

| Hạng mục | Trạng thái | Ghi chú |
|----------|-------------|---------|
| Cấu trúc thư mục | ✅ Xong | Đã tạo đầy đủ 8 thư mục chính |
| AGENTS.md | ✅ Xong | Đọc + cập nhật tiến độ nhiều lần |
| T1 — README.md | ✅ Xong | Commit `31df9f7` |
| T3 — Sơ đồ kiến trúc | ✅ Xong | Commit `31df9f7` |
| T4 phần 1 — Chương 1 | ✅ Xong | Commit `f55dce4` |
| T4 phần 2 — Chương 2 | ✅ Xong | Commit `40020ca` |
| SQL Schema (10 bảng) | ✅ Xong | `database/01-schema/02-create-tables.sql` — xem `git log` |
| Backend FastAPI | ⬜ Chưa làm | |
| Frontend React | ⬜ Chưa làm | |
| AI Model | ⬜ Chưa làm | |

---

## 2. Lịch sử commit

```
40020ca  T4 (phần 2): Add Chapter 2 theoretical foundations report
f55dce4  T4 (phần 1): Add Chapter 1 overview report
31df9f7  T1+T3: Add README and system architecture docs
```

Remote: `origin/main` đã đồng bộ tại `40020ca`.

---

## 3. File đã tạo

| File | Mô tả |
|------|-------|
| `README.md` | Tài liệu chính dự án (11 mục: giới thiệu, tính năng 2 giai đoạn, công nghệ, cấu trúc thư mục, cài đặt, sử dụng, lộ trình) |
| `AGENTS.md` | File hướng dẫn AI — tech stack, quy tắc bắt buộc, tiến độ |
| `docs/03-thiet-ke/kien-truc-he-thong.md` | Kiến trúc tổng thể, Use Case, Sequence, mô tả module, API endpoints, DB schema |
| `docs/02-bao-cao/chuong-1-tong-quan.md` | Chương 1 — Tổng quan đề tài (~2.050 từ) |
| `docs/02-bao-cao/chuong-2-co-so-ly-thuyet.md` | Chương 2 — Cơ sở lý thuyết (~3.500 từ, 6 mục) |

### Chi tiết Chương 1
Mục 1.1 Đặt vấn đề · 1.2 Mục tiêu (chung + GĐ1 + GĐ2) · 1.3 Đối tượng & phạm vi · 1.4 Phương pháp nghiên cứu · 1.5 Ý nghĩa thực tiễn · 1.6 Cấu trúc báo cáo.

### Chi tiết Chương 2
Mục 2.1 Chuỗi cung ứng bán lẻ · 2.2 Bài toán dự báo nhu cầu · 2.3 Năm mô hình dự báo + bảng so sánh 12 tiêu chí · 2.4 Nghiên cứu liên quan + 6 khoảng trống · 2.5 Công nghệ sử dụng · 2.6 Tổng kết.

---

## 4. Quyết định thiết kế đã chốt

Những điều đã thống nhất trong tài liệu — **không nên đổi ngay** vì sẽ phải sửa cả Chương 1 và Chương 2:

| Quyết định | Ghi chú |
|------------|---------|
| Mô hình dự báo cơ sở: **Prophet** | Tự động phát hiện changepoint, xử lý ngày lễ |
| Mô hình dự báo chính: **XGBoost** | Vì có thể feature importance + biến ngoại |
| Đối chứng: **ARIMA** + trung bình động | Để so sánh công bằng |
| **Không dùng LSTM** trong hệ thống | Chỉ trình bày lý thuyết — dữ liệu quy mô nhỏ không đủ |
| Phạm vi: sản phẩm hạn sử dụng **< 90 ngày** | Nhóm rủi ro lãng phí cao nhất |
| AI Agent dùng **grounding** (RAG đơn giản hóa) | Lấy context từ DB rồi gửi Gemini → giảm tình trạng "bịa" số liệu |
| API prefix bắt buộc `/api/v1/` | Theo quy tắc trong AGENTS.md |
| ORM: SQLAlchemy, cấu trúc 3NF | Theo quy tắc trong AGENTS.md |

---

## 5. ⚠️ Việc cần tra cứu / xác minh

Không phải việc bận gấp, nhưng **bắt buộc làm trước khi nộp báo cáo**:

- [ ] **Đối chiếu trích dẫn Chương 2 [5]–[8]**: số tạp, số trang, năm xuất bản với bản gốc
  - Taylor & Letham — *The American Statistician* 72(1), 37–45
  - Chen & Guestrin — KDD '16, 785–794
  - Breiman — *Machine Learning* 45(1), 5–32
  - Hochreiter & Schmidhuber — *Neural Computation* 9(8), 1735–1780
- [ ] **Mục 2.4 hiện là "hướng nghiên cứu" chưa có nguồn cụ thể** — cần tra Google Scholar / IEEE Xplore để gắn bài báo thật
- [ ] **Số liệu lãng phịch thực phẩm Việt Nam** — đang để trống `(cần bổ sung)`, cần nguồn Tổng cục Thống kê hoặc Cục Chế biến & Phát triển thị trường nông nghiệp
- [ ] **Số liệu minh họa biến động nhu cầu theo mùa vụ** trong Chương 1 (mục 2.2.2 của Chương 2)
- [ ] **Tên trường / khoa** trong mục 1.1 Chương 1 và phần tác giả
- [ ] **Khả năng cung cấp dữ liệu thực tế** — Chương 1 ghi cần tối thiểu 12 tháng dữ liệu bán hàng theo ngày; cần xác nhận với đơn vị thực hành
- [ ] **Danh mục tài liệu tham khảo đầy đủ** ở phần cuối báo cáo (thư mục `docs/05-tham-khao/`)

---

## 6. Task ngày mai — theo thứ tự đề xuất

### ✅ Ưu tiên 1: SQL Schema — ĐÃ XONG

File: `database/01-schema/02-create-tables.sql`

**10 bảng (đã thêm `stores` — quyết định 30/09, hỗ trợ chuỗi nhiều cửa hàng):**

| # | Bảng | Ghi chú chính |
|---|------|---------------|
| 1 | `stores` | **THÊM MỚI** — chi nhánh/cửa hàng, thực thể gốc cho toàn bộ dữ liệu |
| 2 | `users` | Tài khoản, role owner/manager/staff, `store_id` NULL = quản lý toàn hệ thống |
| 3 | `categories` | Phân loại nhiều cấp (tự tham chiếu `parent_category_id`) |
| 4 | `products` | **KHÔNG có `expiry_date`** — có `shelf_life_days`, `min_stock`, `max_stock`, `reorder_point` |
| 5 | `inventory` | Tồn kho theo LÔ HÀNG. UNIQUE `(store_id, product_id, expiry_date)` |
| 6 | `inventory_transactions` | **Quan trọng nhất cho dự báo.** import/export/adjustment/disposal |
| 7 | `orders` | `order_type`: sale / purchase (gộp cả bán và nhập) |
| 8 | `order_items` | `line_total` dùng GENERATED ALWAYS AS STORED (PostgreSQL 12+) |
| 9 | `forecasts` | Lưu kết quả TỪNG mô hình để so sánh công bằng + `recommended_import_qty` |
| 10 | `alerts` | 5 loại cảnh báo, phục vụ real-time qua WebSocket |

**Ngoài 10 bảng, file còn có:**
- Hàm `fn_update_updated_at()` + 6 trigger tự cập nhật `updated_at`
- Hàm `fn_generate_inventory_alerts(days)` — sinh cảnh báo theo 4 quy tắc, chống trùng
- 4 view: `v_daily_sales` (nguồn dữ liệu cho dự báo), `v_low_stock`, `v_expiring_inventory`, `v_product_stock_summary`
- Script kiểm tra: đếm số bảng, liệt kê khoá ngoại

**Quyết định thiết kế quan trọng đã chốt:**
1. **Thêm bảng `stores`** → hỗ trợ chuỗi nhiều cửa hàng, thay vì chỉ 1 cửa hàng
2. **`expiry_date` đặt ở `inventory` + `inventory_transactions`**, KHÔNG ở `products` — vì hạn sử dụng thuộc về từng lô hàng tại từng cửa hàng, không phải thuộc tính bất biến của sản phẩm
3. Dùng **CHECK constraint** thay vì PG `ENUM` — dễ migrate, tương thích SQLAlchemy ORM
4. `NUMERIC` mọi số lượng (không FLOAT), `TIMESTAMPTZ` mọi cột thời gian
5. `order_items` UNIQUE `(order_id, product_id)` — 1 sản phẩm 1 dòng trong đơn

> ⚠️ **Cần cập nhật `docs/03-thiet-ke/kien-truc-he-thong.md` mục 7** — nơi đang ghi 9 bảng, chưa có `stores` và còn ghi `products` có `expiry_date`. Chưa sửa vì cần đồng bộ với Chương 3.

### Ưu tiên 2: Seed data (nên làm ngay)

Tạo `database/02-seed/seed-data.sql` — dữ liệu mẫu:
- 3 cửa hàng, 8 nhóm sản phẩm, ~30 sản phẩm (thực phẩm tươi sống + đồ uống hạn ngắn)
- Dữ liệu giao dịch **ít nhất 12 tháng** theo ngày, có mùa vụ Tết rõ rệt để mô hình dự báo học được
- Cố tình tạo một vài tình huống hết hàng để kiểm tra hiện tượng censored demand
- 1 tài khoản cho mỗi role (owner/manager/staff)

Có thể sinh dữ liệu bằng Python (pandas + faker) thay vì viết tay — nhanh và linh hoạt hơn.

### Ưu tiên 3: Chương 3 — Phân tích và thiết kế hệ thống

Tạo `docs/02-bao-cao/chuong-3-phan-tich-thiet-ke.md`:
- 3.1 Phân tích yêu cầu nghiệp vụ
- 3.2 Yêu cầu chức năng / phi chức năng
- 3.3 Thiết kế kiến trúc & mô hình hóa nghiệp vụ
- 3.4 Thiết kế cơ sở dữ liệu
- 3.5 Thiết kế API
- 3.6 Thiết kế giao diện

*(Phần sơ đồ Use Case / Sequence / kiến trúc đã có sẵn ở `docs/03-thiet-ke/kien-truc-he-thong.md` — tham chiếu lại, không cần vẽ lại.)*

### Ưu tiên 4: Setup Backend FastAPI

- `backend/requirements.txt`
- `backend/app/main.py` — FastAPI + CORS cho `localhost:3000` + WebSocket
- `backend/app/config.py`, `database.py`
- `backend/app/models/` — SQLAlchemy models theo **10 bảng**
- `backend/app/routers/` — prefix `/api/v1/`

> **Lưu ý AGENTS.md:** Không sửa `config.py` / `.env` mà không hỏi trước. Mọi truy vấn DB phải qua ORM, **không raw SQL trong routers**.

---

## 7. Lệnh thường dùng

```powershell
# Xem trạng thái
git status --short

# Commit + push (PowerShell dùng dấu chấm phẩy, KHÔNG dùng &&)
git add <file>
git commit -m "message"
git push

# Chạy backend (ghi chú: PowerShell)
cd backend; uvicorn app.main:app --reload --port 8000

# Chạy frontend
cd frontend; npm run dev

# Import schema
psql -U postgres -d spoilage_predictor -f database/01-schema/02-create-tables.sql
```

> ⚠️ PowerShell trên máy này **không hỗ trợ `&&`** — luôn dùng `;`

---

## 8. Quy tắc bắt buộc (rút lại từ AGENTS.md)

1. KHÔNG dùng PHP, ASP.NET hoặc framework ngoài danh sách trong AGENTS.md
2. KHÔNG sửa `config.py`, `.env` mà không hỏi trước
3. Mọi API có prefix `/api/v1/`
4. Mọi truy vấn DB qua ORM — không raw SQL trong routers
5. Tên file Python: `snake_case` · Component React: `PascalCase`
6. Trước khi commit chạy `git status`
7. File Python: `snake_case` · Comment tiếng Việt

---

## 9. Cảnh báo môi trường

| Vấn đề | Ghi chú |
|--------|---------|
| `LF will be replaced by CRLF` | Bình thường trên Windows (do `core.autocrlf`), **không phải lỗi** |
| Token bị giới hạn | AGENTS.md ghi "Token Antigravity có giới hạn → cần commit thường xuyên" |
| Chuyển sang IDE khác | **Luôn yêu cầu AI đọc `AGENTS.md` trước** |
| WebSocket | Nhớ bật CORS cho `localhost:3000` |

---

*Ngày mai: bắt đầu bằng việc đọc lại `AGENTS.md`, kiểm tra `git status`, rồi làm SQL Schema.*
