"""
ReAct Agent — Reasoning + Acting loop for travel planning.

Loop:  Thought → Action → Observation  (repeat up to MAX_STEPS)
         └─ calls a tool from TOOL_REGISTRY
                  └─ result feeds back into next Thought

The agent stops when it emits "Final Answer:" or hits MAX_STEPS.
"""

import json
import re
import time
from typing import Any

from src.providers.llm_provider import LLMProvider
from src.tools.travel_tools import TOOL_REGISTRY
from src.utils.logger import TelemetryLogger, get_logger

logger = get_logger(__name__)

MAX_STEPS = 15

# ---------------------------------------------------------------------------
# System prompt — teaches the model the ReAct format
# ---------------------------------------------------------------------------
def _build_system_prompt() -> str:
    tool_descriptions = "\n".join(
        f"- {name}: {meta['description']}"
        for name, meta in TOOL_REGISTRY.items()
    )
    return f"""Bạn là ReAct Travel Agent — trợ lý tư vấn du lịch Việt Nam chuyên nghiệp.

Bạn có thể sử dụng các tool sau để lấy thông tin chính xác:
{tool_descriptions}
"""


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------
def _parse_action(text: str) -> tuple[str, dict] | None:
    """Extract tool name and args from an Action line."""
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


# ---------------------------------------------------------------------------
# ReAct Agent
# ---------------------------------------------------------------------------
class TravelReActAgent:
    """
    ReAct agent for multi-step travel planning.

    Advantages over TravelChatbot:
    - Verifiable: every number comes from a tool call
    - Traceable: full Thought/Action/Observation log in logs/
    - Debuggable: identify exactly which step fails
    - Accurate: no hallucinated prices or distances
    """

    def __init__(self, provider: LLMProvider, session_id: str = "react_agent"):
        self.provider = provider
        self.telemetry = TelemetryLogger(session_id)
        self.system_prompt = _build_system_prompt()
        logger.info(f"TravelReActAgent initialized with provider: {provider.name}")

    def _call_tool(self, tool_name: str, args: dict) -> Any:
        """Execute a tool and return its result."""
        if tool_name not in TOOL_REGISTRY:
            return {"error": f"Tool '{tool_name}' không tồn tại. Available: {list(TOOL_REGISTRY.keys())}"}
        try:
            result = TOOL_REGISTRY[tool_name]["fn"](**args)
            return result
        except TypeError as e:
            return {"error": f"Sai tham số cho tool '{tool_name}': {e}"}
        except Exception as e:
            return {"error": str(e)}

    def run(self, user_query: str) -> dict:
        """
        Execute the ReAct loop for a user query.

        Returns:
            dict with keys: answer, steps, num_steps, success
        """
        logger.info(f"[AGENT] Query: {user_query}")
        self.telemetry.log("USER_QUERY", {"query": user_query})

        # Build the running scratchpad
        scratchpad = f"Câu hỏi của người dùng: {user_query}\n\n"
        steps = []

        for step_num in range(1, MAX_STEPS + 1):
            # Ask the LLM for the next Thought + Action
            prompt = scratchpad + f"Bước {step_num}:\nThought:"
            try:
                llm_output = "Thought:" + self.provider.complete(prompt, system=self.system_prompt, max_tokens=512)
            except Exception as e:
                self.telemetry.log_error(str(e))
                return {"answer": f"Lỗi LLM: {e}", "steps": steps, "num_steps": step_num, "success": False}

            # --- Thought ---
            thought = _parse_thought(llm_output)
            if thought:
                logger.info(f"[AGENT] Thought: {thought}")
                self.telemetry.log_thought(thought)

            # --- Final Answer? ---
            final_answer = _parse_final_answer(llm_output)
            if final_answer:
                logger.info(f"[AGENT] Final Answer reached at step {step_num}")
                self.telemetry.log_final_answer(final_answer)
                steps.append({"step": step_num, "thought": thought, "final_answer": final_answer})
                return {"answer": final_answer, "steps": steps, "num_steps": step_num, "success": True}

            # --- Action ---
            parsed = _parse_action(llm_output)
            if parsed is None:
                # LLM didn't emit a proper Action — handle gracefully
                logger.warning(f"[AGENT] No action parsed, attempting recovery")
                self.telemetry.log_error("No action parsed")

                # Append a note to the scratchpad for the next iteration
                scratchpad += (
                    f"Thought: {thought}\n"
                    f"Observation: Không thể phân tích hành động từ đầu ra. Vui lòng cung cấp thêm thông tin.\n\n"
                )

                steps.append({
                    "step": step_num,
                    "thought": thought,
                    "parse_error": "Không thể phân tích hành động từ đầu ra."
                })

                # Continue to the next step instead of treating as final answer
                continue

            tool_name, tool_args = parsed
            logger.info(f"[AGENT] Action: {tool_name}({tool_args})")
            self.telemetry.log_action(tool_name, tool_args)

            # --- Observation ---
            observation = self._call_tool(tool_name, tool_args)
            logger.info(f"[AGENT] Observation: {str(observation)[:120]}")
            self.telemetry.log_observation(tool_name, observation)

            steps.append({
                "step": step_num,
                "thought": thought,
                "action": {"tool": tool_name, "args": tool_args},
                "observation": observation,
            })

            # Append to scratchpad for next iteration
            obs_str = json.dumps(observation, ensure_ascii=False)
            scratchpad += (
                f"Thought: {thought}\n"
                f"Action: {{\"tool\": \"{tool_name}\", \"args\": {json.dumps(tool_args, ensure_ascii=False)}}}\n"
                f"Observation: {obs_str}\n\n"
            )

        # Hit MAX_STEPS without final answer
        logger.warning("[AGENT] MAX_STEPS reached without Final Answer")
        self.telemetry.log_error(f"MAX_STEPS ({MAX_STEPS}) reached")
        return {
            "answer": "Đã đạt giới hạn bước suy luận. Vui lòng thử lại với câu hỏi cụ thể hơn.",
            "steps": steps,
            "num_steps": MAX_STEPS,
            "success": False,
        }

# ---------------------------------------------------------------------------
# Comparison Interface
# ---------------------------------------------------------------------------
def run_comparison_interface(query: str):
    """
    Run a user-friendly interface to compare Chatbot and Agent responses.
    Args:
        query: The user query to process.
    """
    from src.chatbot.chatbot import TravelChatbot
    from src.providers.llm_provider import get_provider

    provider = get_provider()

    # Initialize Chatbot and Agent
    chatbot = TravelChatbot(provider, session_id="compare_chatbot")
    agent = TravelReActAgent(provider, session_id="compare_agent")

    print("\n==============================")
    print("⚡ COMPARISON MODE: Chatbot vs ReAct Agent")
    print("==============================")

    # --- Chatbot Response ---
    print("\n🤖 [1/2] CHATBOT RESPONSE")
    print("------------------------------")
    t0 = time.time()
    chatbot_response = chatbot.chat(query)
    chatbot_time = round(time.time() - t0, 2)
    print(f"Chatbot Answer: {chatbot_response}")
    print(f"⏱ Time Taken: {chatbot_time}s")

    # --- Agent Response ---
    print("\n🧠 [2/2] REACT AGENT RESPONSE")
    print("------------------------------")
    t0 = time.time()
    agent_result = agent.run(query)
    agent_time = round(time.time() - t0, 2)

    # Display Agent Steps
    print("\n📋 ReAct Agent Steps:")
    for step in agent_result["steps"]:
        print(f"\n  [Step {step['step']}]")
        if step.get("thought"):
            print(f"  💭 Thought: {step['thought']}")
        if step.get("action"):
            action = step['action']
            print(f"  🔧 Action: {action['tool']}({action['args']})")
        if step.get("observation"):
            obs = step['observation']
            if isinstance(obs, dict) and obs.get("status") == "error":
                print(f"  ⚠️ Observation Error: {obs['message']}")
                print("  🔄 Agent is attempting to find an alternative solution...")
            else:
                print(f"  👁 Observation: {obs}")
        if step.get("final_answer"):
            print(f"  ✅ Final Answer: {step['final_answer']}")

    # Final Agent Answer
    print("\n==============================")
    print(f"✅ Agent Final Answer: {agent_result['answer']}")
    print(f"⏱ Time Taken: {agent_time}s | Steps: {agent_result['num_steps']} | Success: {agent_result['success']}")

    # --- Summary ---
    print("\n==============================")
    print("📊 SUMMARY")
    print("==============================")
    print(f"{'Metric':<25} {'Chatbot':>15} {'ReAct Agent':>15}")
    print("-" * 55)
    print(f"{'Response Time (s)':<25} {chatbot_time:>15} {agent_time:>15}")
    print(f"{'Tool Calls':<25} {'0':>15} {agent_result['num_steps']:>15}")
    print(f"{'Traceable':<25} {'No':>15} {'Yes':>15}")
    print(f"{'Verifiable Data':<25} {'No':>15} {'Yes':>15}")

if __name__ == "__main__":
    user_query = input("Enter your query: ")
    run_comparison_interface(user_query)
