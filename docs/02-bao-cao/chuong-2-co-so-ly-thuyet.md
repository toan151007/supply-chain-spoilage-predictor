# CHƯƠNG 2: CƠ SỞ LÝ THUYẾT

## 2.1. Tổng quan về chuỗi cung ứng bán lẻ

### 2.1.1. Định nghĩa chuỗi cung ứng

Chuỗi cung ứng (supply chain) là mạng lưới liên kết tất cả các chủ thể tham gia vào quá trình tạo ra và đưa sản phẩm đến người tiêu dùng, bao gồm nhà cung cấp nguyên liệu, nhà sản xuất, nhà phân phối, nhà bán lẻ và các đơn vị hỗ trợ vận chuyển, lưu kho. Theo quan điểm quản trị hiện đại, mục tiêu của quản lý chuỗi cung ứng không đơn thuần là giảm chi phí từng khâu, mà là **tối đa hóa giá trị toàn chuỗi** trong điều kiện các thành phần liên kết chặt chẽ với nhau.

Trong bối cảnh đề tài này, chuỗi cung ứng được hiểu theo nghĩa hẹp: chuỗi cung ứng **nội bộ của một đơn vị bán lẻ**, từ khâu đặt hàng từ nhà cung cấp, tiếp nhận và lưu kho, đến khâu bán hàng và xử lý hàng tồn dư. Một chuỗi cung ứng nội bộ điển hình của một cửa hàng tiện lợi bao gồm các chuỗi hoạt động sau:

```
Nhà cung cấp → Đặt hàng → Tiếp nhận & Kiểm đếm → Lưu kho
      → Bán hàng (xuất kho) → Cập nhật tồn kho → Xử lý hàng tồn dư/hết hạn
```

Như vậy, chủ cửa hàng đóng vai trò vừa là khách hàng của nhà cung cấp, vừa là nhà cung cấp cho người tiêu dùng cuối — một vị trí trung gian mà sai sót trong quyết định của họ tác động trực tiếp đến cả hai phía.

### 2.1.2. Đặc điểm của chuỗi cung ứng thực phẩm tươi sống

Chuỗi cung ứng thực phẩm tươi sống có một số đặc điểm khác biệt rõ rệt so với hàng hóa tiêu dùng lâu dài, và các đặc điểm này quyết định bản chất của bài toán quản lý tồn kho:

**Thứ nhất, hạn sử dụng hữu hạn và tương đối ngắn.** Đây là đặc điểm quyết định nhất. Mỗi lô hàng đều mang một mốc hạn, sau đó giá trị thương phẩm giảm nhanh chóng và cuối cùng trở về bằng không. Hệ quả là tồn kho không phải tài sản có thể giữ lâu: tồn kho dư không chỉ tốn vốn mà còn **tiêu hao tài sản theo thời gian**. Điều này phân biệt căn bản bài toán thực phẩm với bài toán tồn kho công nghiệp thông thường, nơi hàng tồn giữ nguyên giá trị.

**Thứ hai, nhu cầu biến động mạnh và mang tính mùa vụ rõ nét.** Nhu cầu rau củ tăng vọt dịp Tết, nhu cầu đồ uống tăng theo mùa nắng nóng, nhu cầu món ăn chay tăng trong tháng gian *(cần bổ sung số liệu minh họa từ dữ liệu thực tế của đơn vị thực hành)*. Biên độ biến động có thể lớn gấp nhiều lần giữa ngày cao điểm và ngày thường.

**Thứ ba, chu kỳ đầu tư ngắn.** Doanh nghiệp bán lẻ phải tái đầu tư vốn liên tục vào hàng hóa mới, không thể dồn vốn như trong sản xuất dài hạn. Điều này khiến áp lực quản lý tồn kho gay gắt hơn vì mỗi chu kỳ vốn đều phải sinh lời.

**Thứ tư, phụ thuộc điều kiện bảo quản.** Nhiều loại thực phẩm yêu cầu bảo quản lạnh, hạn chế thời gian tồn tại trên kệ. Điều này giới hạn mức tồn kho tối đa có thể lưu giữ, kể cả khi dự báo cho thấy nên nhập nhiều hơn.

**Thứ năm, tính chất nguyên liệu đầu vào trong F&B.** Với nhà hàng, nhiều món ăn sử dụng nguyên liệu tươi sống không có đơn vị quy đổi cố định (một con gà cho ra nhiều phần thịt khác nhau), khiến việc định lượng tồn kho phức tạp hơn hàng tính theo số lượng quy đổi.

### 2.1.3. Vấn đề lãng phí trong chuỗi cung ứng

Lãng phí thực phẩm trong chuỗi cung ứng được phân loại theo vị trí xảy ra và thường được trình bày theo mô hình "kệ thực phẩm" (food value chain) của FAO, theo đó mỗi tầng kệ gắn với một nấc thang bậc. Trong phạm vi đề tài, các điểm lãng phí có thể xảy ra gồm: thu hoạch, chế biến, phân phối, bán lẻ và tiêu dùng.

Đối với chuỗi cung ứng **nội bộ** của cửa hàng bán lẻ, có thể phân loại lãng phí thành ba nhóm:

| Nhóm lãng phí | Biểu hiện | Nguyên nhân chủ yếu |
|----------------|-----------|---------------------|
| **Lãng phí về số lượng** | Hàng còn tốt nhưng vượt nhu cầu, phải giảm giá hoặc bán nhanh | Dự báo thiếu chính xác, nhập dư do tích lũy tâm lý "sợ thiếu" |
| **Lãng phí về thời gian** | Hàng hết hạn phải tiêu hủy | Không theo dõi hạn sử dụng, luồng FIFO không được áp dụng |
| **Lãng phí về chất lượng** | Hàng hư hỏng, mất an toàn thực phẩm | Điều kiện bảo quản không đảm bảo, luân chuyển quá nhiều |

Điểm cần lưu ý là ba nhóm này có mối liên hệ nhân quả: lãng phí về số lượng tạo ra tồn kho dư, tồn kho dư dẫn đến luân chuyển chậm, luân chuyển chậm dẫn đến lãng phí về thời gian và chất lượng. Vì vậy, can thiệp vào gốc rễ — tức nâng cao độ chính xác của quyết định nhập hàng — sẽ mang lại hiệu quả giảm lãng phí triệt để hơn so với chỉ xử lý hậu quả.

Theo báo cáo của FAO (2019) [1], khoảng **13% tổng sản lượng lương thực toàn cầu** bị mất hoặc lãng phỉ sau thu hoạch, trước và trong quá trình bán lẻ. Đây là con số được dùng như tham chiếu chung cho nghiên cứu về lãng phịch thực phẩm. Đối với Việt Nam, cần tra cứu số liệu cụ thể từ nguồn chính thống *(cần bổ sung)*.

---

## 2.2. Bài toán dự báo nhu cầu

### 2.2.1. Định nghĩa

Dự báo nhu cầu là quá trình ước lượng giá trị của một đại lượng chưa biết trong tương lai dựa trên dữ liệu quá khứ. Trong bài toán quản lý tồn kho, đối tượng cần dự báo là **nhu cầu bán hàng** — số lượng sản phẩm mà khách hàng sẽ mua trong một khoảng thời gian tương lai, tại một điểm bán cụ thể.

Hyndman & Athanasopoulos [2] phân biệt dự báo thành hai nhóm:

- **Dự báo định tính (qualitative forecasting):** dựa vào ý kiến chuyên gia, dự đoán của người quản lý. Phù hợp khi chưa có dữ liệu lịch sử, nhưng kém khách quan.
- **Dự báo định lượng (quantitative forecasting):** dựa vào dữ liệu lịch sử và mô hình toán học, có thể đo lường được độ chính xác.

Đề tài sử dụng dự báo định lượng làm nền tảng, đồng thời kết hợp định tính thông qua các quy tắc nghiệp vụ do người dùng nhập thủ công (ví dụ: sự kiện sắp diễn ra, chương trình khuyến mãi dự kiến).

### 2.2.2. Các yếu tố ảnh hưởng đến nhu cầu

Nhận diện yếu tố ảnh hưởng là nền tảng để chọn đúng mô hình dự báo. Trong bán lẻ thực phẩm, các yếu tố chính gồm:

| Yếu tố | Cơ chế tác động | Loại dữ liệu | Xử lý trong mô hình |
|---------|------------------|---------------|---------------------|
| **Mùa vụ (seasonality)** | Nhu cầu lặp lại theo chu kỳ tuần, tháng, năm | Ngày bán hàng | Từ khoá `weekly_seasonality`, `yearly_seasonality` trong Prophet; thành phần mùa vụ trong ARIMA |
| **Ngày lễ, Tết** | Nhu cầu tăng đột biến, đồng thời mất hàng ở ngày thường | Lịch lễ Việt Nam | Biến nhị phân (holiday) hoặc thêm regressor lịch |
| **Thời tiết** | Nắng nóng tăng nước giải khát, mưa giảm lượt khách | Dữ liệu khí tượng | Biến ngoại (exogenous variable) |
| **Khuyến mãi** | Giảm giá kích thích nhu cầu ngắn hạn, gây dịch chuyển nhu cầu từ tháng sau | Lịch khuyến mãi | Biến nhị phân (promotion) |
| **Ngày trong tuần** | Cuối tuần nhu cầu cao hơn ngày thường | Ngày trong tuần | Thành phần mùa vụ theo tuần |
| **Tình trạng tồn kho** | Hết hàng khiến doanh số bằng 0 dù nhu cầu có — dữ liệu bị nhiễu | Tồn kho lịch sử | Hiệu chỉnh (censored demand) |

Trong sáu yếu tố trên, yếu tố **tình trạng tồn kho** đặc biệt đáng lưu ý về mặt kỹ thuật: khi sản phẩm hết hàng, doanh số ghi nhận được bị cắt bởi ràng buộc tồn kho chứ không phải bởi nhu cầu thực. Nếu không hiệu chỉnh hiện tượng này, mô hình sẽ học được một mối liên hệ sai lệch — rằng "bán ít nghĩa là nhu cầu thấp" — và dự báo thấp hơn thực tế trong chu kỳ sau. Đây là một lỗi phổ biến và nghiêm trọng trong các dự án dự báo bán lẻ thực tế.

### 2.2.3. Các phương pháp dự báo truyền thống

**a) Phương pháp trung bình động (Moving Average — MA)**

Trung bình động dự báo giá trị tương lai bằng trung bình của *k* giá trị gần nhất:

$$\hat{y}_{t+1} = \frac{1}{k}\sum_{i=0}^{k-1} y_{t-i}$$

Ưu điểm: đơn giản, dễ hiểu, hiệu quả giảm nhiễu ngẫu nhiên. Nhược điểm: không phản ánh được xu hướng (trending) và biến động theo mùa vụ; khi độ biến động thay đổi, tham số *k* cố định không còn phù hợp.

**b) Phương pháp san bằng mũ (Exponential Smoothing — ES)**

Phương pháp này gán trọng số lớn hơn cho các quan sát gần đây:

$$\hat{y}_{t+1} = \alpha y_t + (1-\alpha)\hat{y}_{t}$$

Trong đó *α* (hệ số san bằng, 0 < α ≤ 1) quy định mức độ phản ứng với dữ liệu mới: α càng lớn thì mô hình càng nhạy cảm với biến động gần nhất.

Mở rộng của phương pháp này gồm ba dạng phổ biến:

| Dạng | Thành phần | Phù hợp với |
|------|------------|-------------|
| **SES** (Simple ES) | Mức trung bình | Chuỗi ổn định, không xu hướng, không mùa vụ |
| **Holt** | Mức + xu hướng | Chuỗi có xu hướng tăng/giảm rõ |
| **Holt-Winters** | Mức + xu hướng + mùa vụ | Chuỗi có cả xu hướng và mùa vụ |

Các phương pháp này là **đường cơ sở (baseline)** mà mọi mô hình phức tạp hơn đều phải so sánh cùng. Trong lĩnh vực dự báo, một mô hình phức tạp chỉ được coi là có giá trị nếu nó vượt trội baseline rõ rệt — nguyên tắc này được các chuyên gia khuyến nghị mạnh mẽ [2].

**c) Các phương pháp khác**

- **Phân tích phân rã (Decomposition):** tách chuỗi thành xu hướng, mùa vụ và nhiễu.
- **Phương pháp nhân quả (Causal / Regression):** sử dụng biến giải thích (giá, khuyến mãi, thời tiết) để dự báo. Phù hợp khi có dữ liệu biến giải thích, nhưng cần cẩn thận với tương quan nhân quả giả.

---

## 2.3. Các mô hình dự báo hiện đại

### 2.3.1. Mô hình ARIMA

**Cơ sở lý thuyết.** Mô hình ARIMA (AutoRegressive Integrated Moving Average) do Box và Jenkins phát triển [3] kết hợp ba thành phần: AR — hồi quy tự hồi quy, I — sai phân tích (tích phân), MA — trung bình động. Mô hình cơ bản có dạng:

$$\phi(B)(1-B)^d y_t = c + \theta(B)\varepsilon_t$$

Trong đó *B* là toán tử trễ, *(p, d, q)* lần lượt là bậc AR, bậc sai phân và bậc MA; *d* là bậc tích phân để đưa chuỗi về dạng dừng.

Đối với dữ liệu có tính mùa vụ, biến thể **SARIMA** bổ sung các thành phần mùa vụ theo chu kỳ *s*: SARIMA(p, d, q)(P, D, Q, s).

Quy trình sử dụng theo phương pháp Box-Jenkins gồm: kiểm tra tính dừng → xác định (p, d, q) qua biểu đồ ACF/PACF → ước lượng tham số → kiểm tra phần dư → dự báo.

**Ưu điểm:**
- Nền tảng toán học vững chắc, có cơ sở lý thuyết thống kê rõ ràng.
- Rất hiệu quả với chuỗi ngắn, tuyến tính, ổn định.
- Có khoảng tin cậy (confidence interval) cho dự báo.

**Nhược điểm:**
- Giả định **tính dừng** và **tương quan tuyến tính** giữa các độ trễ — dữ liệu bán lẻ hiếm khi thỏa mãn.
- Quy trình chọn tham số thủ công tốn công sức.
- Khó biểu diễn tác động của các sự kiện bất thường (ngày lễ, khuyến mãi) nếu không mã hóa thủ công.

### 2.3.2. Mô hình Prophet

**Cơ sở lý thuyết.** Prophet do Facebook (Meta) phát triển và được Taylor & Letham giới thiệu năm 2017 [4], sau đó công bố trên tạp chí *The American Statistician* năm 2018 [5]. Prophet phân tích chuỗi thời gian theo mô hình phân rã gồm bốn thành phần:

$$y(t) = g(t) + s(t) + h(t) + r(t)$$

- *g(t)*: xu hướng (tuyến tính hoặc phi tuyến/logistic), thay đổi theo điểm gãy (changepoint).
- *s(t)*: thành phần mùa vụ, mô hình hóa bằng chuỗi Fourier.
- *h(t)*: thành phần ngày lễ (holiday effects).
- *r(t)*: nhiễu, giả định phân phối Gaussian.

**Ưu điểm:**
- **Tự động phát hiện điểm gãy** (changepoint) trong xu hướng — rất quan trọng khi cửa hàng thay đổi quy mô, mở thêm chi nhánh hoặc đổi chiến lược.
- Xử lý **ngày lễ** thuận tiện thông qua tham số `holidays`.
- Tự động lựa chọn điểm gãy theo kiểm định thống kê.
- Giao diện lập trình đơn giản, dễ tích hợp; đồng thời cung cấp khoảng tin cậy.
- Đặc biệt hiệu quả với dữ liệu có mùa vụ rõ, thiếu dữ liệu và biến động phi tuyến.

**Nhược điểm:**
- Thành phần nhiễu giả định Gaussian, không phù hợp với chuỗi có nhiều giá trị bằng 0 (đặc trưng của hàng bán chạy không ổn định).
- Mặc định chỉ xử lý chuỗi đơn, không tận dụng được thông tin từ nhiều sản phẩm liên quan.
- Khó tùy biến sâu hơn so với mô hình thống kê cổ điển.

### 2.3.3. Mô hình XGBoost

**Cơ sở lý thuyết.** XGBoost (eXtreme Gradient Boosting) là thuật toán **gradient boosting** — xây dựng dự báo bằng cách hồi quy bước lần (boosting) trên một tập các cây quyết định, trong đó mỗi cây mới tập trung sửa lỗi của các cây trước đó. Thuật toán được đề xuất bởi Chen & Guestrin năm 2016 [6].

Hàm mục tiêu tối ưu gồm hai thành phần:

$$\mathcal{L}(t) = \sum_{i} l(y_i, \hat{y}_i^{(t-1)} + f_t(x_i)) + \Omega(f_t)$$

Trong đó *l* là hàm sai số, còn $\Omega(f_t)$ là thành phần điều chuẩn phạt độ phức tạp của cây. Thuật toán sử dụng **gradient đứng theo cấp (second-order gradient)** để xây dựng cây tối ưu, kết hợp phương pháp regularization (L1, L2, subsampling, column sampling) để kiểm soát overfitting. Triển khai dạng sparse-aware, có hỗ trợ xử lý dữ liệu thiếu tự nhiên.

**Ưu điểm:**
- **Hiệu năng dự báo vượt trội** trên nhiều bài toán dự báo chuỗi thời gian khi biến đích được xử lý thành bài toán hồi quy với các đặc trưng (feature engineering).
- Tự nhiên xử lý dữ liệu thiếu, không cần cấm hóa.
- Hỗ trợ mạnh mẽ **biến ngoại (exogenous features)**: lịch, ngày lễ, khuyến mãi, thời tiết — những yếu tố được nêu tại mục 2.2.2.
- Cho phép trích xuất **feature importance** để giải thích cho người quản lý — điểm cộng quan trọng trong bối cảnh quyết định kinh doanh.
- Hiệu năng tính toán tốt, mở rộng tốt với dữ liệu lớn.

**Nhược điểm:**
- Phụ thuộc mạnh vào chất lượng đặc trưng đầu vào; kỹ thuật tạo đặc trưng tốn công sức.
- Bản chất "hộp đen" khó giải thích hơn mô hình tuyến tính.
- Chủ yếu mô hình hóa quan hệ, **không tự xử lý thuộc tính chuỗi thời gian** như ARIMA/Prophet — cần tạo thủ công các đặc trưng độ trễ (lag features).

### 2.3.4. Mô hình Random Forest

**Cơ sở lý thuyết.** Random Forest do Leo Breiman đề xuất năm 2001 [7]. Mô hình xây dựng nhiều cây quyết định trên các tập dữ liệu con lấy ngẫu nhiên (bootstrap), mỗi cây sử dụng tập thuộc tính ngẫu nhiên tại mỗi nút, rồi lấy trung bình (hồi quy) hoặc phiếu chọn đa số (phân loại).

$$y_{t} = \frac{1}{B}\sum_{b=1}^{B} T_b(x)$$

**Ưu điểm:**
- Chống overfitting rất tốt nhờ việc trung bình nhiều cây độc lập.
- Sức chứa mô hình cao, có thể nắm bắt quan hệ phi tuyến phức tạp.
- Xử lý tốt dữ liệu thiếu và nhiễu, ít nhạy với tham số.
- Cung cấp giá trị **OOB (Out-of-Bag)** để đánh giá mà không cần tập kiểm tra riêng.

**Nhược điểm:**
- Tốc độ dự báo chậm hơn XGBoost (không tối ưu tăng tốc như gradient boosting tuần tự).
- **Không thể ngoại suy** ra ngoài phạm vi giá trị đã quan sát — đây là hạn chế nghiêm trọng cho bài toán dự báo, vì giá trị tương lai thường nằm ngoài phạm vi lịch sử.
- Dự báo có xu hướng co về phía giá trị trung bình (hiện tượng "thu nhỏ dự báo"), làm mất biên độ mùa vụ.

### 2.3.5. Mô hình LSTM

**Cơ sở lý thuyết.** LSTM (Long Short-Term Memory) là kiến trúc mạng nơ-ron hồi quy do Hochreiter & Schmidhuber đề xuất năm 1997 [8], được thiết kế để khắc phục hiện tượng biến mất gradient (vanishing gradient) trong RNN thông qua cơ chế **cổng (gate)**.

Kiến trúc LSTM duy trì ba loại trạng thái: trạng thái ô nhớ (*cell state* *cₜ*), cổng vào (*input gate*), cổng quên (*forget gate*) và cổng ra (*output gate*). Điểm mấu chốt là **cổng quên** cho phép mô hình chọn lọc thông tin nào nên quên, nhờ đó có thể giữ thông tin từ xa trong chuỗi dài.

**Ưu điểm:**
- Khả năng học phụ thuộc dài hạn, phù hợp với chuỗi có chu kỳ mùa vụ dài.
- Tự động trích xuất đặc trưng, giảm phụ thuộc vào feature engineering thủ công.
- Có thể xử lý tích hợp nhiều chuỗi liên quan.

**Nhược điểm:**
- **Cần lượng dữ liệu lớn** để huấn luyện ổn định — dữ liệu bán lẻ quy mô nhỏ thường không đủ.
- Tốc năng độc lập với thời gian, dễ overfit khi dữ liệu ít.
- Yêu cầu **tinh chỉnh siêu tham số** (learning rate, số lớp, số hidden unit) tốn nhiều công sức; kết quả không ổn định giữa các lần chạy.
- Khó giải thích, khó triển khai trên môi trường với tài nguyên hạn chế.

### 2.3.6. Bảng so sánh tổng hợp 5 mô hình

| Tiêu chí | ARIMA | Prophet | XGBoost | Random Forest | LSTM |
|----------|-------|---------|---------|----------------|------|
| **Loại mô hình** | Thống kê, tuyến tính | Thống kê phân rã | Học có giám sát, cây tăng cường | Học có giám sát, cấp đoàn | Học sâu, mạng nơ-ron hồi quy |
| **Khả năng nắm bắt mùa vụ** | Tốt (qua thành phần mùa vụ SARIMA) | **Rất tốt** (tự động, nhiều chu kỳ) | Tốt (nếu tạo đặc trưng lịch) | Khá (qua đặc trưng) | Rất tốt (nếu đủ dữ liệu) |
| **Xử lý biến ngoại** | Khó (phải thêm ARIMAX) | **Tốt** (regressor, holiday) | **Rất tốt** (mọi biến đều dùng được) | **Rất tốt** | Khá (phải lồng ghép cấu trúc) |
| **Lượng dữ liệu cần** | Trung bình | Thấp – Trung bình | Trung bình – Cao | Trung bình – Cao | **Rất cao** |
| **Độ chính xác (dữ liệu ít, mùa vụ rõ)** | Trung bình | **Cao** | Cao | Trung bình – Cao | Trung bình |
| **Độ chính xác (dữ liệu nhiều, có biến ngoài)** | Thấp – Trung bình | Trung bình | **Rất cao** | Cao | Cao |
| **Độ phức tạp triển khai** | Trung bình | **Thấp** | Trung bình | Thấp – Trung bình | **Cao** |
| **Khả năng giải thích** | **Tốt** (hệ số ý nghĩa) | Khá (thành phần phân rã) | Khá (feature importance) | Khá (feature importance) | **Kém** |
| **Khả năng ngoại suy** | **Tốt** | Tốt | Tốt | **Kém** | Tốt |
| **Rủi ro overfitting** | Thấp | Thấp | Trung bình | Thấp | **Cao** |
| **Khả năng cập nhật dữ liệu mới** | Cần huấn luyện lại | Dễ — tăng dần dữ liệu | Cần huấn luyện lại | Cần huấn luyện lại | Cần huấn luyện lại |

**Định hướng lựa chọn cho đề tài.** Dựa trên đặc thù dữ liệu bán lẻ quy mô vừa và nhỏ tại Việt Nam — vừa có tính mùa vụ rõ, vừa thiếu dữ liệu lịch sử dài hạn, đồng thời cần dễ diễn giải cho người quản lý không chuyên kỹ thuật — đề tài lựa chọn:

- **Prophet** làm mô hình cơ sở (baseline), nhờ khả năng tự động xử lý mùa vụ, ngày lễ và điểm gãy với lượng dữ liệu vừa phải.
- **XGBoost** làm mô hình chính, tận dụng tối đa các đặc trưng nghiệp vụ (lịch, khuyến mãi, giá, thời tiết) và khả năng trích xuất feature importance phục vụ giải thích quyết định.
- **ARIMA** và phương pháp **trung bình động** được dùng làm nhóm đối chứng để đánh giá mức độ cải thiện.

Việc đánh giá thực nghiệm so sánh hiệu năng của các mô hình được trình bày tại Chương 4.

---

## 2.4. Các nghiên cứu liên quan

> **Lưu ý quan trọng:** Các nội dung dưới đây mô tả **những hướng nghiên cứu điển hình** đang được quan tâm trong lĩnh vực dự báo nhu cầu bán lẻ. Vì đồ án được thực hiện với điều kiện tra cứu hạn chế và không thể xác minh tên tác giả, năm xuất bản cùng toạ độ bài báo, **sinh viên cần tra cứu lại nguồn gốc chính xác** từ các cơ sở dữ liệu như Google Scholar, IEEE Xplore, ScienceDirect hoặc thư viện của trường trước khi nộp báo cáo. Các tên bài, tác giả và kết luận cụ thể phải được đối chiếu với bản gốc.

### 2.4.1. Hướng nghiên cứu 1 — Mô hình thống kê cổ điển cho chuỗi bán lẻ

**Mô tả:** Đây là hướng nghiên cứu lâu đời và nền tảng nhất. Các nghiên cứu trong nhóm này áp dụng ARIMA, SARIMA, phân tích phân rã và các phương pháp san bằng mũ để dự báo nhu cầu sản phẩm theo ngày hoặc tuần, thường dựa trên dữ liệu bán hàng lịch sử của một hoặc một số cửa hàng.

**Điểm mạnh:**
- Nền tảng lý thuyết chắc chắn, quy trình xây dựng mô hình rõ ràng, dễ kiểm chứng.
- Giải thích được các hệ số, thuận tiện trong việc trình bày với người quản lý.
- Hoạt động hiệu quả với chuỗi ổn định và dữ liệu ngắn.

**Điểm yếu:**
- Giả định tính dừng và tuyến tính thường không phù hợp với dữ liệu bán lẻ thực tế.
- Khó xử lý các biến tác động bên ngoài như khuyến mãi, thời tiết, ngày lễ mà không cần can thiệp thủ công.
- Độ chính xác có xu hướng thấp hơn khi có nhiều biến cần giải thích.

### 2.4.2. Hướng nghiên cứu 2 — Phương pháp học sâu trên chuỗi thời gian

**Mô tả:** Nhóm nghiên cứu này sử dụng các kiến trúc học sâu như LSTM, GRU, và các biến thể hiện đại hơn như DeepAR, Temporal Fusion Transformer. Các mô hình này tự động học biểu diễn đặc trưng từ dữ liệu thô thay vì phụ thuộc vào thiết kế đặc trưng thủ công, và thường được áp dụng cho các bài toán dự báo đa chuỗi hoặc dự báo có phân phối xác suất.

**Điểm mạnh:**
- Nắm bắt được phụ thuộc dài hạn và quan hệ phức tạp trong chuỗi.
- Hiệu năng rất cao khi có đủ dữ liệu, đặc biệt với bài toán đa chuỗi.
- Có thể mô hình hóa phân phối xác suất của nhu cầu, hỗ trợ tính tồn kho an toàn.

**Điểm yếu:**
- Đòi hỏi lượng dữ liệu lớn — điều kiện khó đáp ứng với quy mô dữ liệu của đơn vị vừa và nhỏ.
- Tính "hộp đen" khiến khó giải thích cho người ra quyết định kinh doanh.
- Tài nguyên tính toán và thời gian huấn luyện đáng kể.
- Nguy cơ overfitting cao khi dữ liệu ít hoặc phân bố thay đổi.

### 2.4.3. Hướng nghiên cứu 3 — Gradient Boosting Tree với đặc trưng lịch

**Mô tả:** Nhóm nghiên cứu này chuyển bài toán dự báo chuỗi thời gian thành bài toán hồi quy bằng cách tạo ra các đặc trưng như giá trị độ trễ (lag features), giá trị trung bình động, chỉ báo ngày lễ, cờ khuyến mãi, điều kiện thời tiết. Các thuật toán XGBoost, LightGBM, CatBoost thường cho kết quả rất tốt trong cấu hình này và ngày càng phổ biến trong cộng đồng khoa học dữ liệu, đặc biệt sau các cuộc thi dự báo như Kaggle *(cần đối chiếu tên cuộc thi và kết quả cụ thể nếu đưa vào báo cáo)*.

**Điểm mạnh:**
- Hiệu năng dự báo rất cao, thường vượt trội so với mô hình thống kê cổ điển.
- Tận dụng được hiệu quả các biến ngoại (khuyến mãi, thời tiết, giá).
- Cho phép trích xuất feature importance hỗ trợ giải thích.
- Có thể dự báo được chuỗi có nhiều điểm không liên tục, giá trị bằng 0.

**Điểm yếu:**
- Chất lượng phụ thuộc vào công sức thiết kế đặc trưng, khó tái lập nếu thiếu tài liệu.
- Không mô hình hóa trực tiếp cấu trúc phụ thuộc thời gian.
- Cần đánh giá cẩn thận để tránh rò rỉ dữ liệu (data leakage) khi tạo đặc trưng độ trễ.

### 2.4.4. Hướng nghiên cứu 4 — Liên kết dự báo với tối ưu tồn kho

**Mô tả:** Hướng nghiên cứu này không dừng lại ở dự báo mà đi sâu vào bài toán quyết định tối ưu lượng đặt hàng, thường được hình thức hóa theo **bài toán nhà bán lẻ đơn kỳ (newsvendor)** hoặc các mô hình tối ưu tồn kho đa kênh. Các nghiên cứu dạng này chỉ ra rằng: **dự báo chính xác hơn chưa chắc dẫn đến lợi nhuận cao hơn** nếu không gắn với hàm chi phí lãng phí cụ thể. Khi tồn kho dư đặt quá tốn kém, dự báo "vừa đủ" có thể là dự báo hợp lý nhất.

**Điểm mạnh:**
- Trực tiếp phục vụ mục tiêu giảm lãng phí chứ không chỉ tối ưu sai số dự báo.
- Phù hợp với đặc thù thực phẩm có hạn sử dụng ngắn.
- Có cơ sở lý thuyết toán học vững chắc.

**Điểm yếu:**
- Hàm chi phí cần được hiệu chuẩn theo từng đơn vị, thường khó ước lượng chính xác.
- Nhiều mô hình giả định biết trước phân phối nhu cầu, thực tế thường không hoàn toàn đúng.
- Phức tạp về mặt toán học so với mức độ năng lực thực tế của đơn vị vừa và nhỏ.

### 2.4.5. Hướng nghiên cứu 5 — Tích hợp dữ liệu ngoài (thời tiết, sự kiện, dữ liệu xã hội)

**Mô tả:** Nghiên cứu trong nhóm này tích hợp dữ liệu bên ngoài vào mô hình dự báo: dữ liệu khí tượng học, lịch nghỉ lễ, dữ liệu từ mạng xã hội, dữ liệu vị trí địa lý. Hướng tiếp cận này nhận được nhiều kết quả tích cực, đặc biệt với ngành thực phẩm nơi thời tiết và dịp lễ có ảnh hưởng rõ rệt đến nhu cầu.

**Điểm mạnh:**
- Cải thiện đáng kể độ chính xác dự báo, đặc biệt ở các thời điểm bất thường.
- Tạo lợi thế cạnh tranh khó sao chép vì phụ thuộc vào nguồn dữ liệu riêng của doanh nghiệp.

**Điểm yếu:**
- Chi phí thu thập, làm sạch và đồng bộ dữ liệu ngoài khá cao.
- Vấn đề tính dụng của dữ liệu khi kết hợp nhiều nguồn.
- Rủi ro "tương quan giả" khi chu kỳ dài hạn bị lẫn vào quan hệ nhân quả.

### 2.4.6. Khoảng trống nghiên cứu mà đề tài hướng tới

Từ việc tổng hợp các hướng nghiên cứu trên, đề tài nhận thấy một số **khoảng trống** mà một hệ thống thực tiễn dành cho đơn vị bán lẻ quy mô vừa và nhỏ tại Việt Nam vẫn còn thiếu:

| Khoảng trống | Biểu hiện trong thực tế | Hướng giải quyết của đồ án |
|---------------|--------------------------|----------------------------|
| **Thiếu hệ thống tích hợp** | Các công cụ dự báo thường đứng riêng lẻ, không gắn với quản lý kho thực tế | Xây dựng nền tảng tích hợp: dự báo → gợi ý nhập hàng → cảnh báo hết hạn trong một hệ thống |
| **Dự báo chưa gắn với quyết định** | Mô hình chỉ dự báo số lượng, không đề xuất được lượng nhập | Tích hợp thuật toán gợi ý nhập hàng xét tồn kho, hạn sử dụng, chi phí và giá bán |
| **Thiếu lớp trợ lý hỏi đáp trực quan** | Người quản lý phải biết thống kê mới đọc được dữ liệu | Xây dựng AI Agent chatbot tra cứu bằng ngôn ngữ tự nhiên |
| **Thiếu cập nhật real-time** | Báo cáo tổng hợp chỉ cập nhật khi mở trang, phản hồi chậm | Sử dụng WebSocket đẩy cảnh báo và tồn kho tức thì |
| **Thiếu dữ liệu thực tế về ngành** | Phần lớn nghiên cứu dùng dữ liệu bán lẻ nước ngoài có hành vi mua khác | Áp dụng mô hình trên dữ liệu bán lẻ Việt Nam với đặc thù ngày lễ Tết, khí hậu nhiệt đới |
| **Thiếu khả năng giải thích** | Mô hình học sâu không giải thích được vì sao đề xuất con số đó | Sử dụng XGBoost kết hợp phân tích feature importance |

Đề tài không đặt mục tiêu phá vỡ kỷ lục độ chính xác, mà hướng tới giải quyết **khoảng trống khả thi**: xây dựng một hệ thống hoàn chỉnh, dễ triển khai, có thể vận hành trong điều kiện dữ liệu và năng lực của đơn vị bán lẻ vừa và nhỏ, đồng thời kết nối được dự báo với quyết định nhập hàng cụ thể.

---

## 2.5. Công nghệ sử dụng

### 2.5.1. FastAPI — Framework Backend

FastAPI là framework web hiện đại dành cho Python, dựa trên tiêu chuẩn OpenAPI và ASGI. Đề tài chọn FastAPI vì các lý do sau:

- **Tốc độ và hiệu năng cao:** FastAPI dựa trên ASGI server (Uvicorn) và xử lý đồng bộ thông qua cơ chế `async`/`await`, cho hiệu năng tương đương Node.js trong các tác vụ I/O-bound *(cần đối chiếu với kết quả benchmark cụ thể nếu cần trích dẫn)*.
- **Tự sinh tài liệu API tự động:** FastAPI tự động tạo Swagger UI tại `/docs` và ReDoc tại `/redoc`, giúp giảm đáng kể công sức viết tài liệu — đối với đồ án cá nhân đây là lợi thế rõ rệt.
- **Kiểm tra dữ liệu tích hợp:** Sử dụng Pydantic để định nghĩa và kiểm tra dữ liệu đầu vào/ra, giúp phát hiện lỗi sớm.
- **Hỗ trợ WebSocket native:** Điều này đặc biệt quan trọng đối với yêu cầu real-time của đề tài — có thể mở rộng ứng dụng FastAPI hiện tại thành WebSocket server mà không cần thêm framework khác.
- **Chuẩn Python type hint:** Giúp mã nguồn dễ đọc, dễ bảo trì và có trải nghiệm phát triển tốt.
- **Hệ sinh thái Python phong phú:** Tận dụng được trực tiếp các thư viện khoa học dữ liệu (pandas, scikit-learn, Prophet, XGBoost) mà không cần cầu nối ngôn ngữ.

### 2.5.2. React — Framework Frontend

React là thư viện JavaScript do Meta phát triển, theo kiến trúc dựa trên thành phần (component-based). Đề tài chọn React kết hợp Vite và Tailwind CSS:

- **Kiến trúc dựa trên thành phần:** Phù hợp với hệ thống có nhiều màn hình chức năng (dashboard, danh sách sản phẩm, biểu đồ dự báo, chatbot) với nhiều thành phần dùng lại như bảng dữ liệu, thẻ cảnh báo, biểu đồ.
- **Hệ sinh thái lớn:** Có sẵn thư viện hỗ trợ biểu đồ như Recharts, Chart.js; thư viện bảng như TanStack Table; thư viện gọi API như Axios hoặc TanStack Query.
- **Cộng đồng lớn, tài liệu phong phú:** Thuận lợi cho việc tự học và tra cứu khi gặp vấn đề.
- **Vite:** Công cụ build hiện đại với thời gian khởi động máy chủ phát triển gần như tức thì (HMR), cải thiện đáng kể trải nghiệm phát triển so với webpack truyền thống.
- **Tailwind CSS:** Utility-first CSS giúp dựng giao diện nhanh, nhất quán, dễ tùy chỉnh, phù hợp với yêu cầu xây dựng giao diện dashboard nhiều biểu đồ.
- **Khả năng tích hợp WebSocket:** Hỗ trợ kết nối real-time tự nhiên thông qua API `WebSocket` của trình duyệt, kết hợp React hook để quản lý vòng đời kết nối.

### 2.5.3. PostgreSQL — Hệ quản trị cơ sở dữ liệu

PostgreSQL là hệ quản trị cơ sở dữ liệu quan hệ mã nguồn mở. Đề tài chọn PostgreSQL với các lý do:

- **Quan hệ đầy đủ:** Phù hợp với lược đồ dữ liệu có nhiều thực thể liên kết (sản phẩm – danh mục – giao dịch – hạn sử dụng), bảo đảm tính nhất quán qua khóa ngoại và ràng buộc toàn vẹn tham chiếu.
- **Chuẩn ACID:** Đảm bảo tính chính xác của dữ liệu tồn kho — yêu cầu bắt buộc với nghiệp vụ kho hàng.
- **Tối ưu truy vấn chuỗi thời gian:** Hỗ trợ chỉ mục B-tree, range partitioning và các kiểu dữ liệu chuyên dụng phù hợp cho phân tích dữ liệu bán hàng theo thời gian.
- **Kiểu dữ liệu phong phú:** Hỗ trợ `NUMERIC` cho số lượng chính xác, `JSONB` cho lưu trữ cấu hình linh hoạt, các kiểu ngày giờ đầy đủ.
- **Mã nguồn mở và miễn phí:** Giảm chi phí vận hành, phù hợp với ngân sách đồ án.
- **Quản lý bằng công cụ quen thuộc:** `psql` dễ sử dụng, có giao diện đồ họa pgAdmin hỗ trợ trực quan.
- **Tương thích tốt với SQLAlchemy:** ORM được sử dụng trong đề tài hỗ trợ PostgreSQL đầy đủ tính năng, giúp viết mã an toàn, tránh SQL injection.

### 2.5.4. Prophet và XGBoost — Bộ thư viện học máy

**Prophet** được chọn làm mô hình dự báo cơ sở vì những đặc điểm đã phân tích tại mục 2.3.2: tự động phát hiện điểm gãy, xử lý tốt mùa vụ đa chu kỳ và ngày lễ, đồng thời tốn ít thời gian cấu hình — yếu tố quan trọng khi hệ thống cần được tái huấn luyện định kỳ mà không cần can thiệp chuyên sâu của chuyên gia.

**XGBoost** được chọn làm mô hình dự báo chính vì: hiệu năng cao trên dữ liệu bán lẻ có nhiều biến ngoài, hỗ trợ xử lý dữ liệu thiếu tự nhiên, và quan trọng nhất là **cho phép trích xuất feature importance** — giúp hệ thống giải thích được yếu tố nào chi phối nhu cầu, từ đó hỗ trợ người quản lý tin tưởng vào khuyến nghị của hệ thống.

Cả hai thư viện đều có giao diện tương thích **scikit-learn**, cho phép tích hợp vào quy trình tự động và so sánh công bằng trên cùng một tập dữ liệu kiểm tra.

### 2.5.5. WebSocket — Truyền thông thời gian thực

WebSocket là giao thức truyền thông song song dựa trên TCP, duy trì kết nối liên tục hai chiều giữa client và server *(theo mô hình chuẩn WebSocket, RFC 6455)*. Đề tài sử dụng WebSocket cho các trường hợp:

| Tình huống | Cách WebSocket giải quyết |
|------------|---------------------------|
| Hàng sắp hết hạn | Khi giao dịch nhập/xuất làm thay đổi trạng thái hạn sử dụng, server đẩy thông báo ngay tới màn hình đang mở |
| Tồn kho vượt ngưỡng | Cập nhật số tồn ngay khi giao dịch hoàn tất, không cần tải lại trang |
| Kết quả dự báo mới | Đẩy kết quả dự báo tới giao diện theo thời gian thực sau khi mô hình cập nhật |

So với phương pháp polling (frontend định kỳ gọi API), WebSocket có ưu điểm giảm tải cho server, độ trễ thấp hơn và trải nghiệm người dùng mượt mà hơn. Đây là yếu tố khác biệt quan trọng về mặt trải nghiệm so với phần lớn hệ thống quản lý kho thông thường.

### 2.5.6. Gemini API — Trợ lý AI Agent

Gemini là dòng mô hình ngôn ngữ lớn (LLM) do Google phát triển, cung cấp API cho phép tích hợp khả năng hiểu và tạo văn bản vào ứng dụng. Đề tài sử dụng Gemini API để xây dựng AI Agent chatbot với các chức năng:

- **Truy vấn dữ liệu bằng ngôn ngữ tự nhiên:** Người dùng hỏi *"Sản phẩm nào sắp hết hạn tuần này?"* thay vì phải biết lọc theo bộ lọc nào.
- **Diễn giải kết quả dự báo:** Giải thích ý nghĩa của kết quả dự báo và đề xuất nhập hàng bằng ngôn ngữ dễ hiểu.
- **Tư vấn nghiệp vụ:** Hỗ trợ trả lời các câu hỏi về quy trình quản lý tồn kho, cách đọc dashboard.

Cơ chế hoạt động của AI Agent trong đề tài: câu hỏi của người dùng kết hợp với **ngữ cảnh dữ liệu lấy từ cơ sở dữ liệu** (tồn kho, hạn sử dụng, kết quả dự báo) được gửi tới Gemini API, mô hình sinh câu trả lời dựa trên ngữ cảnh đó. Cách tiếp cận này — gọi là **RAG đơn giản hóa (grounding)** — giúp hạn chế tình trạng mô hình "bịa" số liệu, một hạn chế cố hữu khi dùng LLM độc lập.

> **Lưu ý:** Việc sử dụng Gemini API trong đồ án cần xem xét kỹ điều khoản sử dụng, giới hạn tần suất gọi miễn phí và yêu cầu bảo mật khóa API. Trong trường hợp không thể sử dụng dịch vụ đám mây do điều kiện môi trường, cần chuẩn bị phương án thay thế *(ghi rõ phương án dự phòng tại Chương 5)*.

---

## 2.6. Tổng kết chương

Chương 2 đã trình bày cơ sở lý thuyết làm nền tảng cho việc phân tích, thiết kế và triển khai hệ thống. Cụ thể:

**Về nghiệp vụ:** Chương này đã làm rõ khái niệm chuỗi cung ứng bán lẻ và đặc điểm riêng của chuỗi cung ứng thực phẩm tươi sống — đặc biệt là hạn sử dụng hữu hạn khiến tồn kho trở thành tài sản bị hao hụt theo thời gian. Ba nhóm lãng phịch (về số lượng, thời gian, chất lượng) được phân tích cùng mối quan hệ nhân quả, từ đó khẳng định nhu cầu can thiệp vào gốc rễ vấn đề là nâng cao độ chính xác của quyết định nhập hàng.

**Về bài toán dự báo:** Dự báo nhu cầu được định nghĩa cùng với sáu yếu tố ảnh hưởng chủ yếu (mùa vụ, ngày lễ, thời tiết, khuyến mãi, ngày trong tuần, tình trạng tồn kho). Đặc biệt, hiện tượng tồn kho cắt bỏ dữ liệu doanh số (censored demand) được chỉ ra là lỗi phổ biến có ảnh hưởng nghiêm trọng đến độ chính xác. Các phương pháp truyền thống như trung bình động và san bằng mũ được trình bày và được xem là đường cơ sở để so sánh.

**Về mô hình:** Năm mô hình đại diện — ARIMA, Prophet, XGBoost, Random Forest và LSTM — được phân tích theo cơ sở lý thuyết, ưu điểm và nhược điểm. Bảng so sánh tổng hợp trên mười tiêu chí cho thấy không có mô hình nào vượt trội tuyệt đối; sự lựa chọn phụ thuộc vào đặc thù dữ liệu và yêu cầu đặc biệt. Dựa trên đặc thù dữ liệu bán lẻ quy mô vừa và nhỏ tại Việt Nam, đề tài lựa chọn **Prophet làm mô hình cơ sở** và **XGBoost làm mô hình chính**.

**Về nghiên cứu liên quan:** Năm hướng nghiên cứu điển hình đã được tổng hợp cùng đánh giá điểm mạnh, điểm yếu. Từ đó, đề tài xác định sáu khoảng trống nghiên cứu mà một hệ thống thực tiễn dành cho đơn vị bán lẻ vừa và nhỏ cần giải quyết — trong đó khoảng trống cốt lõi là việc **kết nối dự báo với quyết định nhập hàng cụ thể** trong một hệ thống tích hợp.

**Về công nghệ:** Mỗi công nghệ được chọn đều gắn với lý do cụ thể: FastAPI cho hiệu năng, tự sinh tài liệu API và hỗ trợ WebSocket native; React cho kiến trúc thành phần và hệ sinh thái; PostgreSQL cho tính nhất quất ACID và năng lực truy vấn chuỗi thời gian; Prophet/XGBoost cho đặc thù bài toán; WebSocket cho trải nghiệm real-time; Gemini API cho lớp trợ lý ngôn ngữ tự nhiên.

Cơ sở lý thuyết đã xây dựng tại chương này sẽ được vận dụng cụ thể trong **Chương 3 — Phân tích và thiết kế hệ thống**, nơi các mô hình và công nghệ đã khảo sát sẽ được chuyển thành yêu cầu chức năng, lược đồ cơ sở dữ liệu, thiết kế API và mô hình hóa nghiệp vụ cụ thể.

---

## Tài liệu tham khảo của chương

| Mã | Tài liệu |
|-----|----------|
| [1] | FAO (2019), *The State of Food and Agriculture 2019: Moving forward on food loss and waste reduction*, Rome. |
| [2] | Hyndman, R.J. & Athanasopoulos, G. (2021), *Forecasting: Principles and Practice*, 3rd edition, OTexts, Melbourne. |
| [3] | Box, G.E.P., Jenkins, G.M., Reinsel, G.C. & Ljung, G.M. (2015), *Time Series Analysis: Forecasting and Control*, 5th edition, Wiley. |
| [4] | Taylor, S.J. & Letham, B. (2017), *Forecasting at Scale*, arXiv preprint. |
| [5] | Taylor, S.J. & Letham, B. (2018), *Forecasting at Scale*, *The American Statistician*, 72(1), pp. 37–45. |
| [6] | Chen, T. & Guestrin, C. (2016), *XGBoost: A Scalable Tree Boosting System*, Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining, pp. 785–794. |
| [7] | Breiman, L. (2001), *Random Forests*, *Machine Learning*, 45(1), pp. 5–32. |
| [8] | Hochreiter, S. & Schmidhuber, J. (1997), *Long Short-Term Memory*, *Neural Computation*, 9(8), pp. 1735–1780. |

> **Ghi chú về tài liệu tham khảo:**
> - Các tài liệu [1] đến [8] là nguồn gốc chính thống của các mô hình và phương pháp được trình bày, được dùng để định hướng nội dung lý thuyết.
> - Thông tin xuất bản (tập, số, trang) của các bài báo [5], [6], [7], [8] cần được **đối chiếu lại với bản gốc** trước khi nộp báo cáo.
> - Danh mục đầy đủ sẽ được bổ sung tại phần cuối báo cáo, thư mục `docs/05-tham-khao/`.
> - Các nghiên cứu được đề cập tại mục 2.4 là **hướng nghiên cứu điển hình**, chưa gắn với bài báo cụ thể — cần tra cứu và ghi rõ nguồn trích dẫn trước khi nộp.
