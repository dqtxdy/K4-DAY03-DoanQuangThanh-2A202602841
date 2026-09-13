"""Facilities tool schemas and deterministic mock backend."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List


TOOLS_SCHEMA: List[Dict[str, Any]] = [
    {
        "name": "check_room_availability",
        "description": (
            "Kiểm tra các phòng họp còn trống theo thời gian, sức chứa và thiết bị. "
            "Chỉ trả về phòng không bị trùng lịch, đủ chỗ và có đủ thiết bị yêu cầu."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "datetime_str": {
                    "type": "string",
                    "description": "Thời gian bắt đầu, định dạng HH:MM DD/MM/YYYY, ví dụ 14:00 15/09/2026",
                },
                "duration_minutes": {
                    "type": "integer",
                    "description": "Thời lượng cuộc họp tính bằng phút, phải lớn hơn 0",
                },
                "attendee_count": {
                    "type": "integer",
                    "description": "Số người tham dự, phải lớn hơn 0",
                },
                "required_equipment": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Danh sách thiết bị bắt buộc, ví dụ ['máy chiếu', 'bảng trắng']",
                },
            },
            "required": ["datetime_str", "duration_minutes", "attendee_count", "required_equipment"],
        },
    },
    {
        "name": "create_room_booking",
        "description": (
            "Tạo booking cho một phòng họp cụ thể. Tool phải tự kiểm tra phòng tồn tại, "
            "thời gian hợp lệ, sức chứa, thiết bị và xung đột lịch trước khi xác nhận."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "room_id": {"type": "string", "description": "Mã phòng cụ thể, ví dụ R201"},
                "datetime_str": {"type": "string", "description": "Thời gian bắt đầu, định dạng HH:MM DD/MM/YYYY"},
                "duration_minutes": {"type": "integer", "description": "Thời lượng cuộc họp tính bằng phút"},
                "attendee_count": {"type": "integer", "description": "Số người tham dự; mặc định 1 nếu người dùng không nêu"},
                "required_equipment": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Danh sách thiết bị bắt buộc; mặc định [] nếu người dùng không nêu",
                },
                "requester_name": {"type": "string", "description": "Tên người đặt phòng"},
                "purpose": {"type": "string", "description": "Mục đích sử dụng phòng; mặc định 'Cuộc họp' nếu người dùng không nêu"},
            },
            "required": [
                "room_id", "datetime_str", "duration_minutes", "requester_name",
            ],
        },
    },
]


ROOMS: Dict[str, Dict[str, Any]] = {
    "R101": {
        "room_id": "R101", "name": "Phòng họp R101", "capacity": 6,
        "equipment": ["bảng trắng"], "location": "Tòa A",
    },
    "R201": {
        "room_id": "R201", "name": "Phòng họp R201", "capacity": 12,
        "equipment": ["máy chiếu", "bảng trắng"], "location": "Tòa B",
    },
    "R301": {
        "room_id": "R301", "name": "Phòng họp R301", "capacity": 20,
        "equipment": ["máy chiếu", "bảng trắng", "video conference"], "location": "Tòa C",
    },
}


# Existing reservations make conflict checks deterministic. Intervals are [start, end).
INITIAL_RESERVATIONS: List[Dict[str, Any]] = [
    {"room_id": "R201", "start": "14:00 15/09/2026", "duration_minutes": 90, "purpose": "Lịch họp nội bộ"},
    {"room_id": "R301", "start": "16:00 15/09/2026", "duration_minutes": 60, "purpose": "Lịch đào tạo"},
]
RESERVATIONS: List[Dict[str, Any]] = []
BOOKING_COUNTER = 0


def reset_facilities_state() -> None:
    """Reset reservations so a test suite starts from the documented fixture."""
    global RESERVATIONS, BOOKING_COUNTER
    RESERVATIONS = [dict(item) for item in INITIAL_RESERVATIONS]
    BOOKING_COUNTER = 0


def _normalise_datetime(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("datetime_str phải là chuỗi dạng HH:MM DD/MM/YYYY")
    cleaned = re.sub(r"\s+", " ", value.strip().replace("ngày", "").strip())
    parsed = datetime.strptime(cleaned, "%H:%M %d/%m/%Y")
    return parsed.strftime("%H:%M %d/%m/%Y")


def _time_window(datetime_str: Any, duration_minutes: Any) -> tuple[datetime, datetime, str]:
    normalised = _normalise_datetime(datetime_str)
    if isinstance(duration_minutes, bool) or not isinstance(duration_minutes, int) or duration_minutes <= 0:
        raise ValueError("duration_minutes phải là số nguyên lớn hơn 0")
    start = datetime.strptime(normalised, "%H:%M %d/%m/%Y")
    return start, start + timedelta(minutes=duration_minutes), normalised


def _equipment_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        values = value.split(",")
    elif isinstance(value, list):
        values = value
    else:
        raise ValueError("required_equipment phải là danh sách chuỗi")
    return [str(item).strip().casefold() for item in values if str(item).strip()]


def _overlaps(start: datetime, end: datetime, reservation: Dict[str, Any]) -> bool:
    reserved_start = datetime.strptime(reservation["start"], "%H:%M %d/%m/%Y")
    reserved_end = reserved_start + timedelta(minutes=reservation["duration_minutes"])
    return start < reserved_end and reserved_start < end


def _validate_common(attendee_count: Any) -> None:
    if isinstance(attendee_count, bool) or not isinstance(attendee_count, int) or attendee_count <= 0:
        raise ValueError("attendee_count phải là số nguyên lớn hơn 0")


def _available_rooms(start: datetime, end: datetime, attendee_count: int, required_equipment: List[str]) -> List[Dict[str, Any]]:
    available = []
    for room in ROOMS.values():
        room_equipment = {item.casefold() for item in room["equipment"]}
        if room["capacity"] < attendee_count or not set(required_equipment).issubset(room_equipment):
            continue
        if any(
            reservation["room_id"] == room["room_id"] and _overlaps(start, end, reservation)
            for reservation in RESERVATIONS
        ):
            continue
        available.append({
            "room_id": room["room_id"], "name": room["name"], "capacity": room["capacity"],
            "equipment": room["equipment"], "location": room["location"],
        })
    return available


def check_room_availability(datetime_str: str, duration_minutes: int, attendee_count: int, required_equipment: List[str]) -> str:
    """Return rooms that satisfy time, capacity and equipment constraints."""
    try:
        start, end, normalised = _time_window(datetime_str, duration_minutes)
        _validate_common(attendee_count)
        equipment = _equipment_list(required_equipment)
        available = _available_rooms(start, end, attendee_count, equipment)
        requested = {
            "datetime": normalised, "duration_minutes": duration_minutes,
            "attendee_count": attendee_count, "required_equipment": equipment,
        }
        if not available:
            return json.dumps({
                "status": "NO_AVAILABLE_ROOM", "requested": requested, "available_rooms": [],
                "message": "Không có phòng phù hợp: hệ thống đã kiểm tra sức chứa, thiết bị và xung đột lịch.",
            }, ensure_ascii=False)
        return json.dumps({
            "status": "SUCCESS", "requested": requested, "available_rooms": available,
            "message": f"Tìm thấy {len(available)} phòng phù hợp.",
        }, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        return json.dumps({"status": "INVALID_REQUEST", "message": str(exc)}, ensure_ascii=False)


def create_room_booking(
    room_id: str,
    datetime_str: str,
    duration_minutes: int,
    requester_name: str,
    purpose: str = "Cuộc họp",
    attendee_count: int = 1,
    required_equipment: List[str] | None = None,
) -> str:
    """Create a booking only after independently rechecking all constraints."""
    global BOOKING_COUNTER
    try:
        room_key = str(room_id).strip().upper()
        if room_key not in ROOMS:
            return json.dumps({"status": "ROOM_NOT_FOUND", "room_id": room_key, "message": "Phòng không tồn tại."}, ensure_ascii=False)
        if not isinstance(requester_name, str) or not requester_name.strip():
            raise ValueError("requester_name không được để trống")
        if not isinstance(purpose, str) or not purpose.strip():
            purpose = "Cuộc họp"
        start, end, normalised = _time_window(datetime_str, duration_minutes)
        _validate_common(attendee_count)
        equipment = _equipment_list(required_equipment or [])
        room = ROOMS[room_key]
        if room["capacity"] < attendee_count:
            return json.dumps({"status": "INVALID_REQUEST", "room_id": room_key, "message": "Phòng không đủ sức chứa."}, ensure_ascii=False)
        missing = [item for item in equipment if item not in {x.casefold() for x in room["equipment"]}]
        if missing:
            return json.dumps({"status": "INVALID_REQUEST", "room_id": room_key, "message": f"Phòng thiếu thiết bị: {', '.join(missing)}."}, ensure_ascii=False)
        if any(
            reservation["room_id"] == room_key and _overlaps(start, end, reservation)
            for reservation in RESERVATIONS
        ):
            return json.dumps({"status": "TIME_CONFLICT", "room_id": room_key, "message": "Phòng đã có lịch trùng trong khoảng thời gian yêu cầu."}, ensure_ascii=False)

        BOOKING_COUNTER += 1
        booking_id = f"BK-{start.strftime('%Y%m%d')}-{BOOKING_COUNTER:03d}"
        RESERVATIONS.append({
            "room_id": room_key, "start": normalised, "duration_minutes": duration_minutes,
            "purpose": str(purpose).strip(), "booking_id": booking_id,
        })
        return json.dumps({
            "status": "SUCCESS", "booking_id": booking_id, "room": room,
            "datetime": normalised, "duration_minutes": duration_minutes,
            "attendee_count": attendee_count, "required_equipment": equipment,
            "requester_name": str(requester_name).strip(), "purpose": str(purpose).strip(),
            "message": f"Booking {booking_id} đã được tạo cho {room_key}.",
        }, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        return json.dumps({"status": "INVALID_REQUEST", "message": str(exc)}, ensure_ascii=False)


TOOL_ROUTER = {
    "check_room_availability": check_room_availability,
    "create_room_booking": create_room_booking,
}


def dispatch_tool_call(tool_name: str, arguments: Dict[str, Any]) -> str:
    """Dispatch a tool call and always return a JSON string."""
    function = TOOL_ROUTER.get(tool_name)
    if function is None:
        return json.dumps({"status": "UNKNOWN_TOOL", "error": f"Tool '{tool_name}' không tồn tại."}, ensure_ascii=False)
    try:
        return function(**arguments)
    except TypeError as exc:
        return json.dumps({"status": "INVALID_REQUEST", "message": str(exc)}, ensure_ascii=False)


reset_facilities_state()
