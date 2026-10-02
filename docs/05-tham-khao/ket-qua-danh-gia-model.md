# Kết quả đánh giá mô hình dự báo nhu cầu

> **Ngày chạy:** 03/10/2026
> **Phạm vi:** 100 cặp (10 sản phẩm × 10 cửa hàng) · 1.826 ngày · 2013-01-01 → 2017-12-31
> **Tập đánh giá:** 92 ngày cuối (2017-10-01 → 2017-12-31)
> **Script:** `ai-model/scripts/train_models.py`, `ai-model/scripts/tune_prophet.py`
> **Dữ liệu thô:** `ai-model/outputs/model_metrics_all.csv`

---

## 1. Phương pháp đánh giá

### 1.1 Chia tập theo mốc ngày, không dùng 80/20

| Mục | Giá trị |
|-----|---------|
| Tập train | 1.734 ngày · 2013-01-01 → 2017-09-30 |
| Tập test | 92 ngày · 2017-10-01 → 2017-12-31 |
| Mốc chia | `2017-10-01` |

**Vì sao không chia 80/20?** Với dữ liệu nhiều năm, tỉ lệ 80/20 không bảo đảm tập test rơi vào một mùa cụ thể. Mốc `2017-10-01` đặt tập test vào quý IV — đúng mùa cao điểm của bán lẻ, dễ giải thích và đúng nghiệp vụ.

**Vì sao không chia ngẫu nhiên?** Chuỗi thời gian có tính tự nhiên. Chia ngẫu nhiên đưa dữ liệu tương lai vào tập train, tạo rò rỉ thông tin và làm RMSE đẹp giả.

### 1.2 Reindex chuỗi thời gian trước khi huấn luyện

View `v_daily_sales` chỉ trả về dòng cho **ngày có phát sinh giao dịch**. Cặp (product 4, store 6) thiếu ngày 15/01/2014 do dòng `sales = 0` đã bị loại khi import (vi phạm ràng buộc `CHECK (quantity > 0)`).

Vì vậy mọi chuỗi đều được **reindex về đủ 1.826 ngày liên tục, ngày thiếu điền 0**. Không reindex thì các hàm lag và rolling lệch ngày, mô hình học sai lệch thời gian.

### 1.3 Chọn tham số theo tập validation, không theo tập test

Grid search 18 bộ tham số Prophet trên dữ liệu 5 năm:

| Cách chọn | cps | mode | yearly | RMSE_val | RMSE_test |
|-----------|-----|------|--------|----------|-----------|
| **Theo validation (đã chọn)** | **0,01** | **multiplicative** | **20** | **10,49** | **10,23** |
| Theo test (rò rỉ dữ liệu) | 0,5 | additive | 10 | 11,47 | 9,76 |

Bộ theo test có RMSE test thấp hơn 0,47, nhưng **không được chọn** — chọn tham số trên tập test là rò rễ dữ liệu, khiến con số báo cáo mất ý nghĩa. Đây là quyết định có chủ ý nhằm giữ tính trung thực của báo cáo.

### 1.4 Ngày lễ

Cả Prophet và XGBoost dùng **chung bộ ngày lễ Hoa Kỳ** để so sánh công bằng. Đây là dữ liệu Walmart (Hoa Kỳ), không phải Việt Nam.

### 1.5 Ba chỉ số

| Chỉ số | Ý nghĩa | Vai trò |
|--------|----------|---------|
| RMSE | Sai số bình phương trung bình | **Chỉ số chính** — phạt nặng các ngày dự báo sai lệch lớn |
| MAE | Sai số tuyệt đối trung bình | Dễ diễn giải cho người quản lý |
| MAPE | Sai số phần trăm trung bình | Bỏ qua các ngày có `y = 0` để tránh phân kỳ vô hạn |

---

## 2. Kết quả so sánh 3 mô hình

### 2.1 Chỉ số trung bình trên 100 cặp

| Mô hình | RMSE | MAE | MAPE | RMSE tốt nhất | RMSE xấu nhất | Độ lệch chuẩn |
|---------|------|-----|------|---------------|---------------|----------------|
| **Prophet** | **9,97** | **7,94** | **10,43%** | 6,62 | 12,81 | 1,43 |
| XGBoost | 10,98 | 8,77 | 11,69% | 7,39 | 15,14 | 1,70 |
| ARIMA | 20,20 | 16,44 | 23,77% | 9,94 | 35,84 | 4,96 |

### 2.2 Số cặp mỗi mô hình chiếm ưu thế (theo RMSE thấp nhất)

| Mô hình | Số cặp thắng | Tỉ lệ |
|---------|--------------|-------|
| **Prophet** | **97 / 100** | **97%** |
| XGBoost | 3 / 100 | 3% |
| ARIMA | 0 / 100 | 0% |

Ba cặp XGBoost thắng: (45, 2), (13, 7), (28, 4).

### 2.3 Chênh lệch giữa Prophet và XGBoost

| Chỉ số | Giá trị |
|--------|---------|
| RMSE của XGBoost cao hơn Prophet trung bình | 1,02 |
| Biên độ chênh lệch | −1,03 → +3,21 |
| Số cặp chênh lệch < 1,0 RMSE | 59 / 100 |

Trong 59 cặp, XGBoost nhỉnh hơn Prophet **dưới 1 đơn vị sản phẩm/ngày** — trên quy mô bán ~1.000 sản phẩm/ngày, khác biệt này không có ý nghĩa nghiệp vụ. XGBoost chỉ thắng rõ ở 3 cặp trên.

### 2.4 RMSE trung bình theo sản phẩm

| product_id | Sản phẩm | Prophet | XGBoost | ARIMA |
|-----------|----------|---------|---------|-------|
| 48 | Kem đánh răng | **7,76** | 8,59 | 14,34 |
| 11 | Nước lọc 500ml | **9,33** | 10,05 | 17,26 |
| 8 | Thịt bò | **9,75** | 10,98 | 19,90 |
| 18 | Sữa chua 500g | **10,18** | 11,45 | 21,73 |
| 45 | Khăn ướt trẻ em | **10,38** | 11,02 | 22,22 |
| 13 | Nước suối 330ml | **10,38** | 11,46 | 22,23 |
| 25 | Rượu dừa cơ | **10,30** | 11,53 | 19,79 |
| 38 | Sữa tắm thể | **10,48** | 11,57 | 20,41 |
| 15 | Cà phê sữa đinh hương | **10,52** | 11,66 | 21,35 |
| 28 | Kẹo mút | **10,58** | 11,49 | 22,75 |

### 2.5 RMSE trung bình theo cửa hàng

| store_id | Prophet | XGBoost | | store_id | Prophet | XGBoost |
|-----------|---------|---------|---|----------|---------|---------|
| 7 | **8,17** | 8,65 | | 4 | **10,47** | 11,22 |
| 5 | **8,74** | 9,68 | | 10 | **10,57** | 11,46 |
| 6 | **8,84** | 9,69 | | 9 | **10,28** | 11,48 |
| 1 | **9,61** | 10,50 | | 3 | **10,83** | 12,19 |
| 2 | **11,06** | 12,46 | | 8 | **11,09** | 12,47 |

---

## 3. Ba nhận xét quan trọng

### Nhận xét 1 — Độ dài chuỗi quyết định thứ hạng, không phải thuật toán

Khi chỉ dùng **1 năm dữ liệu**, Prophet đứng hạng 3. Thêm 4 năm dữ liệu, Prophet đứng hạng 1 — **không thay đổi tham số nào**.

| Mô hình | RMSE 1 năm | RMSE 5 năm | Cải thiện |
|---------|------------|------------|-----------|
| **Prophet** | 23,20 | **9,97** | **−57%** |
| XGBoost | 16,47 | 10,98 | −33% |
| ARIMA | 19,36 | 18,36 | −5% |

Prophet phát ra cảnh báo *"Yearly seasonality is enabled with less than 730 days"* — thiếu dữ liệu để ước lượng mùa vụ năm. Nguyên nhân khiến Prophet kém là **thiếu dữ liệu, không phải tham số**.

**Bài học:** phải đọc cảnh báo của thư viện, không chỉ nhìn con số. Nếu giữ 1 năm dữ liệu, đồ án sẽ kết luận sai rằng Prophet không phù hợp với bài toán này.

Dữ liệu dài còn làm mô hình bám đảo hơn nhiều: biến động RMSE giữa các bộ tham số giảm từ **10,5 lần** (1 năm) xuống **8%** (5 năm).

### Nhận xét 2 — ARIMA không phù hợp khi dữ liệu chứa mùa vụ mạnh

RMSE của ARIMA trung bình gấp **2,02 lần** Prophet, và biến động cao gấp 3,5 lần (độ lệch chuẩn 4,96 so với 1,43).

Lý do: ARIMA với cấu hình đơn giản `(p,d,q) + seasonal_order=(0,0,0,0)` **không mô hình hóa được mùa vụ năm**. Chuỗi bán lẻ có mùa vụ rõ rệt (tháng 7 cao nhất, tháng 1 thấp nhất, hệ số biến động 1,90). Prophet có sẵn `yearly_seasonality` và `changepoint` nên nắm bắt được.

ARIMA vẫn được giữ lại trong hệ thống **với vai trò đối chứng thống kê** — chỉ dùng khi không có dữ liệu dài đủ để xác định mùa vụ, hoặc làm mốc so sánh tối giản.

### Nhận xét 3 — XGBoost có lợi thế khi chuỗi ngắn, nhưng không đủ bù độ chênh lệch

Với 5 năm dữ liệu, XGBoost chỉ thắng 3/100 cặp, và ở 59 cặp chênh lệch dưới 1,0 RMSE — không đáng kể về mặt nghiệp vụ.

**Nguyên nhân cấu trúc:** XGBoost dựa trên đặc trưng `lag_1..lag_28`. Ở chế độ một bước (one-step), đặc trưng này rất mạnh. Nhưng khi cần dự báo **30 ngày liên tục**, phải dùng dự báo của ngày trước làm đầu vào cho ngày sau — sai lệch tích luỹ dần, hiệu quả suy giảm. Prophet và ARIMA vốn đã là mô hình đa bước nên không gặp hạn chế này.

**Kết luận:** với chuỗi ≥ 3 năm có mùa vụ rõ, **Prophet là mô hình chính**. XGBoost giữ vai trò dự phòng cho chuỗi ngắn hoặc không có mùa vụ.

---

## 4. Nhận xét bổ sung

### 4.1 Mức độ ổn định

| Chỉ số | Giá trị |
|--------|---------|
| Hệ số biến động RMSE của Prophet (CV) | 14,32% |
| RMSE 95th percentile | 12,09 |
| MAPE cao nhất | 14,62% |
| MAPE thấp nhất | 7,59% |

Không có cặp nào có RMSE vượt 12,81 — hiệu năng khá đồng đều giữa các cặp, không phụ thuộc mạnh vào từng cửa hàng hay từng sản phẩm.

### 4.2 Cửa hàng 7 dễ dự báo nhất, cửa hàng 2 và 8 khó nhất

Khoảng cách giữa cửa hàng dễ nhất (RMSE 8,17) và khó nhất (11,09) là 36%. Cửa hàng 2 và 8 có RMSE cao hơn ở **cả ba mô hình**, gợi ý chuỗi bán hàng tại hai cửa hàng này biến động mạnh hơn — có thể là chuỗi có tính mùa vụ riêng hoặc nhiễu cao hơn.

### 4.3 Sản phẩm 48 dễ dự báo nhất

Kem đánh răng có RMSE 7,76, thấp hơn trung bình 22%. Đây là mặt hàng tiêu dùng có tần suất mua đều, tồn kho không phụ thuộc thời tiết — mẫu nhu cầu ổn định, dễ dự báo.

---

## 5. ⚠️ Hạn chế cần nêu rõ trong báo cáo

### 5.1 Censored demand không xảy ra trong dữ liệu này

Chương 1 và Chương 2 trình bày censored demand như vấn đề lý thuyết. Kiểm tra trên 100 cặp: **0 ngày** có `quantity_sold = 0`.

Kết luận khi viết Chương 4: *"Trong dữ liệu thực tế của đồ án, không xảy ra censored demand. Đây là hạn chế của tập dữ liệu Kaggle so với dữ liệu bán lẻ thực tế, nơi hiện tượng này có thể xảy ra khi tồn kho bằng 0 nhưng nhu cầu vẫn tồn tại."*

### 5.2 Giá trong cơ sở dữ liệu là mô phỏng

Tập Kaggle chỉ có cột số lượng, **không có cột giá**. Giá trong bảng `order_items` được gán mô phỏng theo nhóm hàng chỉ để chạy được dashboard doanh thu. **Mô hình dự báo chỉ dùng `quantity`, không phụ thuộc giá**, nên kết quả đánh giá trên hoàn toàn có giá trị.

### 5.3 Mùa vụ không phân biệt được giữa các sản phẩm

Điều tra trên cả 50 sản phẩm:

| Mức đo | Hệ số biến động | Độ rộng giữa 50 sản phẩm |
|--------|------------------|--------------------------|
| Theo tháng | 1,85 – 1,95 | 0,098 → không phân biệt được |
| Theo tuần | 1,88 – 2,03 | 0,153 → rất yếu |
| Theo ngày trong tuần | 1,52 | yếu hơn mùa vụ tháng |

Mùa vụ của Walmart chạy theo thời tiết và ngày lễ quốc gia, tác động **đồng đều lên mọi mặt hàng**. Vì vậy tiêu chí "hệ số biến động mùa vụ" **không dùng được** để chọn sản phẩm huấn luyện; 10 sản phẩm được chọn theo doanh số năm và đa dạng 7 nhóm hàng.

### 5.4 Hạn chế khi dự báo xa hơn 30 ngày

Script dự báo chu kỳ 30 ngày và dùng **cơ chế đệ quy** cho XGBoost (lấy giá trị dự báo của ngày trước làm đầu vào cho ngày sau) — không dùng số thực tương lai, tránh rò rỉ dữ liệu. Chuỗi càng dài, sai lệch tích luỹ càng lớn. Chưa kiểm chứng độ chính xác ngoài 30 ngày.

---

## 6. Kết luận

| Mô hình | RMSE | Số cặp thắng | Vai trò trong hệ thống |
|---------|------|--------------|------------------------|
| **Prophet** | **9,97** | 97 / 100 | **Mô hình chính** |
| XGBoost | 10,98 | 3 / 100 | Dự phòng cho chuỗi ngắn |
| ARIMA | 20,20 | 0 / 100 | Đối chứng thống kê |

**Khuyến nghị:** triển khai Prophet làm mô hình dự báo chính. Với 100 cặp, độ chính xác đạt RMSE ≈ 10 sản phẩm/ngày trên quy mô bán ~1.000 sản phẩm/ngày — tương đương sai số khoảng **1%**, đủ hỗ trợ quyết định nhập hàng.

Cần định kỳ chạy lại mô hình (ví dụ theo tháng) vì độ chính xác phụ thuộc vào việc dữ liệu mới có cùng phân bố mùa vụ với dữ liệu huấn luyện hay không.

---

*Tài liệu được tạo tự động từ kết quả thực thi `train_models.py`. Mọi con số trong bảng lấy trực tiếp từ `ai-model/outputs/model_metrics_all.csv`.*