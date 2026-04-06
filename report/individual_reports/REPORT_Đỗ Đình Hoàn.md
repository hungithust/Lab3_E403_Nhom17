# Báo cáo Cá nhân: Lab 3 - Chatbot vs ReAct Agent

**Họ và tên:** Đỗ Đình Hoàn  
**MSSV:** 2A202600036  
**Ngày:** 6/4/2026

---

## I. Đóng góp kỹ thuật (15 điểm)

Trong bài lab này, phần đóng góp chính của em là xây dựng **tầng công cụ (tool layer)** cho ReAct agent. Cụ thể, em đã triển khai một nhóm công cụ liên quan đến lập kế hoạch du lịch và đăng ký chúng vào hệ thống để agent có thể gọi trong vòng lặp **Thought -> Action -> Observation**.

### Các module/chức năng đã triển khai

Dựa trên phần code em viết, các hàm chính bao gồm:

- `weather_tool(...)`
- `attraction_search_tool(...)`
- `restaurant_search_tool(...)`
- `distance_tool(...)`
- `cost_calculator_tool(...)`
- `TOOL_REGISTRY`

### Mô tả chi tiết phần em thực hiện

#### 1. Công cụ tra cứu thời tiết
Em triển khai `weather_tool()` để lấy **thông tin thời tiết hiện tại** từ OpenWeatherMap API.  
Chức năng này:
- ánh xạ tên thành phố tiếng Việt sang định dạng API hiểu được,
- gửi request đến OpenWeatherMap,
- chuẩn hóa phản hồi thành dictionary để agent dễ đọc.

Một điểm quan trọng trong phần này là bảng `_VN_CITY_MAP`, giúp hệ thống xử lý đầu vào địa điểm tiếng Việt ổn định hơn.

```python
_VN_CITY_MAP = {
    "đà nẵng": "Da Nang,VN", "hà nội": "Hanoi,VN",
    "hồ chí minh": "Ho Chi Minh City,VN", "hội an": "Hoi An,VN",
    "nha trang": "Nha Trang,VN", "phú quốc": "Phu Quoc,VN",
    "sapa": "Sa Pa,VN", "đà lạt": "Da Lat,VN",
    "huế": "Hue,VN", "cần thơ": "Can Tho,VN",
}
```

Điều này có ích vì ReAct agent nhận câu hỏi tự nhiên từ người dùng, nên nếu không chuẩn hóa địa điểm thì tool sẽ dễ lỗi.

#### 2. Công cụ tìm địa điểm tham quan
Em triển khai `attraction_search_tool()` bằng Foursquare Places Search API.  
Công cụ này:
- geocode địa điểm đầu vào,
- ánh xạ sở thích người dùng như `"biển"` hoặc `"leo núi"` sang category tương ứng,
- trả về danh sách địa điểm tham quan kèm tên, địa chỉ, rating và mô tả.

```python
_INTEREST_TO_CAT = {
    "biển":    "16032",
    "núi":     "16026",
    "leo núi": "16026",
    "bảo tàng":"10027",
    "văn hóa": "10027",
    "lịch sử": "10027",
    "chùa":    "12046",
    "công viên":"16019",
    "di sản":  "10027",
    "cáp treo":"16000",
}
```

Đóng góp này giúp agent không chỉ trả lời chung chung như chatbot mà còn truy vấn thông tin thực tế phù hợp với sở thích người dùng.

#### 3. Công cụ tìm nhà hàng
Em triển khai `restaurant_search_tool()` để gợi ý nhà hàng theo loại ẩm thực và ngân sách.  
Tool này:
- chuyển loại món ăn sang category ID của Foursquare,
- có thể lọc theo mức giá,
- trả về tên nhà hàng, loại ẩm thực, địa chỉ, rating, trạng thái mở cửa và số điện thoại.

Phần lọc ngân sách là một điểm em bổ sung để hỗ trợ các truy vấn mang tính lập kế hoạch:

```python
if budget_per_person_vnd:
    if budget_per_person_vnd < 100_000:   price_cap = 1
    elif budget_per_person_vnd < 300_000: price_cap = 2
    elif budget_per_person_vnd < 700_000: price_cap = 3
    else:                                  price_cap = 4
```

Nhờ đó, agent có thể đưa ra gợi ý sát với nhu cầu hơn thay vì chỉ liệt kê ngẫu nhiên.

#### 4. Công cụ tính khoảng cách
Em triển khai `distance_tool()` dựa trên **công thức Haversine** kết hợp geocoding.  
Công cụ này dùng để ước tính:
- khoảng cách giữa hai địa điểm,
- thời gian di chuyển tương đối theo phương tiện (`car`, `motorbike`, `walking`).

```python
def _haversine(lat1, lon1, lat2, lon2) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return round(2 * R * math.asin(math.sqrt(a)), 1)
```

Dù đây chỉ là khoảng cách đường chim bay, công cụ vẫn hữu ích vì giúp agent có khả năng lập kế hoạch cơ bản mà không cần thêm routing API phức tạp.

#### 5. Công cụ tính chi phí
Em triển khai `cost_calculator_tool()` để ước tính tổng chi phí chuyến đi.  
Đây là tool chạy hoàn toàn cục bộ, không phụ thuộc API bên ngoài nên khá ổn định và nhanh. Nó tính:
- chi phí lưu trú,
- ăn uống,
- đi lại,
- vé tham quan,
- chi phí khác,
- tổng chi phí và trung bình mỗi ngày.

Tool này giúp agent tiến thêm một bước từ “trả lời thông tin” sang “hỗ trợ lập kế hoạch”.

#### 6. Tích hợp vào Tool Registry
Một phần quan trọng trong đóng góp của em là tích hợp toàn bộ công cụ vào `TOOL_REGISTRY`:

```python
TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    "weather_tool": {"fn": weather_tool, "description": "..."},
    "attraction_search_tool": {"fn": attraction_search_tool, "description": "..."},
    "restaurant_search_tool": {"fn": restaurant_search_tool, "description": "..."},
    "distance_tool": {"fn": distance_tool, "description": "..."},
    "cost_calculator_tool": {"fn": cost_calculator_tool, "description": "..."},
}
```

Registry này giúp ReAct agent có thể tra cứu tên tool, gọi đúng hàm và thực thi động từ Action mà LLM sinh ra.

### Tài liệu hóa: Code của em tương tác với vòng lặp ReAct như thế nào?

Phần code em viết chủ yếu nằm ở **lớp thực thi hành động (Action execution layer)**.

Quy trình hoạt động như sau:

1. Mô hình sinh ra **Thought** để xác định cần thông tin gì.
2. Sau đó mô hình đưa ra **Action**, ví dụ:
   `weather_tool(location="Đà Nẵng")`
3. Hệ thống dùng `TOOL_REGISTRY` để tìm hàm tương ứng.
4. Tool của em chạy và trả về dữ liệu dạng dictionary.
5. Dữ liệu này trở thành **Observation**.
6. Mô hình đọc Observation để sinh Thought tiếp theo hoặc Final Answer.

Nói cách khác, phần em làm là cầu nối giữa suy luận ngôn ngữ tự nhiên và chức năng có thể thực thi. Nếu không có các tool này, agent chỉ giống một chatbot thông thường; có chúng, agent có thể lấy dữ liệu mới và tính toán thật.

---

## II. Phân tích một ca lỗi khi debug (10 điểm)

### Mô tả vấn đề

Một lỗi em nhận thấy trong quá trình làm lab là ReAct agent đôi khi xử lý **kết quả lỗi không nhất quán giữa các tool**, dẫn đến suy luận vòng sau không ổn định.

Ví dụ:
- `weather_tool()` trả lỗi theo dạng:
  ```python
  {"status": "error", "message": "..."}
  ```
- `attraction_search_tool()` cũng dùng trường `status`,
- nhưng `restaurant_search_tool()` và `distance_tool()` lại có lúc trả về:
  ```python
  {"error": "..."}
  ```

Sự không đồng nhất này có thể khiến LLM khó nhận biết chắc chắn rằng tool đã thất bại. Thay vì hiểu đây là lỗi, mô hình có thể coi đó là kết quả hợp lệ nhưng thiếu dữ liệu, rồi tiếp tục suy luận sai.

### Ví dụ tình huống lỗi

> Thought: Tôi cần tìm nhà hàng hải sản ở Đà Nẵng trong ngân sách 150000 VNĐ/người.  
> Action: `restaurant_search_tool(location="Đà Nẵng", cuisine="hải sản", budget_per_person_vnd=150000)`  
> Observation: `{"error": "Không geocode được 'Đà Nẵng'"}`  
> Thought: Danh sách nhà hàng chưa đủ, tôi nên gọi lại tool này.

Mẫu lỗi này dễ làm agent lặp lại hành động thay vì đổi chiến lược.

### Chẩn đoán nguyên nhân

Theo em, hiện tượng này đến từ ba nguyên nhân chính:

1. **Schema đầu ra giữa các tool chưa đồng nhất**  
   LLM phụ thuộc khá nhiều vào mẫu dữ liệu. Khi một số tool dùng `status/message` còn tool khác chỉ trả `error`, mô hình sẽ phải tự suy luận xem đây có phải thất bại hay không.

2. **Prompt và parser chưa bao quát hết tình huống lỗi**  
   Trong hệ ReAct, prompt thường dạy mô hình cách đọc Observation. Nếu format quan sát không thống nhất thì ví dụ trong prompt sẽ kém hiệu quả.

3. **LLM rất nhạy với định dạng**  
   Chỉ cần thay đổi nhỏ trong cấu trúc đầu ra cũng có thể làm mô hình đổi cách hành xử: retry, dừng, hay gọi nhầm tool khác.

### Cách khắc phục

Cách em đề xuất là chuẩn hóa toàn bộ đầu ra của tool theo một schema chung, ví dụ:

```python
{
    "status": "success" | "error",
    "message": "...",
    "data": {...}
}
```

Khi đó mô hình sẽ dễ đọc Observation hơn. Ngoài ra, em cũng sẽ cập nhật system prompt để bổ sung ví dụ như:
- nếu `status = "error"` thì mô hình cần:
  - sửa lại tham số,
  - hoặc chuyển sang tool khác,
  - hoặc giải thích hạn chế cho người dùng.

Bên cạnh đó, em sẽ cải thiện logging để lưu rõ:
- tên tool được gọi,
- tham số đầu vào,
- Observation trả về,
- trạng thái thành công/thất bại.

Như vậy việc phân tích log sẽ dễ hơn rất nhiều.

> Nếu log thực tế của nhóm em có một lỗi khác rõ ràng hơn, em có thể thay phần này bằng đúng tình huống debug trong log của mình.

---

## III. Cảm nhận cá nhân: Chatbot vs ReAct (10 điểm)

### 1. Về khả năng suy luận: Thought block giúp gì hơn chatbot thường?

Điểm khác biệt lớn nhất là **Thought block buộc agent phải chia nhỏ bài toán**.  
Một chatbot thông thường thường trả lời ngay dựa trên kiến thức đã học sẵn. Trong khi đó, ReAct agent có thể suy nghĩ theo từng bước:

- kiểm tra thời tiết trước,
- tìm địa điểm tham quan,
- tính khoảng cách,
- ước lượng chi phí,
- rồi mới đề xuất lịch trình.

Nhờ vậy, câu trả lời có cơ sở hơn và phù hợp với bài toán nhiều bước. Trong phần em làm, các tool đặc biệt hữu ích cho những câu hỏi lập kế hoạch du lịch vì agent không cần “đoán”, mà có thể lấy dữ liệu thật hoặc tự tính toán.

### 2. Về độ tin cậy: Khi nào Agent lại kém hơn Chatbot?

ReAct agent có thể kém hơn chatbot trong các tình huống:
- tool output không ổn định,
- mô hình chọn sai tool,
- tham số truyền vào không hợp lệ,
- API bên ngoài lỗi hoặc trả dữ liệu thiếu.

Trong các trường hợp đó, chatbot thường vẫn có thể đưa ra một câu trả lời trôi chảy ở mức chung chung, còn agent có thể bị lặp, bị sai chuỗi hành động, hoặc tạo ra câu trả lời kém tự nhiên hơn.

Nói cách khác, ReAct mạnh hơn nhưng cũng **mong manh hơn** vì phụ thuộc vào parser, prompt, hợp đồng dữ liệu của tool và chất lượng observation.

### 3. Observation ảnh hưởng thế nào đến bước tiếp theo?

Observation là phần quan trọng nhất của vòng lặp vì nó tác động trực tiếp lên Thought tiếp theo.

Ví dụ:
- nếu thời tiết xấu, agent có thể chuyển từ gợi ý đi biển sang hoạt động trong nhà,
- nếu khoảng cách quá xa, agent có thể đổi lịch trình,
- nếu chi phí quá cao, agent có thể giảm ngân sách ăn uống hoặc số điểm tham quan.

Điều này cho thấy agent không chỉ “suy nghĩ nhiều hơn” mà đang **suy nghĩ dựa trên phản hồi của môi trường**. Đây là ưu điểm quan trọng nhất của ReAct so với chatbot truyền thống.

Tuy nhiên, em cũng nhận thấy rằng nếu Observation bị nhiễu, thiếu, hoặc format không tốt thì chất lượng suy luận ở bước tiếp theo cũng giảm rõ rệt.

---

## IV. Hướng cải tiến trong tương lai (5 điểm)

### 1. Khả năng mở rộng
Nếu triển khai ở mức production, em sẽ tách phần thực thi tool thành một **tầng dịch vụ bất đồng bộ (asynchronous service layer)**.  
Thay vì để agent chờ trực tiếp từng API call, các request đến tool có thể được đưa vào queue hoặc worker riêng. Cách này giúp tăng throughput, dễ retry và ổn định hơn khi số lượng người dùng lớn.

### 2. An toàn
Em sẽ thêm một lớp **supervisor/validator** trước khi thực thi tool call.  
Lớp này sẽ kiểm tra:
- tên tool có hợp lệ không,
- tham số đã đủ chưa,
- hành động có an toàn không,
- agent có đang bị lặp vô hạn hay không.

Nhờ đó hệ thống sẽ tránh được việc gọi sai tool hoặc lặp lại cùng một hành động quá nhiều lần.

### 3. Hiệu năng
Với hệ thống nhiều tool hơn, em sẽ bổ sung:
- cơ chế chọn tool tốt hơn,
- truy xuất tool theo embedding,
- cache cho các API call lặp lại,
- chuẩn hóa toàn bộ schema đầu ra.

Đặc biệt, việc thống nhất định dạng Observation sẽ giúp LLM suy luận ổn định hơn rất nhiều.

---

## Kết luận

Tóm lại, đóng góp chính của em trong lab này là xây dựng tầng công cụ giúp ReAct agent làm được nhiều hơn một chatbot thông thường. Em đã triển khai các tool cho tra cứu thời tiết, tìm điểm tham quan, tìm nhà hàng, tính khoảng cách và tính chi phí, sau đó đưa chúng vào `TOOL_REGISTRY` để agent có thể gọi trong vòng lặp ReAct. Qua bài lab này, em nhận ra rằng ReAct agent mạnh hơn chatbot ở các bài toán nhiều bước và cần dữ liệu bên ngoài, nhưng đồng thời cũng nhạy hơn với format output, chất lượng prompt và độ ổn định của tool.

---

**Ghi chú:** File này được viết dựa trên phần code tool mà em đã triển khai. Khi nộp bài, hãy thay placeholder bằng thông tin cá nhân thật và nếu cần thì đổi tên file/module thành đúng tên trong repo của nhóm.
