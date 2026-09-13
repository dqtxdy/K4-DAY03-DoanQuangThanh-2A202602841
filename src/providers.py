"""LLM adapters for Gemini, OpenAI and an optional deterministic local provider."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List

from dotenv import load_dotenv

load_dotenv()


class BaseLLMProvider:
    model_name = "unknown"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        raise NotImplementedError

    def generate_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools_schema: List[Dict[str, Any]],
        system_prompt: str = "",
    ) -> Dict[str, Any]:
        raise NotImplementedError


def _conversation_text(messages: List[Dict[str, str]]) -> str:
    labels = {"user": "Người dùng", "assistant": "Agent", "tool": "Observation"}
    return "\n\n".join(f"{labels.get(item['role'], item['role'])}: {item['content']}" for item in messages)


def _extract_request(text: str) -> Dict[str, Any]:
    date_match = re.search(r"(\d{1,2}:\d{2})\s+(?:ngày\s+)?(\d{1,2}/\d{1,2}/\d{4})", text, re.IGNORECASE)
    duration_match = re.search(r"(?:trong|thời lượng|khoảng)\s+(\d+)\s*phút", text, re.IGNORECASE)
    attendees_match = re.search(r"(?:cho|có)\s+(\d+)\s*người", text, re.IGNORECASE)
    room_match = re.search(r"(?:phòng\s*)?(R\d{3})\b", text, re.IGNORECASE)
    equipment = []
    for label in ("máy chiếu", "bảng trắng", "video conference"):
        if label in text.casefold():
            equipment.append(label)
    requester = "Người dùng"
    requester_match = re.search(r"(?:người đặt là|người phụ trách là)\s+([^,.]+?)(?:[,.]|$)", text, re.IGNORECASE)
    if not requester_match:
        requester_match = re.search(r"\bcho\s+([^,.]+?)\s+để\b", text, re.IGNORECASE)
    if requester_match:
        candidate = requester_match.group(1).strip()
        if candidate and not candidate.isdigit() and not re.fullmatch(r"\d+\s+người", candidate, re.IGNORECASE):
            requester = candidate
    purpose = "Cuộc họp"
    purpose_match = re.search(r"\bđể\s+(.+?)(?:\.|$)", text, re.IGNORECASE)
    if purpose_match:
        purpose = purpose_match.group(1).strip()
    return {
        "datetime_str": f"{date_match.group(1)} {date_match.group(2)}" if date_match else "",
        "duration_minutes": int(duration_match.group(1)) if duration_match else 60,
        "attendee_count": int(attendees_match.group(1)) if attendees_match else 1,
        "required_equipment": equipment,
        "room_id": room_match.group(1).upper() if room_match else None,
        "requester_name": requester,
        "purpose": purpose,
    }


class MockOfflineProvider(BaseLLMProvider):
    """Deterministic fallback for local backend/evaluator tests."""

    model_name = "Offline-Mock-Model-2026"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        return "Tôi có thể giúp kiểm tra phòng trống, thiết bị và tạo booking phòng họp."

    def generate_with_tools(self, messages, tools_schema, system_prompt=""):
        text = _conversation_text(messages)
        request = _extract_request(messages[0]["content"])
        observation = None
        for message in reversed(messages):
            marker = "OBSERVATION_JSON:"
            if marker in message.get("content", ""):
                try:
                    payload = message["content"].split(marker, 1)[1].strip()
                    observation, _ = json.JSONDecoder().raw_decode(payload)
                except json.JSONDecodeError:
                    observation = None
                break

        booking_requested = any(word in text.casefold() for word in ("đặt phòng", "đặt luôn", "tạo booking", "booking"))
        availability_requested = any(word in text.casefold() for word in ("phòng trống", "kiểm tra", "tìm phòng", "phù hợp"))

        if any(phrase in text.casefold() for phrase in ("có thể hỗ trợ", "bạn hỗ trợ tôi những gì", "khả năng hỗ trợ")) and not request["datetime_str"]:
            return {
                "type": "text",
                "content": "Tôi có thể kiểm tra phòng trống theo thời gian, số người và thiết bị; sau đó tạo booking nếu bạn yêu cầu.",
                "decision": "Câu hỏi chỉ yêu cầu giới thiệu khả năng, không cần gọi tool.",
            }

        if observation is not None:
            if observation.get("status") == "SUCCESS" and observation.get("available_rooms") and booking_requested:
                request["room_id"] = observation["available_rooms"][0]["room_id"]
                return {
                    "type": "tool_call",
                    "tool_name": "create_room_booking",
                    "arguments": request,
                    "decision": "Observation có phòng phù hợp; chọn phòng đầu tiên và gửi yêu cầu booking.",
                }
            if observation.get("status") == "SUCCESS" and "booking_id" in observation:
                return {
                    "type": "text",
                    "content": f"Đã đặt phòng {observation['room']['room_id']} thành công với mã booking {observation['booking_id']}.",
                    "decision": "Booking đã thành công; trả kết quả cho người dùng.",
                }
            if observation.get("status") == "SUCCESS" and observation.get("available_rooms"):
                room_ids = ", ".join(room["room_id"] for room in observation["available_rooms"])
                return {
                    "type": "text",
                    "content": f"Các phòng phù hợp đang trống: {room_ids}.",
                    "decision": "Yêu cầu chỉ kiểm tra; báo các phòng lấy từ Observation và không tạo booking.",
                }
            if observation.get("status") != "SUCCESS" or not observation.get("available_rooms"):
                return {
                    "type": "text",
                    "content": observation.get("message", "Không thể hoàn tất yêu cầu đặt phòng."),
                    "decision": "Observation không cho phép tiếp tục booking; giải thích kết quả cho người dùng.",
                }

        if request["room_id"] and booking_requested:
            return {
                "type": "tool_call",
                "tool_name": "create_room_booking",
                "arguments": request,
                "decision": "Người dùng chỉ rõ room_id; gửi booking để backend tự xác thực.",
            }
        if availability_requested or booking_requested:
            return {
                "type": "tool_call",
                "tool_name": "check_room_availability",
                "arguments": {
                    "datetime_str": request["datetime_str"],
                    "duration_minutes": request["duration_minutes"],
                    "attendee_count": request["attendee_count"],
                    "required_equipment": request["required_equipment"],
                },
                "decision": "Cần kiểm tra phòng theo thời gian, sức chứa và thiết bị trước khi trả lời.",
            }
        return {
            "type": "text",
            "content": "Tôi có thể kiểm tra phòng trống theo thời gian, số người và thiết bị; sau đó tạo booking nếu bạn yêu cầu.",
            "decision": "Câu hỏi chỉ yêu cầu giới thiệu khả năng, không cần gọi tool.",
        }


class GeminiProvider(BaseLLMProvider):
    """Google Gemini adapter using native function declarations."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gemini-2.5-flash"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            return MockOfflineProvider().generate(prompt, system_prompt)
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config={"system_instruction": system_prompt} if system_prompt else None,
            )
            return response.text or ""
        except Exception as exc:
            print(f"⚠️ [Gemini API Warning]: {exc}")
            return MockOfflineProvider().generate(prompt, system_prompt)

    def generate_with_tools(self, messages, tools_schema, system_prompt=""):
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            return MockOfflineProvider().generate_with_tools(messages, tools_schema, system_prompt)
        try:
            from google import genai

            client = genai.Client(api_key=self.api_key)
            declarations = [
                {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool["parameters"],
                }
                for tool in tools_schema
            ]
            response = client.models.generate_content(
                model=self.model_name,
                contents=_conversation_text(messages),
                config={
                    "system_instruction": system_prompt,
                    "tools": [{"function_declarations": declarations}],
                    "temperature": 0.2,
                },
            )
            if response.function_calls:
                call = response.function_calls[0]
                args = dict(call.args) if call.args else {}
                return {
                    "type": "tool_call",
                    "tool_name": call.name,
                    "arguments": args,
                    "decision": f"Gemini chọn gọi {call.name} với các tham số đã trích xuất.",
                }
            return {
                "type": "text",
                "content": response.text or "",
                "decision": "Gemini trả lời bằng văn bản sau khi xem ngữ cảnh hiện tại.",
            }
        except Exception as exc:
            print(f"⚠️ [Gemini API Warning]: {exc}. Chuyển sang Mock Offline cho lượt này.")
            fallback = MockOfflineProvider().generate_with_tools(messages, tools_schema, system_prompt)
            fallback["_fallback"] = True
            fallback["_fallback_reason"] = str(exc)
            return fallback


class OpenAIProvider(BaseLLMProvider):
    """OpenAI adapter using native function declarations."""

    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model_name = model or os.getenv("LLM_MODEL") or "gpt-4o-mini"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            return MockOfflineProvider().generate(prompt, system_prompt)
        try:
            from openai import OpenAI
            messages = ([{"role": "system", "content": system_prompt}] if system_prompt else [])
            messages.append({"role": "user", "content": prompt})
            response = OpenAI(api_key=self.api_key).chat.completions.create(model=self.model_name, messages=messages)
            return response.choices[0].message.content or ""
        except Exception as exc:
            print(f"⚠️ [OpenAI API Warning]: {exc}")
            return MockOfflineProvider().generate(prompt, system_prompt)

    def generate_with_tools(self, messages, tools_schema, system_prompt=""):
        if not self.api_key or self.api_key == "your_openai_api_key_here":
            return MockOfflineProvider().generate_with_tools(messages, tools_schema, system_prompt)
        try:
            from openai import OpenAI

            api_messages = ([{"role": "system", "content": system_prompt}] if system_prompt else [])
            api_messages.extend(messages)
            tools = [
                {"type": "function", "function": {
                    "name": tool["name"], "description": tool.get("description", ""),
                    "parameters": tool["parameters"],
                }}
                for tool in tools_schema
            ]
            response = OpenAI(api_key=self.api_key).chat.completions.create(
                model=self.model_name, messages=api_messages, tools=tools, tool_choice="auto",
            )
            message = response.choices[0].message
            if message.tool_calls:
                call = message.tool_calls[0]
                return {
                    "type": "tool_call",
                    "tool_name": call.function.name,
                    "arguments": json.loads(call.function.arguments or "{}"),
                    "decision": f"OpenAI chọn gọi {call.function.name} với các tham số đã trích xuất.",
                }
            return {
                "type": "text",
                "content": message.content or "",
                "decision": "OpenAI trả lời bằng văn bản sau khi xem ngữ cảnh hiện tại.",
            }
        except Exception as exc:
            print(f"⚠️ [OpenAI API Warning]: {exc}. Chuyển sang Mock Offline cho lượt này.")
            fallback = MockOfflineProvider().generate_with_tools(messages, tools_schema, system_prompt)
            fallback["_fallback"] = True
            fallback["_fallback_reason"] = str(exc)
            return fallback


def get_llm_provider() -> BaseLLMProvider:
    provider_type = os.getenv("LLM_PROVIDER", "gemini").lower()
    if provider_type == "gemini" and os.getenv("GEMINI_API_KEY") not in (None, "", "your_gemini_api_key_here"):
        return GeminiProvider()
    if provider_type == "openai" and os.getenv("OPENAI_API_KEY") not in (None, "", "your_openai_api_key_here"):
        return OpenAIProvider()
    return MockOfflineProvider()
