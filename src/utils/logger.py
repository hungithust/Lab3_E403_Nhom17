
from __future__ import annotations

import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_now() -> str:
    return _utc_now().isoformat()


def _safe_name(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]+", "_", value.strip())
    return cleaned.strip("._") or f"session_{uuid.uuid4().hex[:8]}"


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    logger.addHandler(handler)
    logger.propagate = False
    return logger


class TelemetryLogger:
    """
    Structured telemetry logger for one chatbot/agent run.

    It writes a single JSON file per run in logs/ so you can aggregate:
    - latency
    - token usage
    - cost
    - loop count
    - error metrics
    """

    def __init__(self, session_id: str, log_dir: str = "logs"):
        self.session_id = session_id
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = _utc_now().strftime("%Y%m%dT%H%M%SZ")
        self.file_path = self.log_dir / f"{_safe_name(session_id)}_{timestamp}.json"

        self.run_data: dict[str, Any] = {
            "schema_version": 1,
            "session_id": session_id,
            "created_at": _iso_now(),
            "started_at": None,
            "finished_at": None,
            "task_type": None,
            "query": None,
            "provider": None,
            "success": None,
            "answer_preview": None,
            "events": [],
            "llm_calls": [],
            "thoughts": [],
            "actions": [],
            "observations": [],
            "errors": [],
            "final_answer": None,
            "metrics": {
                "duration_ms": None,
                "num_llm_calls": 0,
                "num_steps": 0,
                "num_tool_calls": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "estimated_cost_usd": 0.0,
                "error_count": 0,
            },
        }
        self._started_monotonic: float | None = None
        self._persist()

    def _persist(self) -> None:
        self.file_path.write_text(
            json.dumps(self.run_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _append_event(self, event_type: str, data: dict[str, Any]) -> None:
        self.run_data["events"].append(
            {
                "timestamp": _iso_now(),
                "event": event_type,
                "data": data,
            }
        )
        self._persist()

    def start_task(self, task_type: str, query: str, provider_name: str) -> None:
        import time

        self._started_monotonic = time.perf_counter()
        self.run_data["started_at"] = _iso_now()
        self.run_data["task_type"] = task_type
        self.run_data["query"] = query
        self.run_data["provider"] = provider_name
        self._append_event(
            "TASK_START",
            {
                "task_type": task_type,
                "provider": provider_name,
                "query": query,
            },
        )

    def finish_task(
        self,
        success: bool,
        answer: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        import time

        finished_at = _iso_now()
        self.run_data["finished_at"] = finished_at
        self.run_data["success"] = success
        self.run_data["answer_preview"] = (answer or "")[:300]
        if answer is not None:
            self.run_data["final_answer"] = answer

        duration_ms = None
        if self._started_monotonic is not None:
            duration_ms = round((time.perf_counter() - self._started_monotonic) * 1000, 2)

        metrics = self.run_data["metrics"]
        metrics["duration_ms"] = duration_ms
        metrics["num_llm_calls"] = len(self.run_data["llm_calls"])
        metrics["num_tool_calls"] = len(self.run_data["actions"])
        metrics["num_steps"] = extra.get("num_steps") if extra else metrics["num_tool_calls"]
        metrics["error_count"] = len(self.run_data["errors"])

        if extra:
            self.run_data["extra"] = extra

        self._append_event(
            "TASK_END",
            {
                "success": success,
                "duration_ms": duration_ms,
                "extra": extra or {},
            },
        )

    def log(self, event_type: str, data: dict[str, Any]) -> None:
        self._append_event(event_type, data)

    def log_llm_call(self, metrics: dict[str, Any]) -> None:
        if not metrics:
            return

        prompt_tokens = int(metrics.get("prompt_tokens") or 0)
        completion_tokens = int(metrics.get("completion_tokens") or 0)
        total_tokens = int(metrics.get("total_tokens") or (prompt_tokens + completion_tokens))
        estimated_cost_usd = float(metrics.get("estimated_cost_usd") or 0.0)

        entry = {
            "timestamp": _iso_now(),
            **metrics,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": round(estimated_cost_usd, 8),
        }
        self.run_data["llm_calls"].append(entry)

        agg = self.run_data["metrics"]
        agg["prompt_tokens"] += prompt_tokens
        agg["completion_tokens"] += completion_tokens
        agg["total_tokens"] += total_tokens
        agg["estimated_cost_usd"] = round(agg["estimated_cost_usd"] + estimated_cost_usd, 8)

        self._append_event("LLM_CALL", entry)

    def log_error(
        self,
        message: str,
        code: str = "runtime_error",
        extra: dict[str, Any] | None = None,
    ) -> None:
        payload = {
            "code": code,
            "message": message,
            "extra": extra or {},
        }
        self.run_data["errors"].append(payload)
        self._append_event("ERROR", payload)

    def log_thought(self, thought: str) -> None:
        self.run_data["thoughts"].append(thought)
        self._append_event("THOUGHT", {"text": thought})

    def log_action(self, tool_name: str, args: dict[str, Any]) -> None:
        payload = {"tool": tool_name, "args": args}
        self.run_data["actions"].append(payload)
        self._append_event("ACTION", payload)

    def log_observation(self, tool_name: str, observation: Any) -> None:
        payload = {"tool": tool_name, "observation": observation}
        self.run_data["observations"].append(payload)
        self._append_event("OBSERVATION", payload)

    def log_final_answer(self, answer: str) -> None:
        self.run_data["final_answer"] = answer
        self._append_event("FINAL_ANSWER", {"answer_preview": answer[:300]})


IndustryLogger = TelemetryLogger
logger = get_logger("travel-agent")
