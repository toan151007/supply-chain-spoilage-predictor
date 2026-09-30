# CHƯƠNG 1: TỔNG QUAN ĐỀ TÀI

## 1.1. Đặt vấn đề

Ngành bán lẻ thực phẩm và dịch vụ ăn uống (F&B) tại Việt Nam đang trong giai đoạn mở rộng nhanh, đặc biệt là mô hình cửa hàng tiện lợi (convenience store) và chuỗi nhà hàng thức ăn nhanh. Trong bối cảnh cạnh tranh khốc liệt về giá và chất lượng, hiệu quả quản lý tồn kho trở thành một trong những yếu tố quyết định lợi nhuận của doanh nghiệp. Tuy nhiên, phần lớn các đơn vị quy mô nhỏ và vừa tại Việt Nam vẫn tổ chức hoạt động nhập hàng dựa trên kinh nghiệm trực giác của chủ cửa hàng hoặc quản lý, chưa có hệ thống hỗ trợ ra quyết định dựa trên dữ liệu.

Thực trạng phổ biến có thể khái quát qua một số đặc điểm sau:

- **Ước lượng nhu cầu mang tính kinh nghiệm:** Quyết định nhập hàng phần lớn dựa vào trải nghiệm cá nhân, "cảm tính" về mùa vụ và tình hình kinh doanh gần đây. Phương pháp này đơn giản, chi phí thấp nhưng độ chính xác phụ thuộc nhiều vào năng lực và kinh nghiệm cá nhân của người quyết định.
- **Phản ứng chậm với biến động thị trường:** Khi có biến động bất thường (ngày lễ tết, thay đổi thời tiết, chương trình khuyến mãi đối thủ, thay đổi thói quen tiêu dùng), lượng nhập không được điều chỉnh kịp thời.
- **Thiếu dữ liệu tập trung:** Dữ liệu bán hàng, tồn kho và hạn sử dụng thường được ghi chép rời rạc trên sổ tay, file Excel cục bộ hoặc phần mềm bán hàng độc lập, khiến việc tổng hợp và phân tích xu hướng rất khó khăn.
- **Không có cảnh báo chủ động:** Phần lớn các hệ thống quản lý hiện có chỉ cung cấp thông tin tồn kõ hiện tại mà không chủ động cảnh báo khi sản phẩm sắp hết hạn hoặc tồn kho vượt ngưỡng an toàn.

Vấn đề cốt lõi của phương pháp nhập hàng theo kinh nghiệm thể hiện rõ trong hai chiều đối lập:

| Hình thức | Hậu quả trực tiếp | Hậu quả tài chính |
|----------|-------------------|-------------------|
| **Nhập dư** (nhập nhiều hơn nhu cầu thực tế) | Sản phẩm tích tụ tồn kho, đến hạn sử dụng mà chưa kịp bán; chất lượng suy giảm đối với sản phẩm tươi sống; phải tiêu hủy, giảm giá hoặc chuyển nhượng | Mất trực tiếp giá trị hàng hóa, tăng chi phí xử lý, chiếm vốn và mặt bằng kho |
| **Nhập thiếu** (nhập ít hơn nhu cầu) | Hết hàng bán trước, ảnh hưởng trải nghiệm khách hàng; đặc biệt nghiêm trọng với món ăn, nguyên liệu đầu vào | Mất doanh thu, mất khách hàng, đánh cạnh tranh bất lợi |

Điểm đáng chú ý là đối với ngành thực phẩm tươi sống, hai rủi ro này thường xuất hiện đồng thời và bù trừ cho nhau theo chu kỳ: những lần nhập dư dẫn đến tiêu hủy, buộc người quản lý "siết" lượng nhập ở lần sau, lại dẫn đến thiếu hàng. Kết quả là chu kỳ này lặp lại liên tục, tạo ra biến động tồn kho lớn và làm tổng chi phí vận hành tăng cao.

Về quy mô lãng phí thực phẩm, các tổ chức quốc tế đã đưa ra nhiều con số ước tính đáng chú ý. Báo cáo của Hiệp ước Lương thực và Nông nghiệp (FAO) cho biết khoảng **13% tổng sản lượng lương thực toàn cầu bị mất hoặc lãng ph** (FAO, 2019) [1]. Đối với Việt Nam, các số liệu liên quan đến chi phí lãng phí thực phẩm trong chuỗi cung ứng còn khá phân tán giữa các nguồn và phương pháp thống kê khác nhau *(cần bổ sung số liệu cụ thể từ nguồn chính thống của Việt Nam, ưu tiên số liệu từ Tổng cục Thống kê, Cục Chế biến và Phát triển thị trường nông nghiệp hoặc các bài báo khoa học uy tín)*. Do đó, trong phạm vi đồ án này, các số liệu tham khảo được sử dụng với vai trò minh họa cho tính nghiêm trọng của vấn đề, không dùng làm cơ sở định lượng chính xác.

Ngoài lãng phí trực tiếp, lãng phí thực phẩm còn kéo theo nhiều chi phí gián tiếp: chi phí xử lý và tiêu hủy, chi phí vận chuyển phát sinh, chi phí nhân sự theo dõi, và ảnh hưởng tiêu cực đến uy tín thương hiệu đối với khách hàng nhạy cảm về vấn đề an toàn thực phẩm. Đây chính là lý do nhiều doanh nghiệp bán lẻ đầu tư vào công nghệ quản lý chuỗi cung ứng.

Từ thực tiễn trên, có thể nhận thấy nhu cầu cấp thiết về một hệ thống có khả năng:

1. **Thu thập và tập trung hóa dữ liệu** về sản phẩm, tồn kho, giao dịch nhập xuất và hạn sử dụng.
2. **Phân tích xu hướng dữ liệu** để dự báo nhu cầu thay vì dựa vào kinh nghiệm chủ quan.
3. **Chủ động cảnh báo** người quản lý về rủi ro hết hạn và tồn kho bất thường.
4. **Hỗ trợ ra quyết định nhập hàng** bằng gợi ý số lượng dựa trên dự báo kho học.

Đây chính là cơ sở để đề xuất đề tài: **"Xây dựng nền tảng Quản trị Chuỗi cung ứng Chống lãng phí (Supply Chain Spoilage Predictor) cho chuỗi cửa hàng bán lẻ/F&B"**.

---

## 1.2. Mục tiêu nghiên cứu

### 1.2.1. Mục tiêu chung

Xây dựng một nền tảng quản trị chuỗi cung ứng chống lãng phí hoàn chỉnh, tích hợp ba năng lực cốt lõi: **quản lý dữ liệu vận hành**, **dự báo nhu cầu bằng học máy** và **hỗ trợ ra quyết định bằng trí tuệ nhân tạo**, nhằm giảm tỷ lệ lãng phí thực phẩm và tối ưu hiệu quả vận hành cho chuỗi cửa hàng bán lẻ và F&B quy mô vừa và nhỏ.

### 1.2.2. Mục tiêu cụ thể giai đoạn 1 — Nền tảng quản lý

Giai đoạn 1 tập trung xây dựng nền tảng dữ liệu và các chức năng quản lý cơ bản, tạo nền tảng dữ liệu cho giai đoạn 2:

| STT | Mục tiêu | Mô tả kết quả cần đạt |
|-----|----------|----------------------|
| 1 | Xây dựng cơ sở dữ liệu quan hệ | Thiết kế và hiện thực hóa lược đồ cơ sở dữ liệu PostgreSQL cho sản phẩm, kho, giao dịch, hạn sử dụng |
| 2 | Quản lý sản phẩm | Cho phép thêm, sửa, xóa, tra cứu thông tin sản phẩm bao gồm mã, tên, loại, đơn vị tính, hạn sử dụng |
| 3 | Quản lý kho hàng | Ghi nhận và theo dõi giao dịch nhập xuất, cập nhật tồn kho theo thời gian thực |
| 4 | Quản lý hạn sử dụng | Theo dõi ngày hết hạn, phân loại sản phẩm theo mức độ rủi ro hết hạn |
| 5 | Import dữ liệu Excel | Hỗ trợ nhập dữ liệu sản phẩm, tồn kho từ file Excel để giảm thời gian nhập liệu thủ công |
| 6 | Xây dựng dashboard | Hiển thị biểu đồ tổng quan: tồn kho, giá trị tồn kho theo hạn sử dụng, sản phẩm bán chạy |
| 7 | Hệ thống cảnh báo | Tự động cảnh báo sản phẩm sắp hết hạn, tồn kho dưới ngưỡng tối thiểu hoặc vượt ngưỡng tối đa |

### 1.2.3. Mục tiêu cụ thể giai đoạn 2 — Dự báo và trí tuệ nhân tạo

Giai đoạn 2 xây dựng trên nền tảng dữ liệu của giai đoạn 1, bổ sung các năng lực phân tích dự báo và hỗ trợ quyết định:

| STT | Mục tiêu | Mô tả kết quả cần đạt |
|-----|----------|----------------------|
| 1 | Xây dựng mô hình dự báo nhu cầu | Huấn luyện và đánh giá các mô hình ARIMA, Prophet, XGBoost trên dữ liệu lịch sử bán hàng |
| 2 | Đề xuất số lượng nhập hàng | Kết hợp kết quả dự báo nhu cầu với dữ liệu tồn kho, hạn sử dụng, chi phí và giá bán để tính toán gợi ý nhập hàng tối ưu |
| 3 | Xây dựng AI Agent chatbot | Tích hợp Gemini API xây dựng trợ lý ảo trả lời câu hỏi về tình trạng kho, tồn kho, doanh thu và đề xuất nhập hàng bằng ngôn ngữ tự nhiên |
| 4 | Cập nhật dữ liệu real-time | Sử dụng WebSocket để đẩy thông báo cảnh báo và cập nhật tồn kho đến giao diện mà không cần tải lại trang |
| 5 | Đánh giá hiệu quả mô hình | So sánh độ chính xác của các mô hình dự báo trên các chỉ số RMSE, MAE, MAPE và lựa chọn mô hình phù hợp nhất |

---

## 1.3. Đối tượng và phạm vi nghiên cứu

### 1.3.1. Đối tượng nghiên cứu

Đối tượng nghiên cứu của đề tài là **các đơn vị kinh doanh bán lẻ thực phẩm và dịch vụ ăn uống quy mô vừa và nhỏ**, cụ thể gồm:

- **Chuỗi cửa hàng tiện lợi (convenience store):** Bán đa dạng hàng hóa tiêu dùng nhanh, thực phẩm tươi sống, đồ uống, nhu cầu quản lý đa nhóm hàng với hạn sử dụng ngắn.
- **Chuỗi nhà hàng thức ăn nhanh (F&B):** Quản lý nguyên liệu đầu vào, tồn kho bếp, theo dõi hạn sử dụng nguyên liệu tươi sống.
- **Kho bán lẻ và kho phân phối nhỏ:** Phục vụ nhiều điểm bán lẻ, cần đồng bộ tồn kho giữa các chi nhánh.

Đối tượng người sử dụng hệ thống bao gồm chủ chuỗi, quản lý vận hành và nhân viên kho.

### 1.3.2. Phạm vi nghiên cứu

**Phạm vi về sản phẩm:**

- Nhóm **thực phẩm tươi sống**: rau củ, trái cây, thịt, cá, trứng, đồ uống không đóng bình.
- Nhóm **đồ uống và thực phẩm có hạn sử dụng ngắn**: sữa, nước giải khát, đồ uống đóng chai, bánh ngọt, thực phẩm chế biến sẵn.
- Tiêu chí lựa chọn: sản phẩm có **hạn sử dụng ngắn (dưới 90 ngày)** và **biến động nhu cầu rõ nét** — đây là nhóm sản phẩm mà việc dự báo sai lệch gây hậu quả lãng phí lớn nhất.

**Phạm vi về chức năng:**

- Trọng tâm vào **quản lý tồn kho và dự báo nhu cầu bán hàng**.
- Không bao gồm các chức năng thuộc phạm vi quản trị chuỗi cung ứng đầy đủ như: quản lý nhà cung cấp, tối ưu hóa vận tải, quản lý trung tâm phân phối, thanh toán điện tử, quản lý nhân sự *(các hướng mở rộng được trình bày tại Chương 5)*.

**Phạm vi về công nghệ:**

- Ứng dụng web chạy trên nền tảng trình duyệt, hỗ trợ truy cập trên máy tính và máy tính bảng.
- Dữ liệu lịch sử bán hàng phục vụ huấn luyện mô hình dự báo: dự kiến **tối thiểu 12 tháng dữ liệu bán hàng theo ngày** để mô hình nắm bắt được tính mùa vụ *(cần bổ sung: khả năng cung cấp dữ liệu thực tế từ đơn vị thực hành)*.

**Phạm vi về thời gian:**

Thời gian thực hiện đồ án: **từ ngày 05/10/2026 đến ngày 22/12/2026** (11 tuần), bao gồm các giai đoạn phân tích yêu cầu, thiết kế, lập trình, xây dựng mô hình, kiểm thử và viết báo cáo.

| Giai đoạn | Thời gian | Nội dung chính |
|-----------|-----------|----------------|
| Tuần 1–2 | 05/10 – 16/10/2026 | Đề cương, phân tích yêu cầu, thiết kế cơ sở dữ liệu, viết tài liệu |
| Tuần 3–6 | 19/10 – 27/11/2026 | Xây dựng backend, frontend, các chức năng quản lý |
| Tuần 7–9 | 30/11 – 18/12/2026 | Xây dựng mô hình dự báo, AI Agent, tích hợp và kiểm thử |
| Tuần 10–11 | 21/12 – 22/12/2026 | Hoàn thiện báo cáo, chuẩn bị bảo vệ đồ án |

---

## 1.4. Phương pháp nghiên cứu

Đề tài sử dụng kết hợp nhiều phương pháp nghiên cứu phù hợp với đặc thù đồ án tốt nghiệp ngành Khoa học Máy tính, trong đó trọng tâm là **phương pháp phát triển phần mềm theo mô hình Agile kết hợp ứng dụng kỹ thuật học máy**.

### 1.4.1. Phương pháp phân tích nghiệp vụ

Thực hiện khảo sát quy trình vận hành hiện tại của đơn vị thực hành, gồm các bước:

1. **Khảo sát thực tế:** Phỏng vấn chủ cửa hàng/nhân viên về quy trình nhập hàng, ghi nhận tồn kho, xử lý sản phẩm hết hạn.
2. **Phân tích yêu cầu nghiệp vụ (Business Requirements Analysis - BRA):** Xác định các yêu cầu chức năng và phi chức năng của hệ thống từ dữ liệu khảo sát thu được.
3. **Mô hình hóa nghiệp vụ:** Sử dụng biểu đồ Use Case, biểu đồ hoạt động (Activity Diagram) và biểu đồ luồng dữ liệu (DFD) để đặc tả nghiệp vụ *(xem tài liệu thiết kế hệ thống tại `docs/03-thiet-ke/`)*.

Kết quả của bước này là danh sách yêu cầu cụ thể làm đầu vào cho giai đoạn thiết kế và phát triển.

### 1.4.2. Phương pháp thiết kế cơ sở dữ liệu quan hệ

Thiết kế cơ sở dữ liệu theo mô hình quan hệ với các bước:

- Xác định các thực thể nghiệp vụ: Sản phẩm, Danh mục, Kho, Tồn kho, Giao dịch, Đơn hàng, Hạn sử dụng, Cảnh báo, Người dùng.
- Chuẩn hóa lược đồ ở mức chuẩn 3NF để loại bỏ dị thường cập nhật, bảo đảm tính nhất quán dữ liệu.
- Xác định khóa chính, khóa ngoại, ràng buộc toàn vẹn tham chiếu và ràng buộc miền giá trị.
- Thiết kế chỉ mục (index) trên các cột thường xuyên truy vấn như `product_id`, `expiry_date`, `transaction_date` để tối ưu truy vấn.

### 1.4.3. Phương pháp phát triển phần mềm

Áp dụng **mô hình Agile với khung Scrum** trong quy trình phát triển, phù hợp với đặc thù đồ án cá nhân với các đặc điểm:

- Yêu cầu có thể thay đổi sau mỗi vòng lặp phản hồi từ người sử dụng thực tế.
- Cho phép đưa sản phẩm ra sử dụng sớm ở giai đoạn 1 (quản lý cơ bản) rồi bổ sung dần năng lực dự báo ở giai đoạn 2.
- Tạo động lực thông qua các mốc bàn giao (milestone) theo tuần.

Quy trình phát triển được tổ chức theo chu kỳ 1–2 tuần với các hoạt động: Lập kế hoạch (Sprint Planning) → Phát triển → Kiểm thử → Rà soát (Sprint Review) → Cải tiến (Sprint Retrospective).

Ngoài ra, đề tài tuân thủ nguyên tắc **viết mã sạch (Clean Code)** và tuân thủ quy ước đặt tên: tên file Python theo dạng `snake_case`, tên component React theo dạng `PascalCase`, mọi API tuân thủ tiền tố `/api/v1/` nhằm đảm bảo khả năng mở rộng và bảo trì về sau.

### 1.4.4. Phương pháp ứng dụng kỹ thuật học máy

Đối với bài toán dự báo nhu cầu, đề tài thực hiện theo quy trình chuẩn của một bài toán học máy trên dữ liệu chuỗi thời gian:

```
Thu thập dữ liệu → Làm sạch dữ liệu → Trực quan hóa & phân tích khám phá (EDA)
        ↓
Chia tập dữ liệu (Train/Validation/Test)
        ↓
Xây dựng và huấn luyện mô hình (ARIMA, Prophet, XGBoost)
        ↓
Đánh giá mô hình (RMSE, MAE, MAPE)
        ↓
Lựa chọn mô hình tối ưu → Tích hợp vào hệ thống
```

Các bước cụ thể:

1. **Thu thập và làm sạch dữ liệu:** Xử lý giá trị thiếu, giá trị trùng lặp, dữ liệu bất thường trong lịch sử giao dịch bán hàng.
2. **Trực quan hóa và phân tích khám phá dữ liệu (EDA):** Xác định xu hướng, tính mùa vụ (theo tuần, tháng), ảnh hưởng của ngày lễ và chương trình khuyến mãi.
3. **Phân chia tập dữ liệu theo thời gian:** Chia theo tỷ lệ 70% huấn luyện, 15% kiểm định, 15% kiểm tra — bảo đảm không rò rỉ dữ liệu tương lai vào tập huấn luyện.
4. **Huấn luyện và đánh giá:** So sánh hiệu năng của các mô hình trên cùng một tập dữ liệu để lựa chọn mô hình phù hợp nhất với đặc thù dữ liệu bán lẻ Việt Nam.
5. **Tích hợp vào hệ thống:** Đóng gói mô hình đã huấn luyện và gọi từ backend thông qua dịch vụ dự báo, cập nhật định kỳ theo lịch.

### 1.4.5. Phương pháp đánh giá hệ thống

Hệ thống được đánh giá theo ba tiêu chí:

- **Chức năng:** Kiểm thử từng chức năng theo yêu cầu nghiệp vụ đã xác định, bao gồm kiểm thử tự động (unit test) và kiểm thử tích hợp.
- **Hiệu năng mô hình dự báo:** Đánh giá bằng các chỉ số sai số quen thuộc — RMSE, MAE, MAPE.
- **Trải nghiệm người dùng:** Khảo sát phản hồi từ người sử dụng thực tế sau khi thử nghiệm hệ thống.

---

## 1.5. Ý nghĩa thực tiễn

### 1.5.1. Ý nghĩa đối với doanh nghiệp bán lẻ và F&B

**Giảm lãng phí thực phẩm:** Nhờ dự báo nhu cầu chính xác hơn so với ước lượng kinh nghiệm, lượng nhập hàng sẽ gần với nhu cầu thực tế hơn. Điều này trực tiếp giảm lượng hàng dư dẫn đến hết hạn và tiêu hủy. Đây là nguồn lợi ích tài chính trực tiếp và rõ ràng nhất của hệ thống.

**Tối ưu dòng vốn lưu động:** Tồn kho là khoản chi chiếm lượng vốn lớn thứ hai sau tiền mặt trong hoạt động bán lẻ. Giảm tồn kho dư thừa đồng nghĩa với giải phóng vốn, giảm chi phí cơ hội và chi phí kho bãi. Bên cạnh đó, việc tránh tình trạng hết hàng giúp bảo đảm doanh thu không bị gián đoạn.

**Giảm chi phí vận hành:** Tự động hóa quy trình ghi nhận giao dịch, theo dõi hạn sử dụng và cảnh báo giúp giảm thời gian và nhân sự dành cho công tác kiểm kê thủ công. Quyết định nhập hàng chỉ còn dành cho các trường hợp cần can thiệp, thay vì áp dụng đồng loạt cho toàn bộ nhóm hàng.

**Hỗ trợ ra quyết định dựa trên dữ liệu:** Hệ thống cung cấp bằng chứng khách quan cho các quyết định nhập hàng, thay thế cho phương pháp "cảm tính" truyền thống. Điều này đặc biệt có giá trị với các chủ cửa hàng mới tham gia thị trường, khi kinh nghiệm còn hạn chế.

**Quản lý hạn sử dụng chủ động:** Cơ chế cảnh báo đa mức độ (cảnh báo sớm, cảnh báo khẩn, cảnh báo hết hạn) giúp đơn vị chủ động xử lý hàng gần hết hạn thay vì phát hiện khi đã quá muộn.

### 1.5.2. Ý nghĩa đối với xã hội và môi trường

Lãng phí thực phẩm không chỉ là vấn đề kinh tế mà còn mang ý nghĩa môi trường đáng kể. Sản phẩm bị tiêu hủy tiêu tốn tài nguyên đã bị hao tán từ khâu sản xuất (nước, đất, năng lượng, phân bón), phát thải khí methane từ quá trình phân hủy hữu cơ, và tạo ra khối lượng chất thải rắn. Giảm lãng phí thực phẩm vì vậy đóng góp trực tiếp vào mục tiêu phát triển bền vững.

Bên cạnh đó, khi doanh thu không bị tổn thất do nhập dư, người bán có thể giữ được mức giá hợp lý thay vì buộc phải giảm giá xả hàng nhanh để thu hồi vốn. Điều này góp phần duy trì sự ổn định giá cả trong thị trường và bảo vệ lợi ích người tiêu dùng.

### 1.5.3. Ý nghĩa đối với sinh viên

Thông qua đồ án, sinh viên có cơ hội tổng hợp và vận dụng kiến thức đã học trong toàn bộ chương trình đào tạo:

- Kiến thức cơ sở dữ liệu: thiết kế lược đồ quan hệ, tối ưu truy vấn, bảo đảm tính nhất quán dữ liệu.
- Kiến thức hệ thống và mạng: thiết kế kiến trúc phân tán, giao tiếp REST API, giao tiếp real-time qua WebSocket.
- Kiến thức trí tuệ nhân tạo và học máy: xử lý dữ liệu chuỗi thời gian, huấn luyện và đánh giá mô hình dự báo.
- Kiến thức phát triển phần mềm: quy trình phát triển Agile, quản lý phiên bản với Git, kiểm thử phần mềm.
- Kỹ năng nghiên cứu: khả năng tìm kiếm, tổng hợp tài liệu và giải quyết vấn đề độc lập.

---

## 1.6. Cấu trúc báo cáo

Báo cáo đồ án tốt nghiệp được trình bày trong **05 chương**, bao gồm phần đánh giá kết quả và hướng phát triển. Cụ thể như sau:

**Chương 1 — Tổng quan đề tài** *(chương hiện tại)*

Giới thiệu bối cảnh thực tế, nêu bật vấn đề lãng phí thực phẩm trong chuỗi cửa hàng bán lẻ/F&B; trình bày mục tiêu nghiên cứu chung và mục tiêu cụ thể cho hai giai đoạn; xác định đối tượng, phạm vi và phương pháp nghiên cứu; khẳng định ý nghĩa thực tiễn của đề tài; giới thiệu cấu trúc báo cáo.

**Chương 2 — Cơ sở lý thuyết**

Trình bày tổng quan về chuỗi cung ứng bán lẻ; phân tích bài toán dự báo nhu cầu và các yếu tố ảnh hưởng; giới thiệu và so sánh các mô hình dự báo tiền tiến gồm ARIMA, Prophet, XGBoost, Random Forest và LSTM; tổng hợp các nghiên cứu liên quan; giới thiệu và lý do lựa chọn các công nghệ sử dụng trong hệ thống.

**Chương 3 — Phân tích và thiết kế hệ thống**

Trình bày quy trình phân tích yêu cầu nghiệp vụ; đặc tả yêu cầu chức năng và phi chức năng; thiết kế kiến trúc tổng thể, sơ đồ Use Case, sơ đồ hoạt động; thiết kế cơ sở dữ liệu với lược đồ quan hệ và mô tả các bảng; thiết kế API và giao diện người dùng.

**Chương 4 — Cài đặt và triển khai**

Trình bày môi trường triển khai; cài đặt cơ sở dữ liệu và backend FastAPI; xây dựng frontend React; cài đặt và huấn luyện mô hình dự báo; tích hợp AI Agent chatbot; kết quả thử nghiệm và đánh giá hiệu năng hệ thống.

**Chương 5 — Kết luận và hướng phát triển**

Tổng kết các kết quả đã đạt được so với mục tiêu đề ra; đánh giá ưu điểm, hạn chế của hệ thống; đề xuất hướng mở rộng tính năng như tích hợp quản lý nhà cung cấp, tối ưu vận tải, phát triển ứng dụng di động và mở rộng phạm vi áp dụng.

Ngoài 05 chương nội dung chính, báo cáo còn bao gồm phần **Mở đầu** (lời cam đoan, lời cảm ơn, mục lục, danh mục hình bảng, danh mục từ viết tắt), phần **Kết luận** và các **phụ lục** (mã nguồn, truy vấn SQL, kết quả đánh giá mô hình).

---

## Tài liệu tham khảo của chương

| Mã | Tài liệu |
|-----|----------|
| [1] | FAO (2019), *The State of Food and Agriculture 2019: Moving forward on food loss and waste reduction*, Rome. |
| [2] | Tài liệu đề cương đồ án tốt nghiệp — Trường *(cần bổ sung)*, *(cần bổ sung tên trường và khoa)*. |
| [3] | Tài liệu thiết kế hệ thống của đề tài, thư mục `docs/03-thiet-ke/`. |
| [4] | Nguồn số liệu thống kê lãng phí thực phẩm tại Việt Nam *(cần bổ sung từ Tổng cục Thống kê hoặc cơ quan có thẩm quyền)*. |

> **Ghi chú:** Các tài liệu tham khảo trong chương này được trích dẫn ở mức định hướng. Danh mục tài liệu tham khảo đầy đủ của đồ án sẽ được tổng hợp và hoàn thiện tại phần cuối báo cáo, thư mục `docs/05-tham-khao/`. Các vị trí đánh dấu *(cần bổ sung)* cần được hoàn thiện trong quá trình viết báo cáo.
