# Báo cáo nghiệm thu Facilities Agent

**Học viên:** Đoàn Quang Thanh
**MSSV:** 2A202602841
**Chủ đề:** Trợ lý Đặt Phòng họp & Thiết bị (Facilities Agent)

## Agentic Fit Scoring Matrix

| Tiêu chí | Điểm | Giải trình |
| :--- | :---: | :--- |
| Multi-step Reasoning | 4 / 5 | Agent kiểm tra phòng, đọc Observation và chọn phòng phù hợp trước khi booking. |
| Tool Interaction | 5 / 5 | Hai tool qua MCP kiểm tra dữ liệu phòng và tạo booking có xác thực độc lập. |
| Dynamic Decision Making | 4 / 5 | Availability quyết định room_id được chọn hoặc quyết định dừng khi không có phòng. |
| Long-Horizon Goal | 3 / 5 | Mục tiêu được giữ trong nhiều bước ReAct của một phiên booking ngắn. |
| **Tổng** | **16 / 20** | Bài toán cần tool use, Observation và quyết định phụ thuộc dữ liệu. |

## Kết quả nghiệm thu live

**Provider:** GeminiProvider
**Model:** `gemini-2.5-flash`
**Lệnh chạy:** `LLM_PROVIDER=gemini python src/app.py --all`
**Kết quả:** **5/5 PASS**, 5 tool calls, không có fallback provider.

| Test | Tool sequence thực tế | Kết quả |
| :--- | :--- | :---: |
| TC01 | `FINAL` | PASS |
| TC02 | `check_room_availability → FINAL` | PASS |
| TC03 | `create_room_booking → FINAL` | PASS |
| TC04 | `check_room_availability → create_room_booking → FINAL` | PASS |
| TC05 | `check_room_availability → FINAL` | PASS |

Trace live được lưu tại [`docs/trace_waterfall.json`](trace_waterfall.json). Toàn bộ 10 event đều có `provider: GeminiProvider`; không có `provider_error`, event Mock, hay residue Academic.

## TC04: bằng chứng ReAct nhiều bước

Ở step 1, `check_room_availability` nhận yêu cầu 10 người, 90 phút, cần máy chiếu lúc 14:00 15/09/2026 và trả về đúng một phòng phù hợp: `R301`. Ở step 2, Gemini gọi `create_room_booking` với `room_id: R301`; backend trả `SUCCESS` cùng `booking_id: BK-20260915-002`. Step 3 là câu trả lời cuối cùng từ Gemini. Điều này chứng minh booking được quyết định sau khi model nhận Observation, không phải do Python tự gọi tool thứ hai.

## TC05: bằng chứng xử lý failure

`check_room_availability` trả `NO_AVAILABLE_ROOM` cho yêu cầu 25 người. Trace TC05 có 0 lần gọi `create_room_booking`, 0 booking ID và final answer giải thích rằng không có phòng phù hợp. Vì vậy negative case không thể tạo booking thành công.

## Backend và trạng thái nộp bài

Backend kiểm tra định dạng thời gian, sức chứa, thiết bị, tồn tại phòng và xung đột theo khoảng `[start, end)` trước khi tạo booking. Booking ID tăng theo bộ đếm trong phiên, không hard-code.

Trace và báo cáo đã được tái tạo từ run Gemini thật. Trạng thái commit/push GitHub cần được học viên hoàn tất trước khi nộp.
