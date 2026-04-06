# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Nguyễn Công Thành
- **Student ID**: 4A202600142
- **Date**: 06/04/2026

---

## I. Technical Contribution (15 Points)

*Describe your specific contribution to the codebase (e.g., implemented a specific tool, fixed the parser, etc.).*

  - src/utils/logger.py – Hệ thống logging và telemetry

   - tests/test_travel_agent.py – Bộ test tự động cho agent

   - src/providers/llm_provider.py – Lớp trừu tượng hóa LLM provider

---

## II. Debugging Case Study (10 Points)

*Analyze a specific failure event you encountered during the lab using the logging system.*

- **Problem Description**: Problem Description: Agent bị lỗi KeyError: 'tool' khi parse action vì LLM trả về Action: weather_tool({"location": "Đà Nẵng"}) thiếu cặp ngoặc nhọn bao quanh tool name.
- **Log Source** (từ logs/2026-04-06.log): 
        [AGENT] LLM Output: Thought: Cần xem thời tiết Đà Nẵng
        Action: weather_tool({"location": "Đà Nẵng"})
        [ERROR] No action parsed, treating output as final answer
- **Diagnosis**: r"Action:\s*(\{.*\})" chỉ bắt được JSON object có dấu {} xung quanh. LLM không tuân thủ format {"tool": "...", "args": {...}} mà chỉ ghi tên tool trực tiếp.
- **Solution**:Sửa regex để hỗ trợ cả 2 format, Đồng thời cập nhật system prompt yêu cầu LLM luôn dùng format JSON chuẩn.



---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

*Reflect on the reasoning capability difference.*

1.  **Reasoning**: Thought buộc LLM phải giải thích từng bước, tránh trả lời vội vàng. Chatbot thường "đoán" luôn đáp án, dễ sai số liệu. Agent có Thought sẽ tự nhủ "cần gọi tool A trước, rồi tool B" → chính xác hơn.
2.  **Reliability**: Agent thực hiện tệ hơn chatbot trong các câu hỏi siêu ngắn, không cần tool, ví dụ: "Chào bạn". Chatbot trả lời lịch sự ngay, còn agent mất thêm 1-2 bước để suy nghĩ "không cần tool, trả lời trực tiếp" → chậm hơn và có thể bị lỗi parse nếu output không đúng format.
3.  **Observation**:  Phản hồi từ môi trường (kết quả tool) là "sự thật" giúp điều chỉnh suy luận. Ví dụ: Observation: Không có chuyến bay từ Hà Nội đi Huế → agent biết phải hỏi lại người dùng hoặc đề xuất phương tiện khác, không cố gắng gọi tool sai tiếp.

---

## IV. Future Improvements (5 Points)

*How would you scale this for a production-level AI agent system?*

- **Scalability**:  Dùng hàng đợi message queue (RabbitMQ) để xử lý các tool call bất đồng bộ, tránh block agent khi tool chậm. 
- **Safety**: Thêm Supervisor LLM (một agent riêng) kiểm tra lại hành động trước khi thực thi, ví dụ: phát hiện tool book_flight với số tiền quá lớn → yêu cầu xác nhận từ người dùng.
- **Performance**: Với hệ thống có 50+ tool, cần vector database (Chroma, FAISS) để retrieval đúng tool dựa trên ngữ nghĩa câu hỏi, thay vì nhồi nhét tất cả vào prompt.

---

Kết luận cá nhân: ReAct agent vượt trội về độ chính xác cho tác vụ đa bước, nhưng cần tối ưu thêm về latency và xử lý edge cases. Logging chi tiết là chìa khóa để debug thành công.
> [!NOTE]
> Submit this report by renaming it to `REPORT_[YOUR_NAME].md` and placing it in this folder.
