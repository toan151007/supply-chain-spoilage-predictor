# FreshChain — Frontend

Giao diện React cho nền tảng quản trị chuỗi cung ứng chống lãng phí thực phẩm.

## Công nghệ

- Vite 8 + React 19
- Tailwind CSS 3.4 (`darkMode: 'class'`)
- React Router 7, Axios, Recharts

## Chạy dev

```bash
npm install
npm run dev
```

Mở `http://localhost:3000`. Vite proxy mọi request `/api` sang backend FastAPI ở
`http://localhost:8000`, nên **phải chạy backend trước**:

```bash
cd ../backend
python -m uvicorn app.main:app --port 8000
```

## Tài khoản dev

| Vai trò | Tên đăng nhập | Mật khẩu |
|---------|---------------|----------|
| Chủ sở hữu | `owner` | `Owner@2026` |
| Quản lý | `manager` | `Manager@2026` |
| Nhân viên | `staff` | `Staff@2026` |

Chỉ dùng trong môi trường phát triển.

## Cấu trúc

```
src/
  components/common/   Icon, Spinner
  components/layout/   Layout, Header, Sidebar, ProtectedRoute
  contexts/            AuthContext (JWT + role), ThemeContext (sáng/tối)
  pages/               LoginPage, DashboardPage, ProductsPage, NotFoundPage
  services/api.js      Axios instance + interceptor token/refresh
  utils/format.js      Định dạng tiền, ngày, thông báo lỗi
```

## Phân quyền và giao diện

- `owner` / `manager`: thấy đầy đủ menu và nút thêm/sửa/xoá.
- `staff`: ẩn nhóm Phân tích, ẩn nút thêm/sửa/xoá; backend vẫn kiểm tra quyền lần cuối.
- Dark Mode lưu trong `localStorage` (`scsp_theme`), mặc định theo hệ điều hành.
- Responsive: sidebar cố định trên desktop, drawer trên mobile.

## Build

```bash
npm run build
npm run preview
```
