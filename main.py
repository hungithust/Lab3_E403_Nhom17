from src.agent.agent import ReActAgent
from src.core.gemini_provider import GeminiProvider

llm = GeminiProvider(api_key="AIzaSyChmJRJ6Oy-8uw22QShs3C7Oc24yiplUEo")

response = llm.generate("Hello")

print(response)