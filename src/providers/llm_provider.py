
from __future__ import annotations

import os
import time
from abc import ABC, abstractmethod
from typing import Any, Optional

from dotenv import load_dotenv

load_dotenv()


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _estimate_tokens_fallback(text: str) -> int:
    if not text:
        return 0
    return max(1, round(len(text) / 4))


def _pricing_table() -> dict[str, dict[str, float]]:
    return {
        # Override any entry via env if pricing changes.
        "gpt-4o": {
            "input": _env_float("PRICE_GPT_4O_INPUT_PER_1M", 0.0),
            "output": _env_float("PRICE_GPT_4O_OUTPUT_PER_1M", 0.0),
        },
        "gpt-4o-mini": {
            "input": _env_float("PRICE_GPT_4O_MINI_INPUT_PER_1M", 0.0),
            "output": _env_float("PRICE_GPT_4O_MINI_OUTPUT_PER_1M", 0.0),
        },
        "gemini-1.5-flash": {
            "input": _env_float("PRICE_GEMINI_15_FLASH_INPUT_PER_1M", 0.0),
            "output": _env_float("PRICE_GEMINI_15_FLASH_OUTPUT_PER_1M", 0.0),
        },
        "gemini-1.5-pro": {
            "input": _env_float("PRICE_GEMINI_15_PRO_INPUT_PER_1M", 0.0),
            "output": _env_float("PRICE_GEMINI_15_PRO_OUTPUT_PER_1M", 0.0),
        },
        "local/gguf": {
            "input": 0.0,
            "output": 0.0,
        },
    }


def _estimate_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    pricing = _pricing_table().get(model)
    if pricing is None:
        return 0.0

    return round(
        (prompt_tokens / 1_000_000) * pricing["input"]
        + (completion_tokens / 1_000_000) * pricing["output"],
        8,
    )


class LLMProvider(ABC):
    """Base interface for all LLM providers."""

    def __init__(self) -> None:
        self._last_metrics: dict[str, Any] = {}

    @abstractmethod
    def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 1024,
    ) -> str:
        """Send a prompt and return the text response."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    def _set_last_metrics(self, metrics: dict[str, Any]) -> None:
        self._last_metrics = metrics

    def pop_last_metrics(self) -> dict[str, Any]:
        data = dict(self._last_metrics)
        self._last_metrics = {}
        return data


class OpenAIProvider(LLMProvider):
    def __init__(self, model: str = "gpt-4o"):
        super().__init__()
        from openai import OpenAI

        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model

    @property
    def name(self) -> str:
        return self.model

    def complete(self, prompt: str, system: Optional[str] = None, max_tokens: int = 1024) -> str:
        started = time.perf_counter()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
        )
        text = (response.choices[0].message.content or "").strip()

        usage = getattr(response, "usage", None)
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        total_tokens = int(getattr(usage, "total_tokens", prompt_tokens + completion_tokens) or 0)
        latency_ms = round((time.perf_counter() - started) * 1000, 2)

        self._set_last_metrics(
            {
                "provider": "openai",
                "model": self.model,
                "latency_ms": latency_ms,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "estimated_cost_usd": _estimate_cost_usd(
                    self.model,
                    prompt_tokens,
                    completion_tokens,
                ),
            }
        )
        return text


class GeminiProvider(LLMProvider):
    def __init__(self, model: str = "gemini-1.5-flash"):
        super().__init__()
        import google.generativeai as genai

        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model_name = model
        self._genai = genai

    @property
    def name(self) -> str:
        return self.model_name

    def complete(self, prompt: str, system: Optional[str] = None, max_tokens: int = 1024) -> str:
        started = time.perf_counter()
        model = self._genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system or "",
        )
        response = model.generate_content(
            prompt,
            generation_config={"max_output_tokens": max_tokens},
        )
        text = (getattr(response, "text", "") or "").strip()

        usage = getattr(response, "usage_metadata", None)
        prompt_tokens = int(getattr(usage, "prompt_token_count", 0) or 0)
        completion_tokens = int(getattr(usage, "candidates_token_count", 0) or 0)
        total_tokens = int(getattr(usage, "total_token_count", prompt_tokens + completion_tokens) or 0)

        if total_tokens == 0:
            prompt_tokens = _estimate_tokens_fallback((system or "") + prompt)
            completion_tokens = _estimate_tokens_fallback(text)
            total_tokens = prompt_tokens + completion_tokens

        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        self._set_last_metrics(
            {
                "provider": "google",
                "model": self.model_name,
                "latency_ms": latency_ms,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "estimated_cost_usd": _estimate_cost_usd(
                    self.model_name,
                    prompt_tokens,
                    completion_tokens,
                ),
            }
        )
        return text


class LocalProvider(LLMProvider):
    def __init__(self, model_path: Optional[str] = None):
        super().__init__()
        from llama_cpp import Llama

        path = model_path or os.getenv(
            "LOCAL_MODEL_PATH",
            "./models/Phi-3-mini-4k-instruct-q4.gguf",
        )
        self.llm = Llama(model_path=path, n_ctx=4096, verbose=False)

    @property
    def name(self) -> str:
        return "local/gguf"

    def complete(self, prompt: str, system: Optional[str] = None, max_tokens: int = 1024) -> str:
        started = time.perf_counter()
        full_prompt = (
            f"<|system|>{system}<|end|>\n<|user|>{prompt}<|end|>\n<|assistant|>"
            if system
            else prompt
        )
        output = self.llm(full_prompt, max_tokens=max_tokens, stop=["<|end|>", "<|user|>"])
        text = (output["choices"][0]["text"] or "").strip()

        prompt_tokens = int(output.get("usage", {}).get("prompt_tokens", 0) or 0)
        completion_tokens = int(output.get("usage", {}).get("completion_tokens", 0) or 0)
        if prompt_tokens == 0:
            prompt_tokens = _estimate_tokens_fallback(full_prompt)
        if completion_tokens == 0:
            completion_tokens = _estimate_tokens_fallback(text)

        total_tokens = prompt_tokens + completion_tokens
        latency_ms = round((time.perf_counter() - started) * 1000, 2)

        self._set_last_metrics(
            {
                "provider": "local",
                "model": self.name,
                "latency_ms": latency_ms,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "estimated_cost_usd": 0.0,
            }
        )
        return text


def get_provider() -> LLMProvider:
    """Return the provider configured in .env DEFAULT_PROVIDER."""
    provider = os.getenv("DEFAULT_PROVIDER", "openai").lower()
    model = os.getenv("DEFAULT_MODEL", "gpt-4o")

    if provider == "openai":
        return OpenAIProvider(model=model)
    if provider == "google":
        return GeminiProvider(model=model)
    if provider == "local":
        return LocalProvider()

    raise ValueError(f"Unknown provider: {provider}. Choose from: openai | google | local")
