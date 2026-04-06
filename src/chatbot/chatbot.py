
"""Simple LLM Chatbot — baseline for comparison with ReAct Agent."""

from __future__ import annotations

from src.providers.llm_provider import LLMProvider
from src.utils.logger import TelemetryLogger, get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """Bạn là trợ lý tư vấn du lịch Việt Nam thân thiện.
Hãy trả lời câu hỏi của người dùng về lịch trình du lịch, địa điểm tham quan, nhà hàng, thời tiết và chi phí dựa trên kiến thức của bạn.
Trả lời bằng tiếng Việt, rõ ràng và hữu ích.
"""


class TravelChatbot:
    """Baseline chatbot — single-shot LLM response, no tool use."""

    def __init__(self, provider: LLMProvider, session_id: str = "chatbot"):
        self.provider = provider
        self.telemetry = TelemetryLogger(session_id)
        self.history: list[dict] = []
        logger.info("TravelChatbot initialized with provider: %s", provider.name)

    def chat(self, user_input: str) -> str:
        """Send a message and get a single-shot response."""
        logger.info("[CHATBOT] User: %s", user_input)
        self.telemetry.start_task("chatbot", user_input, self.provider.name)
        self.telemetry.log("USER_INPUT", {"input": user_input})

        history_text = ""
        for turn in self.history[-4:]:
            history_text += f"Người dùng: {turn['user']}\nTrợ lý: {turn['assistant']}\n\n"

        prompt = f"{history_text}Người dùng: {user_input}\nTrợ lý:"
        try:
            response = self.provider.complete(prompt, system=SYSTEM_PROMPT, max_tokens=1024)
            self.telemetry.log_llm_call(self.provider.pop_last_metrics())
        except Exception as e:
            error_msg = f"Lỗi kết nối LLM: {e}"
            self.telemetry.log_error(str(e), code="llm_error")
            self.telemetry.finish_task(False, answer=error_msg, extra={"num_steps": 1})
            logger.error(error_msg)
            return error_msg

        self.history.append({"user": user_input, "assistant": response})
        self.telemetry.log("CHATBOT_RESPONSE", {"response": response})
        self.telemetry.log_final_answer(response)
        self.telemetry.finish_task(True, answer=response, extra={"num_steps": 1})
        logger.info("[CHATBOT] Response: %s...", response[:80])
        return response

    def reset(self) -> None:
        """Clear conversation history."""
        self.history = []
