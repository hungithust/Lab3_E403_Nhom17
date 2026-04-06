# Báo cáo Cá nhân: Lab 3 - Chatbot vs ReAct Agent

**Họ và tên:** Nguyễn Viết Hùng
**MSSV:** 2A2026000240
**Ngày:** 6/4/2026

---

## I. Đóng góp kỹ thuật (15 điểm)

Trong phần này, em tập trung xây dựng **lớp giao diện và lớp chạy thử** để so sánh trực tiếp giữa `TravelChatbot` và `TravelReActAgent`. Đóng góp của em không nằm ở bản thân tool du lịch, mà ở việc tạo ra cách **chạy, quan sát và so sánh** hai hệ thống qua CLI và web interface.

### Các phần em thực hiện
- **`main.py`**: xây dựng chương trình chạy ở terminal với nhiều chế độ `chatbot`, `agent`, `compare`, `demo`.
- **`print_agent_steps()`**: in toàn bộ ReAct trace gồm Thought, Action, Observation, Final Answer để dễ debug.
- **`run_compare()` / `run_comparison_interface()`**: chạy đồng thời chatbot và agent trên cùng một câu hỏi, sau đó so sánh thời gian phản hồi, số bước và khả năng kiểm chứng.
- **`interactive_mode()`**: cho phép trò chuyện trực tiếp với chatbot hoặc agent để quan sát hành vi theo thời gian thực.
- **`web_interface.py`**: xây dựng backend Flask + SocketIO để nhận query từ web, chạy chatbot và agent, rồi stream kết quả về trình duyệt.
- **`index.html`**: tạo giao diện nhập câu hỏi, vùng hiển thị các bước agent, final answer và chatbot response.
- **`style.css`**: thiết kế giao diện đơn giản, dễ nhìn với container, progress bar và form nhập liệu.

### Vai trò của phần code trong hệ ReAct
Phần em làm chủ yếu hỗ trợ **quan sát và đánh giá** quá trình suy luận của agent. Quy trình hoạt động là:
1. Người dùng nhập câu hỏi từ CLI hoặc web.
2. Chatbot trả lời theo kiểu single-shot, không dùng tool.
3. ReAct agent chạy theo vòng lặp **Thought -> Action -> Observation**.
4. CLI hoặc web UI hiển thị lại các bước để người dùng thấy agent đã suy luận như thế nào.
5. Cuối cùng hệ thống so sánh kết quả của hai cách tiếp cận.

Nhờ đó, phần em triển khai giúp bài lab không chỉ “chạy được” mà còn **dễ quan sát, dễ demo và dễ debug**.

---

## II. Phân tích một ca lỗi khi debug (10 điểm)

Một lỗi đáng chú ý em gặp là **sự không đồng bộ giữa dữ liệu stream từ backend và dữ liệu mà frontend mong đợi**. Trong `index.html`, frontend giả định mỗi event `agent_step` đều có các trường như `progress`, `thought` và `final_answer`. Tuy nhiên, ở `web_interface.py`, backend chỉ `emit('agent_step', step)` từ `agent.run_stream(query)`, tức là hoàn toàn phụ thuộc vào cấu trúc dữ liệu mà agent trả ra.

Khi cấu trúc `step` không có đủ các trường frontend cần, các lỗi có thể xảy ra như:
- progress bar không tăng hoặc hiển thị sai,
- UI không biết khi nào agent đã hoàn thành,
- final answer không được cập nhật đúng thời điểm.

### Chẩn đoán nguyên nhân
Theo em, đây không phải lỗi của model mà là **lỗi tích hợp giữa frontend và backend**:
1. Frontend và backend chưa thống nhất chặt chẽ về schema của event `agent_step`.
2. `run_stream()` được giả định là luôn trả dữ liệu đúng định dạng, nhưng chưa có lớp kiểm tra trung gian.
3. UI xử lý optimistic quá mức, không có fallback khi thiếu trường dữ liệu.

### Cách khắc phục
Em sẽ sửa theo hướng:
- chuẩn hóa schema event, ví dụ luôn có `step`, `progress`, `thought`, `observation`, `final_answer`;
- thêm kiểm tra ở backend trước khi emit dữ liệu ra socket;
- thêm fallback ở frontend, ví dụ nếu thiếu `progress` thì không cập nhật progress bar;
- tách riêng event `agent_final` để UI biết chắc thời điểm kết thúc.

Qua lỗi này em nhận ra rằng với ReAct agent, **không chỉ reasoning đúng là đủ**, mà lớp hiển thị kết quả cũng phải ăn khớp với trace của agent.

---

## III. Cảm nhận cá nhân: Chatbot vs ReAct (10 điểm)

Về **khả năng suy luận**, ReAct agent tốt hơn vì có trace rõ ràng. Từ `main.py`, em có thể in ra từng bước Thought, Action và Observation nên dễ hiểu agent đã đi đến câu trả lời bằng cách nào. Trong khi đó, chatbot chỉ cho ra một câu trả lời cuối cùng nên nhanh nhưng khó kiểm chứng.

Về **độ tin cậy**, agent mạnh hơn ở các bài toán nhiều bước vì có thể dùng tool và tự điều chỉnh theo observation. Tuy nhiên, agent cũng dễ lỗi hơn do phụ thuộc vào parser, cấu trúc step, event stream và sự tương thích giữa backend với frontend. Chatbot lại ổn định hơn trong các câu hỏi đơn giản vì không cần nhiều thành phần phối hợp.

Về **vai trò của observation**, em thấy đây là điểm quan trọng nhất. Khi observation được hiển thị qua CLI hoặc web UI, người dùng có thể thấy agent đang phản ứng với dữ liệu thực thay vì chỉ đoán. Chính observation làm cho ReAct trở thành một hệ thống có thể kiểm chứng, thay vì chỉ là một chatbot nói chuyện trôi chảy.

---

## IV. Hướng cải tiến trong tương lai (5 điểm)

Nếu phát triển ở mức production, em sẽ cải tiến theo ba hướng:
- **Scalability**: tách phần chạy agent/chatbot thành worker riêng để web server không bị block khi xử lý query dài.
- **Safety**: thêm lớp validator cho event stream và output schema trước khi đẩy dữ liệu ra frontend.
- **Performance**: cache response, giảm dữ liệu trace không cần thiết, và bổ sung session management để theo dõi nhiều người dùng cùng lúc.

Ngoài ra, em cũng muốn cải thiện giao diện bằng cách:
- hiển thị Action và Observation rõ ràng hơn,
- thêm trạng thái lỗi trên UI,
- lưu lịch sử so sánh giữa chatbot và agent để phục vụ đánh giá thực nghiệm.

---

## Kết luận

Tóm lại, đóng góp chính của em trong phần này là xây dựng **môi trường chạy thử và so sánh** giữa Chatbot và ReAct Agent thông qua CLI và web interface. Em đã triển khai phần hiển thị trace, so sánh kết quả, streaming qua SocketIO và giao diện web để người dùng quan sát trực tiếp quá trình suy luận của agent. Qua đó, em thấy ReAct agent có ưu thế lớn về khả năng giải thích và kiểm chứng, nhưng để hoạt động ổn định thì việc đồng bộ giữa backend, frontend và trace schema là rất quan trọng.
