# Báo cáo nghiệm thu Facilities Agent

**Học viên:** Đoàn Quang Thanh
**MSSV:** 2A202602841
**Chủ đề:** Trợ lý Đặt Phòng họp & Thiết bị (Facilities Agent)

## 1. Agentic Fit Scoring Matrix

| Tiêu chí | Điểm | Giải trình |
| :--- | :---: | :--- |
| Multi-step Reasoning | 4 / 5 | Agent phải trích xuất yêu cầu, kiểm tra phòng rồi đọc Observation để chọn phòng trước khi booking; một số yêu cầu đơn giản chỉ cần một tool. |
| Tool Interaction | 5 / 5 | Quy trình sử dụng hai tool qua MCP Server: một tool kiểm tra dữ liệu phòng live/mock và một tool tạo booking có xác thực độc lập. |
| Dynamic Decision Making | 4 / 5 | Kết quả availability quyết định việc có được gọi booking hay không và room_id nào được chọn; các lỗi như thiếu phòng sẽ dừng quy trình. |
| Long-Horizon Goal | 3 / 5 | Mục tiêu được giữ qua nhiều bước trong một phiên ReAct, nhưng quy trình booking hiện vẫn ngắn và không yêu cầu theo dõi dài hạn qua nhiều phiên. |
| **Tổng** | **16 / 20** | Facilities Agent phù hợp với Agentic System vì có tool use, Observation và quyết định phụ thuộc dữ liệu. |

## 2. Thiết kế và an toàn backend

Mock facilities database có ba phòng: R101 (6 chỗ, bảng trắng), R201 (12 chỗ, máy chiếu và bảng trắng), R301 (20 chỗ, máy chiếu, bảng trắng và video conference). Availability kiểm tra đồng thời:

- định dạng thời gian và thời lượng;
- sức chứa;
- thiết bị bắt buộc;
- xung đột theo khoảng `[start, end)`.

`create_room_booking` kiểm tra lại phòng, thời gian, sức chứa, thiết bị và conflict trước khi ghi reservation. Booking ID dùng bộ đếm deterministic trong phiên, không bị hard-code cố định.

## 3. Kết quả test suite

Trace được lưu tại [`docs/trace_waterfall.json`](trace_waterfall.json). Lần chạy deterministic gần nhất dùng `LLM_PROVIDER=mock` đạt **5/5 PASS**, với tổng cộng **5 tool calls**.

| Test | Kết quả | Tool sequence | Bằng chứng |
| :--- | :---: | :--- | :--- |
| TC01 | PASS | Không gọi tool | Câu hỏi về khả năng hỗ trợ nhận câu trả lời trực tiếp. |
| TC02 | PASS | `check_room_availability` | Trả về R201 và R301; không tạo booking. |
| TC03 | PASS | `create_room_booking` | R201 được xác thực và tạo `BK-20260915-001`. |
| TC04 | PASS | `check_room_availability → create_room_booking` | Observation trả về R301, sau đó Agent gọi booking cho R301 và nhận `BK-20260915-002`. |
| TC05 | PASS | `check_room_availability` | 25 người vượt sức chứa; nhận `NO_AVAILABLE_ROOM`, không gọi booking. |

## 4. Bằng chứng ReAct và negative case

TC04 có ba sự kiện theo đúng thứ tự trong trace: tool kiểm tra ở step 1, tool booking ở step 2, final answer ở step 3. Observation của step 1 chứa `available_rooms` với R301; `room_id` ở bước booking được chọn từ chính Observation đó.

TC05 nhận `NO_AVAILABLE_ROOM` vì không phòng nào có sức chứa 25 người. Agent dừng sau Observation, evaluator xác nhận không có `create_room_booking` và không có `booking_id` thành công.

## 5. Provider và trạng thái nộp bài

Code vẫn hỗ trợ Gemini native function calling, OpenAI native function calling và Mock Offline cho kiểm thử deterministic. Gemini đã phản hồi ở một số lượt trong lần thử live, nhưng tài khoản free-tier hết quota giữa suite (`429 RESOURCE_EXHAUSTED`), nên các lượt còn lại đã fallback về Mock và không thể dùng làm nghiệm thu toàn bộ LLM thật. Trace hiện tại được tạo lại bằng `LLM_PROVIDER=mock`; cần chạy lại trên môi trường có quota trước khi nộp nghiệm thu live.

Trạng thái commit/push GitHub chưa được xác minh trong môi trường này.
