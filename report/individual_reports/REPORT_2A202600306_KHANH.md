# Báo cáo Cá nhân: Lab 3 - Chatbot vs ReAct Agent

**Họ và tên:** [Trần Quốc Khánh]  
**MSSV:** [2A202600306]  
**Ngày:** [06/04/2026]  

---

## I. Đóng góp kỹ thuật (15 điểm)

Trong phần code này, đóng góp chính của em tập trung vào ba phần quan trọng của hệ thống:  
1. **Lớp helper để gọi API và xử lý lỗi**,  
2. **System prompt cho ReAct Agent**,  
3. **Baseline Chatbot không dùng tool để so sánh với ReAct Agent**.  

### Các thành phần đã triển khai

Dựa trên đoạn code em viết, các phần chính bao gồm:

- `_get(...)`
- `_geocode(...)`
- `_fsq_headers()`
- `_build_system_prompt()`
- `TravelChatbot`
- `TravelChatbot.chat()`
- `TravelChatbot.reset()`

### Mô tả chi tiết phần thực hiện

#### 1. Hàm helper gọi API và xử lý lỗi
Em triển khai `_get()` để gom toàn bộ logic gọi `GET request` vào một chỗ và xử lý lỗi theo cách nhất quán.  
Hàm này:
- gửi request bằng `requests.get(...)`,
- đặt `timeout=10`,
- parse JSON nếu thành công,
- trả về dict lỗi nếu gặp `HTTPError`, `ConnectionError`, `Timeout`, hoặc exception khác.


#### 2. Hàm geocoding dùng chung cho tool
Em triển khai `_geocode()` để lấy tọa độ từ tên địa điểm bằng OpenWeatherMap Geocoding API.  
Hàm này giúp chuẩn hóa bước chuyển từ địa danh sang `lat/lon`, để các tool khác có thể tái sử dụng.

#### 3. Hàm tạo header cho Foursquare API
Em viết `_fsq_headers()` để sinh header dùng chung cho Foursquare Places API:

#### 4. System prompt cho ReAct Agent
Em xây dựng `_build_system_prompt()` để mô tả rõ cho mô hình cách hoạt động theo ReAct format.  
Điểm quan trọng của phần này là:
- prompt được tạo **động** từ `TOOL_REGISTRY`,
- mô hình được yêu cầu đi theo chuỗi:
  **Thought -> Action -> Observation -> Final Answer**,
- định dạng `Action` được ép về JSON hợp lệ,
- prompt có thêm các ràng buộc nghiệp vụ như:
  - luôn kiểm tra thời tiết trước khi lên lịch trình ngoài trời


#### 5. Xây dựng baseline Chatbot để đối chiếu
Em triển khai class `TravelChatbot` làm **baseline chatbot** không dùng tool.  
Mục đích là để có một mốc so sánh rõ ràng với ReAct Agent.

#### 6. Quản lý lịch sử hội thoại và logging
Trong hàm `chat()`, em thêm logic ghép 4 lượt hội thoại gần nhất thành ngữ cảnh:

```python
history_text = ""
for turn in self.history[-4:]:
    history_text += f"Người dùng: {turn['user']}\nTrợ lý: {turn['assistant']}\n\n"
```

Sau đó tạo prompt và gửi đến provider:

```python
response = self.provider.complete(prompt, system=SYSTEM_PROMPT, max_tokens=1024)
```

Ngoài ra em còn dùng:
- `logger.info(...)` để log quá trình chạy,
- `TelemetryLogger` để lưu `USER_INPUT`, `CHATBOT_RESPONSE` và lỗi,
- `reset()` để xóa lịch sử hội thoại khi cần.

### Tài liệu hóa: Code của em tương tác với ReAct loop như thế nào?

Trong đoạn code này, phần liên quan trực tiếp nhất đến ReAct loop là `_build_system_prompt()`.

Cụ thể:
1. `_build_system_prompt()` tạo ra luật chơi cho agent.
2. Prompt này hướng dẫn mô hình phải suy nghĩ theo từng bước.
3. Model đọc prompt, quyết định tool cần gọi.
4. Tool chạy và trả về Observation.
5. Observation được dùng để tạo Thought tiếp theo.
6. Khi đủ thông tin, model sinh `Final Answer`.

Trong khi đó, `TravelChatbot` đóng vai trò baseline để so sánh. Nó **không có Thought/Action/Observation**, mà trả lời trực tiếp bằng một lần gọi LLM. Chính vì vậy, phần em viết cho chatbot giúp làm nổi bật khác biệt giữa chatbot thường và agent có khả năng hành động.

---

## II. Phân tích một ca lỗi khi debug (10 điểm)

### Mô tả vấn đề

Một lỗi điển hình em gặp trong quá trình làm lab là **mô hình sinh ra Action không đúng JSON format**, dù prompt đã yêu cầu rất rõ:

```python
Action: {"tool": "tên_tool", "args": {"arg1": "value1", "arg2": "value2"}}
```

Trong log, có những lúc mô hình sinh ra dạng như:
- thêm giải thích trước JSON,
- bọc JSON trong markdown code fence,
- hoặc viết Action theo ngôn ngữ tự nhiên thay vì JSON thuần.

Ví dụ:

> Thought: Tôi nên kiểm tra thời tiết ở Đà Nẵng trước.  
> Action: Tôi sẽ dùng weather_tool với location là Đà Nẵng.  

hoặc:

> Action:
> ```json
> {"tool": "weather_tool", "args": {"location": "Đà Nẵng"}}
> ```

Các trường hợp này dễ làm parser thất bại và khiến agent không chạy tiếp được.

### Nguồn log

Phần này có thể lấy từ log telemetry hoặc log file của nhóm, ví dụ:
- `logs/YYYY-MM-DD.log`
- hoặc bản ghi từ `TelemetryLogger` với event như `USER_INPUT`, `ACTION_PARSE_ERROR`, `LLM_RAW_OUTPUT`

Nếu nộp bản cuối, em nên thay phần này bằng đúng snippet log thực tế mà nhóm đã lưu.

### Chẩn đoán nguyên nhân

Theo em, lỗi này xảy ra do ba nguyên nhân chính:
 **Prompt mới chỉ mô tả định dạng, chưa có ví dụ đủ mạnh**  
 **Thiếu lớp kiểm tra/chuẩn hóa trước parser**  

### Cách khắc phục

Để xử lý lỗi này, em sẽ làm ba việc:

#### a. Cải thiện system prompt
Bổ sung ví dụ đúng/sai ngay trong prompt:

```text
Ví dụ đúng:
Action: {"tool": "weather_tool", "args": {"location": "Đà Nẵng"}}

Ví dụ sai:
Action: Tôi sẽ gọi weather tool để kiểm tra thời tiết.
```

#### b. Thêm lớp parser mềm hơn
Trước khi parse JSON, có thể:
- loại bỏ code fence như ```json ... ```,
- tách phần text thừa,
- chỉ lấy object JSON đầu tiên hợp lệ.

Nhờ đó agent sẽ bền hơn với lỗi định dạng nhỏ.

---

## III. Cảm nhận cá nhân: Chatbot vs ReAct (10 điểm)

### 1. Về khả năng suy luận: Thought block giúp gì hơn chatbot thường?

Thought block giúp agent chia một bài toán lớn thành nhiều bước nhỏ làm cho quá trình suy luận có cấu trúc hơn và ít mang tính “đoán mò” hơn.

### 2. Về độ tin cậy: Khi nào Agent lại kém hơn Chatbot?

ReAct agent có thể kém hơn chatbot trong các tình huống:
- Action sinh sai định dạng nên parser lỗi,
- tool gọi API bị timeout hoặc trả lỗi.

### 3. Observation ảnh hưởng thế nào đến bước tiếp theo?

Observation là phần quyết định bước suy luận kế tiếp của agent.  
Nếu observation cho biết thời tiết xấu → agent đổi từ hoạt động ngoài trời sang trong nhà

Trong khi đó, chatbot baseline không có observation nên không thể tự hiệu chỉnh theo dữ liệu mới.

---

## IV. Hướng cải tiến trong tương lai (5 điểm)

### 1. Khả năng mở rộng
Nếu phát triển ở mức production, tách phần tool execution khỏi agent chính và đưa vào một tầng service riêng.  

### 2. An toàn
Bổ sung một lớp validator trước khi thực thi Action để kiểm tra:
- tên tool có hợp lệ không,
- args có thiếu trường nào không,
- JSON có parse được không

### 3. Hiệu năng
Cải tiến thêm bằng cách:
- cache các kết quả API thường dùng,
- giới hạn độ dài history hợp lý hơn,


