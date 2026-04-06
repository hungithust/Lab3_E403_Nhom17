
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from statistics import median
from typing import Any


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    if len(values) == 1:
        return float(values[0])
    rank = (len(values) - 1) * p
    lower = int(rank)
    upper = min(lower + 1, len(values) - 1)
    if lower == upper:
        return float(values[lower])
    weight = rank - lower
    return float(values[lower] * (1 - weight) + values[upper] * weight)


def load_runs(log_dir: Path, session_prefix: str | None = None) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for path in sorted(log_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if data.get("schema_version") != 1:
            continue
        session_id = str(data.get("session_id", ""))
        if session_prefix and not session_id.startswith(session_prefix):
            continue
        runs.append(data)
    return runs


def summarize(runs: list[dict[str, Any]]) -> dict[str, Any]:
    latencies = []
    total_tokens = []
    loop_counts = []
    costs = []
    success_count = 0
    error_counter = Counter()
    by_task_type = Counter()

    for run in runs:
        metrics = run.get("metrics", {})
        by_task_type.update([run.get("task_type") or "unknown"])

        duration_ms = metrics.get("duration_ms")
        if isinstance(duration_ms, (int, float)):
            latencies.append(float(duration_ms))

        total = metrics.get("total_tokens")
        if isinstance(total, (int, float)):
            total_tokens.append(float(total))

        loops = metrics.get("num_steps")
        if isinstance(loops, (int, float)):
            loop_counts.append(float(loops))

        cost = metrics.get("estimated_cost_usd")
        if isinstance(cost, (int, float)):
            costs.append(float(cost))

        if run.get("success") is True:
            success_count += 1

        for err in run.get("errors", []):
            code = err.get("code", "unknown_error")
            error_counter.update([code])

    count = len(runs)
    return {
        "num_tasks": count,
        "success_rate": round(success_count / count, 4) if count else 0.0,
        "p50_latency_ms": round(median(latencies), 2) if latencies else 0.0,
        "p99_latency_ms": round(percentile(latencies, 0.99), 2) if latencies else 0.0,
        "avg_tokens_per_task": round(sum(total_tokens) / count, 2) if count else 0.0,
        "total_cost_usd": round(sum(costs), 8),
        "avg_loops_per_task": round(sum(loop_counts) / count, 2) if count else 0.0,
        "error_breakdown": dict(error_counter),
        "task_type_breakdown": dict(by_task_type),
    }


def print_report(summary: dict[str, Any]) -> None:
    print("\n=== TELEMETRY SUMMARY ===")
    print(f"Số tác vụ               : {summary['num_tasks']}")
    print(f"Tỷ lệ thành công        : {summary['success_rate'] * 100:.2f}%")
    print(f"P50 latency             : {summary['p50_latency_ms']} ms")
    print(f"P99 latency             : {summary['p99_latency_ms']} ms")
    print(f"Token trung bình / task : {summary['avg_tokens_per_task']}")
    print(f"Tổng chi phí            : ${summary['total_cost_usd']}")
    print(f"Loop trung bình / task  : {summary['avg_loops_per_task']}")
    print(f"Lỗi                     : {summary['error_breakdown']}")
    print(f"Loại tác vụ             : {summary['task_type_breakdown']}")

    print("\nMarkdown dùng cho report:")
    print(f"- **Độ trễ trung bình (P50)**: {summary['p50_latency_ms']} ms")
    print(f"- **Độ trễ cực đại (P99)**: {summary['p99_latency_ms']} ms")
    print(f"- **Số token trung bình mỗi tác vụ**: {summary['avg_tokens_per_task']}")
    print(f"- **Tổng chi phí bộ test**: ${summary['total_cost_usd']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize telemetry JSON logs.")
    parser.add_argument("--log-dir", default="logs")
    parser.add_argument("--session-prefix", default=None)
    parser.add_argument("--output", default=None, help="Optional output JSON path")
    args = parser.parse_args()

    runs = load_runs(Path(args.log_dir), args.session_prefix)
    summary = summarize(runs)
    print_report(summary)

    if args.output:
        Path(args.output).write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
