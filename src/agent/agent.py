
"""
ReAct Agent — Reasoning + Acting loop for travel planning.
"""

from __future__ import annotations

import json
import re
from typing import Any

from src.providers.llm_provider import LLMProvider
from src.tools.travel_tools import TOOL_REGISTRY
from src.utils.logger import TelemetryLogger, get_logger

logger = get_logger(__name__)

MAX_STEPS = 15


def _build_system_prompt() -> str:
    tool_descriptions = "\n".join(
        f"- {name}: {meta['description']}" for name, meta in TOOL_REGISTRY.items()
    )
    return f"""Bạn là ReAct Travel Agent — trợ lý tư vấn du lịch Việt Nam chuyên nghiệp.

Bạn có thể sử dụng các tool sau để lấy thông tin chính xác:
{tool_descriptions}

Quy trình làm việc (PHẢI tuân theo):
1. Thought: Suy nghĩ về bước tiếp theo cần làm
2. Action: Gọi tool theo định dạng JSON chính xác
3. Observation: Đọc kết quả từ tool
4. Lặp lại cho đến khi có đủ thông tin
5. Final Answer: Đưa ra câu trả lời hoàn chỉnh

Định dạng Action (PHẢI là JSON hợp lệ):
Action: {{"tool": "tên_tool", "args": {{"arg1": "value1", "arg2": "value2"}}}}

Khi đã có đủ thông tin, kết thúc bằng:
Final Answer: [câu trả lời đầy đủ, rõ ràng bằng tiếng Việt]

Ràng buộc:
- Luôn kiểm tra thời tiết trước khi lên lịch trình ngoài trời.
- Tính toán chi phí dựa trên số liệu thực từ tool, không ước đoán.
- Sắp xếp địa điểm theo khoảng cách hợp lý để tối ưu thời gian di chuyển.
- Đảm bảo lịch trình phù hợp với sở thích và ngân sách của người dùng.
- Trả lời bằng tiếng Việt, rõ ràng và dễ hiểu.
- Nếu thực hiện một bước nào đó không thành công, hãy suy nghĩ lại và thử hành động khác phù hợp.
- Nếu không thể tìm thấy thông tin, hãy thông báo rõ ràng và đề xuất giải pháp thay thế.
"""


def _parse_action(text: str) -> tuple[str, dict] | None:
    match = re.search(r"Action:\s*(\{.*\})", text, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
        return data.get("tool"), data.get("args", {})
    except json.JSONDecodeError:
        return None


def _parse_final_answer(text: str) -> str | None:
    match = re.search(r"Final Answer:\s*(.*)", text, re.DOTALL)
    return match.group(1).strip() if match else None


def _parse_thought(text: str) -> str | None:
    match = re.search(r"Thought:\s*(.*?)(?=Action:|Final Answer:|$)", text, re.DOTALL)
    return match.group(1).strip() if match else None


class TravelReActAgent:
    """ReAct agent for multi-step travel planning."""

    def __init__(self, provider: LLMProvider, session_id: str = "react_agent"):
        self.provider = provider
        self.telemetry = TelemetryLogger(session_id)
        self.system_prompt = _build_system_prompt()
        logger.info("TravelReActAgent initialized with provider: %s", provider.name)

    def _call_tool(self, tool_name: str, args: dict) -> Any:
        if tool_name not in TOOL_REGISTRY:
            return {
                "error": f"Tool '{tool_name}' không tồn tại. Available: {list(TOOL_REGISTRY.keys())}"
            }
        try:
            return TOOL_REGISTRY[tool_name]["fn"](**args)
        except TypeError as e:
            return {"error": f"Sai tham số cho tool '{tool_name}': {e}"}
        except Exception as e:
            return {"error": str(e)}

    def run(self, user_query: str) -> dict:
        logger.info("[AGENT] Query: %s", user_query)
        self.telemetry.start_task("agent", user_query, self.provider.name)
        self.telemetry.log("USER_QUERY", {"query": user_query})

        scratchpad = f"Câu hỏi của người dùng: {user_query}\n\n"
        steps = []

        for step_num in range(1, MAX_STEPS + 1):
            prompt = scratchpad + f"Bước {step_num}:\nThought:"
            try:
                llm_output = "Thought:" + self.provider.complete(
                    prompt,
                    system=self.system_prompt,
                    max_tokens=512,
                )
                self.telemetry.log_llm_call(self.provider.pop_last_metrics())
            except Exception as e:
                self.telemetry.log_error(str(e), code="llm_error", extra={"step": step_num})
                answer = f"Lỗi LLM: {e}"
                self.telemetry.finish_task(False, answer=answer, extra={"num_steps": step_num})
                return {
                    "answer": answer,
                    "steps": steps,
                    "num_steps": step_num,
                    "success": False,
                }

            thought = _parse_thought(llm_output)
            if thought:
                logger.info("[AGENT] Thought: %s", thought)
                self.telemetry.log_thought(thought)

            final_answer = _parse_final_answer(llm_output)
            if final_answer:
                logger.info("[AGENT] Final Answer reached at step %s", step_num)
                self.telemetry.log_final_answer(final_answer)
                steps.append({"step": step_num, "thought": thought, "final_answer": final_answer})
                self.telemetry.finish_task(
                    True,
                    answer=final_answer,
                    extra={"num_steps": step_num},
                )
                return {
                    "answer": final_answer,
                    "steps": steps,
                    "num_steps": step_num,
                    "success": True,
                }

            parsed = _parse_action(llm_output)
            if parsed is None:
                logger.warning("[AGENT] No action parsed, attempting recovery")
                self.telemetry.log_error(
                    "No action parsed",
                    code="parse_error",
                    extra={"step": step_num, "raw_output": llm_output[:500]},
                )
                scratchpad += (
                    f"Thought: {thought}\n"
                    "Observation: Không thể phân tích hành động từ đầu ra. "
                    "Vui lòng dùng đúng format Action JSON.\n\n"
                )
                steps.append(
                    {
                        "step": step_num,
                        "thought": thought,
                        "parse_error": "Không thể phân tích hành động từ đầu ra.",
                    }
                )
                continue

            tool_name, tool_args = parsed
            logger.info("[AGENT] Action: %s(%s)", tool_name, tool_args)
            self.telemetry.log_action(tool_name, tool_args)

            observation = self._call_tool(tool_name, tool_args)
            logger.info("[AGENT] Observation: %s", str(observation)[:120])
            self.telemetry.log_observation(tool_name, observation)

            steps.append(
                {
                    "step": step_num,
                    "thought": thought,
                    "action": {"tool": tool_name, "args": tool_args},
                    "observation": observation,
                }
            )

            obs_str = json.dumps(observation, ensure_ascii=False)
            scratchpad += (
                f"Thought: {thought}\n"
                f"Action: {{\"tool\": \"{tool_name}\", \"args\": {json.dumps(tool_args, ensure_ascii=False)}}}\n"
                f"Observation: {obs_str}\n\n"
            )

        logger.warning("[AGENT] MAX_STEPS reached without Final Answer")
        answer = "Đã đạt giới hạn bước suy luận. Vui lòng thử lại với câu hỏi cụ thể hơn."
        self.telemetry.log_error(
            f"MAX_STEPS ({MAX_STEPS}) reached",
            code="max_steps",
            extra={"max_steps": MAX_STEPS},
        )
        self.telemetry.finish_task(False, answer=answer, extra={"num_steps": MAX_STEPS})
        return {
            "answer": answer,
            "steps": steps,
            "num_steps": MAX_STEPS,
            "success": False,
        }
