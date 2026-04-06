# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Nguyễn Xuân Tùng
- **Student ID**: 2A202600247
- **Date**: 6/4/2026

---

## I. Technical Contribution (15 Points)

_Describe your specific contribution to the codebase (e.g., implemented a specific tool, fixed the parser, etc.)._

- **Modules Implementated**: `src/agent/agent.py`
- **Code Highlights**: `[src\agent\agent.py]`
- **Documentation**: `## ReAct loop hoạt động trong code (ngắn gọn)

**ReAct = Reason (suy nghĩ) + Act (hành động)**

### 1. System Prompt

LLM được yêu cầu luôn trả về theo format:

```
Thought → Action → Observation → (lặp) → Final Answer
```

và biết danh sách tool trong `TOOL_REGISTRY`.

---

### 2. Scratchpad = bộ nhớ tạm

`scratchpad` lưu toàn bộ lịch sử:

- Câu hỏi user
- Thought / Action / Observation trước đó

Giúp LLM có đủ ngữ cảnh để suy nghĩ tiếp.

---

### 3. Mỗi vòng lặp = 1 bước ReAct

Trong `run()`:

1. LLM sinh **Thought + Action**
2. Agent parse kết quả:
   - Có `Final Answer` → dừng
   - Có `Action` → gọi tool

---

### 4. Agent gọi tool (Act)

`_call_tool()` thực thi tool trong `TOOL_REGISTRY` để lấy dữ liệu thật.

---

### 5. Observation → quay lại LLM

Kết quả tool được thêm vào scratchpad → LLM suy nghĩ tiếp.

---

### 6. Dừng khi có Final Answer hoặc hết bước

**Tóm tắt vòng lặp:**

```
LLM suy nghĩ → gọi tool → nhận dữ liệu → suy nghĩ tiếp → trả lời cuối
```

→ Câu trả lời có dữ liệu thật, có log, và có thể kiểm chứng.
`

---

## II. Debugging Case Study (10 Points)

_Analyze a specific failure event you encountered during the lab using the logging system._

- **Problem Description**: `Một lỗi điển hình em gặp trong quá trình làm lab là **mô hình sinh ra Action không đúng JSON format**, dù prompt đã yêu cầu rất rõ:

```python
Action: {"tool": "tên_tool", "args": {"arg1": "value1", "arg2": "value2"}}
```

Trong log, có những lúc mô hình sinh ra dạng như:

- thêm giải thích trước JSON,
- bọc JSON trong markdown code fence,
- hoặc viết Action theo ngôn ngữ tự nhiên thay vì JSON thuần.

Các trường hợp này dễ làm parser thất bại và khiến agent không chạy tiếp được.`

- **Log Source**:
  > Thought: Tôi nên kiểm tra thời tiết ở Đà Nẵng trước.  
  > Action: Tôi sẽ dùng weather_tool với location là Đà Nẵng.

hoặc:

> Action:
>
> ```json
> { "tool": "weather_tool", "args": { "location": "Đà Nẵng" } }
> ```

- **Diagnosis**:
  Theo em, lỗi này xảy ra do ba nguyên nhân chính:
  **Prompt mới chỉ mô tả định dạng, chưa có ví dụ đủ mạnh**  
   **Thiếu lớp kiểm tra/chuẩn hóa trước parser**
- **Solution**: Để xử lý lỗi này, em sẽ làm:

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

- loại bỏ code fence như `json ... `,
- tách phần text thừa,
- chỉ lấy object JSON đầu tiên hợp lệ.

## Nhờ đó agent sẽ bền hơn với lỗi định dạng nhỏ.

## III. Personal Insights: Chatbot vs ReAct (10 Points)

### 1. Reasoning

`Thought` giúp agent **lập kế hoạch từng bước trước khi trả lời**, thay vì trả lời ngay như chatbot.

- Chatbot → trả lời trực tiếp dựa trên kiến thức sẵn có.
- ReAct Agent → phân tích vấn đề → chọn tool → lấy dữ liệu → cập nhật kế hoạch → mới trả lời.
  => Kết quả: suy luận có cấu trúc, giải quyết được bài toán nhiều bước và cần dữ liệu bên ngoài.

---

### 2. Reliability

Agent có thể **kém hơn chatbot** trong một số trường hợp:

- Bài toán đơn giản → agent vẫn tốn bước “suy nghĩ + gọi tool” → chậm và rườm rà.
- Tool lỗi / trả dữ liệu sai → agent suy luận dựa trên dữ liệu sai → kết quả sai.
- Loop nhiều bước → dễ bị “overthinking” hoặc đi sai hướng.

=> Chatbot thường ổn định hơn với câu hỏi đơn giản hoặc không cần tool.

---

### 3. Observation

Observation (kết quả từ tool) đóng vai trò như **feedback từ môi trường**.

- Sau mỗi action, agent nhìn vào observation để biết bước trước đúng hay sai.
- Observation giúp agent **cập nhật kế hoạch và điều chỉnh bước tiếp theo**.
  => Tạo vòng lặp học hỏi liên tục: _Action → Feedback → Improve next step_.

---

## IV. Future Improvements (5 Points)

### Scalability

- Dùng **message queue async** (RabbitMQ / Kafka) để xử lý tool calls song song và tránh block hệ thống.
- Tách kiến trúc thành **microservices**: LLM service, Tool service, Memory service.
- Thêm **caching layer (Redis)** cho các kết quả tool phổ biến để giảm chi phí và latency.

---

### Safety

- Thêm **Supervisor / Guardrail LLM** để kiểm tra plan và action trước khi thực thi (policy check, prompt injection, data leakage).
- Áp dụng **permission & sandboxing** cho tool (mỗi tool chỉ được quyền truy cập phạm vi cần thiết).
- Log + audit toàn bộ Thought/Action để có thể trace khi có lỗi hoặc hành vi nguy hiểm.

---

### Performance

- Dùng **Vector Database (FAISS / Pinecone / Weaviate)** để tìm tool & tài liệu nhanh trong hệ thống nhiều tool.
- Tối ưu bằng **tool routing / tool ranking** để tránh agent thử quá nhiều tool không cần thiết.
- Dùng **model nhỏ cho bước đơn giản, model lớn cho bước reasoning phức tạp** (model cascading).

---

> [!NOTE]
> Submit this report by renaming it to `REPORT_[YOUR_NAME].md` and placing it in this folder.
