"""
LLM Provider abstraction — supports OpenAI, Google Gemini, and local GGUF models.
Switch providers via DEFAULT_PROVIDER in .env without changing any other code.
"""

import os
from abc import ABC, abstractmethod
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class LLMProvider(ABC):
    """Base interface for all LLM providers."""

    @abstractmethod
    def complete(self, prompt: str, system: Optional[str] = None, max_tokens: int = 1024) -> str:
        """Send a prompt and return the text response."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------
class OpenAIProvider(LLMProvider):
    def __init__(self, model: str = "gpt-4o"):
        from openai import OpenAI
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model

    @property
    def name(self) -> str:
        return f"openai/{self.model}"

    def complete(self, prompt: str, system: Optional[str] = None, max_tokens: int = 1024) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()


# ---------------------------------------------------------------------------
# Google Gemini
# ---------------------------------------------------------------------------
class GeminiProvider(LLMProvider):
    def __init__(self, model: str = "gemini-1.5-flash"):
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model_name = model
        self._genai = genai

    @property
    def name(self) -> str:
        return f"google/{self.model_name}"

    def complete(self, prompt: str, system: Optional[str] = None, max_tokens: int = 1024) -> str:
        model = self._genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system or "",
        )
        response = model.generate_content(
            prompt,
            generation_config={"max_output_tokens": max_tokens},
        )
        return response.text.strip()


# ---------------------------------------------------------------------------
# Local GGUF via llama-cpp-python
# ---------------------------------------------------------------------------
class LocalProvider(LLMProvider):
    def __init__(self, model_path: Optional[str] = None):
        from llama_cpp import Llama
        path = model_path or os.getenv("LOCAL_MODEL_PATH", "./models/Phi-3-mini-4k-instruct-q4.gguf")
        self.llm = Llama(model_path=path, n_ctx=4096, verbose=False)

    @property
    def name(self) -> str:
        return "local/gguf"

    def complete(self, prompt: str, system: Optional[str] = None, max_tokens: int = 1024) -> str:
        full_prompt = f"<|system|>{system}<|end|>\n<|user|>{prompt}<|end|>\n<|assistant|>" if system else prompt
        output = self.llm(full_prompt, max_tokens=max_tokens, stop=["<|end|>", "<|user|>"])
        return output["choices"][0]["text"].strip()


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def get_provider() -> LLMProvider:
    """Return the provider configured in .env DEFAULT_PROVIDER."""
    provider = os.getenv("DEFAULT_PROVIDER", "openai").lower()
    model = os.getenv("DEFAULT_MODEL", "gpt-4o")

    if provider == "openai":
        return OpenAIProvider(model=model)
    elif provider == "google":
        return GeminiProvider(model=model)
    elif provider == "local":
        return LocalProvider()
    else:
        raise ValueError(f"Unknown provider: {provider}. Choose from: openai | google | local")
