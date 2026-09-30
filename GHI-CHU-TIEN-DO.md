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
| SQL Schema | ⬜ Chưa làm | **Task kế tiếp** |
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

### Ưu tiên 1: SQL Schema (task đang ghi "đang làm" từ đầu)

Tạo `database/01-schema/02-create-tables.sql` theo lược đồ đã thống nhất tại `docs/03-thiet-ke/kien-truc-he-thong.md` (mục 7) và Chương 3 sẽ dùng lại.

**9 bảng đã thống nhất:**

| Bảng | Ghi chú chính |
|------|---------------|
| `users` | Tài khoản người dùng |
| `categories` | Phân loại sản phẩm |
| `products` | Có `expiry_date`, `min_stock`, `max_stock` |
| `inventory` | Tồn kho hiện tại, unique theo (product_id, store_id) |
| `inventory_transactions` | Lịch sử nhập/xuất — **bảng quan trọng nhất cho dự báo** |
| `orders` | Đơn hàng |
| `order_items` | Chi tiết đơn hàng |
| `forecasts` | Kết quả dự báo + model đã dùng |
| `alerts` | Cảnh báo hết hạn / tồn kho bất thường |

**Yêu cầu cần nhớ:**
- Chuẩn 3NF, khoá chính/khoá ngoại rõ ràng
- Chỉ mục trên `product_id`, `expiry_date`, `transaction_date`
- `NUMERIC` cho số lượng chính xác (không dùng FLOAT cho tồn kho)
- Timestamptz cho mọi cột thời gian
- Comment `COMMENT ON TABLE/COLUMN` bằng tiếng Việt (rất thuyết phục khi bảo vệ đồ án)

**Kèm theo nên làm:** `database/02-seed/seed-data.sql` — dữ liệu mẫu đủ 6–12 tháng để test mô hình dự báo ngay.

### Ưu tiên 2: Chương 3 — Phân tích và thiết kế hệ thống

Tạo `docs/02-bao-cao/chuong-3-phan-tich-thiet-ke.md`:
- 3.1 Phân tích yêu cầu nghiệp vụ
- 3.2 Yêu cầu chức năng / phi chức năng
- 3.3 Thiết kế kiến trúc & mô hình hóa nghiệp vụ
- 3.4 Thiết kế cơ sở dữ liệu
- 3.5 Thiết kế API
- 3.6 Thiết kế giao diện

*(Phần sơ đồ Use Case / Sequence / kiến trúc đã có sẵn ở `docs/03-thiet-ke/kien-truc-he-thong.md` — tham chiếu lại, không cần vẽ lại.)*

### Ưu tiên 3: Setup Backend FastAPI

- `backend/requirements.txt`
- `backend/app/main.py` — FastAPI + CORS cho `localhost:3000` + WebSocket
- `backend/app/config.py`, `database.py`
- `backend/app/models/` — SQLAlchemy models theo 9 bảng
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
