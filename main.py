from src.agent.agent import ReActAgent
from src.core.gemini_provider import GeminiProvider

llm = GeminiProvider(api_key="")

response = llm.generate("Hello")

print(response)