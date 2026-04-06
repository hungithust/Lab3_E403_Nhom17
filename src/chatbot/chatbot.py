"""
Simple LLM Chatbot — Baseline for comparison with ReAct Agent.

The chatbot answers in a single LLM call with no tools.
Observe how it handles multi-step reasoning vs the ReAct Agent.
"""

from src.providers.llm_provider import LLMProvider
from src.utils.logger import TelemetryLogger, get_logger

logger = get_logger(__name__)

SYSTEM_PROMPT = """Bạn là trợ lý tư vấn du lịch Việt Nam thân thiện.
Hãy trả lời câu hỏi của người dùng về lịch trình du lịch, địa điểm tham quan,
nhà hàng, thời tiết và chi phí dựa trên kiến thức của bạn.
Trả lời bằng tiếng Việt, rõ ràng và hữu ích.
"""


class TravelChatbot:
    """
    Baseline chatbot — single-shot LLM response, no tool use.

    Limitations you will observe:
    - May hallucinate prices, distances, or weather data
    - Cannot perform real calculations
    - Cannot verify real-time information
    """

    def __init__(self, provider: LLMProvider, session_id: str = "chatbot"):
        self.provider = provider
        self.telemetry = TelemetryLogger(session_id)
        self.history: list[dict] = []
        logger.info(f"TravelChatbot initialized with provider: {provider.name}")

    def chat(self, user_input: str) -> str:
        """Send a message and get a single-shot response."""
        logger.info(f"[CHATBOT] User: {user_input}")
        self.telemetry.log("USER_INPUT", {"input": user_input})

        # Build a simple history string for context
        history_text = ""
        for turn in self.history[-4:]:
            history_text += f"Người dùng: {turn['user']}\nTrợ lý: {turn['assistant']}\n\n"

        prompt = f"{history_text}Người dùng: {user_input}\nTrợ lý:"

        try:
            response = self.provider.complete(prompt, system=SYSTEM_PROMPT, max_tokens=1024)
        except Exception as e:
            error_msg = f"Lỗi kết nối LLM: {e}"
            self.telemetry.log_error(str(e))
            logger.error(error_msg)
            return error_msg

        self.history.append({"user": user_input, "assistant": response})
        self.telemetry.log("CHATBOT_RESPONSE", {"response": response})
        logger.info(f"[CHATBOT] Response: {response[:80]}...")
        return response

    def reset(self):
        """Clear conversation history."""
        self.history = []
