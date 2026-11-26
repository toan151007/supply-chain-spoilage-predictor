# AGENTS.md — Supply Chain Spoilage Predictor

## Project Overview

Nền tảng Quản trị Chuỗi cung ứng Chống lãng phí cho chuỗi cửa hàng bán lẻ/F&B.
Mục tiêu: Dự báo nhu cầu, tối ưu nhập hàng, giảm lãng phí thực phẩm.

Từ 31/10/2026 hệ thống được nâng thành **nền tảng điều phối chuỗi cung ứng thông minh**:
ngoài dự báo nhu cầu còn có **điều chuyển hàng giữa cửa hàng** (5 bước có duyệt),
**dự báo theo mùa vụ** (tự động làm mới 5 phút) và **chatbot tối ưu tốc độ**.

## Tech Stack

- Frontend: React.js + Vite + Tailwind CSS
- Backend: Python FastAPI (hoặc Node.js/Express)
- Database: **Microsoft SQL Server 2025 Express** — instance `LAPTOP-I39E3UT2\SQLEXPRESS`, database `spoilage_predictor` (**bắt buộc theo yêu cầu GVHD**)
- Truy cập DB: `pyodbc` + ODBC Driver 18 for SQL Server, **100% Stored Procedure**
- AI/ML: Prophet, XGBoost, ARIMA (Python)
- Real-time: WebSocket
- AI Agent: Gemini API (chatbot hỏi đáp kho)
- Email: `fastapi-mail` + Gmail SMTP (App Password) — gửi thông tin tài khoản mới

## Commands

- Cài đặt backend: `pip install -r backend/requirements.txt`
- Chạy backend: `cd backend; uvicorn app.main:app --reload --port 8000`
- Test backend: mở `http://localhost:8000/docs`
- Cài đặt frontend: `cd frontend && npm install`
- Chạy frontend: `npm run dev` (cổng 3000)
- Kết nối database (SSMS): server `LAPTOP-I39E3UT2\SQLEXPRESS`, login `sa`, database `spoilage_predictor`
- Chạy SQL bằng dòng lệnh: `sqlcmd -S "LAPTOP-I39E3UT2\SQLEXPRESS" -U sa -P <mat_khau> -C -d spoilage_predictor -i <file.sql>`
- Tạo schema + Stored Procedure: xem `database/HUONG-DAN-CHAY-SSMS.md` (copy/paste trên SSMS), sau đó chạy `database/03-migrations/010-sqlserver-analytics-procedures.sql` và `database/03-migrations/011-transfers-seasonal.sql`
- Chạy migration 011 bằng dòng lệnh: `sqlcmd -S "<host>" -U sa -P <mat_khau> -C -d spoilage_predictor -I -b -i database\03-migrations\011-transfers-seasonal.sql`
- Chạy migration 012 (làm mới dữ liệu cảnh báo) rồi nạp lại: `sqlcmd ... -i database\03-migrations\012-refresh-alert-demo-data.sql` sau đó `python scripts\refresh_alert_demo_data.py`
- Chạy migration 013 (quyền người dùng + email): `sqlcmd ... -I -b -i database\03-migrations\013-users-permissions.sql`
- Cấu hình gửi mail: điền `MAIL_USERNAME`, `MAIL_PASSWORD` (**App Password 16 ký tự**, không phải mật khẩu Gmail), `MAIL_FROM` trong `.env` — xem `backend/.env.example`
- Chạy AI model: `cd ai-model && jupyter notebook`

> ⚠️ **Dữ liệu PostgreSQL cũ KHÔNG tự chuyển sang SQL Server.** File T-SQL trong
> `HUONG-DAN-CHAY-SSMS.md` chỉ tạo cấu trúc (10 bảng + trigger + view + procedure).
> Việc nạp lại dữ liệu (912.999 `order_items`, 3.000 `forecasts`…) sẽ làm ở bước sau.

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

## Frontend (đã triển khai F1 — 24/10/2026)

1. **Công nghệ:** Vite 8 + React 19 + Tailwind CSS 3.4 (`darkMode: 'class'`) +
   React Router 7 + Axios + Recharts. Dev server cổng **3000**, proxy `/api` →
   `http://localhost:8000` (không cần CORS khi dev). Màu chủ đạo được thiết kế theo tông Trắng - Xanh dương LHU (`#2a5aaa`, `#3b7bdb`, `#f8fafc`), thay đổi tại redesign LoginPage (31/10/2026).
2. **Phân quyền Admin và User thường**
   - `owner` / `manager` → quyền quản trị (master data, import, dự báo, xoá cảnh báo)
   - `staff` → chỉ thao tác tồn kho, đơn hàng, trạng thái cảnh báo
   - Ẩn/hiện menu và nút theo role; backend vẫn là nơi quyết định cuối cùng.
   - Frontend dùng `isAdmin` từ `AuthContext` (owner/manager); role lấy từ `/auth/me`.
3. **Dark Mode (Sáng / Tối)** — lưu `scsp_theme` trong `localStorage`, mặc định theo
   `prefers-color-scheme`; script trong `index.html` áp dụng class `dark` trước khi React mount.
4. **Responsive Design** — sidebar cố định từ breakpoint `lg`, dưới `lg` là drawer +
   backdrop + hamburger; nội dung dùng grid/flex và bảng cuộn ngang.
5. **Trang đã có:** Login (JWT thật), Layout (Header/Sidebar/Content),
   Dashboard (mockup số liệu minh hoạ), Sản phẩm (gọi API thật, tìm kiếm/lọc/phân trang).
6. **CRUD đã hoàn thiện (27/10/2026):** Sản phẩm, Nhóm hàng, Cửa hàng, Kho hàng đều có
   Thêm / Sửa / Xoá thật, gọi `POST` · `PUT` · `DELETE` qua `/api/v1/...`.
   Dùng chung 4 component: `Modal` (hộp thoại), `ConfirmDialog` (xác nhận xoá),
   `Toast` (thông báo xanh/đỏ) và `Field` (label + ô nhập).
   - Modal Sửa điền sẵn dữ liệu cũ; lỗi validate hiển thị **chữ đỏ ngay trong modal**.
   - Xoá luôn hỏi xác nhận; lỗi 409 (trùng mã / đang được tham chiếu) hiện toast đỏ.
   - Nút thêm/sửa/xoá chỉ render khi `isAdmin` (owner/manager); `staff` chỉ xem.
8. **Điều chuyển hàng (31/10/2026):** trang `/transfers` (`TransfersPage.jsx`) — thanh 5
   bước bấm được để lọc (Đề xuất → Chờ duyệt → Đã duyệt → Đang chuyển → Đã nhận),
   3 thẻ tổng hợp, bảng có tìm kiếm + lọc + phân trang, modal tạo yêu cầu, modal xác
   nhận thao tác (có ghi chú) và modal chi tiết hiển thị tiến trình theo mốc thời gian.
   Nút thao tác đổi theo trạng thái **và** theo vai trò: `staff` chỉ thấy Gửi duyệt /
   Huỷ / Xác nhận giao / Xác nhận nhận; Duyệt và Từ chối chỉ hiện với owner/manager.
9. **Dự báo theo mùa vụ:** `ForecastsPage` có 2 tab — "Dự báo mới nhất" (giữ nguyên) và
   "Dự báo theo mùa" (`components/forecasts/SeasonalPanel.jsx`). Tab mùa vụ **tự động
   gọi lại API mỗi 5 phút** (`REFRESH_MS = 5 * 60 * 1000`) và hiện đồng hồ đếm ngược,
   giờ cập nhật, nút "Làm mới ngay". Không cần F5.
10. **Việc còn lại:** nối Dashboard với API thật, tạo đơn hàng mới và hoàn thiện các mẫu
    báo cáo CSV/XLSX/PDF còn lại. Mục "Đề xuất nhập hàng" **đã bỏ khỏi Sidebar** và thay
    bằng trang Báo cáo Hàng hóa (xem mục 17); các endpoint đề xuất nhập hàng ở backend
    vẫn giữ nguyên.
11. **Tinh giản giao diện + Lọc nhanh cảnh báo (10/11/2026):**
    - `AlertsPage` có 4 nút lọc nhanh dạng pill: **Tất cả · Đã hết hạn · Sắp hết hạn ·
      Tồn kho thấp** — bấm là gọi API ngay (`?alert_type=...`), không cần nút "Áp dụng".
    - Bảng cảnh báo rút từ 7 cột xuống 4 (Cảnh báo · Mức độ · Ngày tạo · Thao tác):
      bỏ cột "Loại" trùng với pill, bỏ badge "Đã đọc/Chưa đọc" (thay bằng chấm xanh
      nhỏ), mức độ hiển thị bằng **chấm màu + chữ** thay vì pill nền đặc.
    - `InventoryPage`: tình trạng hạn dùng của lô còn mới là **chữ xám thường**, chỉ lô
      hết hạn / còn ≤ 7 ngày mới có màu + chấm. Bỏ `title` tooltip ở các nút icon
      (đã có `aria-label`) ở Sản phẩm, Kho hàng, Nhóm hàng, Cửa hàng, Điều chuyển.
    - Biểu đồ (Dashboard, Dự báo) đổi màu chuỗi từ xanh lá sang dải LHU Blue.
12. **Chuẩn hoá định dạng tiền tệ (10/11/2026):**
    - `utils/format.js`: `formatCurrency(1420000000)` → **`1.420.000.000 đ`** (dấu chấm
      phân cách hàng nghìn, đơn vị `đ` ở cuối thay cho ký hiệu `₫`).
    - `formatCompactCurrency` **không dùng `Intl notation:'compact'`** nữa (bản `vi-VN`
      trả `1,42 T` / `842 Tr`, không phải tiếng Việt) mà tự chia đơn vị
      `nghìn tỷ → tỷ → triệu → nghìn`, giữ **2 chữ số thập phân**: `1,42 tỷ đ`,
      `842 triệu đ`, `1,85 triệu đ`.
    - `DashboardPage`: mảng `KPIS` lưu **số thật** (`1420000000`, `842000000`),
      `KpiCard` render qua `formatCurrency` cho `typeof value === 'number'`;
      thêm `tabular-nums` + `whitespace-nowrap` để số dài không ngắt dòng.
    - Đo thật: `1.420.000.000 đ` rộng **170 px** ở 24 px bold, thẻ hẹp nhất còn **191 px**
      nội dung → không tràn ở breakpoint 4 cột (1280 px).
    - **Hệ quả toàn cục:** mọi bảng dùng `formatCurrency` (Đơn hàng…) cũng đổi từ `₫`
      sang `đ` — cố ý, để cả hệ thống cùng một kiểu.
13. **Tên tài khoản dùng thử ở trang Đăng nhập (19/11/2026):**
    - `LoginPage.jsx` giữ mảng `DEMO_ACCOUNTS` với 3 trường: `label` (chữ hiển thị),
      `note` (mô tả quyền) và `username`/`password` (giá trị điền vào form).
    - Hiển thị: **Toàn (Admin)** · **Quản lý** · **Nhân viên** — không còn lộ chuỗi
      thô `owner` / `manager` / `staff` trên giao diện.
    - Bấm nút vẫn điền đúng `owner` / `manager` / `staff` + mật khẩu, nên logic đăng
      nhập không đổi; `title` + `aria-label` giữ tên tài khoản thật để dễ kiểm tra.
    - `users.full_name` của `owner` là **"Toàn"** (migration 013), nên Header sau khi
      đăng nhập hiện đúng "Toàn" + "Chủ sở hữu" + ảnh đại diện.
14. **Khoá tự sửa quyền của chính mình (19/11/2026):** trong modal Sửa tài khoản,
    `UsersPage.jsx` tự nhận biết `editing.user_id === currentUser.user_id` rồi
    - hiện banner vàng "Đây là tài khoản của bạn…",
    - **disable** ô Vai trò (kèm ghi chú "Bạn không thể tự thay đổi vai trò của mình."),
    - **disable** cả 7 công tắc quyền + công tắc "Tài khoản đang hoạt động" + hai nút
      "Chọn tất cả"/"Bỏ chọn",
    - **ẩn** nút xoá ở dòng của chính mình (dòng khác vẫn có).
    Khi submit, payload **bỏ** `role`, `is_active` và các cờ quyền — chỉ gửi họ tên,
    username, email, avatar (+ mật khẩu nếu có). Nhờ vậy sửa tên chính mình vẫn lưu được
    dù backend chặn đổi quyền.
15. **Tách tab Danh sách / Phân quyền (21/11/2026):** trang `/users` có **2 tab**:
    - **"Danh sách tài khoản"** — bảng Họ tên · Username · Email · Vai trò ·
      **Ngày giờ tạo** (`formatDateTime` → `dd/mm/yyyy HH:mm`) · Trạng thái · Thao tác.
      Chỉ 3 thao tác: Thêm tài khoản mới (`POST /users`), Sửa thông tin cơ bản
      (`PUT /users/{id}` — **chỉ họ tên + email**, username là khoá đăng nhập),
      Khoá/Mở khoá (`PUT /users/{id}/status`). Không có công tắc quyền ở tab này.
      Nút Xoá nằm trong modal Sửa (footer bên trái) để bảng không có thao tác thứ tư.
    - **"Cấp phép & Phân quyền"** — danh sách dọc bên trái (kèm `x/7 quyền`), khung bên
      phải có ô Vai trò + 7 công tắc + "Chọn tất cả / Bỏ chọn / Mặc định theo vai trò"
      + **"Lưu thay đổi quyền"** (chỉ bật khi `draftDirty`) + "Hoàn tác". Tự chọn tài
      khoản của mình thì khoá hết kèm banner.
    - Backend: thêm `PUT /users/{id}/permissions` (7 cờ tuỳ chọn + `role` tuỳ chọn,
      `None` = giữ nguyên) và `PUT /users/{id}/status` (`{is_active}`). Cả hai đọc dòng
      bằng `sp_Users_GetById`, merge rồi gọi `sp_Users_Update` với `PasswordHash = NULL`
      qua helper `_save_row` — **không thêm procedure, không đổi schema**. Vẫn owner-only
      và vẫn giữ 3 chốt chống tự khoá mình (403).
    - `ConfirmDialog` có thêm prop `tone` / `icon` / `busyLabel` (mặc định giữ nguyên đỏ +
      thùng rác) để dùng cho hộp "Khoá tài khoản" mà không hiện chữ "Đang xoá…".

16. **Gợi ý điều chuyển từ AI + tinh gọn mô hình + chặn timeout chatbot (22/11/2026):**
    - Trang `/transfers` có **2 tab**: "Danh sách yêu cầu" (giữ nguyên toàn bộ quy trình
      5 bước) và **"Gợi ý từ AI"** (`components/transfers/AISuggestionsPanel.jsx`).
      Tab AI gọi `GET /api/v1/transfers/suggestions` → `sp_Transfer_SuggestAI`, hiển thị
      cặp **cửa hàng dư → cửa hàng thiếu** kèm số lượng gợi ý, lý do, mức ưu tiên và
      nút "Tạo yêu cầu" (chỉ hiện khi có `can_manage_transfer`).
    - Nút "Tạo yêu cầu" trong tab AI **điền sẵn** form tạo yêu cầu (cửa hàng gửi/nhận,
      sản phẩm, số lượng làm tròn, mức ưu tiên, lý do), người dùng chỉ cần xác nhận.
      Tạo xong tự chuyển về tab danh sách, xoá lọc và về trang 1 để thấy yêu cầu mới.
    - **Chỉ dùng Prophet** cho cả tab AI và trang Dự báo: `model_name=prophet` được
      truyền từ frontend; `@ModelName` ở procedure vẫn là tham số nên có thể truyền
      `xgboost` khi cần đối chứng. Trang `/forecasts` **bỏ cột "Mô hình"** (còn 6 cột)
      vì mọi dòng đều là Prophet.
    - Chatbot: `api.js` đặt **timeout 60 giây riêng cho URL chứa `/chat`** (các API khác
      vẫn 20 giây). `chat_router.py` gọi Gemini trong `ThreadPoolExecutor` và **dùng
      chung một hạn 15 giây cho cả 2 lần thử**; hết hạn trả
      `"Hệ thống đang bận, vui lòng thử lại sau"` với `sources=[{"type":"timeout"}]`
      thay vì lỗi timeout.

17. **Báo cáo Hàng hóa & Rủi ro Hao hụt (23/11/2026):** mục "Đề xuất nhập hàng" (nhãn
    "SẮP RA MẮT") **bị xoá khỏi Sidebar**; nhóm "PHÂN TÍCH" chỉ còn **Báo cáo Hàng hóa**
    (`chart` icon) → route `/reports/spoilage`.
    - Trang `frontend/src/pages/SpoilageReportPage.jsx` gồm: header lọc **Hôm nay / 7 ngày /
      30 ngày**, Danh mục, Chi nhánh, Mức độ rủi ro + nút **Làm mới / Xuất Excel / Xuất
      PDF**; 4 thẻ KPI (Tổng tồn kho, Giá trị nguy cơ hao hụt, Tỷ lệ hao hụt, Số lô cần
      xử lý); biểu đồ cột chồng An toàn/Cảnh báo/Nguy cơ cao theo danh mục; biểu đồ đường
      xu hướng thất thoát + tỷ lệ xử lý; khung **"Tóm tắt & Khuyến nghị thông minh"**
      (Gemini, có fallback luật tiếng Việt); bảng chi tiết 500 lô và **Drawer "Xử lý"**
      bên phải với 3 thao tác **Khuyến mãi · Điều chuyển · Kiểm kê**.
    - Backend: `GET /api/v1/reports/spoilage` (chi tiết), `/spoilage/summary` (4 KPI + dữ
      liệu biểu đồ), `/spoilage/advice` (AI) và `/spoilage/export?format=xlsx|pdf|csv`;
      tất cả nằm trong `report_router.py` nên kế thừa `can_view_report`.
    - CSDL: migration `015-spoilage-risk-report.sql` thêm **view `v_spoilage_risk`** (một
      nơi duy nhất chứa công thức rủi ro) + **`sp_Reports_SpoilageRisk`** và
      **`sp_Reports_SpoilageSummary`**.
    - Drawer: "Khuyến mãi" tạo kế hoạch giảm giá theo số ngày còn lại (≤2 ngày: 50%,
      ≤7 ngày: 30%, còn lại 15%) và hiện ngay trong Drawer; "Điều chuyển" mở
      `/transfers`, "Kiểm kê" mở `/inventory`.

18. **Mặt hàng bán chạy theo ngày (24/11/2026):** tab thứ hai của nhóm báo cáo.
    - **Thanh tab dùng chung** `frontend/src/components/reports/ReportTabs.jsx` gắn ở
      đầu cả `SpoilageReportPage` (`/reports/spoilage`) lẫn `TopSellingPage`
      (`/reports/top-selling`); Sidebar vẫn chỉ có một mục "Báo cáo Hàng hóa".
    - Trang `frontend/src/pages/TopSellingPage.jsx` thiết kế như app bán hàng trên
      điện thoại: header có **nút quay lại · tiêu đề · kính lúp · phễu lọc**; hàng ngày
      `‹ Thứ Sáu, 20/11/2026 ›` (bấm vào chữ ngày mở `showPicker()` của
      `<input type="date">` ẩn); dải 3 ô tổng hợp **Sản phẩm · Bán ra · Doanh thu**;
      danh sách dọc **chấm màu + tên + nhóm/mã + doanh thu + ô SL**, sắp theo số lượng
      bán giảm dần.
    - Ô tìm kiếm **bỏ dấu tiếng Việt** (`normalize('NFD')` + xoá dấu + `đ→d`) nên gõ
      `sua` vẫn ra "Sữa chua 500g"; lọc theo tên, mã sản phẩm hoặc nhóm hàng.
    - Bộ lọc cho chọn **sắp xếp** (số lượng / doanh thu / tên A→Z) và **số dòng hiển thị**
      (10 / 20 / 50 / tất cả). Lọc và sắp xếp chạy ở client trên dữ liệu của một ngày,
      không gọi lại API.
    - Backend `GET /api/v1/reports/top-selling?date=YYYY-MM-DD` (`date` bỏ trống = ngày
      bán gần nhất) → `sp_Reports_TopSelling` (migration `016-top-selling.sql`), schema
      `top_selling_schema.py`. Nằm trong `report_router.py` nên kế thừa `can_view_report`.
    - **Ngày mặc định lấy từ dữ liệu, không lấy `GETDATE()`:** hôm nay là 24/11/2026
      nhưng bán hàng dừng ở 20/11/2026, nên mở trang phải thấy dữ liệu thật. Ngày được
      suy ra từ `sale_date` của dòng đầu tiên API trả về, rồi các mũi tên `‹ ›` mới dùng
      ngày tường minh. Ngày không có đơn hiện khung "Không có dữ liệu bán hàng cho ngày
      này" + nút "Về ngày có dữ liệu gần nhất" (đặt `date = null` để API tự chọn lại).
    - Ngày được parse theo **giờ địa phương** (`parseISO` tách chuỗi) chứ không dùng
      `new Date('2026-11-16')` — chuỗi ISO trần bị hiểu là UTC và lệch một ngày ở một số
      múi giờ.

19. **Ẩn trang Nhóm hàng khỏi giao diện (24/11/2026):** mục menu "Nhóm hàng"
    (`/categories`) **bị comment trong `Sidebar.jsx`** và route bị bỏ khỏi `App.jsx`
    (import `CategoriesPage` cũng bỏ) để giảm menu thừa — nhóm hàng đã quản lý gián tiếp
    qua form Sản phẩm. **Không xoá gì ở backend/DB:** bảng `categories`, API
    `/api/v1/categories` và các Stored Procedure vẫn nguyên; file `CategoriesPage.jsx`
    vẫn giữ trong repo để tham khảo. Dropdown chọn nhóm hàng ở trang Sản phẩm và bộ lọc
    danh mục ở Dashboard / Báo cáo Hàng hóa **không bị ảnh hưởng** vì chúng gọi thẳng API,
    không đi qua route này. Nếu cần bật lại: bỏ comment dòng menu và thêm lại route.

## Rules (BẮT BUỘC TUÂN THỦ)

- KHÔNG dùng PHP, ASP.NET, hay bất kỳ framework nào ngoài danh sách trên.
- KHÔNG sửa file cấu hình (config.py, .env) mà không hỏi trước.
- Mọi API phải có prefix `/api/v1/`.
- **Mọi thao tác dữ liệu phải gọi Stored Procedure** (`EXEC dbo.sp_...`). KHÔNG viết `SELECT/INSERT/UPDATE/DELETE` trực tiếp trong router, KHÔNG dùng ORM để đọc/ghi nghiệp vụ.
- **Mỗi Stored Procedure bắt buộc có `BEGIN TRY ... BEGIN CATCH` và `TRANSACTION`** (mẫu: `IF @@TRANCOUNT = 0 BEGIN TRANSACTION; ... IF @@TRANCOUNT > 0 COMMIT;` / `CATCH: IF @@TRANCOUNT > 0 ROLLBACK; THROW;`).
- Đặt tên file Python: snake_case. Tên React component: PascalCase.
- **Comment trong code Python dùng tiếng Anh KHÔNG DẤU** (tương thích console Windows cp1252). Tài liệu `.md` và file SQL vẫn dùng tiếng Việt / ASCII theo quy tắc riêng.
- Trước khi commit, chạy `git status` để kiểm tra.

## SQL Rules (BẮT BUỘC TUÂN THỦ)

- **SQL Server / T-SQL**, không dùng cú pháp PostgreSQL (`SERIAL`, `RETURNING`, `::`, `ILIKE`, `ON CONFLICT`…).
- Kiểu dữ liệu: `IDENTITY(1,1)`, `DATETIME2(7)`, `NVARCHAR`/`NVARCHAR(MAX)`, `BIT`, `DECIMAL`.
- Trước khi viết INDEX / VIEW / PROCEDURE, phải kiểm tra cột đã tồn tại trong CREATE TABLE chưa.
- KHÔNG tham chiếu cột không tồn tại. Chỉ dùng cột của bảng trong đúng JOIN đó.
- Sau khi viết file SQL, PHẢI tự test thật bằng `sqlcmd -i file.sql` (hoặc SSMS) trước khi commit.
- Nếu có lỗi, sửa ngay, không để lỗi sang task khác.
- File SQL giữ ASCII (comment tiếng Anh) để chạy được trên Windows PowerShell.
- Muốn thêm tiếng Việt vào SQL thì dùng cơ chế i18n: lưu KEY, dịch ở `backend/app/i18n/vi.json`.
- **UNIQUE + NULL:** SQL Server coi nhiều `NULL` là trùng nhau, PostgreSQL thì không. Với cột cho phép NULL (vd `inventory.expiry_date`), dùng **filtered unique index** `WHERE expiry_date IS NOT NULL`.
- **Không có `ON DELETE` ghép nhiều đường cascade** và **không cascade trên khoá tự tham chiếu** (`categories.parent_category_id`) — SQL Server báo lỗi 1785. Xử lý bằng Stored Procedure (set NULL cho con trước khi xoá).
- **Mã lỗi nghiệp vụ** do `THROW` trong procedure (router map sang HTTP):
  `50001` NOT_FOUND → 404 · `50002` DUPLICATE → 409 · `50003` REFERENCED → 409 · `50004` INVALID_STATE → 409 · `50005` INVALID_INPUT → 422.
- **Partial update:** Stored Procedure `Update` nhận **toàn bộ dòng đích**; router phải merge thay đổi vào dòng hiện tại trước khi gọi, để phân biệt "không đổi" và "xoá về NULL".
- **Không gọi procedure ghi khác bên trong một transaction đang mở** nếu procedure đó cũng `COMMIT` — sẽ commit sớm transaction ngoài. Các procedure đọc không được gọi trong transaction ghi.
- **`GO` là lệnh của SSMS/sqlcmd, KHÔNG gửi được qua pyodbc.** Khi gọi từ Python chỉ gửi một câu `EXEC dbo.sp_...`.
- **Bắt buộc bật `SET QUOTED_IDENTIFIER ON` + `SET ANSI_NULLS ON`** khi tạo bảng có filtered index / computed column (SSMS bật sẵn, sqlcmd thì không).

## Môi trường phát triển (đã kiểm chứng 02/10/2026)

| Thành phần | Phiên bản / thông tin |
|-----------|----------------------|
| Python | 3.14.7 (pip 26.2.1) |
| pandas | 3.0.6 |
| numpy | 2.5.3 |
| SQLAlchemy | 2.1.2 (chỉ dùng ở giai đoạn PostgreSQL cũ — sẽ bỏ dần) |
| pyodbc | 5.3.0 |
| ODBC Driver | 18 for SQL Server |
| FastAPI | 0.143.0 |
| uvicorn | 0.54.0 (`[standard]` — kèm websockets cho realtime) |
| pydantic | 2.14.1 |
| pydantic-settings | 2.15.0 |
| Node.js | v24.15.0 (npm 11.12.1) |
| SQL Server | 2025 Express (17.0.1000.7) · instance `LAPTOP-I39E3UT2\SQLEXPRESS` · port 1433 |
| Database | `spoilage_predictor` · 10 bảng · **dữ liệu sẽ nạp lại** (PostgreSQL cũ không tự chuyển) |
| Xác thực | SQL Server Authentication (`sa`) · mật khẩu nằm trong `.env` cục bộ, KHÔNG commit |

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
- **CHECK constraint** thay vì ENUM (dễ migrate, tương thích cả SQL Server)
- **Chuyển sang SQL Server (24/10/2026):** toàn bộ schema + Stored Procedure nằm trong `database/HUONG-DAN-CHAY-SSMS.md`. Các file `.sql` PostgreSQL cũ chỉ còn giá trị tham khảo, **KHÔNG chạy lại**.
- **100% thao tác dữ liệu qua Stored Procedure** — không ORM, không raw SQL trong router.

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

> **Lưu ý lịch sử:** các mục trong tiểu mục **"Giai đoạn PostgreSQL (lịch sử)"**
> bên dưới được ghi trong giai đoạn PostgreSQL. Nhiều mục **không còn áp dụng**
> (view `v_daily_sales` bản PostgreSQL, sequence, `psycopg2`, `timestamptz`…).
> Giữ lại để tham khảo lịch sử.

### SQL Server (24/10/2026) — mới

- **Bước 3 dùng `DbSession` bọc `pyodbc` raw connection, KHÔNG dùng SQLAlchemy Session.** `Session` không có `nextset()`, và procedure tự `COMMIT` transaction ngầm của pyodbc gây lỗi `266 Transaction count after EXECUTE...`. Engine tạo với `autocommit=True`, lấy connection bằng `engine.raw_connection()`. Router gọi `db.call("sp_Ten", {TenThamSo: value})` → `list[list[dict]]` (mỗi result set là list dict theo TÊN cột).
- **Chuỗi kết nối phải dựng qua `mssql+pyodbc:///?odbc_connect=<quote_plus(...)>`** vì host chứa dấu `\` bị URL-encode sai nếu viết dạng `user:pass@host`.
- **Có 95 Stored Procedure**: 49 trong `database/HUONG-DAN-CHAY-SSMS.md` + 25 trong `database/03-migrations/010-sqlserver-analytics-procedures.sql` (dashboard, dashboard nâng cao, đề xuất nhập hàng, báo cáo, import dùng `OPENJSON`) + **10 điều chuyển + 1 dự báo mùa vụ** trong `database/03-migrations/011-transfers-seasonal.sql` + **2 bảo trì cảnh báo** (`012-refresh-alert-demo-data.sql`) + **4 quản lý người dùng** (`sp_Users_List/Create/Update/Delete`) trong `013-users-permissions.sql` + **1 gợi ý điều chuyển AI** (`014-smart-transfer.sql`) + **2 báo cáo rủi ro hao hụt** (`015-spoilage-risk-report.sql`) + **1 mặt hàng bán chạy** (`016-top-selling.sql`). Chạy migration 010 → 011 → 012 → 013 → 014 → 015 → 016 sau file hướng dẫn.
- **Có 11 bảng** (10 bảng gốc + `transfer_requests`) và **5 view** (thêm `v_spoilage_risk`).
- **Nạp dữ liệu dev**: `python scripts/convert_seed_to_sqlserver.py` (sinh `database/02-seed/seed-sqlserver.sql`) rồi `python scripts/load_sqlserver_data.py`. Script nạp **bỏ các dòng `sales = 0`** để không vi phạm `CHECK (quantity > 0)` — đúng bài học cũ.
- **`sp_Orders_Delete` xoá dòng hàng trước rồi xoá đơn** trong cùng transaction (khôi phục `ON DELETE CASCADE` của PostgreSQL). Xoá đơn `completed` vẫn bị chặn ở tầng trạng thái.
- **Bảng `forecasts` hiện có 3.000 dòng = 100 cặp × 30 ngày** (97 cặp `prophet` + 3 cặp `xgboost`, đúng mô hình thắng cuộc của từng cặp). Số cũ 2.820 (94 cặp) là do loader lọc `model == 'prophet'` rồi bỏ thêm 3 cặp — đã sửa 05/11/2026.
- **`forecasts` PHẢI chứa dự báo TỪNG NGÀY, không phải trung bình tháng chia đều.** Bản cũ trong `scripts/load_sqlserver_data.py` làm `daily = total_predicted / 30`, bịa biên độ ±10% và ghi cứng `rmse/mae/mape = 9,97/7,94/10,43` cho mọi dòng → 30 ngày của một cặp giống hệt nhau, không thể đối chiếu theo ngày. Đã thay bằng `ai-model/scripts/forecast_next_month_sqlserver.py` (sinh `ai-model/outputs/forecasts_30d.csv`). Kiểm tra nhanh: `SELECT COUNT(DISTINCT predicted_quantity) FROM forecasts WHERE product_id=45 AND store_id=1` phải bằng **30**, không phải 1.
- **`forecast_summary_30d.csv` là snapshot của lần chạy M2 gốc**, giữ nguyên để đối chiếu `total_predicted`; script dự báo mới **không ghi đè** file này. Cột `forecasts.recommended_import_qty` lấy từ snapshot đó — API `/recommendations/import` không đọc cột này mà tự tính lại từ `SUM(predicted_quantity)` + tồn kho.
- **Smoke test API**: `python scripts/smoke_test_api.py` (48 check đọc) và `python scripts/smoke_test_writes.py` (29 check ghi). Cần chạy server trước bằng `python -m uvicorn` — máy này KHÔNG có `uvicorn` trên PATH.
- **sqlcmd cần `-I`** khi xoá/sửa bảng có computed column / filtered index, nếu không báo lỗi 1934 về `QUOTED_IDENTIFIER`.

- **sqlcmd mặc định tắt `QUOTED_IDENTIFIER`** → tạo filtered index / computed column báo lỗi 1934. Đầu file T-SQL phải có `SET QUOTED_IDENTIFIER ON; SET ANSI_NULLS ON;` (file hướng dẫn đã có).
- **SQL Server coi nhiều `NULL` là trùng nhau** trong UNIQUE. `inventory` và `inventory_transactions` phải dùng filtered unique index `WHERE ... IS NOT NULL`.
- **Không cascade được trên khoá tự tham chiếu** (`categories.parent_category_id`) → lỗi 1785. `sp_Categories_Delete` tự set `parent_category_id = NULL` cho các con rồi mới xoá.
- **`DATEPART(WEEKDAY, ...)` phụ thuộc `DATEFIRST`.** View `v_daily_sales` tính thứ bằng `DATEDIFF(DAY, '1900-01-01', ngày) % 7 + 1` (1900-01-01 là thứ Hai) để không phụ thuộc cấu hình.
- **`ORDER BY` + `OFFSET/FETCH` phải nằm trong CTE** khi cần join thêm bảng, nếu không SQL Server báo lỗi cú pháp.
- **`WITH` (CTE) không đứng ngay sau `IF`** → phải gán biến trong CTE rồi mới `IF`.
- **Không gọi procedure ghi khác trong lúc transaction đang mở** nếu procedure đó cũng `COMMIT` — transaction ngoài bị commit sớm. Các procedure `Create/Update` trong file đã tự inline phần tính lại tổng thay vì gọi `sp_Orders_RecalculateTotals`.
- **`GO` không gửi được qua pyodbc** — chỉ dùng trong SSMS/sqlcmd.
- **`THROW` bắt buộc câu lệnh trước kết thúc bằng `;`.** Đã gặp lỗi cú pháp khi đặt `IF ... THROW` ngay sau CTE.
- **`@@ROWCOUNT` phải đọc ngay sau câu lệnh vừa chạy**, trước mọi `IF`/`SELECT` khác.
- **Mã lỗi nghiệp vụ** 50001–50005 (xem mục SQL Rules) — router phải map sang HTTP, không trả 500.
- **Script tạo schema có `DROP`** — chạy trên DB đang có dữ liệu sẽ mất sạch. Chỉ chạy khi DB trống hoặc đã backup.

#### Làm mới dữ liệu cảnh báo (10/11/2026)

- **Seed cũ sinh ngày 24/10/2026 và không bao giờ tự cập nhật** → cảnh báo hiện
  "hết hạn 33 ngày" nhưng `created_at` vẫn 24/10. Đã thêm migration
  `database/03-migrations/012-refresh-alert-demo-data.sql` với **2 procedure bảo trì**:
  `sp_Maintenance_RefreshInventoryDates` (ghi lại `expiry_date`/`received_date` theo
  hôm nay, xoá sạch `alerts`) và `sp_Maintenance_FinalizeAlerts` (xoá cảnh báo
  `over_stock`, dàn `created_at` trong 3 ngày gần nhất).
- **Script `scripts/refresh_alert_demo_data.py` gọi tuần tự 3 procedure** (không ghi
  trực tiếp bảng): RefreshInventoryDates → `sp_Alerts_Generate @WarningDays = 7` →
  FinalizeAlerts. Chạy lại nhiều lần vẫn **không tích luỹ** cặp tồn kho thấp
  (procedure tự nâng các cặp còn dưới `min_stock` mà lần này không chọn lên trước).
- **`created_at` phải dàn theo hai chiều:** cảnh báo `expired` tạo **sau** ngày hết hạn,
  cảnh báo `expiring_soon` tạo **trước** ngày hết hạn. Nếu chỉ dàn ngẫu nhiên 0–3 ngày
  sẽ có dòng "hết hạn 1 ngày" nhưng "tạo 3 ngày trước" — vẫn vô lý.
- **Phải xoá cảnh báo `over_stock` sau khi generate.** `max_stock` trong seed (40–100)
  không cùng thang đo với nhu cầu Kaggle (hàng trăm/ngày) nên **mỗi cặp** đều vượt
  ngưỡng → 492 cảnh báo rác. Đây đúng là hạn chế đã ghi ở mục "KHÔNG sửa `max_stock`".
- **`sp_Alerts_Generate` không tạo được `low_stock` với seed gốc** vì mỗi cặp tồn
  400–1.000 đơn vị trong khi `min_stock` chỉ 8–30. Procedure bảo trì chọn **8 cặp**
  (theo `group_no % 63 = 1`) rồi hạ số lượng xuống dưới `min_stock` để có dữ liệu demo
  cho pill "Tồn kho thấp". Tổng tồn kho giảm ~2,6% — chấp nhận được với dữ liệu mẫu.
- **Không để `quantity = 0`** sau khi hạ tồn kho: các lô còn lại được đặt **1 đơn vị**
  (không phải 0) để bảng Kho hàng không hiện dòng "0" vô nghĩa.

### Điều chuyển hàng · dự báo mùa vụ · chatbot (31/10/2026)

- **`transfer_requests` có 5 khoá ngoại trỏ tới `users` đều phải `NO ACTION`.** Đặt
  `CASCADE` cho cả 5 → SQL Server báo lỗi **1785** (*may cause cycles or multiple
  cascade paths*). Cùng loại lỗi đã gặp với `categories.parent_category_id`.
- **`uq_transactions_reference` phải gồm `store_id`.** Một lần điều chuyển sinh **2**
  dòng `inventory_transactions` (xuất ở kho gửi, nhập ở kho nhận) cùng
  `reference_type='transfer'` và cùng `reference_id`. Thiếu `store_id` trong khoá là
  hai dòng đụng nhau ngay lần hoàn tất đầu tiên.
- **`chk_inv_tx_reference_type` phải mở rộng thêm `'transfer'`**, nếu không không ghi
  được giao dịch nào của điều chuyển.
- **`sp_Transfer_Complete` trừ kho theo FEFO:** chọn `expiry_date` thì trừ đúng lô đó,
  để trống thì lặp qua các lô **hết hạn trước**. Cộng kho đích thì gộp vào lô cùng hạn
  nếu đã có, chưa có mới tạo lô mới. Toàn bộ nằm trong **một** transaction.
- **`INSERT ... EXEC` KHÔNG dùng được với Stored Procedure có `BEGIN TRY/CATCH` +
  `ROLLBACK`.** SQL Server báo `Msg 3915 Cannot use the ROLLBACK statement within an
  INSERT-EXEC statement` **ngay cả khi procedure chạy thành công**. Muốn lấy kết quả
  thì gọi trực tiếp `EXEC` (hoặc `sqlcmd -o file`), đừng bọc trong `INSERT ... EXEC`.
- **Chỉ số mùa vụ phải là chỉ số TƯƠNG ĐỐI + XẾP HẠNG, không dùng ngưỡng tuyệt đối.**
  Chỉ số tuyệt đối (doanh số mùa/ngày ÷ doanh số năm/ngày) cho **mọi** sản phẩm cùng
  một giá trị (≈0,91 Xuân · ≈1,06 Thu) vì mùa vụ Walmart tác động đều lên 50 sản phẩm.
  Chỉ số tương đối (tỷ trọng sản phẩm trong mùa ÷ tỷ trọng toàn hệ thống) chỉ có biên độ
  **0,992–1,009** → ngưỡng 1,05/0,95 cho ra **200/200 `neutral`**. Cách đang dùng:
  **top 20% → `import`, bottom 20% → `avoid`** (10 + 30 + 10 mỗi mùa). Khi viết Chương 4
  phải nói rõ đây là so sánh **giữa các sản phẩm trong cùng mùa**, không phải mức tăng
  tuyệt đối.
- **`sp_Forecasts_Seasonal` chỉ trả `season_code` (ASCII: spring/summer/autumn/winter).**
  Nhãn tiếng Việt (`Xuân/Hạ/Thu/Đông`) và danh sách tháng nằm ở
  `backend/app/services/seasonal.py`, không nhét vào SQL.
- **Stored Procedure mùa vụ dùng bảng tạm, không dùng CTE** — vì `WITH` không đứng ngay
  sau `IF` (bài học cũ), mà procedure cần `IF` để chặn tham số.
- **`sp_Forecasts_Seasonal` nặng (~3 giây) nên phải cache.** `services/seasonal.py` cache
  **300 giây** trong RAM, đúng bằng chu kỳ auto-refresh 5 phút của frontend. Cache mất
  khi restart backend. Đo thật: lần đầu **3.086 ms**, các lần sau **45 ms**.
- **Route `/transfers/summary` phải khai báo TRƯỚC `/transfers/{transfer_id}`** — nếu
  không FastAPI cố parse chuỗi `"summary"` thành `int` và trả 422.
- **Chatbot có "đường nhanh": câu hỏi không có từ khoá nghiệp vụ thì trả lời ngay**,
  không chạm database và không gọi Gemini (10–144 ms thay vì ~4.500 ms). Từ khoá được
  chia theo khối (`inventory`/`alerts`/`orders`/`forecasts`/`transfers`/`seasonal`) và
  router **chỉ nạp khối liên quan**. Thêm khối mới thì phải thêm từ khoá vào
  `SECTION_KEYWORDS`, nếu không câu hỏi về khối đó sẽ rơi vào đường nhanh và trả lời sai.
- **`TYPO_MAP` phải sắp xếp cụm DÀI trước cụm NGẮN** và dùng ranh giới từ
  `(?<!\w)…(?!\w)`; nếu không `kho` sẽ khớp vào giữa `tồn kho` và `hạ` khớp vào `hạch toán`.
- **Vite dev server trên Windows giữ cache module cũ khi đường dẫn dự án có dấu tiếng Việt.**
  Đã gặp: sửa `Sidebar.jsx` thêm mục menu nhưng giao diện vẫn không đổi, dù file trên đĩa
  đúng và request `?probe=…` trả nội dung mới — vì watcher không nhận thay đổi nên module
  graph vẫn phục vụ bản cũ cho URL **không có query**. → **Khởi động lại `npm run dev`**
  rồi tải lại trang. Đừng mất thời gian tìm lỗi React.

### Quản lý người dùng · phân quyền · email thông báo (19/11/2026)

- **`users` có 7 cột quyền `BIT`** (`can_edit_product`, `can_delete_product`,
  `can_view_report`, `can_manage_inventory`, `can_manage_order`, `can_manage_transfer`,
  `can_manage_user`) + `avatar_url`, thêm bằng migration `013-users-permissions.sql`.
  `/auth/me` trả kèm các cờ này nên frontend không cần gọi thêm API.
- **Phân quyền owner-only ở tầng router**: `APIRouter(dependencies=[Depends(require_role("owner"))])`
  cho `/users`. Manager/Staff nhận **403** dù có cờ `can_manage_user`.
- **`uq_users_email` đổi thành filtered unique index** `WHERE email IS NOT NULL` — cùng lý do
  đã gặp ở `inventory`: SQL Server coi nhiều `NULL` là trùng nhau.
- **Stored Procedure `sp_Users_Update` chặn hạ cấp/xoá owner hoạt động cuối cùng**
  (`50004`) và chặn xoá tài khoản đang được `transfer_requests` tham chiếu (`50003`).
- **Chống tự khoá mình (self-lockout) ở router, không chỉ ở giao diện.** `PUT /users/{id}`
  trả **403** khi caller sửa chính mình mà đổi `role`, tắt một quyền đang bật, hoặc đặt
  `is_active = false`; `DELETE /users/{id}` trả **403** khi xoá chính mình. Thông điệp:
  "Không thể tự thay đổi vai trò của chính mình" · "Không thể tự thu hồi quyền hạn của
  chính mình" · "Không thể tự khoá tài khoản của mình" · "Không thể tự xóa tài khoản của mình".
  Frontend khoá ô Vai trò + toàn bộ công tắc quyền + công tắc hoạt động và **ẩn nút xoá**
  ở dòng của chính mình; payload khi tự sửa **không gửi** `role`/`is_active`/các cờ quyền
  (procedure hiểu là "giữ nguyên").
- **Chỉ chặn khi giá trị THỰC SỰ đổi.** So sánh với dòng hiện tại trước khi trả 403, nhờ vậy
  client gửi kèm nguyên trạng (role cũ, cờ đang bật) vẫn sửa được tên/email/mật khẩu —
  nếu chặn theo kiểu "có mặt trong payload là cấm" thì mọi lần tự sửa đều hỏng.
- **Còn một khe hở nhỏ giữa `_get_row_or_404` và `sp_Users_Update`:** owner thứ hai có thể
  đổi dòng trong khoảng đó. Chấp nhận được ở mô hình một chủ sở hữu; procedure vẫn giữ
  bất biến "luôn còn ít nhất một owner đang hoạt động".
- **Gửi mail là best-effort, chạy SAU khi đã ghi DB.** `POST /users` tạo tài khoản trước rồi
  mới gọi `send_account_info_email`; SMTP lỗi **không** rollback tài khoản. Response
  `UserCreated` có thêm `email_sent` + `email_message` để UI chọn toast xanh/đỏ.
- **`MAIL_PASSWORD` là App Password 16 ký tự của Gmail**, không phải mật khẩu đăng nhập.
  Phải bật 2-Step Verification rồi tạo tại `myaccount.google.com/apppasswords`.
- **Giá trị mẫu trong `.env` được coi là CHƯA cấu hình.** `Settings.mail_configured` loại
  `email_cua_ban@gmail.com` / `mat_khau_ung_dung`, nhờ vậy demo không gửi SMTP bằng thông tin
  giả rồi treo chờ timeout; API trả "Tạo thành công nhưng chưa gửi được mail (chưa cấu hình SMTP)".
- **Muốn kiểm thử đường gửi mail thành công mà không có tài khoản Gmail thật:** chạy server
  với biến môi trường `MAIL_USERNAME`/`MAIL_PASSWORD` giả + `MAIL_SUPPRESS_SEND=1`
  (`fastapi-mail` bỏ qua kết nối SMTP nhưng vẫn dựng message). Biến môi trường **ưu tiên hơn**
  file `.env`.
- **Form Thêm tài khoản dùng `noValidate`.** Để `required` của HTML tự chặn thì Chromium hiện
  bubble tiếng Anh ("Please fill out this field."), không khớp phần còn lại của giao diện.
  `noValidate` + kiểm tra trong `handleSubmit` cho ra thông báo tiếng Việt thống nhất.
- **Email bắt buộc khi TẠO tài khoản, không bắt buộc khi SỬA.** Tài khoản cũ có thể chưa có
  email; bắt buộc ở cả hai chiều sẽ khoá không cho cập nhật tên.
- **Cổng 8000 có thể vẫn do tiến trình cũ giữ.** `Stop-Process` theo `-LocalPort` đôi khi
  không dừng kịp: uvicorn mới bind lỗi `10048` nhưng `/health` vẫn trả `ok` vì **server cũ**
  đang phục vụ → test lại rơi vào code cũ. Kiểm tra `Get-NetTCPConnection -LocalPort 8000`
  và `Get-Content uvicorn_err.log` trước khi kết luận API sai.
- **Avatar lưu KEY, không lưu đường dẫn build.** Cột `avatar_url` giữ `toan`; frontend map key
  sang `src/assets/Avatar.jpg`. Lưu `/assets/Avatar-abc123.jpg` sẽ hỏng ngay lần build sau vì
  Vite băm tên file.

### Gợi ý điều chuyển AI · Prophet-only · timeout chatbot (22/11/2026)

- **`sp_Transfer_SuggestAI` đo bằng "số ngày phủ" chứ không so tồn kho tuyệt đối.**
  `days_cover = current_stock / (predicted_qty / horizon_days)`. Cửa hàng có
  `days_cover > @TargetDays` là dư, `< @TargetDays` là thiếu. Cách này chịu được
  việc mỗi sản phẩm có nhu cầu/ngày rất khác nhau.
- **`@TargetDays` mặc định 14, không phải 30.** Với dữ liệu hiện tại, **100/100 cặp
  đều phủ dưới 30 ngày** (20 cặp < 7 ngày, 54 cặp 7–14 ngày, 26 cặp 14–30 ngày) nên
  mục tiêu 30 ngày sẽ **không có cửa hàng nào dư** → 0 gợi ý. Mức 14 ngày cho ra danh
  sách có nghĩa; giao diện cho chọn 7/14/21/30 để thấy ngưỡng thay đổi kết quả.
- **Ghép cặp theo hạng (greedy) trong từng sản phẩm:** cửa hàng dư xếp theo
  `surplus_qty DESC`, cửa hàng thiếu xếp theo `shortage_qty DESC`, ghép cùng hạng
  `rn`; số lượng gợi ý = `MIN(surplus_qty, shortage_qty)`. Nhờ vậy không bao giờ
  đề xuất chuyển nhiều hơn lượng dư thật của kho nguồn.
- **`@ModelName` mặc định `'prophet'`** để tab AI và trang Dự báo cùng một mô hình.
  Truyền `NULL` nếu muốn trộn mọi mô hình (không dùng trên web).
- **`sp_Forecasts_Latest` thêm `@ModelName`** → `GET /forecasts/latest?model_name=prophet`
  trả **97 cặp** thay vì 100, vì 3 cặp XGBoost thắng không còn dòng Prophet. Đây là
  chủ ý: web chỉ hiển thị Prophet, còn 3 cặp kia vẫn nằm trong bảng để đối chứng.
- **`/transfers/suggestions` phải khai báo TRƯỚC `/transfers/{transfer_id}`**, cùng lý
  do với `/summary`: nếu không FastAPI cố parse chuỗi `"suggestions"` thành `int` → 422.
- **`reason` và `priority` viết ở router Python, không viết trong SQL.** File SQL giữ
  ASCII; câu tiếng Việt có dấu soạn ở `transfer_router.py` (helper `_vi_num` định dạng
  dấu chấm hàng nghìn).
- **Chặn timeout chatbot bằng thread, không bằng timeout của SDK.** `google-genai`
  không bảo đảm tôn trọng timeout HTTP, nên `_generate_with_timeout` chạy
  `generate_content` trong `ThreadPoolExecutor(max_workers=1)` rồi
  `future.result(timeout=remaining)`. Hết hạn → `executor.shutdown(wait=False)` và trả
  câu "Hệ thống đang bận…". **Thread nền vẫn tiếp tục chạy** (Python không kill được
  thread); chấp nhận được vì request đã trả lời và kết nối sẽ tự đóng.
- **Hạn 15 giây là hạn CHUNG cho cả 2 lần thử**, không phải 15 giây mỗi lần. Trước đây
  vòng lặp thử lại có thể giữ người dùng 30+ giây khi Gemini treo.
- **Frontend đặt timeout 60 giây theo URL, không đổi timeout mặc định.** Chỉ
  `config.url.includes('/chat')` mới được nâng lên 60000 ms; API đọc/ghi khác vẫn 20
  giây để lỗi mạng hiện ra sớm.

### Báo cáo rủi ro hao hụt · view `v_spoilage_risk` (23/11/2026)

- **Một view giữ toàn bộ công thức, hai procedure chỉ lọc.** `v_spoilage_risk` trả **một
  dòng cho mỗi lô còn tồn** (`quantity > 0` và có `expiry_date`), không lọc cửa hàng /
  nhóm / số ngày; `sp_Reports_SpoilageRisk` và `sp_Reports_SpoilageSummary` tự lọc. Sửa
  công thức rủi ro chỉ sửa một chỗ, không sợ hai bên lệch nhau.
- **Tốc độ bán ưu tiên Prophet, fallback về bán thực tế.** `daily_demand` lấy
  `SUM(predicted_quantity) / COUNT(DISTINCT forecast_date)` của `model_name='prophet'`;
  chưa có dự báo thì lấy `SUM(order_items.quantity) / 30` trong 30 ngày quanh **ngày bán
  cuối cùng** (`MAX(order_date)` của đơn `completed` + `sale`), không neo `GETDATE()`.
  Nhờ vậy nạp lại dữ liệu cũ không làm tốc độ bán tụt về 0. Cột `demand_source` =
  `forecast | sales | none`.
- **`sellable_qty = MIN(quantity, daily_demand × days_left)`**, `unsold_qty =
  quantity - sellable_qty`, **hết hạn thì toàn bộ lô là unsold**. `loss_value =
  unsold_qty × unit_cost` (giá vốn trong `products.unit_cost`).
- **Điểm rủi ro = `100 × (0.7 × unsold/quantity + 0.3 × (1 - days_left/30))`**; lô
  `days_left < 0` luôn **100 điểm**; `days_left ≥ 30` thì phần khẩn cấp bằng 0. Ngưỡng:
  **≥70 `high` · ≥40 `warning` · còn lại `safe`**.
- **`@Days` là cửa sổ hạn sử dụng tính TỚI TƯƠNG LAI, không phải số ngày quá khứ.**
  `0` = lô hết hạn hôm nay **cộng toàn bộ lô đã hết hạn** (vì `days_left` âm luôn
  `<= @Days`); `7` / `30` là mốc mở rộng. Đừng hiểu `0` là "không lọc gì".
- **`expired_lots` đếm toàn bộ lô đã hết hạn; `high_risk_lots` và `lots_to_handle` chỉ
  đếm trong cửa sổ `@Days`.** Vì lô hết hạn luôn nằm trong cửa sổ nên `expired_lots`
  không đổi khi đổi 7 ↔ 30 ngày; `high_risk_lots` thì đổi.
- **`trend` gom theo `expiry_date` và chỉ lấy `expiry_date >= hôm nay - 30`**, nên trục
  thời gian **có khoảng trống** ở ngày không có lô nào hết hạn — đúng bản chất dữ liệu,
  không phải lỗi biểu đồ. `handled_rate = 100 × (1 - loss_value/total_value)` là **tỷ lệ
  giá trị còn cứu được**, không phải log thao tác thủ công (hệ thống chưa lưu lịch sử xử
  lý) — khi viết Chương 4 phải nói rõ.
- **Giao diện có hiệu ứng đếm số ở thẻ KPI.** Ngay sau khi đổi bộ lọc, đọc DOM có thể
  thấy `0 đơn vị` trong lúc animation chạy; chờ ~0,5 giây rồi đọc lại mới đúng. Đừng kết
  luận API trả 0 khi test bằng trình duyệt — kiểm tra `network.get` hoặc gọi thẳng API.
- **Bảng chi tiết mặc định `limit=500`** (tối đa 2.000) và sắp theo `risk_score DESC,
  loss_value DESC, days_left ASC`; trang hiển thị đủ 500 lô đầu, không phân trang.
- **CSV/PDF dùng tiêu đề cột ASCII không dấu** ("Ma lo", "Ten SP"…) để reportlab
  không lỗi font khi vẽ PDF; dữ liệu tiếng Việt trong ô vẫn giữ nguyên. PDF giới hạn
  1.000 dòng như các báo cáo khác.
- **XLSX có đường render riêng `_spoilage_xlsx()`, KHÔNG dùng `_render()`** (24/11/2026):
  tiêu đề tiếng Việt có dấu ở dòng 3, dòng 1–2 là tiêu đề báo cáo + dòng ngữ cảnh
  (`Xuất lúc … · Khung N ngày · Danh mục … · Cửa hàng … · Mức rủi ro … · N lô`),
  header `1F3864` in đậm, zebra `F8FAFC`, freeze `A4`, auto-filter, khổ ngang
  `fitToWidth = 1`. Cột số (`Số lượng`, `Tốc độ bán/ngày`, `Điểm rủi ro`,
  `Giá trị thất thoát`) là **số thật** với number-format `#,##0.###` / `#,##0.00` /
  `0.0` / `#,##0`; `Hạn sử dụng` là ô **datetime** với format `dd/mm/yyyy`;
  `Mức độ rủi ro` tô màu theo mức (`high` đỏ · `warning` vàng · `safe` xanh) và dịch
  sang tiếng Việt. `Nguồn tốc độ` / `Gợi ý xử lý` cũng dịch key ASCII sang nhãn tiếng Việt.
- **Độ rộng cột tính từ nội dung thật, có chặn trên** (`_display_len()` + `min/max` trong
  `SPOILAGE_XLSX_COLUMNS`): cột co theo ô dài nhất nhưng không vượt `maximum`, nên tên
  sản phẩm dài sẽ xuống dòng thay vì đẩy các cột số ra ngoài khổ ngang. Ba cột được
  phép `wrap_text` nằm trong `SPOILAGE_WRAP_COLUMNS` (4, 6, 16).
- **Dòng ngữ cảnh ghi cả danh mục và cửa hàng đang lọc** — `_spoilage_filter_labels()`
  đọc tên qua `sp_Categories_Get` / `sp_Stores_Get` (best-effort: lỗi tra cứu thì in
  `#id`, không làm hỏng file). Nhờ vậy mở file là biết ngay đang xem phạm vi nào.
- **Đổi tên file tải về lấy từ `Content-Disposition`** (`Bao_Cao_Hao_Hut_YYYYMMDD_HHMM.xlsx`)
  và có hàm dựng lại cùng quy ước nếu proxy bỏ header. Vì `responseType: 'blob'` nên
  body lỗi cũng là Blob — `readBlobError()` đọc text rồi parse `detail` trước khi hiện
  Toast. **Riêng 403 luôn hiện câu tiếng Việt** ("Bạn không có quyền xuất báo cáo…")
  chứ không dùng `detail` của backend, vì `require_permission` trả thông điệp tiếng Anh.
- **AI advice chạy 10 giây trong thread rồi fallback luật tiếng Việt** (`model="fallback"`);
  panel tải độc lập với bảng nên Gemini chậm không chặn trang. Gọi lại API advice mỗi
  lần đổi bộ lọc.

### Mặt hàng bán chạy theo ngày · `sp_Reports_TopSelling` (24/11/2026)

- **`@Date = NULL` phải rơi về ngày bán gần nhất, không phải `GETDATE()`.** Dữ liệu bán
  hàng dừng ở 20/11/2026 trong khi hôm nay là 24/11/2026, nên mở trang với `GETDATE()`
  sẽ ra bảng rỗng và trông như lỗi. Procedure lấy `MAX(order_date)` của đơn
  `completed` + `sale` rồi mới lọc.
- **Doanh thu lấy `SUM(order_items.line_total)`, không nhân lại `quantity × unit_price`.**
  `line_total` là generated column đã trừ `discount_percent`; tự tính lại sẽ lệch với mọi
  báo cáo khác.
- **Chỉ tính đơn `status='completed' AND order_type='sale'`.** Thiếu điều kiện này thì hôm
  nay có một đơn nháp là số liệu đổi, và đơn `return` / `purchase` bị cộng vào doanh thu.
- **Một dòng cho mỗi sản phẩm, gom 10 cửa hàng.** `GROUP BY product_id`, `SUM` cả số lượng
  lẫn doanh thu; ngày 16/11/2026 ra **50 sản phẩm / 26.441 đơn vị / 1.016.451.000 đ**.
- **`sale_date` trả về theo từng dòng dữ liệu, không phải tham số đầu vào.** Nhờ vậy
  frontend biết ngày thực tế đang xem mà không phải đoán lại khi gọi API không kèm `date`.
- **Ngày `2026-11-21` trở đi trả mảng rỗng** (không có đơn) — đúng dữ liệu, không phải lỗi.
  Giao diện phân biệt rõ "ngày không có dữ liệu" với "bộ lọc không khớp".
- **Đừng dùng `new Date('2026-11-16')` trong JS.** Chuỗi ISO trần bị hiểu là UTC; máy ở
  múi giờ âm sẽ hiện 15/11. Hàm `parseISO` tách chuỗi và dựng `new Date(y, m-1, d)` theo
  giờ địa phương.
- **Hàng chờ trong lúc đổi ngày:** `loading` giữ danh sách cũ ở `opacity-60` thay vì xoá
  trắng, để bấm mũi tên liên tục không bị nháy. Chỉ hiện skeleton khi chưa có dòng nào.

### Giai đoạn PostgreSQL (lịch sử)

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
- [x] **SQL Server BƯỚC 1**: cập nhật AGENTS.md + GHI-CHU-TIEN-DO.md cho migration PostgreSQL → SQL Server (24/10/2026)
- [x] **SQL Server BƯỚC 2**: `database/HUONG-DAN-CHAY-SSMS.md` — 10 bảng + index + 6 trigger + 4 view + **49 Stored Procedure** (đã test thật trên SQL Server 2025)
- [x] **SQL Server BƯỚC 3**: `config.py`/`database.py` dùng pyodbc (`DbSession` + `autocommit`), 18 router gọi Stored Procedure, migration `010` thêm **25 SP** (tổng **74**), nạp lại **912.999 `order_items`** — test HTTP **48/48** đọc + **29/29** ghi PASS (24/10/2026)
- [x] F1: Setup Frontend React + Tailwind — Login JWT, phân quyền owner/manager vs staff, Dark Mode, Responsive, Dashboard mockup, trang Sản phẩm gọi API thật (24/10/2026)
- [x] F2: Hoàn thiện các trang giao diện còn lại — Kho hàng (tabs hết hạn), Đơn hàng (xem chi tiết), Cảnh báo (đánh dấu đã đọc), Dự báo (bảng + biểu đồ), Nhóm hàng/Cửa hàng, cập nhật menu/routes (24/10/2026)
- [x] I1: Tích hợp AI Chatbot (Google Gemini) + WebSocket realtime cảnh báo (24/10/2026)
- [x] FIX: Thêm nút "Quay lại" cho tất cả trang con (24/10/2026)
- [x] SCRIPT: Thêm `start_all.bat` tự động dọn cổng 8000/3000 và khởi động cả 2 server (27/10/2026)
- [x] DOCS: Viết lại toàn bộ `README.md` theo đúng tech stack SQL Server + Gemini + WebSocket (27/10/2026)
- [x] FIX: Đổi `GEMINI_MODEL=gemini-3.5-flash-lite` tránh lỗi 503 quá tải + sửa `start_all.bat` dùng `cd backend &&` (27/10/2026)
- [x] FIX: Tạo lại `start_all.bat` bằng script Python — CRLF, ASCII, không BOM, có `cd /d "%~dp0"` để chạy đúng khi đường dẫn có dấu cách; đã test thật cả 2 cổng lên (27/10/2026)
- [x] FIX: Chatbot trả lời tự nhiên — viết lại System Prompt (3-5 câu, không danh sách thô, xưng "Tôi"/"Bạn") + context dùng tên sản phẩm/cửa hàng thay vì `SP#`/`CH#`, đổi `SL`/`HH` thành câu tiếng Việt (27/10/2026)
- [x] F3: Hoàn thiện CRUD thật cho Sản phẩm · Nhóm hàng · Cửa hàng · Kho hàng — Modal thêm/sửa, ConfirmDialog xoá, Toast thông báo, phân quyền owner/manager; sửa `_extract_detail` để lỗi 409 không còn trả tuple pyodbc thô (27/10/2026)
- [x] **ĐIỀU CHUYỂN HÀNG (31/10/2026)**: migration `011-transfers-seasonal.sql` — bảng `transfer_requests` (11 bảng), mở rộng `chk_inv_tx_reference_type` + `uq_transactions_reference`, **10 Stored Procedure** (Create/Submit/Approve/Reject/Cancel/Ship/Complete/Get/List/Summary); `transfer_router.py` (9 endpoint) + `transfer_schema.py`; trang `/transfers` với thanh 5 bước, modal tạo yêu cầu, modal xác nhận, modal chi tiết tiến trình. Test: sqlcmd đủ 5 bước (kho 489→484 / 1.179→1.184) + **HTTP 30/30 PASS**
- [x] **DỰ BÁO THEO MÙA VỤ (31/10/2026)**: `sp_Forecasts_Seasonal` (200 dòng = 50 SP × 4 mùa, dữ liệu 2013-01-01→2017-12-31); `services/seasonal.py` (cache 300 giây, nhãn tiếng Việt); `GET /api/v1/forecasts/seasonal` (lần đầu 3.086 ms → cache 45 ms); tab "Dự báo theo mùa" + **tự động làm mới 5 phút** (đã kiểm chứng bằng cách hạ tạm xuống 10 giây)
- [x] **TỐI ƯU CHATBOT (31/10/2026)**: đường nhanh cho câu ngoài nghiệp vụ (4.500 ms → 10–144 ms), `TYPO_MAP` ~45 mục (sửa cả gõ sai dấu và gõ không dấu), chỉ nạp khối dữ liệu liên quan, thêm khối mùa vụ + điều chuyển, System Prompt 10 quy tắc. Test 8 câu thật, không câu nào lộ `SP#`/`CH#`/`SL`
- [x] Kiểm chứng sau nâng cấp (31/10/2026): smoke test **48/48** đọc + **29/29** ghi; `npm run build` PASS (681 module); `npm run lint` 0 error; DB **11 bảng · 4 view · 85 Stored Procedure**
- [x] **QUẢN LÝ NGƯỜI DÙNG + PHÂN QUYỀN CHI TIẾT (19/11/2026)**: migration `013-users-permissions.sql` (7 cột quyền `BIT` + `avatar_url`, filtered unique index cho `email`, 4 procedure CRUD); `user_router.py` owner-only + `UserRead` trả quyền cho `/auth/me`; trang `/users` với modal thêm/sửa có công tắc từng quyền, `Avatar.jpg` chuyển vào `frontend/src/assets/`, Header hiện ảnh + tên "Toàn"; Sidebar ẩn "Báo cáo" khi thiếu `can_view_report`. Test: sqlcmd + API + trình duyệt (tạo Manager tắt quyền báo cáo → đăng nhập Manager → mục Báo cáo biến mất), `npm run build` PASS
- [x] **EMAIL THÔNG BÁO TÀI KHOẢN (19/11/2026)**: `fastapi-mail==1.6.8` + `services/email_service.py`; `POST /users` gửi thông tin đăng nhập tới email trong form (best-effort, không rollback tài khoản nếu SMTP lỗi); response `UserCreated` thêm `email_sent`/`email_message`; form bắt buộc Email khi tạo + toast "Đã tạo tài khoản và gửi thông tin về email …" hoặc cảnh báo vàng. Test: API 201 + `email_sent=false` khi chưa cấu hình SMTP, `email_sent=true` với `MAIL_SUPPRESS_SEND=1`
- [x] **CHẶN TỰ HẠ QUYỀN / TỰ XOÁ MÌNH (19/11/2026)**: `PUT /users/{id}` trả 403 khi tự đổi vai trò, tự tắt quyền đang bật hoặc tự khoá tài khoản; `DELETE /users/{id}` trả 403 khi xoá chính mình. Modal Sửa tài khoản của chính mình khoá Vai trò + 7 công tắc quyền + công tắc hoạt động, ẩn nút xoá, và không gửi các trường bị khoá trong payload. Test API 6/6 PASS (4 lần 403 + tự sửa tên 200 + owner vẫn hoạt động); trình duyệt xác nhận disable/ẩn đúng; `npm run build` PASS
- [x] **CHUẨN HOÁ RBAC + ĐỒNG BỘ DỮ LIỆU 2026 (20/11/2026)**: `dependencies.require_permission(flag)` chặn theo 7 cờ quyền (đọc lại `users` mỗi request nên có hiệu lực ngay); gắn vào toàn bộ endpoint ghi — sản phẩm/nhóm/cửa hàng/import dùng `can_edit_product` (+ `can_delete_product` khi xoá), kho dùng `can_manage_inventory`, đơn hàng `can_manage_order`, điều chuyển `can_manage_transfer`, `/reports/*` là `can_view_report`, `/chat` yêu cầu đăng nhập. Frontend tách `canEdit`/`canDelete`/`canWrite` cho Sản phẩm · Nhóm hàng · Cửa hàng, dùng cờ cho Kho/Đơn hàng/Điều chuyển (staff vẫn ghi được). Script `scripts/shift_and_generate_2026.py`: cộng **3287 ngày** cho dữ liệu trước 2019 (2013→2022 … 2017→2026), sinh lại bán hàng 01/01→20/11/2026 (3.240 đơn · 162.000 dòng hàng) theo mùa vụ + ngày lễ, dời khung dự báo về 21/11–20/12/2026, chạy lại 3 procedure cảnh báo. 0 lỗi FK, `npm run build` PASS
- [x] **TÁCH TAB DANH SÁCH / PHÂN QUYỀN (21/11/2026)**: `/users` có 2 tab — "Danh sách tài khoản" (bảng có cột **Ngày giờ tạo** `dd/mm/yyyy HH:mm`, chỉ Thêm / Sửa thông tin cơ bản (tên + email) / Khoá–Mở khoá, không có công tắc quyền) và "Cấp phép & Phân quyền" (danh sách chọn bên trái, khung 7 công tắc + ô vai trò + "Lưu thay đổi quyền" bên phải). Backend thêm `PUT /users/{id}/permissions` và `PUT /users/{id}/status` (owner-only, merge dòng hiện tại rồi gọi `sp_Users_Update` với `PasswordHash = NULL`, không thêm procedure mới). Test API **30/30 PASS**, quyền mới có hiệu lực ngay với token đang dùng (report 403 → 200), tài khoản bị khoá không đăng nhập được; trình duyệt xác nhận 2 tab, modal sửa cơ bản, hộp khoá tài khoản; `npm run build` PASS, `npm run lint` 0 error
- [x] **GỢI Ý ĐIỀU CHUYỂN TỪ AI + TINH GỌN PROPHET + CHẶN TIMEOUT CHATBOT (22/11/2026)**: migration `014-smart-transfer.sql` (`sp_Transfer_SuggestAI` + `sp_Forecasts_Latest` có `@ModelName`); `GET /transfers/suggestions` (so dự báo với tồn kho, `target_days=14`, `model_name=prophet`, `reason`/`priority` viết ở router); tab "Gợi ý từ AI" trong `/transfers` với nút "Tạo yêu cầu" điền sẵn form; trang `/forecasts` chỉ gọi `model_name=prophet` và bỏ cột "Mô hình"; `api.js` timeout 60 giây riêng `/chat`; `chat_router.py` gọi Gemini trong thread với hạn chung 15 giây và trả "Hệ thống đang bận, vui lòng thử lại sau". Test: API suggestions 5 dòng đúng, `/forecasts/latest?model_name=prophet` trả 97 cặp, timeout guard 0,5 giây raise đúng và nhánh busy trả đúng câu, chat thật 1,7 giây; `npm run build` PASS (688 module), `npm run lint` 0 error
- [x] **BÁO CÁO HÀNG HÓA & RỦI RO HAO HỤT (23/11/2026)**: xoá mục "Đề xuất nhập hàng" ("SẮP RA MẮT") khỏi Sidebar, thay bằng **Báo cáo Hàng hóa** (`/reports/spoilage`, icon biểu đồ); migration `015-spoilage-risk-report.sql` (view `v_spoilage_risk` + `sp_Reports_SpoilageRisk` + `sp_Reports_SpoilageSummary`); 4 endpoint `GET /reports/spoilage`, `/spoilage/summary`, `/spoilage/advice` (Gemini 10 giây, fallback luật), `/spoilage/export?format=xlsx|pdf|csv` (kế thừa `can_view_report`); trang `SpoilageReportPage.jsx` có 4 thẻ KPI, biểu đồ cột chồng theo danh mục, biểu đồ đường xu hướng thất thoát, panel AI, bảng 500 lô và Drawer "Xử lý" (Khuyến mãi · Điều chuyển · Kiểm kê). Đo thực tế khung 30 ngày: **331.239 đơn vị · 8.877.108.500 đ tồn kho · 834.809.519 đ nguy cơ (9,4%) · 648 lô trong khung · 290 lô cần xử lý · 183 lô hết hạn · 261 lô nguy cơ cao** (7 danh mục, 28 điểm xu hướng, 5 lô rủi ro nhất); khung 7 ngày còn 797.213.585 đ (8,98%) / 363 lô, "Hôm nay" còn 233 lô. Trình duyệt: lọc danh mục + chi nhánh + mức rủi ro ra đúng 3 lô Fresh Food/CH Q.3; Drawer mở đúng, "Khuyến mãi" hiện kế hoạch giảm 50% cho lô quá hạn, "Điều chuyển" → `/transfers`, "Kiểm kê" → `/inventory`; tải XLSX 22.912 byte và PDF 95.771 byte. `npm run build` PASS (689 module), `npm run lint` 0 error
- [x] **MẶT HÀNG BÁN CHẠY THEO NGÀY (24/11/2026)**: migration `016-top-selling.sql` (`sp_Reports_TopSelling @Date`, mặc định ngày bán gần nhất); `GET /reports/top-selling?date=YYYY-MM-DD` + `top_selling_schema.py` (kế thừa `can_view_report`); thanh tab dùng chung `components/reports/ReportTabs.jsx` gắn ở cả hai trang báo cáo; trang `TopSellingPage.jsx` kiểu app bán hàng (nút quay lại · kính lúp · phễu lọc; hàng ngày `‹ Thứ Sáu, 20/11/2026 ›` mở date picker; 3 ô tổng hợp; danh sách dọc tên + nhóm + doanh thu + SL), tìm kiếm bỏ dấu tiếng Việt, lọc sắp xếp (số lượng/doanh thu/tên) và giới hạn 10/20/50/tất cả. Đo thật qua API: 16/11 **50 sản phẩm · 26.441 đơn vị · 1.016.451.000 đ** (top Kẹo mút 888), 19/11 **31.741 / 1.223.421.000 đ** (top Cà phê sữa 1.104), 20/11 **21.165 / 817.332.500 đ**; ngày 21/11 trả rỗng và hiện đúng khung "Không có dữ liệu". Trình duyệt: mũi tên ‹ › đổi ngày đúng, tìm `sua` ra 5 sản phẩm, giới hạn 10 dòng, sắp theo doanh thu ra Thịt bò 90.045.000 đ, Dark Mode + khung 360 px không tràn. `npm run build` PASS (963,76 kB), `npm run lint` 0 error
- [ ] T2: README con cho từng thư mục
- [ ] Tích hợp AI Model

