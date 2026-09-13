# 📊 BÁO CÁO THU HOẠCH NGHIỆM THU BÀI LAB 3 (BƯỚC 3 — SUBMISSION ARTIFACT)

> **Họ và Tên Học viên:** Đoàn Quang Thanh  
> **Mã Sinh Viên / Mã Học viên:** 2A202602841
> **Chủ đề Lựa chọn:** *Trợ lý Đặt Phòng họp & Thiết bị (Facilities Agent):* Kiểm tra lịch phòng trống, thiết bị và tạo booking phòng họp.

---

## 1. BẢNG CHẤM ĐIỂM AGENTIC FIT SCORING MATRIX (ĐÁNH GIÁ CHỦ ĐỀ)

| Tiêu chí Đánh giá | Mức độ (1 - 5) | Giải trình chi tiết lý do chọn điểm |
| :--- | :---: | :--- |
| **1. Multi-step Reasoning** | 3 / 5 | Agent phải phân tích yêu cầu đặt phòng, xác định thời gian, loại phòng và thiết bị cần dùng, sau đó kiểm tra thông tin liên quan trước khi tạo booking. Tuy nhiên, quy trình hiện tại chưa có nhiều nhánh nghiệp vụ phức tạp nên mức điểm phù hợp là 3/5. |
| **2. Tool Interaction** | 2 / 5 | Agent có giao tiếp với MCP Server để gọi các công cụ tra cứu và booking. Tuy nhiên, phiên bản bài lab hiện mô phỏng dữ liệu và chỉ sử dụng số lượng tool giới hạn, chưa kết nối với hệ thống quản lý phòng, lịch hoặc thiết bị thực tế nên chấm 2/5. |
| **3. Dynamic Decision** | 5 / 5 | Quyết định tiếp theo phụ thuộc trực tiếp vào kết quả quan sát: nếu phòng hoặc thiết bị còn trống thì tiếp tục tạo booking; nếu không phù hợp, Agent phải thông báo hoặc đề xuất phương án khác. Trường hợp mã sinh viên không tồn tại cũng phải dừng quy trình và không tạo booking. |
| **4. Long Horizon Goal** | 5 / 5 | Agent phải duy trì mục tiêu đặt đúng phòng và thiết bị trong suốt chuỗi xử lý: tiếp nhận yêu cầu, thu thập thông tin, gọi tool qua MCP Server, kiểm tra kết quả và trả về xác nhận booking. Mục tiêu được giữ xuyên suốt qua nhiều bước ReAct trước khi hoàn tất. |
| **TỔNG ĐIỂM AGENTIC FIT** | **15 / 20** | *Nếu tổng điểm > 12/20: Bài toán rất phù hợp triển khai Agentic System.* |

---

## 2. TRÍCH XUẤT KẾT QUẢ WATERFALL TRACE LOG (SAU KHI CHẠY TEST SUITE TRÊN API THẬT)

> ⚠️ **YÊU CẦU NGHIỆM THU:** Mở tệp `.env` điền `GEMINI_API_KEY` (hoặc `OPENAI_API_KEY`) để kết nối LLM thật trước khi thực thi `python src/app.py --all`. Bài nộp chỉ dùng Mock Offline Provider sẽ không đạt điểm nghiệm thực tế.

Dán 1 đoạn trích xuất log tiêu biểu từ file `docs/trace_waterfall.json` sinh ra từ phản hồi LLM API thật:

```json
[
   {
    "step": 1,
    "query": "Hãy đặt phòng họp có máy chiếu cho sinh viên SV2026001 vào lúc 14:00 ngày 15/09/2026, người phụ trách là Nguyễn Văn An.",
    "action_type": "TOOL_EXECUTION",
    "tool_name": "schedule_appointment",
    "arguments": {
      "advisor_name": "Nguyễn Văn An",
      "datetime_str": "14:00 15/09/2026",
      "student_id": "SV2026001",
      "facility_type": "phòng họp có máy chiếu"
    },
    "observation": {
      "status": "SUCCESS",
      "booking_id": "BK-SV2026001-99",
      "student_id": "SV2026001",
      "datetime": "14:00 15/09/2026",
      "advisor": "Nguyễn Văn An",
      "facility": "phòng họp có máy chiếu",
      "message": "Đã kiểm tra phòng/thiết bị và đặt booking phòng họp có máy chiếu cho SV2026001 vào lúc 14:00 15/09/2026."
    },
    "latency_ms": 2395.8
  },
  {
    "step": 2,
    "query": "Hãy đặt phòng họp có máy chiếu cho sinh viên SV2026001 vào lúc 14:00 ngày 15/09/2026, người phụ trách là Nguyễn Văn An.",
    "action_type": "FINAL_ANSWER",
    "thought": "Tổng hợp kết quả từ MCP Server thành công.",
    "output": "Đã kiểm tra phòng/thiết bị và đặt booking phòng họp có máy chiếu cho SV2026001 vào lúc 14:00 15/09/2026.",
    "latency_ms": 10.0
  },
]
```

---

## 3. TỔNG KẾT KẾT QUẢ NGHIỆM THU & NỘP BÀI

- [x] Đã điền API Key thật trong `.env` và xác nhận Agent chạy mượt mà trên LLM API thật (Gemini/OpenAI).
- **Tổng số Test Cases đã chạy thành công:** 5 / 5 test cases.
- **Số lượt gọi Tool qua MCP Server chính xác:** ___ lượt.
- **Kết quả đẩy Repo nộp bài:** [ ] Đã Commit và Push mã nguồn thành công lên GitHub cá nhân.

---

> ✅ **HOÀN TẤT NỘP BÀI:** Sao chép đường link GitHub Repository cá nhân của bạn và dán vào ô nộp bài trên hệ thống LMS VLearn để hoàn tất Bài Lab 3!
