"""
main.py — Interactive CLI to run and compare TravelChatbot vs TravelReActAgent.

Usage:
    python main.py --mode chatbot       # Run simple chatbot
    python main.py --mode agent         # Run ReAct agent
    python main.py --mode compare       # Run both on same query, side by side
    python main.py --mode demo          # Run a preset demo query
"""

import argparse
import json
import sys
import time

from src.providers.llm_provider import get_provider
from src.chatbot.chatbot import TravelChatbot
from src.agent.agent import TravelReActAgent

DEMO_QUERY = (
    "Tôi có 3 ngày ở Đà Nẵng, ngân sách 2 triệu/ngày, "
    "thích ăn hải sản và leo núi. Gợi ý lịch trình và ước tính tổng chi phí."
)

SEPARATOR = "=" * 70


def print_agent_steps(steps: list):
    print("\n📋 ReAct Trace:")
    for s in steps:
        print("đây chính là step:", steps)
        print(f"\n  [Bước {s['step']}]")
        if s.get("thought"):
            print(f"  💭 Thought: {s['thought']}")
        if s.get("action"):
            print(f"  🔧 Action : {s['action']['tool']}({json.dumps(s['action']['args'], ensure_ascii=False)})")
        if s.get("observation"):
            obs = json.dumps(s["observation"], ensure_ascii=False)
            print(f"  👁  Obs   : {obs[:200]}{'...' if len(obs) > 200 else ''}")
        if s.get("final_answer"):
            print(f"  ✅ Final  : (see answer below)")
        if s.get("parse_error"):
            print(f"  ⚠️  Parse error at this step")


def run_chatbot(query: str):
    print(f"\n{SEPARATOR}")
    print("🤖 CHATBOT (single-shot LLM, no tools)")
    print(SEPARATOR)
    print(f"❓ Query: {query}\n")

    provider = get_provider()
    chatbot = TravelChatbot(provider, session_id="chatbot_demo")

    t0 = time.time()
    response = chatbot.chat(query)
    elapsed = round(time.time() - t0, 2)

    print(f"💬 Answer:\n{response}")
    print(f"\n⏱  {elapsed}s | Provider: {provider.name}")


def run_agent(query: str, verbose: bool = True):
    print(f"\n{SEPARATOR}")
    print("🧠 REACT AGENT (Thought → Action → Observation loop)")
    print(SEPARATOR)
    print(f"❓ Query: {query}\n")

    provider = get_provider()
    agent = TravelReActAgent(provider, session_id="agent_demo")

    t0 = time.time()
    result = agent.run(query)
    elapsed = round(time.time() - t0, 2)

    if verbose:
        print_agent_steps(result["steps"])

    print(f"\n{SEPARATOR}")
    print(f"✅ Final Answer:\n{result['answer']}")
    print(f"\n⏱  {elapsed}s | Steps: {result['num_steps']} | Success: {result['success']} | Provider: {provider.name}")


def run_compare(query: str):
    print(f"\n{'#' * 70}")
    print("⚡ COMPARISON MODE: Chatbot  vs  ReAct Agent")
    print(f"{'#' * 70}")

    provider = get_provider()

    # --- Chatbot ---
    print(f"\n{SEPARATOR}")
    print("🤖 [1/2] CHATBOT")
    print(SEPARATOR)
    chatbot = TravelChatbot(provider, session_id="compare_chatbot")
    t0 = time.time()
    cb_response = chatbot.chat(query)
    cb_time = round(time.time() - t0, 2)
    print(cb_response)
    print(f"\n⏱  {cb_time}s")

    # --- Agent ---
    print(f"\n{SEPARATOR}")
    print("🧠 [2/2] REACT AGENT")
    print(SEPARATOR)
    agent = TravelReActAgent(provider, session_id="compare_agent")
    t0 = time.time()
    ag_result = agent.run(query)
    ag_time = round(time.time() - t0, 2)
    print_agent_steps(ag_result["steps"])
    print(f"\n{SEPARATOR}")
    print(ag_result["answer"])
    print(f"\n⏱  {ag_time}s | Steps: {ag_result['num_steps']}")

    # --- Summary ---
    print(f"\n{'#' * 70}")
    print("📊 SUMMARY")
    print(f"{'#' * 70}")
    print(f"{'Metric':<25} {'Chatbot':>15} {'ReAct Agent':>15}")
    print("-" * 55)
    print(f"{'Response time (s)':<25} {cb_time:>15} {ag_time:>15}")
    print(f"{'Tool calls':<25} {'0':>15} {ag_result['num_steps']:>15}")
    print(f"{'Hallucination risk':<25} {'HIGH':>15} {'LOW':>15}")
    print(f"{'Traceable':<25} {'No':>15} {'Yes':>15}")
    print(f"{'Verifiable data':<25} {'No':>15} {'Yes':>15}")


def run_comparison_interface(query: str):
    """
    Run a user-friendly interface to compare Chatbot and Agent responses.
    Args:
        query: The user query to process.
    """
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


def interactive_mode(mode: str):
    provider = get_provider()
    if mode == "chatbot":
        bot = TravelChatbot(provider, session_id="interactive_chatbot")
        print("🤖 Chatbot mode (gõ 'quit' để thoát, 'reset' để xóa lịch sử)\n")
        while True:
            query = input("Bạn: ").strip()
            if query.lower() == "quit":
                break
            if query.lower() == "reset":
                bot.reset()
                print("✅ Đã xóa lịch sử hội thoại\n")
                continue
            print(f"\nChatbot: {bot.chat(query)}\n")
    else:
        agent = TravelReActAgent(provider, session_id="interactive_agent")
        print("🧠 ReAct Agent mode (gõ 'quit' để thoát)\n")
        while True:
            query = input("Bạn: ").strip()
            if query.lower() == "quit":
                break
            result = agent.run(query)
            print_agent_steps(result["steps"])
            print(f"\n✅ {result['answer']}\n")


def main():
    parser = argparse.ArgumentParser(description="Travel Agent — Chatbot vs ReAct Agent")
    parser.add_argument("--mode", choices=["chatbot", "agent", "compare", "demo"],
                        default="demo", help="Run mode")
    parser.add_argument("--query", type=str, default=None, help="Custom query")
    parser.add_argument("--no-trace", action="store_true", help="Hide ReAct trace")
    args = parser.parse_args()

    query = args.query or DEMO_QUERY

    if args.mode == "demo":
        run_compare(query)
    elif args.mode == "chatbot":
        if args.query:
            run_chatbot(query)
        else:
            interactive_mode("chatbot")
    elif args.mode == "agent":
        if args.query:
            run_agent(query, verbose=not args.no_trace)
        else:
            interactive_mode("agent")
    elif args.mode == "compare":
        run_compare(query)


if __name__ == "__main__":
    main()
