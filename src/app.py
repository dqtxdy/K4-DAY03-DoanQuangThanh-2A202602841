"""Facilities ReAct agent, MCP orchestration, test evaluation and tracing."""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any, Dict, List

from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mcp_server import MCPFacilitiesServer
from prompts import CHATBOT_BASELINE_PROMPT, MAX_ITERATIONS, REACT_AGENT_SYSTEM_PROMPT
from providers import get_llm_provider
from tools import reset_facilities_state

load_dotenv()


def load_test_cases() -> List[Dict[str, Any]]:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "config", "test_cases.json")
    if not os.path.exists(config_path):
        config_path = os.path.join(base_dir, "config", "test_cases.example.json")
    with open(config_path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_waterfall_trace(trace_data: List[Dict[str, Any]]) -> str:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    trace_path = os.path.join(base_dir, "docs", "trace_waterfall.json")
    with open(trace_path, "w", encoding="utf-8") as file:
        json.dump(trace_data, file, ensure_ascii=False, indent=2)
    print(f"📊 [TRACE]: Đã lưu {len(trace_data)} sự kiện tại {trace_path}")
    return trace_path


def run_baseline_chatbot(user_query: str, provider) -> str:
    response = provider.generate(user_query, system_prompt=CHATBOT_BASELINE_PROMPT)
    print(f"\n💬 [BASELINE] {response}")
    return response


def run_react_agent(
    user_query: str,
    provider,
    mcp_server: MCPFacilitiesServer,
    test_id: str | None = None,
) -> Dict[str, Any]:
    """Run genuine decision -> tool -> observation iterations until final text."""
    messages: List[Dict[str, str]] = [{"role": "user", "content": user_query}]
    trace: List[Dict[str, Any]] = []
    tool_calls: List[str] = []
    last_observation: Dict[str, Any] | None = None
    final_answer = ""
    provider_fallbacks = []

    print(f"\n🤖 [FACILITIES AGENT] Câu hỏi: {user_query}")
    for step in range(1, MAX_ITERATIONS + 1):
        print(f"\n--- 🔄 ReAct step {step}/{MAX_ITERATIONS} ---")
        llm_started = time.perf_counter()
        response = provider.generate_with_tools(
            messages,
            mcp_server.list_tools(),
            system_prompt=REACT_AGENT_SYSTEM_PROMPT,
        )
        llm_latency_ms = round((time.perf_counter() - llm_started) * 1000, 2)
        decision = response.get("decision", "Model returned a response.")
        provider_info = {"provider": provider.__class__.__name__}
        if response.get("_fallback"):
            reason = response.get("_fallback_reason", "provider error")
            provider_fallbacks.append(reason)
            provider_info["provider_fallback"] = reason
        print(f"🧠 [Decision]: {decision}")

        if response.get("type") == "text":
            final_answer = response.get("content", "").strip()
            print(f"🏁 [Final Answer]: {final_answer}")
            trace.append({
                "test_case_id": test_id,
                "step": step,
                "query": user_query,
                "action_type": "FINAL_ANSWER",
                "decision": decision,
                "output": final_answer,
                "latency_ms": llm_latency_ms,
                **provider_info,
            })
            break

        if response.get("type") != "tool_call":
            final_answer = "Agent không nhận được phản hồi hợp lệ từ model."
            trace.append({
                "test_case_id": test_id,
                "step": step,
                "query": user_query,
                "action_type": "ERROR",
                "decision": "Provider returned an unsupported response type.",
                "output": final_answer,
                "latency_ms": llm_latency_ms,
                **provider_info,
            })
            break

        tool_name = response.get("tool_name", "")
        arguments = response.get("arguments", {})
        print(f"🛠️ [Action]: {tool_name}({arguments})")
        tool_started = time.perf_counter()
        mcp_result = mcp_server.call_tool(tool_name, arguments)
        tool_latency_ms = round((time.perf_counter() - tool_started) * 1000, 2)
        observation = mcp_result.get("result", {})
        last_observation = observation
        tool_calls.append(tool_name)
        print(f"👁️ [Observation]: {json.dumps(observation, ensure_ascii=False)}")
        trace.append({
            "test_case_id": test_id,
            "step": step,
            "query": user_query,
            "action_type": "TOOL_EXECUTION",
            "decision": decision,
            "tool_name": tool_name,
            "arguments": arguments,
            "observation": observation,
            "latency_ms": round(llm_latency_ms + tool_latency_ms, 2),
            "llm_latency_ms": llm_latency_ms,
            "tool_latency_ms": tool_latency_ms,
            **provider_info,
        })

        # The next model call sees both the model decision and the structured Observation.
        messages.append({
            "role": "assistant",
            "content": f"Decision: {decision}\nTool call: {tool_name} {json.dumps(arguments, ensure_ascii=False)}",
        })
        messages.append({
            "role": "user",
            "content": (
                f"OBSERVATION_JSON: {json.dumps(observation, ensure_ascii=False)}\n"
                "Hãy xem Observation này và quyết định bước tiếp theo. Nếu đã đủ thông tin, trả lời người dùng."
            ),
        })
    else:
        final_answer = "Agent đã đạt giới hạn số bước và chưa thể hoàn tất yêu cầu."
        trace.append({
            "test_case_id": test_id,
            "step": MAX_ITERATIONS + 1,
            "query": user_query,
            "action_type": "LIMIT_REACHED",
            "decision": "MAX_ITERATIONS reached before a final model response.",
            "output": final_answer,
        })

    return {
        "trace": trace,
        "final_answer": final_answer,
        "tool_calls": tool_calls,
        "last_observation": last_observation or {},
        "provider_fallbacks": provider_fallbacks,
    }


def evaluate_test_case(test_case: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    """Validate observable behavior without relying on exact response wording."""
    expectations = test_case.get("expectations", {})
    tool_calls = result["tool_calls"]
    expected_sequence = expectations.get("expected_tool_sequence", [])
    passed = True
    reasons = []

    if expected_sequence and tool_calls != expected_sequence:
        passed = False
        reasons.append(f"tool sequence {tool_calls} != {expected_sequence}")
    for forbidden in expectations.get("forbidden_tools", []):
        if forbidden in tool_calls:
            passed = False
            reasons.append(f"forbidden tool {forbidden} was called")
    if len(tool_calls) < expectations.get("min_tool_calls", 0):
        passed = False
        reasons.append("too few tool calls")
    if len(tool_calls) > expectations.get("max_tool_calls", 999):
        passed = False
        reasons.append("too many tool calls")
    expected_status = expectations.get("expected_final_status")
    actual_status = result["last_observation"].get("status")
    if expected_status and actual_status != expected_status:
        passed = False
        reasons.append(f"final status {actual_status!r} != {expected_status!r}")
    if expectations.get("must_not_book") and (
        "create_room_booking" in tool_calls or "booking_id" in result["last_observation"]
    ):
        passed = False
        reasons.append("a successful booking was observed but must_not_book is true")
    if expectations.get("must_have_final_answer") and not result["final_answer"]:
        passed = False
        reasons.append("missing final answer")
    return {"id": test_case["id"], "passed": passed, "reasons": reasons, "tool_calls": tool_calls, "status": actual_status}


def run_test_suite(provider, mcp_server: MCPFacilitiesServer, tests: List[Dict[str, Any]]) -> Dict[str, Any]:
    reset_facilities_state()
    all_trace: List[Dict[str, Any]] = []
    evaluations = []
    for test_case in tests:
        print("\n==================================================")
        print(f"🧪 [{test_case['id']}] {test_case['question']}")
        result = run_react_agent(test_case["question"], provider, mcp_server, test_case["id"])
        evaluation = evaluate_test_case(test_case, result)
        evaluations.append(evaluation)
        all_trace.extend(result["trace"])
        label = "PASS" if evaluation["passed"] else "FAIL"
        reason = "; ".join(evaluation["reasons"]) or "observable behavior matched expectations"
        print(f"✅ [{label}] {test_case['id']}: {reason}")
    save_waterfall_trace(all_trace)
    passed = sum(1 for item in evaluations if item["passed"])
    total_tools = sum(len(item["tool_calls"]) for item in evaluations)
    print(f"\n📊 [RESULT] executed={len(evaluations)}/{len(tests)} passed={passed}/{len(tests)} tool_calls={total_tools}")
    return {"evaluations": evaluations, "trace": all_trace, "passed": passed, "tool_calls": total_tools}


if __name__ == "__main__":
    print("==========================================================")
    print("🏫 VINUNI FACILITIES AGENT — REACT + MCP")
    print("==========================================================")
    provider = get_llm_provider()
    mcp_server = MCPFacilitiesServer()
    tests = load_test_cases()
    print(f"🔌 LLM Provider: {provider.__class__.__name__} ({provider.model_name})")
    print(f"🌐 MCP Server: {mcp_server.server_name}")
    print(f"✅ Đã tải {len(tests)} test cases.")

    if "--all" in sys.argv:
        run_test_suite(provider, mcp_server, tests)
    elif "--interactive" in sys.argv:
        print("Nhập câu hỏi Facilities Agent; gõ 'exit' để kết thúc.")
        while True:
            question = input("👤 Bạn: ").strip()
            if question.lower() in {"exit", "quit"}:
                break
            result = run_react_agent(question, provider, mcp_server)
            save_waterfall_trace(result["trace"])
    else:
        print("Dùng `python src/app.py --all` để chạy 5 test cases hoặc `--interactive` để chat.")
