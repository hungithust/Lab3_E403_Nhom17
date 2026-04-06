# Báo cáo Cá nhân: Lab 3 - Chatbot vs ReAct Agent

**Họ và tên:** Đỗ Đình Hoàn  
**MSSV:** 2A202600036  
**Ngày:** 6/4/2026  

---

## I. Đóng góp kỹ thuật (15 điểm)

Trong bài lab này, em phụ trách xây dựng **tầng tool** cho ReAct agent nhằm hỗ trợ bài toán tư vấn du lịch. Các thành phần chính em triển khai gồm `weather_tool`, `attraction_search_tool`, `restaurant_search_tool`, `distance_tool`, `cost_calculator_tool` và `TOOL_REGISTRY`. Những tool này giúp agent lấy dữ liệu thật, tính toán và phản hồi theo vòng lặp **Thought -> Action -> Observation** thay vì chỉ trả lời từ kiến thức có sẵn. Nội dung này được rút gọn từ bản markdown bạn đã gửi. fileciteturn1file0

### Các phần em thực hiện
- **`weather_tool()`**: lấy thời tiết hiện tại từ OpenWeatherMap, đồng thời chuẩn hóa tên thành phố tiếng Việt qua `_VN_CITY_MAP` để giảm lỗi nhập địa điểm. fileciteturn1file0
- **`attraction_search_tool()`**: dùng Foursquare Places Search để tìm điểm tham quan theo địa điểm và sở thích như biển, núi, bảo tàng, chùa. fileciteturn1file0
- **`restaurant_search_tool()`**: tìm nhà hàng theo loại ẩm thực và lọc theo ngân sách, giúp gợi ý sát nhu cầu hơn. fileciteturn1file0
- **`distance_tool()`**: tính khoảng cách và thời gian di chuyển tương đối bằng công thức Haversine kết hợp geocoding. fileciteturn1file0
- **`cost_calculator_tool()`**: ước tính tổng chi phí chuyến đi theo số ngày, ăn uống, lưu trú, đi lại và vé tham quan. fileciteturn1file0
- **`TOOL_REGISTRY`**: đăng ký toàn bộ tool để agent có thể tra cứu tên tool, gọi đúng hàm và nhận Observation tương ứng. fileciteturn1file0

### Code tương tác với ReAct loop như thế nào?
Quy trình hoạt động gồm: mô hình tạo **Thought** để xác định cần thông tin gì, sinh **Action** gọi tool phù hợp, hệ thống tra cứu tool trong `TOOL_REGISTRY`, thực thi hàm, nhận **Observation** dưới dạng dictionary, rồi dùng Observation đó để suy luận bước tiếp theo hoặc tạo **Final Answer**. Vì vậy, phần code em làm chính là cầu nối giữa suy luận ngôn ngữ tự nhiên và khả năng thực thi thực tế của agent. fileciteturn1file0

---

## II. Phân tích một ca lỗi khi debug (10 điểm)

Một lỗi em gặp là **đầu ra lỗi giữa các tool chưa thống nhất**. Cụ thể, `weather_tool()` và `attraction_search_tool()` thường trả về dạng `{"status": "error", "message": "..."}`, trong khi `restaurant_search_tool()` hoặc `distance_tool()` có lúc chỉ trả `{"error": "..."}`. Điều này khiến LLM khó nhận biết chắc chắn là tool đã thất bại, từ đó có thể suy luận sai hoặc lặp lại cùng một action. fileciteturn1file0

Ví dụ, khi agent gọi `restaurant_search_tool(location="Đà Nẵng", cuisine="hải sản", budget_per_person_vnd=150000)` và nhận về `{"error": "Không geocode được 'Đà Nẵng'"}`, mô hình có thể hiểu nhầm là dữ liệu chưa đủ thay vì tool lỗi, rồi tiếp tục gọi lại cùng tool. fileciteturn1file0

Nguyên nhân chính theo em là:
1. Schema output giữa các tool chưa đồng nhất.
2. Prompt và parser chưa xử lý tốt các trường hợp lỗi.
3. LLM rất nhạy với định dạng Observation. fileciteturn1file0

Cách khắc phục là chuẩn hóa toàn bộ đầu ra tool theo một schema chung như:
```python
{"status": "success" | "error", "message": "...", "data": {...}}
```
Ngoài ra cần bổ sung ví dụ lỗi trong system prompt và cải thiện logging để lưu rõ tool, tham số đầu vào, observation và trạng thái thành công/thất bại. fileciteturn1file0

---

## III. Cảm nhận cá nhân: Chatbot vs ReAct (10 điểm)

Về **khả năng suy luận**, Thought block giúp agent chia bài toán thành nhiều bước thay vì trả lời ngay như chatbot thường. Ví dụ, với bài toán lập lịch trình du lịch, agent có thể kiểm tra thời tiết, tìm điểm tham quan, tính khoảng cách rồi mới ước lượng chi phí và đề xuất kế hoạch. Nhờ đó câu trả lời có cơ sở hơn và bám sát dữ liệu hơn. fileciteturn1file0

Về **độ tin cậy**, ReAct agent mạnh hơn chatbot ở các tác vụ nhiều bước hoặc cần dữ liệu bên ngoài, nhưng cũng dễ lỗi hơn nếu tool output không ổn định, chọn sai tool, tham số sai hoặc API thất bại. Trong một số trường hợp đơn giản, chatbot có thể cho câu trả lời trôi chảy hơn vì không phụ thuộc vào parser hay tool execution. fileciteturn1file0

Về **Observation**, đây là yếu tố quyết định bước suy luận tiếp theo. Nếu thời tiết xấu, agent sẽ đổi lịch trình ngoài trời; nếu khoảng cách xa, agent sẽ sắp xếp lại thứ tự địa điểm; nếu chi phí cao, agent sẽ điều chỉnh kế hoạch. Điều đó cho thấy ReAct không chỉ “suy nghĩ nhiều hơn” mà là suy nghĩ dựa trên phản hồi thực tế từ môi trường. fileciteturn1file0

---

## IV. Hướng cải tiến trong tương lai (5 điểm)

Để phát triển lên mức production, em đề xuất:
- **Scalability**: tách phần thực thi tool thành tầng dịch vụ bất đồng bộ để tăng throughput và dễ retry.
- **Safety**: thêm lớp supervisor/validator để kiểm tra tool name, tham số và phát hiện vòng lặp vô hạn.
- **Performance**: chuẩn hóa schema đầu ra, thêm cache cho API và cải thiện cơ chế chọn tool khi số lượng tool tăng. fileciteturn1file0

---

## Kết luận

Tóm lại, đóng góp chính của em là xây dựng tầng công cụ cho ReAct agent, gồm các tool tra cứu thời tiết, tìm địa điểm tham quan, tìm nhà hàng, tính khoảng cách và ước lượng chi phí, sau đó tích hợp vào `TOOL_REGISTRY` để agent sử dụng trong vòng lặp ReAct. Qua bài lab này, em nhận thấy ReAct agent mạnh hơn chatbot ở các bài toán nhiều bước và cần dữ liệu thực, nhưng để hoạt động ổn định thì prompt, parser, logging và schema dữ liệu phải được thiết kế rất cẩn thận. fileciteturn1file0
