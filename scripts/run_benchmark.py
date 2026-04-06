
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.agent.agent import TravelReActAgent
from src.chatbot.chatbot import TravelChatbot
from src.providers.llm_provider import get_provider
from scripts.summarize_telemetry import load_runs, print_report, summarize


def load_cases(path: str) -> list[str]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list) or not all(isinstance(x, str) for x in data):
        raise ValueError("File case phải là JSON array gồm các câu hỏi string.")
    return data


def run_one(mode: str, query: str, session_id: str) -> None:
    provider = get_provider()
    if mode == "chatbot":
        bot = TravelChatbot(provider, session_id=session_id)
        bot.chat(query)
        return

    agent = TravelReActAgent(provider, session_id=session_id)
    agent.run(query)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a benchmark suite and write telemetry logs.")
    parser.add_argument("--mode", choices=["chatbot", "agent"], default="agent")
    parser.add_argument("--cases", default="tests/benchmark_cases.json")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--log-dir", default="logs")
    args = parser.parse_args()

    cases = load_cases(args.cases)
    benchmark_id = f"bench_{args.mode}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

    print(f"Benchmark ID: {benchmark_id}")
    print(f"Số câu hỏi   : {len(cases)}")
    print(f"Số vòng lặp  : {args.runs}")

    counter = 0
    for run_idx in range(1, args.runs + 1):
        for case_idx, query in enumerate(cases, start=1):
            counter += 1
            session_id = f"{benchmark_id}_{case_idx:02d}_run{run_idx}"
            print(f"[{counter}] {session_id}")
            run_one(args.mode, query, session_id)

    runs = load_runs(Path(args.log_dir), session_prefix=benchmark_id)
    summary = summarize(runs)
    summary_path = Path(args.log_dir) / f"{benchmark_id}_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print_report(summary)
    print(f"\nĐã lưu summary tại: {summary_path}")


if __name__ == "__main__":
    main()
