"""
📚 [REFERENCE ONLY / CODE MẪU THAM KHẢO]
🧠 CẤP ĐỘ 3: NATIVE MCP AGENT (Native Tool Calling + MCP Server Integration)
⚠️ Lưu ý: File này chỉ dùng để đọc tham khảo kiến trúc. Không chỉnh sửa hay debug file này.
"""

import json

def get_weather(city: str) -> str:
    return f"Thời tiết {city}: 28°C, Nắng nhẹ."

def run_level3_demo():
    print("=== DEMO CẤP ĐỘ 3: NATIVE MCP AGENT ===")
    user_goal = "Tìm phòng họp cho 10 người lúc 14:00, cần máy chiếu"
    print(f"🎯 Goal: {user_goal}")
    print("🧠 [Decision]: Cần kiểm tra phòng trước khi booking...")
    print("🛠️ [Native Tool Call]: check_room_availability({'attendee_count': 10, 'required_equipment': ['máy chiếu']})")
    print("👁️ [MCP Server Observation]: {'status': 'SUCCESS', 'available_rooms': [{'room_id': 'R301'}]}")
    print("🏁 [Final Answer]: Có thể tiếp tục đặt phòng R301 sau khi xác nhận booking.")

if __name__ == "__main__":
    run_level3_demo()
