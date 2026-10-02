# Dữ liệu (Datasets)

## ⚠️ File CSV KHÔNG được commit lên Git

Thư mục `raw/`, `processed/`, `sample/` đã được thêm vào `.gitignore`.

**Lý do:** `train.csv` có dung lượng **17 MB**. Commit vào Git làm repo nặng dần theo mỗi lần thay đổi file, và có nguy cơ vượt giới hạn 100 MB của GitHub.

---

## Nguồn dữ liệu

### 1. Walmart Store Sales - Time Series Forecasting

| Mục | Nội dung |
|-----|----------|
| **Nguồn** | Kaggle Competition |
| **Link** | https://www.kaggle.com/competitions/demand-forecasting-kernels-only |
| **File** | `train.csv`, `test.csv`, `sample_submission.csv` |
| **Số dòng** | `train.csv`: 913.000 dòng dữ liệu |
| **Cột** | `date`, `store`, `item`, `sales` |
| **Kích thước** | 50 items (id 1–50) × 10 stores (id 1–10) |
| **Giai đoạn** | 2013-01-01 → 2017-12-31 (test set bắt đầu 2018-01-01) |

**Đặc điểm quan trọng:** dataset **KHÔNG có cột giá** (price). Vì vậy khi nạp vào hệ thống, `unit_price` và `total_amount` phải xử lý riêng — xem mục "Xử lý khi nạp" bên dưới.

#### Cách tải

1. Đăng nhập vào [kaggle.com](https://www.kaggle.com)
2. Mở link cuộc thi ở trên → tab **Data**
3. Tải `train.csv` và `test.csv`
4. Đặt vào `datasets/raw/`

Hoặc dùng Kaggle CLI:

```bash
kaggle competitions download demand-forecasting-kernels-only -p datasets/raw
```

---

## Xử lý khi nạp vào database

Quyết định đã chốt: nạp dataset vào **`orders` + `order_items`** (không tạo bảng `sales` riêng).

### Ánh xạ cột

| Cột Kaggle | Cột database | Ghi chú |
|------------|--------------|---------|
| `date` | `orders.order_date` | Mỗi cặp (date, store) → 1 đơn |
| `store` | `orders.store_id` | Map 1–10 vào bảng `stores` |
| `item` | `order_items.product_id` | Map 1–50 vào bảng `products` |
| `sales` | `order_items.quantity` | Số lượng bán |
| *(tự sinh)* | `orders.order_code` | Định dạng `ORD-2017-000001` |
| *(tự sinh)* | `order_items.unit_price` | **Giá không có trong dataset** |
| *(tính toán)* | `orders.total_amount` | Tổng `order_items.line_total` |

### ⚠️ Vấn đề cột giá

Vì dataset không có giá, khi nạp cần chọn 1 trong 3 cách:

| Cách | Ưu | Nhược |
|------|-----|-------|
| Để `unit_price = 0` | Trung thực với dữ liệu gốc | `revenue` trong `v_daily_sales` = 0, dashboard doanh thu vô nghĩa |
| Gán giá ảo theo nhóm hàng | Dashboard doanh thu chạy được | Số liệu không phải thật, phải ghi rõ là **mô phỏng** |
| Tách bảng giá riêng | Đúng mô hình nghiệp vụ | Thêm độ phức tạp, không cần cho đồ án |

**Mô hình dự báo chỉ dùng `quantity`, không dùng `revenue`** → cả 3 cách đều cho kết quả dự báo giống nhau.

---

## Cấu trúc thư mục

```
datasets/
├── README.md        ← file này
├── raw/             ← dữ liệu gốc tải từ Kaggle (KHÔNG commit)
├── processed/       ← dữ liệu đã làm sạch (KHÔNG commit)
└── sample/          ← dữ liệu mẫu nhỏ để test nhanh (KHÔNG commit)
```

## Quy trình xử lý dữ liệu

```
train.csv (raw)
    ↓  lọc theo khoảng thời gian, loại bỏ giá trị thiếu
    ↓  hiệu chỉnh censored demand
processed/
    ↓  nạp vào PostgreSQL qua SQLAlchemy
orders + order_items
```

## Cảnh báo về việc sử dụng dữ liệu

- Dataset Kaggle này lấy từ **Walmart (Hoa Kỳ)**, không phải dữ liệu bán lẻ Việt Nam.
- Khi viết báo cáo đồ án, **phải nêu rõ đây là dữ liệu tham khảo**, và giải thích khác biệt về hành vi tiêu dùng (thói quen mua sắm, chu kỳ ngày lễ, tỷ giá, đơn vị đo khác nhau).
- Nếu có thể, nên bổ sung dữ liệu thực tế từ đơn vị thực hành để đối chiếu.
