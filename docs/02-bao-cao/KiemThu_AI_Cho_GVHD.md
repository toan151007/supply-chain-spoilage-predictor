# BÁO CÁO KIỂM THỬ AI

**Đề tài:** Supply Chain Spoilage Predictor — nền tảng điều phối chuỗi cung ứng thông minh
**Người thực hiện:** (sinh viên thực hiện đồ án)
**Ngày kiểm thử:** 05/11/2026
**Môi trường:** Python 3.14.7 · SQL Server 2025 Express (`LAPTOP-I39E3UT2\SQLEXPRESS`, DB `spoilage_predictor`) · FastAPI `127.0.0.1:8000`

---

## 0. Tóm tắt kết quả

| # | Hạng mục kiểm thử | Kết quả | Bằng chứng |
|---|-------------------|---------|------------|
| 1 | AI dự báo nhu cầu (Prophet / XGBoost / ARIMA) có ra đúng số liệu không? | **ĐẠT** — sai số đo lại khớp file kết quả gốc tới **0,000000** | Mục 4.1 |
| 2 | Bảng `forecasts` có đối chiếu được với doanh số thực tế không? | **KHÔNG THỂ** — hai khoảng thời gian không giao nhau; API trả `mape = null` thay vì bịa số | Mục 4.2 |
| 3 | Bảng `forecasts` có đúng là dự báo từng ngày không? | **ĐẠT sau khi sửa lỗi** — trước khi sửa: 1 giá trị lặp 30 lần; sau khi sửa: 30/30 giá trị khác nhau | Mục 4.3 |
| 4 | AI điều phối / dự báo theo mùa vụ có đúng logic không? | **ĐẠT** — 200/200 dòng khớp phép tính độc lập, **0 lỗi logic** | Mục 4.4 |
| 5 | Chatbot có nhanh và trả lời đúng số liệu không? | **ĐẠT sau khi sửa 2 lỗi** — 41 ms (đường nhanh) đến 5.929 ms (có gọi Gemini); số liệu đúng | Mục 4.5 |

**Kết luận ngắn:** số liệu của cả 3 khối AI đều đúng và tái lập được. Trong quá trình kiểm thử đã phát hiện và sửa **5 lỗi thật** (chi tiết ở mục 5) — nếu không kiểm thử thì các lỗi này sẽ bị giảng viên phát hiện khi chấm.

---

## 1. Danh mục AI đang dùng trong hệ thống

| # | Khối AI | Công nghệ / thuật toán | Mã nguồn | API | Bảng dữ liệu |
|---|---------|------------------------|----------|-----|--------------|
| 1 | **Dự báo nhu cầu** (mô hình chính) | **Prophet 1.4.0** — `changepoint_prior_scale=0.01`, `seasonality_mode='multiplicative'`, `yearly_seasonality=20`, ngày lễ Hoa Kỳ | `ai-model/scripts/train_models.py`<br>`ai-model/scripts/forecast_next_month_sqlserver.py` | `GET /api/v1/forecasts/latest` | `forecasts` (2.910 dòng) |
| 2 | **Dự báo nhu cầu** (mô hình đối chứng) | **XGBoost 3.4.1** — đặc trưng `lag_1..7`, `lag_14`, `lag_28`, `roll_mean_7/28`, `dow`, `month`, `is_weekend`, `trend`, `is_holiday` | `ai-model/scripts/train_models.py` (`build_features`, `run_xgboost`) | như trên | `forecasts` (90 dòng) |
| 3 | **Dự báo nhu cầu** (mô hình đối chứng) | **ARIMA 0.15.0** (statsmodels) — bậc chọn theo AIC | `ai-model/scripts/train_models.py` (`run_arima`) | như trên | `forecasts` (không cặp nào thắng) |
| 4 | **Điều phối theo mùa vụ** | Chỉ số mùa vụ **tương đối + xếp hạng** (top 20% → nên nhập, bottom 20% → nên hạn chế) | `database/03-migrations/011-transfers-seasonal.sql`<br>→ `sp_Forecasts_Seasonal`<br>`backend/app/services/seasonal.py` (cache 300 giây) | `GET /api/v1/forecasts/seasonal` | `orders` + `order_items` |
| 5 | **Chatbot hỏi đáp kho** | **Google Gemini** `gemini-3.5-flash-lite` + đường nhanh không gọi API + sửa lỗi chính tả tiếng Việt | `backend/app/routers/chat_router.py` | `POST /api/v1/chat` | 6 khối: tồn kho, cảnh báo, đơn hàng, dự báo, điều chuyển, mùa vụ |
| 6 | **Đề xuất nhập hàng** | Công thức `nhu cầu dự báo + tồn an toàn − tồn hiện tại`, chặn trên bởi `max_stock` | `database/03-migrations/010-sqlserver-analytics-procedures.sql`<br>→ `sp_Recommendations_Import` | `GET /api/v1/recommendations/import` | `forecasts` + `inventory` + `products` |

**Tham số mô hình đã chốt** (ghi trong `ai-model/scripts/train_models.py`):

| Mục | Giá trị |
|-----|---------|
| Dữ liệu | 2013-01-01 → 2017-12-31 · 912.999 dòng · 1.826 ngày · 10 cửa hàng × 50 sản phẩm |
| 10 sản phẩm huấn luyện | `[45, 8, 15, 13, 25, 11, 28, 48, 38, 18]` — đủ 7 nhóm hàng |
| Chia tập | Theo **mốc ngày 2017-10-01**: train 1.734 ngày · test 92 ngày (Q4/2017) |
| Chuỗi thời gian | Reindex đủ 1.826 ngày, ngày thiếu điền **0** |
| Chọn tham số | Theo **validation**, không theo test (tránh rò rỉ dữ liệu) |

---

## 2. Hướng dẫn chạy lại (dành cho giảng viên)

### 2.1. Chuẩn bị (một lần)

```powershell
# 1. Cài thư viện
pip install -r backend/requirements.txt
pip install prophet xgboost statsmodels pyodbc pandas numpy

# 2. Kiểm tra file .env ở thư mục gốc có 4 dòng này (không commit lên Git)
#    DB_HOST=LAPTOP-I39E3UT2\SQLEXPRESS
#    DB_NAME=spoilage_predictor
#    DB_USER=sa
#    DB_PASSWORD=<mật khẩu>
```

### 2.2. Khởi động backend (bắt buộc, vì phần mùa vụ và chatbot gọi qua HTTP)

```powershell
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Mở terminal thứ hai, kiểm tra: `http://127.0.0.1:8000/health` phải trả `{"status":"ok"}`.

### 2.3. Chạy toàn bộ kiểm thử

```powershell
# Từ thư mục gốc dự án
python scripts/verify_ai_models.py
```

Thời gian chạy: **~45 giây** (có train lại 3 cặp mô hình) hoặc **~5 giây** nếu bỏ phần train lại:

```powershell
python scripts/verify_ai_models.py --skip-models
```

Kết quả được ghi ra 3 file:

| File | Nội dung |
|------|----------|
| `docs/02-bao-cao/kiem-thu-ai-log.txt` | Toàn bộ log (UTF-8), đúng những gì in ra màn hình |
| `docs/02-bao-cao/kiem-thu-ai-backtest.csv` | Bảng sai số RMSE / MAE / MAPE của 3 cặp vừa train lại |
| `ai-model/outputs/forecasts_30d.csv` | 3.000 dòng dự báo từng ngày (nguồn nạp bảng `forecasts`) |

### 2.4. Chạy riêng từng phần (nếu cần)

```powershell
# Chỉ kiểm tra mùa vụ + chatbot
python scripts/verify_ai_models.py --skip-models

# Sinh lại toàn bộ dự báo 30 ngày (100 cặp, ~1,2 phút) và ghi vào DB
python ai-model/scripts/forecast_next_month_sqlserver.py

# Chạy thử không ghi DB
python ai-model/scripts/forecast_next_month_sqlserver.py --dry-run --limit 3

# Chạy lại đánh giá 100 cặp (13 phút)
python ai-model/scripts/train_models.py
```

### 2.5. Kiểm tra nhanh bằng SQL (không cần chạy script)

```sql
-- 1. Mỗi cặp phải có đúng 30 ngày và 30 giá trị KHÁC NHAU (không phải 1)
SELECT product_id, store_id, COUNT(*) AS so_ngay,
       COUNT(DISTINCT predicted_quantity) AS so_gia_tri_khac_nhau
FROM dbo.forecasts
WHERE product_id = 45 AND store_id = 1
GROUP BY product_id, store_id;
-- Kỳ vọng: so_ngay = 30, so_gia_tri_khac_nhau = 30

-- 2. Khoảng tin cậy phải bao quanh giá trị dự báo
SELECT COUNT(*) AS so_dong_sai
FROM dbo.forecasts
WHERE lower_bound > predicted_quantity OR upper_bound < predicted_quantity;
-- Kỳ vọng: 0

-- 3. Sai số phải là của TỪNG cặp, không phải một số dùng chung
SELECT COUNT(DISTINCT CONCAT(product_id, '-', store_id, '-', rmse)) AS so_cap_khac_rmse
FROM dbo.forecasts;
-- Kỳ vọng: 100 (trước khi sửa chỉ có 1)
```

---

## 3. Phạm vi và phương pháp kiểm thử

| Khối | Câu hỏi kiểm thử | Cách làm |
|------|------------------|----------|
| Dự báo | Mô hình dự báo có sát thực tế không? | **Backtest**: huấn luyện lại trên dữ liệu **quá khứ** (train đến 30/09/2017), dự báo 92 ngày Q4/2017 rồi so với doanh số **đã biết**. Đây là cách duy nhất đo được sai số thật. |
| Dự báo | Kết quả có tái lập được không? | So RMSE/MAE/MAPE vừa tính với `ai-model/outputs/model_metrics_all.csv` (kết quả gốc lưu từ trước). |
| Dự báo | Bảng `forecasts` trong DB có đúng là output của mô hình? | Kiểm tra cấu trúc: đủ 30 ngày/cặp, giá trị biến thiên, khoảng tin cậy hợp lệ, sai số theo từng cặp, tổng 30 ngày khớp file tổng hợp M2. |
| Mùa vụ | Công thức và xếp hạng có bị sai không? | Gọi API, sau đó **tính lại độc lập từ SQL Server** (đọc thẳng `orders` + `order_items`) rồi so từng dòng: chỉ số, hạng, khuyến nghị. |
| Chatbot | Trả lời có nhanh, đúng số liệu, đúng văn phong? | Gửi 4 câu hỏi thật, đo mili giây, đối chiếu số liệu với DB, kiểm tra không lộ `SP#` / `CH#` / `SL` / `HH`. |

> **Vì sao phần mùa vụ đọc SQL trực tiếp?** Đây là phép **đối chiếu độc lập**. Nếu lấy lại kết quả API rồi so với chính API thì không chứng minh được gì. Script chỉ `SELECT` (không ghi) và nằm ngoài backend, nên không vi phạm quy tắc "mọi thao tác dữ liệu của ứng dụng phải qua Stored Procedure".

---

## 4. Kết quả kiểm thử chi tiết

### 4.1. AI dự báo nhu cầu — đo sai số thật bằng backtest

**Log thực tế (trích nguyên văn từ `kiem-thu-ai-log.txt`):**

```
==============================================================================
PHAN 0 - MOI TRUONG VA DU LIEU DANG CO
==============================================================================
Python          : 3.14.7 (Windows)
pandas          : 3.0.6
numpy           : 2.5.3
prophet         : 1.4.0
xgboost         : 3.4.1
statsmodels     : 0.15.0
SQL Server      : LAPTOP-I39E3UT2\SQLEXPRESS / spoilage_predictor
v_daily_sales   : 912,999 dong | 2013-01-01 -> 2017-12-31 | 10 cua hang x 50 san pham
forecasts       : 3,000 dong | 100 cap | 2018-01-01 -> 2018-01-30
model_metrics   : 100 cap (train/test 2017-10-01)

Ket luan: doanh so thuc te ket thuc 2017-12-31, du bao bat dau 2018-01-01.
          -> HAI KHOANG KHONG GIAO NHAU. Khong the do sai so cua bang
             forecasts bang cach so voi doanh so that (xem PHAN 2).

==============================================================================
PHAN 1 - DO CHINH XAC THAT CUA MO HINH (BACKTEST TREN DU LIEU QUA KHU)
==============================================================================
Phuong phap (dung chinh code cua do an, khong viet lai):
  - Du lieu   : 2013-01-01 -> 2017-12-31, reindex du 1.826 ngay, ngay thieu = 0
  - Tap train : 2013-01-01 -> 2017-09-30 (1.734 ngay)
  - Tap test  : 2017-10-01 -> 2017-12-31 (92 ngay, quy 4 - mua cao diem)
  - Moc chia theo NGAY, khong dung 80/20 (xem AGENTS.md)
  - Sai so    : MAE / RMSE / MAPE tinh tren 92 ngay test

[1/3] Cap san pham 45 - cua hang 1
    chuoi  : 1826 ngay | thieu 0 ngay | ban = 0 o 0 ngay
  split   : train 1734 ngay (-> 2017-09-30), test 92 ngay (2017-10-01 -> 2017-12-31)
  prophet : RMSE=    9.58  MAE=    7.60  MAPE= 10.85%  (2.0s)
  xgboost : RMSE=   10.55  MAE=    8.49  MAPE= 12.04%  (2.6s)
  arima   : RMSE=   18.45  MAE=   14.47  MAPE= 22.74%  (4.7s)
  -> MO HINH TOT NHAT: PROPHET (RMSE=9.58)

[2/3] Cap san pham 45 - cua hang 2
  prophet : RMSE=   12.63  MAE=   10.21  MAPE=  9.92%  (1.0s)
  xgboost : RMSE=   12.36  MAE=    9.88  MAPE=  9.50%  (0.7s)
  arima   : RMSE=   27.41  MAE=   22.04  MAPE= 23.71%  (3.3s)
  -> MO HINH TOT NHAT: XGBOOST (RMSE=12.36)

[3/3] Cap san pham 8 - cua hang 1
  prophet : RMSE=    9.57  MAE=    7.80  MAPE= 11.52%  (0.8s)
  xgboost : RMSE=   10.80  MAE=    8.72  MAPE= 12.99%  (0.6s)
  arima   : RMSE=   16.73  MAE=   13.92  MAPE= 22.13%  (3.5s)
  -> MO HINH TOT NHAT: PROPHET (RMSE=9.57)

Doi chieu voi ai-model/outputs/model_metrics_all.csv:
       cap |  RMSE moi   RMSE cu      lech |  MAPE moi   MAPE cu      lech
  ----------------------------------------------------------------------
   45/1    |    9.5753    9.5753  0.000000 |   10.8473   10.8473  0.000000
   45/2    |   12.6294   12.6294  0.000000 |    9.9234    9.9234  0.000000
    8/1    |    9.5737    9.5737  0.000000 |   11.5221   11.5221  0.000000

  Lech RMSE lon nhat: 0.000000 -> KHOP (mo hinh tai lap duoc)

Tong hop 100 cap (doc tu model_metrics_all.csv, do la ket qua M1 da chay):
  PROPHET : RMSE TB    9.97 | MAE TB    7.94 | MAPE TB  10.43% | thang  97/100 cap
  XGBOOST : RMSE TB   10.98 | MAE TB    8.77 | MAPE TB  11.69% | thang   3/100 cap
  ARIMA   : RMSE TB   20.20 | MAE TB   16.44 | MAPE TB  23.77% | thang   0/100 cap
```

**Bảng sai số chi tiết (đơn vị: sản phẩm/ngày):**

| Cặp (SP / CH) | Mô hình | RMSE | MAE | MAPE | Doanh số TB/ngày (92 ngày test) | Sai số tuyệt đối điển hình |
|---------------|---------|------|-----|------|------------------|-----------------------------|
| 45 / 1 | **Prophet** (thắng) | **9,5753** | **7,5992** | **10,85%** | 75,6 | ±7,6 sản phẩm/ngày |
| 45 / 1 | XGBoost | 10,5539 | 8,4907 | 12,04% | 75,6 | ±8,5 sản phẩm/ngày |
| 45 / 1 | ARIMA | 18,4450 | 14,4743 | 22,74% | 75,6 | ±14,5 sản phẩm/ngày |
| 45 / 2 | Prophet | 12,6294 | 10,2112 | 9,92% | 109,1 | ±10,2 sản phẩm/ngày |
| 45 / 2 | **XGBoost** (thắng) | **12,3558** | **9,8840** | **9,50%** | 109,1 | ±9,9 sản phẩm/ngày |
| 45 / 2 | ARIMA | 27,4078 | 22,0432 | 23,71% | 109,1 | ±22,0 sản phẩm/ngày |
| 8 / 1 | **Prophet** (thắng) | **9,5737** | **7,7991** | **11,52%** | 72,9 | ±7,8 sản phẩm/ngày |
| 8 / 1 | XGBoost | 10,8044 | 8,7208 | 12,99% | 72,9 | ±8,7 sản phẩm/ngày |
| 8 / 1 | ARIMA | 16,7339 | 13,9200 | 22,13% | 72,9 | ±13,9 sản phẩm/ngày |

**Toàn bộ 100 cặp (kết quả M1, lưu trong `model_metrics_all.csv`):**

| Mô hình | RMSE TB | MAE TB | MAPE TB | Số cặp thắng |
|---------|---------|--------|---------|--------------|
| **Prophet** | **9,97** | **7,94** | **10,43%** | **97 / 100** |
| XGBoost | 10,98 | 8,77 | 11,69% | 3 / 100 |
| ARIMA | 20,20 | 16,44 | 23,77% | 0 / 100 |

**Đánh giá:** số liệu dự báo **đúng và tái lập được**:
- Chạy lại 3 cặp cho kết quả **trùng khít** file gốc, lệch **0,000000** → mô hình không bị "làm đẹp số".
- MAPE 10,43% nghĩa là dự báo 30 ngày tới lệch trung bình **khoảng 10,4%** so với doanh số thật — mức chấp nhận được với dữ liệu bán lẻ có mùa vụ tuần mạnh.
- Kết quả **đảo so với kỳ vọng ở Chương 2** (Chương 2 dự kiến XGBoost là mô hình chính). Nguyên nhân: XGBoost dựa trên `lag_1..lag_28` nên mạnh ở chế độ one-step, nhưng khi phải đệ quy 30 ngày liên tục thì sai số tích lũy; Prophet vốn là mô hình đa bước và có sẵn `yearly_seasonality`. **Đây là giá trị của phần thực nghiệm, không phải lỗi.**

### 4.2. Bảng `forecasts` có đối chiếu được với doanh số thực tế không?

**Log thực tế:**

```
==============================================================================
PHAN 2 - SO SANH BANG forecasts VOI DOANH SO THUC TE
==============================================================================
Khoang du bao   : 2018-01-01 -> 2018-01-30
Khoang ban that : 2013-01-01 -> 2017-12-31
Goi API GET /api/v1/dashboard/forecast-vs-actual (san pham 45, cua hang 1) trong 431 ms
  matched_rows = 0
  mape         = None
  rmse         = None
  mae          = None
  message      = No forecast for model 'prophet' could be matched to an actual in open
                 start..open end. The table holds 30 forecast row(s) and 0 actual row(s)
                 within the forecast window, but they cover different periods. Stored
                 forecasts run from 2018-01-01 to 2018-01-30 while sales data ends
                 2017-12-31, so accuracy cannot be measured until actual sales exist
                 for the forecast horizon.

Ket luan: hai khoang khong giao nhau nen KHONG the do MAPE cua bang
          forecasts bang doanh so that. API tra mape = null kem giai
          thich, khong bia ra mot con so. Sai so that duoc do bang
          backtest o PHAN 1 (92 ngay quy 4/2017).
```

**Đánh giá (phải nêu rõ trong Chương 4):**

Dữ liệu bán hàng kết thúc **31/12/2017**, còn dự báo trong DB phủ **01/01/2018 → 30/01/2018**. Hai khoảng **không giao nhau một ngày nào**, nên **không thể** tính MAPE của bảng `forecasts` bằng doanh số thật. API trả `mape = null` kèm giải thích thay vì bịa ra một con số — đây là hành vi đúng.

**Con số MAPE 10,43% ở mục 4.1 là đo trên tập test nội bộ của mô hình (92 ngày Q4/2017), không phải kiểm chứng ngoài mẫu trên tháng 1/2018.** Hai thứ này khác nhau và không được thay thế cho nhau khi viết báo cáo.

### 4.3. Bảng `forecasts` có đúng là dự báo từng ngày không?

#### 4.3.1. Lỗi phát hiện được (trước khi sửa)

Khi kiểm tra, 30 dòng của cặp (sản phẩm 45, cửa hàng 1) **giống hệt nhau**:

```
forecast_date | predicted_quantity | lower_bound | upper_bound
2018-01-01    | 58.960             | 53.064      | 64.856
2018-01-02    | 58.960             | 53.064      | 64.856
...
2018-01-30    | 58.960             | 53.064      | 64.856
```

**Nguyên nhân:** `scripts/load_sqlserver_data.py` (hàm `load_forecasts`) chia đều tổng tháng cho 30 ngày:

```python
daily = total_predicted / 30.0          # lặp lại cho cả 30 ngày
rows.append((..., 30, round(daily, 3),
             round(daily * 0.9, 3),      # biên dưới KHÔNG phải khoảng tin cậy thật
             round(daily * 1.1, 3),      # biên trên  KHÔNG phải khoảng tin cậy thật
             round(recommended, 3),
             9.97, 7.94, 10.43))         # sai số TOÀN HỆ THỐNG, không phải của cặp này
```

Ba hệ quả: (1) bảng mất mùa vụ tuần nên không thể đối chiếu theo ngày; (2) khoảng tin cậy là số bịa ±10%; (3) `rmse/mae/mape` ghi cứng một giá trị cho mọi dòng, che mất sự khác biệt giữa các cặp (cặp 45/2 thật ra RMSE 12,63 chứ không phải 9,97). Ngoài ra loader lọc `model == 'prophet'` nên **3 cặp XGBoost thắng cuộc bị dán nhãn sai** thành Prophet.

#### 4.3.2. Cách sửa

Viết mới `ai-model/scripts/forecast_next_month_sqlserver.py` — bản SQL Server của `forecast_next_month.py` (bản cũ chỉ chạy PostgreSQL). Script **dùng lại nguyên các hàm mô hình** của bản cũ, chỉ thay phần đọc/ghi dữ liệu:

1. Đọc lịch sử 2013–2017 từ `v_daily_sales` bằng `pyodbc`, reindex đủ 1.826 ngày.
2. Chọn mô hình **thắng cuộc của từng cặp** theo `model_metrics_all.csv`.
3. Train lại trên toàn bộ dữ liệu, dự báo 30 ngày.
4. Ghi `predicted_quantity` / `lower_bound` / `upper_bound` **thật của từng ngày**, `horizon_days = 1..30`, `model_name` đúng tên mô hình.
5. Ghi `rmse/mae/mape` **của chính cặp đó**.
6. Xuất `ai-model/outputs/forecasts_30d.csv` để `load_sqlserver_data.py` nạp lại được (đã sửa loader theo).

#### 4.3.3. Kết quả sau khi sửa

**Log thực tế:**

```
==============================================================================
PHAN 3 - KIEM TRA TINH TOAN VEN CUA BANG forecasts
==============================================================================
So cap co du bao: 100
  - Cap co dung 30 ngay      : 100/100
  - Cap co gia tri LAP LAI   : 0/100 (0 la tot - moi ngay phai khac nhau)
  - horizon_days = 1..30     : DUNG
  - lower <= predicted <= upper: DUNG
  - Mo hinh theo cap:
      prophet   2910 dong / 97 cap
      xgboost     90 dong / 3 cap
  - Tong 30 ngay khop forecast_summary_30d.csv: lech lon nhat 0.052 (thieu 0 cap)
  - rmse/mae/mape dung cua tung cap (khop model_metrics_all.csv): 100/100

Vi du 7 ngay dau cua cap san pham 45 - cua hang 1:
  ngay           h     du bao       duoi       tren
  2018-01-01     1     40.374     22.894     57.136
  2018-01-02     2     53.817     37.410     69.965
  2018-01-03     3     54.375     37.567     70.677
  2018-01-04     4     58.810     40.833     77.913
  2018-01-05     5     65.536     48.938     82.368
  2018-01-06     6     70.467     53.148     87.252
  2018-01-07     7     78.283     62.034     94.655
  -> 30/30 gia tri khac nhau, min 40.0 / max 78.3 (co mua vu tuan, khong con la mot so lap lai)
```

**Bảng trước / sau khi sửa:**

| Tiêu chí | Trước khi sửa | Sau khi sửa |
|----------|---------------|-------------|
| Số dòng bảng `forecasts` | 2.820 | **3.000** |
| Số cặp có dự báo | 94 | **100** |
| Cặp có 30 giá trị giống hệt nhau | **94 / 94** | **0 / 100** |
| `horizon_days` | luôn = 30 | **1 → 30** |
| Khoảng tin cậy | bịa ±10% | **lấy từ mô hình (95%)** |
| `rmse/mae/mape` | một giá trị dùng chung (9,97 / 7,94 / 10,43) | **theo từng cặp (100 giá trị khác nhau)** |
| Nhãn mô hình | tất cả `prophet` | **97 Prophet + 3 XGBoost (đúng cặp thắng)** |
| Tổng 30 ngày so với file M2 gốc | — | **lệch lớn nhất 0,052 trên tổng 191.582** |

**Đánh giá:** sau khi sửa, bảng `forecasts` đúng là output của mô hình: có mùa vụ tuần (thứ Bảy/Chủ Nhật cao hơn), khoảng tin cậy bao quanh giá trị dự báo, sai số đúng theo cặp. Tổng 30 ngày khớp file tổng hợp gốc → chứng minh pipeline không làm sai lệch kết quả mô hình.

### 4.4. AI điều phối / dự báo theo mùa vụ

**Công thức đang dùng** (trong `sp_Forecasts_Seasonal`):

```
season_share  = doanh số sản phẩm trong mùa / doanh số năm của sản phẩm
market_share  = doanh số toàn hệ thống trong mùa / doanh số toàn hệ thống cả năm
seasonal_index = season_share / market_share
```

Xếp hạng giảm dần theo `seasonal_index`; **top 20% → `import`** (nên nhập), **bottom 20% → `avoid`** (nên hạn chế), còn lại `neutral`. Với 50 sản phẩm: 10 / 30 / 10 mỗi mùa.

**Log thực tế (trích):**

```
==============================================================================
PHAN 4 - AI DIEU PHOI / DU BAO THEO MUA VU
==============================================================================
Goi API GET /api/v1/forecasts/seasonal trong 1575 ms
  du lieu   : 2013-01-01 -> 2017-12-31
  mua hien tai: winter
  so mua    : 4

--- XUAN (thang 2, 3, 4)
    50 san pham | nen nhap 10 | trung tinh 30 | nen hanh che 10
    5 san pham NEN NHAP nhieu nhat:
       1. Banh trung cuon              chi so 1.0045  (Snacks)
       2. Dieu hoa khong moi           chi so 1.0033  (Household)
       3. Ca phe den                   chi so 1.0032  (Beverages)
       4. Pho mai vi t                 chi so 1.0029  (Snacks)
       5. Tra xanh chai                chi so 1.0027  (Beverages)
    5 san pham NEN HANH CHE nhat:
      50. Banh snack                   chi so 0.9940  (Snacks)
      49. Khoai lang                   chi so 0.9960  (Fresh Food)
      48. Bong bien sang               chi so 0.9963  (Household)
      47. Thuc pham an dam             chi so 0.9964  (Baby Care)
      46. Xa phong                     chi so 0.9968  (Household)

--- HA (thang 5, 6, 7)
    5 san pham NEN NHAP nhieu nhat:
       1. Rau muong toi                chi so 1.0049  (Snacks)
       2. Banh snack                   chi so 1.0036  (Snacks)
       3. Buoi Long An                 chi so 1.0034  (Fresh Food)
       4. Xa phong                     chi so 1.0032  (Household)
       5. Nuoc loc 500ml               chi so 1.0028  (Beverages)
    5 san pham NEN HANH CHE nhat:
      50. Pho mai vi t                 chi so 0.9954  (Snacks)
      48. Sua tuoi tu 1 lit            chi so 0.9971  (Dairy)
      49. Trung ga                     chi so 0.9971  (Fresh Food)
      47. Ban cuon mat                 chi so 0.9972  (Dairy)
      46. Tra dau khong                chi so 0.9975  (Beverages)

--- THU (thang 8, 9, 10)
    5 san pham NEN NHAP nhieu nhat:
       1. Sua tuoi tu 1 lit            chi so 1.0087  (Dairy)
       2. Banh snack                   chi so 1.0036  (Snacks)
       3. Ban cuon mat                 chi so 1.0035  (Dairy)
       4. Tra dau khong                chi so 1.0031  (Beverages)
       5. Xa phong                     chi so 1.0030  (Household)
    5 san pham NEN HANH CHE nhat:
      50. Buoi Long An                 chi so 0.9922  (Fresh Food)
      49. Kem chong nang               chi so 0.9963  (Personal Care)
      48. Nuoc loc 500ml               chi so 0.9966  (Beverages)
      47. Ban quy                      chi so 0.9969  (Snacks)
      46. Nuoc khoang 500ml            chi so 0.9973  (Beverages)

--- DONG (thang 11, 12, 1)  <== mua hien tai
    5 san pham NEN NHAP nhieu nhat:
       1. Kem chong nang               chi so 1.0054  (Personal Care)
       2. Bong bien sang               chi so 1.0043  (Household)
       3. Khoai lang                   chi so 1.0043  (Fresh Food)
       4. Pho mai vi t                 chi so 1.0040  (Snacks)
       5. Buoi Long An                 chi so 1.0038  (Fresh Food)
    5 san pham NEN HANH CHE nhat:
      50. Ca phe den                   chi so 0.9945  (Beverages)
      49. Xa phong                     chi so 0.9949  (Household)
      48. Sua tuoi tu 1 lit            chi so 0.9953  (Dairy)
      47. Thit ga ta moi               chi so 0.9962  (Fresh Food)
      46. Banh snack                   chi so 0.9966  (Snacks)

Kiem tra doc lap (tinh lai tu SQL Server, khong dung API):
  spring : chi so 1.0045 -> 0.9940 (bien do 0.0105) | ranh gioi hang 10/11 chenh 0.00010
  summer : chi so 1.0049 -> 0.9954 (bien do 0.0095) | ranh gioi hang 10/11 chenh 0.00000
  autumn : chi so 1.0087 -> 0.9922 (bien do 0.0165) | ranh gioi hang 10/11 chenh 0.00000
  winter : chi so 1.0054 -> 0.9945 (bien do 0.0109) | ranh gioi hang 10/11 chenh 0.00030
  - So dong doi chieu        : 200 (200 dong = 50 san pham x 4 mua)
  - Lech chi so mua vu lon nhat: 0.000051 (API lam tron 4 chu so thap phan)
  - Cap hang ke nhau trung chi so: 112 (tie-break theo ten san pham)
  - So loi logic             : 0

Ket luan: chi so, xep hang va khuyen nghi khop hoan toan voi phep tinh doc lap.
```

**Đánh giá:** logic mùa vụ **đúng**:
- 200/200 dòng (50 sản phẩm × 4 mùa) khớp phép tính độc lập, lệch lớn nhất **0,000051** (chỉ do API làm tròn 4 chữ số thập phân).
- **0 lỗi logic**: mỗi mùa đúng 50 sản phẩm, đúng 10 `import` / 30 `neutral` / 10 `avoid`, hạng là hoán vị 1..50, thứ tự nhất quán với chỉ số, danh sách nhập giảm dần và danh sách hạn chế tăng dần.
- Mùa hiện tại được xác định đúng (`winter`, tháng 11–12–1, hôm nay 05/11).

**Hạn chế phải nêu trong Chương 4:** chỉ số mùa vụ có biên độ **rất hẹp** (0,992 → 1,009, tức ±0,9% quanh mức trung bình). Nguyên nhân: mùa vụ của bộ dữ liệu Walmart tác động **đồng đều lên mọi sản phẩm**, nên chỉ số tương đối gần như không phân biệt được sản phẩm. Hệ quả định lượng: ở 3/4 mùa, **hạng 10 và hạng 11 chênh nhau dưới 0,0003** — nghĩa là ranh giới "nên nhập" / "trung tính" rất dễ đảo nếu dữ liệu thay đổi. Đây là **hạn chế của dữ liệu**, không phải lỗi công thức; khi viết báo cáo phải nói rõ đây là so sánh **giữa các sản phẩm trong cùng mùa**, không phải mức tăng tuyệt đối.

### 4.5. Chatbot AI

**Log thực tế:**

```
==============================================================================
PHAN 5 - CHATBOT AI (Gemini)
==============================================================================
[Chao hoi] Hoi: Xin chào, bạn là ai và bạn giúp được gì cho tôi?
   Tra loi (41 ms, model: (duong nhanh, khong goi Gemini)):
     Chào bạn, tôi là trợ lý của FreshChain. Tôi có thể giúp bạn kiểm tra tồn kho, hàng
     sắp hết hạn, cảnh báo cần xử lý, đơn hàng gần đây và gợi ý nhập hàng theo mùa. Bạn
     cần xem thông tin gì trước?
   Kiem tra chat luong cau tra loi:
     - do dai            : 193 ky tu
     - so cau           : 3
     - ky hieu viet tat  : KHONG co (dat)

[Ton kho] Hoi: Tồn kho của cửa hàng Q.3 hiện tại thế nào?
   Tra loi (5929 ms, model: gemini-3.5-flash-lite):
     Chào bạn, hiện tại tổng số lô hàng còn tồn tại Cửa hàng tiện lợi Q.3 là 150 lô với
     đa dạng các mặt hàng khác nhau. Đáng chú ý, sản phẩm Khoai lang đang vừa sắp hết hạn
     sau 2 đến 3 ngày tới lại vừa dư thừa số lượng lớn so với nhu cầu, vì vậy tôi gợi ý
     bạn nên chủ động chuyển bớt sang cửa hàng khác thay vì tiếp tục nhập thêm. Bạn có
     muốn xem chi tiết hơn về các sản phẩm này không?
   Kiem tra chat luong cau tra loi:
     - do dai            : 381 ky tu
     - so cau           : 4
     - ky hieu viet tat  : KHONG co (dat)
     - so lieu dung      : KHOP (150)

[Mua vu] Hoi: Mùa này nên nhập nhiều mặt hàng nào?
   Tra loi (3859 ms, model: gemini-3.5-flash-lite):
     Chào bạn, trong mùa đông hiện tại, tôi đề xuất bạn nên chú ý nhập nhiều hơn các mặt
     hàng như Kem chống nắng, Bông biển sáng và Khoai lang vì các sản phẩm này có chỉ số
     mùa vụ cao hơn mức chung. Ngược lại, bạn nên hạn chế nhập Cà phê đen, Xà phòng và
     Sữa tươi từ 1 lít do chỉ số mùa vụ của chúng thấp hơn mức chung. Những điều chỉnh
     này sẽ giúp bạn tối ưu hóa lượng hàng hóa và tránh lãng phí thực phẩm. Bạn có muốn
     xem thêm chi tiết về kế hoạch nhập hàng không?
   Kiem tra chat luong cau tra loi:
     - do dai            : 461 ky tu
     - so cau           : 4
     - ky hieu viet tat  : KHONG co (dat)
     - so lieu dung      : KHOP (Kem chống nắng)

[Khong dau] Hoi: mua nay nen nhap nhieu mat hang nao
   Tra loi (1846 ms, model: gemini-3.5-flash-lite):
     Chào bạn, hiện tại đang là mùa Đông nên tôi xin gợi ý một số mặt hàng bạn nên chú ý
     cân đối. Bạn nên ưu tiên nhập nhiều hơn các sản phẩm như Kem chống nắng, Bông biển
     sáng và Khoai lang vì chỉ số mùa vụ của chúng cao hơn mức chung. Ngược lại, bạn nên
     hạn chế nhập Cà phê đen, Xà phòng và Sữa tươi từ 1 lít do các mặt hàng này có chỉ số
     mùa vụ thấp hơn mức chung. Bạn có muốn xem thêm chi tiết về kế hoạch nhập hàng này
     không?
   Kiem tra chat luong cau tra loi:
     - do dai            : 425 ky tu
     - so cau           : 4
     - ky hieu viet tat  : KHONG co (dat)
     - so lieu dung      : KHOP (Kem chống nắng)
```

**Bảng tổng hợp thời gian phản hồi:**

| Câu hỏi | Loại | Thời gian | Model |
|---------|------|-----------|-------|
| "Xin chào, bạn là ai…" | Chào hỏi (đường nhanh, không chạm DB, không gọi Gemini) | **41 ms** | — |
| "Tồn kho của cửa hàng Q.3…" | Nghiệp vụ, có gọi Gemini | **5.929 ms** | gemini-3.5-flash-lite |
| "Mùa này nên nhập nhiều mặt hàng nào?" | Nghiệp vụ + khối mùa vụ (cache) | **3.859 ms** | gemini-3.5-flash-lite |
| "mua nay nen nhap nhieu mat hang nao" (không dấu) | Nghiệp vụ, kiểm tra khả năng hiểu câu không dấu | **1.846 ms** | gemini-3.5-flash-lite |

**Đánh giá:** chatbot **đúng số liệu**:
- Câu chào hỏi đi **đường nhanh**: 41 ms (nhanh gấp ~140 lần so với gọi Gemini) và không chạm database.
- Câu tồn kho trả đúng **150 lô** của cửa hàng Q.3 (đối chiếu SQL: `SELECT COUNT(*) FROM inventory WHERE store_id = 1` = 150). **Trước khi sửa chatbot trả 1.330 lô** — đó là tổng số lô của cả 10 cửa hàng, bị gán sai cho một cửa hàng.
- Câu mùa vụ trả đúng 3 sản phẩm nên nhập và 3 sản phẩm nên hạn chế, khớp bảng ở mục 4.4 (mùa Đông: Kem chống nắng, Bông biển sáng, Khoai lang / Cà phê đen, Xà phòng, Sữa tươi từ 1 lít).
- Cả 4 câu đều **3–4 câu văn**, không có danh sách thô, **không lộ** `SP#`, `CH#`, `CB#`, `DH#`, `SL`, `HH`.
- Câu **không dấu** vẫn hiểu đúng (1.846 ms) nhờ cơ chế bỏ dấu khi so khớp từ khóa.

---

## 5. Các lỗi phát hiện và đã sửa trong đợt kiểm thử

| # | Lỗi | Mức độ | Nguyên nhân | Đã sửa |
|---|-----|--------|-------------|--------|
| 1 | Bảng `forecasts` lưu **trung bình tháng chia đều 30 ngày**, khoảng tin cậy bịa ±10%, `rmse/mae/mape` ghi cứng 9,97/7,94/10,43 cho mọi dòng, 3 cặp XGBoost bị dán nhãn `prophet` | **Nghiêm trọng** — bảng dự báo không dùng được để đối chiếu | `scripts/load_sqlserver_data.py::load_forecasts` làm `daily = total_predicted / 30` | Viết `ai-model/scripts/forecast_next_month_sqlserver.py`, ghi dự báo **từng ngày**; sửa loader đọc `forecasts_30d.csv`. Bảng hiện có 3.000 dòng / 100 cặp, 30/30 giá trị khác nhau mỗi cặp |
| 2 | Chatbot báo **1.330 lô** (tổng 10 cửa hàng) cho riêng cửa hàng Q.3 (thật là **150 lô**) | **Cao** — trả lời sai số liệu | `_build_context` lấy `sp_Inventory_List` không lọc cửa hàng, rồi câu "Tổng số lô hàng còn tồn trong kho" không ghi rõ phạm vi | Thêm `_detect_store()` nhận diện cửa hàng theo mã/tên (bỏ dấu), truyền `StoreId` vào `sp_Inventory_List` và `sp_Inventory_ListExpiring`, ghi rõ phạm vi trong câu dẫn |
| 3 | Chatbot **không hiểu câu hỏi không dấu** ("mua nay nen nhap nhieu mat hang nao") → rơi vào đường nhanh và trả lời chung chung | **Trung bình** | `_match()` so khớp nguyên văn, từ khóa có dấu (`"mùa"`) không khớp chuỗi không dấu (`"mua"`) | Thêm `_strip_diacritics()` (chuẩn hóa NFD + xử lý `đ/Đ`), so khớp **không phân biệt dấu** cho mọi từ khóa nghiệp vụ |
| 4 | Gemini trả 503 khi quá tải → endpoint `/chat` trả **HTTP 500**, người dùng không nhận được gì | **Trung bình** | Không có cơ chế thử lại / dự phòng | Thử lại 1 lần, nếu vẫn lỗi thì trả **bản tóm tắt từ dữ liệu thật** (`model = "fallback"`) kèm lý do trong `sources`, không trả 500 |
| 5 | Rác dữ liệu: đơn test `SMOKE-ORDER-1` (2 dòng hàng, năm 2026) còn sót trong DB, làm `v_daily_sales` lòi thêm 2 dòng và `MAX(sale_date)` thành 2026-10-24 | **Thấp** — nhưng làm sai mọi thống kê "30 ngày gần nhất" | `scripts/smoke_test_writes.py` tạo đơn rồi chuyển `completed` (bị khóa, không xoá được qua API) và không dọn | Đã xoá đơn + dòng hàng. `v_daily_sales` trở lại **912.999 dòng, 2013-01-01 → 2017-12-31** |

> **Lưu ý về lỗi #1:** `forecast_summary_30d.csv` (file tổng hợp của lần chạy M2 gốc) được **giữ nguyên** để đối chiếu tổng 30 ngày; cột `forecasts.recommended_import_qty` vẫn lấy giá trị snapshot từ file này. API `/recommendations/import` **không đọc** cột đó mà tự tính lại từ `SUM(predicted_quantity)` + tồn kho hiện tại, nên việc sửa bảng không làm lệch trang Đề xuất nhập hàng.

---

## 6. Hạn chế dữ liệu phải nêu rõ trong Chương 4

Đây là các hạn chế **của dữ liệu**, không phải lỗi mô hình. Nếu không nêu, người đọc sẽ hiểu sai kết quả.

| # | Hạn chế | Hệ quả | Cách trình bày |
|---|---------|--------|----------------|
| 1 | `forecasts` phủ 01/2018, doanh số kết thúc 31/12/2017 | **Không thể** đo MAPE ngoài mẫu | Nêu rõ MAPE 10,43% là đo trên tập test nội bộ 92 ngày Q4/2017 |
| 2 | `max_stock` trong seed (48–300) nhỏ hơn nhiều so với nhu cầu thật (861–2.793/ngày) | `recommended_import_qty` bị nén mạnh; tổng đề xuất sau chặn chỉ **7.286** trong khi nhu cầu thuần **192.387** | Nêu rõ đây là hạn chế seed data; cột `raw_need` trong `forecast_summary_30d.csv` giữ nhu cầu chưa chặn để đối chiếu |
| 3 | Mùa vụ Walmart tác động đều lên 50 sản phẩm | Chỉ số mùa vụ chỉ chênh ±0,9%; ranh giới top 20% rất mỏng (hạng 10/11 chênh < 0,0003) | Nêu rõ là so sánh **giữa các sản phẩm trong cùng mùa**, không phải mức tăng tuyệt đối |
| 4 | Dữ liệu Kaggle **không có hiện tượng censored demand** (0 ngày bán = 0) | Chương 1–2 trình bày lý thuyết, nhưng thực nghiệm không gặp | Ghi rõ: "đây là hạn chế của dataset Kaggle so với bán lẻ thực tế" |
| 5 | Giá trong DB là **mô phỏng** theo nhóm hàng (Kaggle không có cột giá) | Doanh thu chỉ để demo dashboard | Không trình bày như số liệu thật; mô hình chỉ dùng `quantity` nên không ảnh hưởng kết quả |

---

## 7. Phụ lục — danh sách file liên quan

| File | Vai trò |
|------|---------|
| `scripts/verify_ai_models.py` | Script kiểm thử tổng hợp (chạy lại được nhiều lần) |
| `docs/02-bao-cao/kiem-thu-ai-log.txt` | Log đầy đủ của lần chạy (UTF-8) |
| `docs/02-bao-cao/kiem-thu-ai-backtest.csv` | Bảng sai số 3 cặp vừa train lại |
| `ai-model/scripts/train_models.py` | Huấn luyện + đánh giá 3 mô hình (100 cặp) |
| `ai-model/scripts/forecast_next_month_sqlserver.py` | Sinh dự báo 30 ngày từng ngày, ghi bảng `forecasts` |
| `ai-model/outputs/model_metrics_all.csv` | Kết quả đánh giá 100 cặp (nguồn đối chiếu) |
| `ai-model/outputs/forecast_summary_30d.csv` | Tổng hợp 30 ngày của lần chạy M2 gốc |
| `ai-model/outputs/forecasts_30d.csv` | 3.000 dòng dự báo từng ngày (nguồn nạp DB) |
| `backend/app/services/seasonal.py` | Nhãn tiếng Việt + cache 300 giây cho mùa vụ |
| `backend/app/routers/chat_router.py` | Chatbot: system prompt, từ khóa, sửa lỗi chính tả, nhận diện cửa hàng |
| `database/03-migrations/011-transfers-seasonal.sql` | `sp_Forecasts_Seasonal` + 10 Stored Procedure điều chuyển |
| `database/03-migrations/010-sqlserver-analytics-procedures.sql` | `sp_Recommendations_Import` và các procedure phân tích |

**Tài liệu tham chiếu thêm:** `docs/05-tham-khao/ket-qua-danh-gia-model.md` (bảng đánh giá 100 cặp chi tiết).
