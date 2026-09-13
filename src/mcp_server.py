"""MCP-style server that exposes the Facilities tools."""

import json
import sys
from typing import Any, Dict, List

from tools import TOOLS_SCHEMA, dispatch_tool_call


if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


class MCPFacilitiesServer:
    """Small JSON-RPC-shaped adapter between the agent and Facilities tools."""

    def __init__(self, server_name: str = "vinuni-facilities-mcp-server"):
        self.server_name = server_name
        self.version = "2026.1.0"

    def list_tools(self) -> List[Dict[str, Any]]:
        return TOOLS_SCHEMA

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        tool_result = dispatch_tool_call(tool_name, arguments)
        content = json.loads(tool_result)
        return {
            "jsonrpc": "2.0",
            "server": self.server_name,
            "tool": tool_name,
            "result": content,
        }


if __name__ == "__main__":
    server = MCPFacilitiesServer()
    print("==========================================================")
    print(f"🔌 MCP SERVER: {server.server_name}")
    print("==========================================================")
    print(f"✅ Khởi tạo thành công (Version: {server.version})")
    print(f"📦 Số lượng Tools công bố: {len(server.list_tools())}")
    result = server.call_tool(
        "check_room_availability",
        {
            "datetime_str": "09:00 15/09/2026",
            "duration_minutes": 60,
            "attendee_count": 8,
            "required_equipment": ["máy chiếu"],
        },
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
