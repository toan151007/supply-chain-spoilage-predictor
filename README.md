# Supply Chain Spoilage Predictor

**Nền tảng Quản trị Chuỗi cung ứng Chống lãng phí**

[![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.143-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-8-646CFF?logo=vite&logoColor=white)](https://vite.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.4-06B6D4?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![SQL Server](https://img.shields.io/badge/SQL_Server-2025_Express-CC2927?logo=microsoftsqlserver&logoColor=white)](https://www.microsoft.com/sql-server)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Giới thiệu

Trong ngành bán lẻ và F&B, việc nhập hàng dựa trên kinh nghiệm thường dẫn đến **lãng phí thực phẩm** nghiêm trọng — hàng hóa bị hỏng, hết hạn sử dụng hoặc tồn kho quá lâu. Theo thống kê ngành, khoảng **30–40%** sản phẩm thực phẩm bị lãng phí mỗi năm.

**Supply Chain Spoilage Predictor** là nền tảng quản trị chuỗi cung ứng chống lãng phí, giúp chủ cửa hàng:

- **Dự báo nhu cầu** bán hàng chính xác bằng AI (Prophet, XGBoost, ARIMA)
- **Tối ưu nhập hàng** dựa trên dự báo nhu cầu và hạn sử dụng
- **Giảm lãng phí** thực phẩm tối đa
- **Cảnh báo sớm** hàng sắp hết hạn, tồn kho thấp/dư thừa

> **Lưu ý về dữ liệu:** Bộ dữ liệu huấn luyện lấy từ Kaggle *Walmart Store Sales — Time Series Forecasting* (2013–2017). Dataset **không có cột giá**, nên giá bán/giá nhập trong hệ thống là **giá mô phỏng theo nhóm hàng**, chỉ dùng để demo dashboard doanh thu — **không phải số liệu thật**. Mô hình dự báo chỉ dùng `quantity` nên kết quả không bị ảnh hưởng.

---

## Công nghệ sử dụng

### Tech Stack

| Lớp | Công nghệ | Ghi chú |
|-----|-----------|---------|
| **Frontend** | React 19, Vite 8, Tailwind CSS 3.4, React Router 7, Axios, Recharts | Dark Mode, Responsive (Sidebar/Drawer) |
| **Backend** | Python 3.14, FastAPI 0.143, Uvicorn, Pydantic v2 | JWT Authentication, phân quyền theo role |
| **Database** | Microsoft SQL Server 2025 Express | **100% Stored Procedure** (74 SP), `pyodbc` + ODBC Driver 18 |
| **AI/ML** | Prophet (mô hình chính), XGBoost, ARIMA, scikit-learn | Dự báo nhu cầu 30 ngày tới |
| **AI Chatbot** | Google Gemini API (`google-genai` SDK) | Hỏi đáp dựa trên dữ liệu thật của hệ thống |
| **Real-time** | WebSocket (FastAPI native) | Push cảnh báo tức thời, không cần reload |

### Vì sao 100% Stored Procedure?

Mọi thao tác đọc/ghi dữ liệu đều đi qua `EXEC dbo.sp_...` — không ORM, không raw SQL trong router. Lợi ích:

- Logic nghiệp vụ nằm một chỗ, dễ audit và bảo trì
- Mỗi procedure có `BEGIN TRY ... BEGIN CATCH` + `TRANSACTION` đảm bảo toàn vẹn dữ liệu
- Mã lỗi nghiệp vụ thống nhất (`50001` NOT_FOUND → 404, `50002` DUPLICATE → 409, `50003` REFERENCED → 409, `50004` INVALID_STATE → 409, `50005` INVALID_INPUT → 422)

---

## Tính năng chính

### Quản lý nghiệp vụ

| Tính năng | Mô tả |
|-----------|-------|
| **Danh mục & Sản phẩm** | CRUD nhóm hàng (phân cấp cha/con), sản phẩm, đơn vị tính, giá bán/giá nhập |
| **Kho hàng** | Theo dõi lô hàng theo cửa hàng, ngày nhập, hạn sử dụng; lọc hàng sắp hết hạn (3/7/14/30 ngày) |
| **Đơn hàng** | Quản lý đơn bán/nhập, dòng chi tiết, trạng thái `pending`/`completed`/`cancelled` |
| **Cửa hàng** | Quản lý cửa hàng tiện lợi, nhà hàng, kho trong chuỗi |

### Phân tích & Báo cáo

| Tính năng | Mô tả |
|-----------|-------|
| **Dashboard** | Doanh thu, top sản phẩm, giá trị tồn kho, lãng phí, doanh thu theo cửa hàng/nhóm hàng |
| **Import dữ liệu** | Upload Excel/CSV cho sản phẩm, đơn hàng, tồn kho (chiến lược `rollback` hoặc `skip`) |
| **Xuất báo cáo** | CSV · XLSX · PDF cho báo cáo bán hàng, tồn kho, lãng phí, đề xuất nhập hàng |

### AI & Real-time

| Tính năng | Mô tả |
|-----------|-------|
| **Dự báo nhu cầu** | Dự báo 30 ngày tới cho từng cặp sản phẩm × cửa hàng (2.820 dòng dự báo) |
| **Đề xuất nhập hàng** | Gợi ý số lượng nhập tối ưu dựa trên dự báo + hạn sử dụng + `max_stock` |
| **Chatbot AI** | Hỏi đáp về tồn kho, đơn hàng, cảnh báo, dự báo — dựa trên dữ liệu thật qua Stored Procedure |
| **Cảnh báo thời gian thực** | WebSocket `/ws/alerts` push thông báo khi cảnh báo được cập nhật/xóa |

### Phân quyền người dùng

| Role | Quyền hạn |
|------|-----------|
| **Owner** | Toàn quyền: master data, import, dự báo, xóa cảnh báo, cấu hình |
| **Manager** | Như Owner (quản trị master data, import, báo cáo) |
| **Staff** | Chỉ thao tác tồn kho, đơn hàng, đánh dấu cảnh báo đã đọc |

> Backend là nơi quyết định cuối cùng: **28 endpoint ghi** (POST/PUT/DELETE) được bảo vệ bằng JWT + role check.

---

## Cấu trúc thư mục

```
supply-chain-spoilage-predictor/
├── backend/                    # FastAPI server
│   ├── app/
│   │   ├── config.py           # Cấu hình (đọc từ .env)
│   │   ├── database.py         # DbSession bọc pyodbc, map mã lỗi SQL Server
│   │   ├── main.py             # Điểm khởi động, đăng ký router
│   │   ├── dependencies.py     # JWT, require_role
│   │   ├── security.py         # Hash mật khẩu (bcrypt), tạo/giải mã token
│   │   ├── websocket_manager.py# Quản lý kết nối WebSocket
│   │   ├── i18n/vi.json        # Bản dịch tiếng Việt cho cảnh báo
│   │   ├── routers/            # 19 router (products, orders, chat, ws...)
│   │   ├── schemas/            # Pydantic request/response models
│   │   └── models/             # ORM models (chỉ tham khảo cấu trúc)
│   ├── requirements.txt
│   └── .env.example            # File mẫu cấu hình
├── frontend/                   # React app
│   ├── src/
│   │   ├── pages/              # 10 trang (Dashboard, Products, Inventory...)
│   │   ├── components/
│   │   │   ├── common/         # Icon, Spinner, BackButton, Chatbot, RealtimeAlerts
│   │   │   └── layout/         # Layout, Header, Sidebar, ProtectedRoute
│   │   ├── contexts/           # AuthContext, ThemeContext
│   │   ├── services/api.js     # Axios instance + interceptor refresh token
│   │   └── utils/format.js     # formatCurrency, formatDate, formatNumber
│   ├── vite.config.js          # Proxy /api → localhost:8000
│   └── package.json
├── database/                   # Schema + Stored Procedure
│   ├── HUONG-DAN-CHAY-SSMS.md  # 10 bảng + 49 SP (chạy bằng SSMS)
│   ├── 03-migrations/          # Migration 010: 25 SP phân tích/báo cáo
│   ├── 02-seed/                # Seed data SQL Server
│   └── 04-queries/             # Truy vấn kiểm tra
├── ai-model/                   # Jupyter notebooks + script huấn luyện
│   ├── outputs/                # forecast_summary_30d.csv, kết quả đánh giá
│   └── scripts/                # train_models.py, forecast_next_month.py
├── datasets/                   # Dữ liệu mẫu (raw không commit CSV)
├── docs/                       # Tài liệu đồ án (báo cáo, thiết kế, timeline)
├── scripts/                    # Script tiện ích (smoke test, import, convert)
├── tests/                      # Unit tests
├── start_all.bat               # Script khởi động nhanh cả 2 server
├── AGENTS.md                   # Quy tắc phát triển dự án
├── GHI-CHU-TIEN-DO.md          # Nhật ký tiến độ
└── README.md
```

---

## Hướng dẫn cài đặt & Chạy

### Yêu cầu hệ thống

| Thành phần | Phiên bản tối thiểu | Ghi chú |
|-----------|---------------------|---------|
| **Python** | 3.10+ (khuyến nghị 3.14) | Đã kiểm chứng trên 3.14.7 |
| **Node.js** | 20+ (khuyến nghị 24) | Kèm npm 11+ |
| **SQL Server** | 2019+ (khuyến nghị 2025 Express) | Instance `LAPTOP-I39E3UT2\SQLEXPRESS` |
| **ODBC Driver** | 18 for SQL Server | Bắt buộc cho `pyodbc` |
| **Git** | 2.30+ | |

### Bước 1 — Clone dự án

```bash
git clone https://github.com/toan151007/supply-chain-spoilage-predictor.git
cd supply-chain-spoilage-predictor
```

### Bước 2 — Cài đặt Backend

```bash
pip install -r backend/requirements.txt
```

> ⚠️ `uvicorn[standard]` kéo theo `websockets` — bắt buộc cho realtime.

### Bước 3 — Cài đặt Frontend

```bash
cd frontend
npm install
cd ..
```

### Bước 4 — Cấu hình file `.env`

Sao chép file mẫu và điền thông tin thật:

```bash
Copy-Item backend/.env.example .env     # Windows PowerShell
# hoặc: cp backend/.env.example .env    # Linux/macOS
```

Nội dung cần điền trong `.env` (đặt ở **thư mục gốc**, không phải `backend/`):

```env
# ---- Database ----
DB_USER=sa
DB_PASSWORD=<mat_khau_sql_server_cua_ban>
DB_HOST=LAPTOP-I39E3UT2\SQLEXPRESS
DB_PORT=1433
DB_NAME=spoilage_predictor
DB_DRIVER=ODBC Driver 18 for SQL Server

# ---- CORS ----
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]

# ---- JWT ----
SECRET_KEY=<chuoi_ngau_nhien_dai_it_nhat_32_ky_tu>
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# ---- AI Chatbot (Google Gemini) ----
GEMINI_API_KEY=<api_key_cua_ban>
GEMINI_MODEL=gemini-2.5-flash
```

> 🔒 **`.env` đã nằm trong `.gitignore` — KHÔNG BAO GIỜ commit file này.**
> Tạo `SECRET_KEY` bằng: `python -c "import secrets; print(secrets.token_urlsafe(48))"`

### Bước 5 — Tạo Database

1. Mở **SQL Server Management Studio (SSMS)**
2. Kết nối tới instance `LAPTOP-I39E3UT2\SQLEXPRESS` bằng SQL Server Authentication (`sa`)
3. Mở file `database/HUONG-DAN-CHAY-SSMS.md`, copy/paste từng khối T-SQL theo thứ tự:
   - Tạo database `spoilage_predictor`
   - 10 bảng + index + 6 trigger + 4 view
   - **49 Stored Procedure**
4. Chạy migration bổ sung 25 SP phân tích/báo cáo:

```
database/03-migrations/010-sqlserver-analytics-procedures.sql
```

5. (Tuỳ chọn) Nạp dữ liệu mẫu:

```bash
python scripts/convert_seed_to_sqlserver.py
python scripts/load_sqlserver_data.py
```

> ⚠️ **KHÔNG chạy lại script tạo schema khi DB đã có dữ liệu** — file đó có `DROP TABLE`.

### Bước 6 — Chạy nhanh bằng `start_all.bat` ⭐

Đây là cách **được khuyến nghị**. Script tự động:

1. **Kill** mọi tiến trình đang chiếm cổng **8000** và **3000** (tránh `WinError 10013`)
2. Mở cửa sổ mới chạy **Backend**: `python -m uvicorn app.main:app --reload --port 8000`
3. Mở cửa sổ mới chạy **Frontend**: `npm run dev`

**Cách dùng:** chỉ cần **click đúp** vào file `start_all.bat` ở thư mục gốc dự án.

| Dịch vụ | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API docs (Swagger) | http://localhost:8000/docs |
| Backend ReDoc | http://localhost:8000/redoc |
| WebSocket cảnh báo | ws://localhost:8000/ws/alerts |

### Chạy thủ công (nếu cần)

**Backend** — bắt buộc `cd backend` trước, vì module import theo đường dẫn tuyệt đối `from app.config import settings`:

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

**Frontend**:

```bash
cd frontend
npm run dev
```

### Kiểm tra nhanh

```bash
# Đọc: 48 check
python scripts/smoke_test_api.py

# Ghi: 29 check (cần server đang chạy)
python scripts/smoke_test_writes.py
```

---

## Tài khoản Test

Ba tài khoản mẫu đã được seed sẵn (mật khẩu hash bcrypt thật):

| Username | Password | Role | Quyền hạn |
|----------|----------|------|-----------|
| `owner` | `Owner@2026` | Owner | Toàn quyền quản trị |
| `manager` | `Manager@2026` | Manager | Quản trị master data, import, báo cáo |
| `staff` | `Staff@2026` | Staff | Tồn kho, đơn hàng, đánh dấu cảnh báo |

> ⚠️ **Chỉ dùng cho môi trường phát triển.** Đổi mật khẩu trước khi triển khai production.

---

## Kết quả mô hình dự báo

Đánh giá trên **100 cặp** (sản phẩm × cửa hàng), chia tập theo mốc ngày `2017-10-01`:

| Mô hình | RMSE | MAE | MAPE | Số cặp thắng |
|---------|------|-----|------|--------------|
| **Prophet** ⭐ | **9,97** | **7,94** | **10,43%** | **97 / 100** |
| XGBoost | 10,98 | 8,77 | 11,69% | 3 / 100 |
| ARIMA | 20,20 | 16,44 | 23,77% | 0 / 100 |

> **Prophet là mô hình chính** — kết quả thực nghiệm đảo ngược kỳ vọng ban đầu (Chương 2 dự kiến XGBoost). XGBoost mạnh ở chế độ one-step nhưng suy giảm khi dự báo 30 ngày liên tục do phải đệ quy.
>
> Chi tiết: `docs/05-tham-khao/ket-qua-danh-gia-model.md`

---

## Tài liệu tham khảo

| File | Nội dung |
|------|----------|
| `AGENTS.md` | Quy tắc phát triển bắt buộc (SQL, Python, React) |
| `GHI-CHU-TIEN-DO.md` | Nhật ký tiến độ chi tiết từng bước |
| `database/HUONG-DAN-CHAY-SSMS.md` | Schema + 49 Stored Procedure |
| `docs/` | Báo cáo đồ án, thiết kế hệ thống, timeline |

---

## Tác giả

| Thông tin | Giá trị |
|-----------|---------|
| **Sinh viên thực hiện** | *(điền tên của bạn)* |
| **MSSV** | *(điền MSSV)* |
| **Lớp** | *(điền lớp)* |
| **GVHD** | *(điền tên giảng viên hướng dẫn)* |
| **Trường** | *(điền tên trường)* |
| **Năm** | 2026 |

---

## Giấy phép

Dự án phát hành theo giấy phép **MIT License**.

```
MIT License

Copyright (c) 2026 Supply Chain Spoilage Predictor

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

<div align="center">

**Supply Chain Spoilage Predictor** — Giảm lãng phí, tăng lợi nhuận 🌱

</div>
