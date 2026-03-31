#!/usr/bin/env python3
"""Integration validation: LangGraph graph + ChatCopilot multi-turn & thread isolation."""
import asyncio
import sys
import uuid

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from app.auth.manager import CopilotAuthManager
from app.graph.builder import build_graph
from app.providers.copilot import ChatCopilot


async def main():
    auth = CopilotAuthManager()
    model = sys.argv[1] if len(sys.argv) > 1 else "gpt-4.1"
    llm = ChatCopilot(model=model, auth_manager=auth)
    checkpointer = MemorySaver()
    graph = build_graph(llm, checkpointer)

    thread_a = str(uuid.uuid4())
    thread_b = str(uuid.uuid4())

    try:
        print(f"Using model: {model}")
        print(f"Thread A: {thread_a}")
        print(f"Thread B: {thread_b}")
        print()

        # --- GRPH-01: Multi-turn history ---
        print("=== GRPH-01: Multi-turn history ===")
        config_a = {"configurable": {"thread_id": thread_a}}

        print("Turn 1: 'My name is Alice.'")
        result1 = await graph.ainvoke(
            {"messages": [HumanMessage(content="My name is Alice.")]},
            config=config_a,
        )
        reply1 = result1["messages"][-1].content
        print(f"  Reply: {reply1}")
        assert reply1, "ERROR: Empty response on turn 1"

        print("Turn 2: 'What is my name?'")
        result2 = await graph.ainvoke(
            {"messages": [HumanMessage(content="What is my name?")]},
            config=config_a,
        )
        reply2 = result2["messages"][-1].content
        print(f"  Reply: {reply2}")
        assert reply2, "ERROR: Empty response on turn 2"

        # Check history accumulated (result2 should have 4 messages: H, A, H, A)
        assert len(result2["messages"]) == 4, (
            f"ERROR: Expected 4 messages in thread A, got {len(result2['messages'])}"
        )
        print(f"  PASS: Thread A has {len(result2['messages'])} messages (multi-turn history works)")

        # Check the reply mentions Alice (heuristic -- LLM should recall the name)
        if "alice" in reply2.lower():
            print("  PASS: Reply references 'Alice' (context retained)")
        else:
            print(f"  WARN: Reply does not contain 'Alice' -- manual check needed: {reply2}")

        print()

        # --- GRPH-02: Thread isolation ---
        print("=== GRPH-02: Thread isolation ===")
        config_b = {"configurable": {"thread_id": thread_b}}

        print("Thread B Turn 1: 'What is my name?'")
        result3 = await graph.ainvoke(
            {"messages": [HumanMessage(content="What is my name?")]},
            config=config_b,
        )
        reply3 = result3["messages"][-1].content
        print(f"  Reply: {reply3}")
        assert reply3, "ERROR: Empty response on thread B"

        # Thread B should only have 2 messages (H + A)
        assert len(result3["messages"]) == 2, (
            f"ERROR: Expected 2 messages in thread B, got {len(result3['messages'])}"
        )
        print(f"  PASS: Thread B has {len(result3['messages'])} messages (isolated from A)")

        if "alice" not in reply3.lower():
            print("  PASS: Thread B does not know 'Alice' (thread isolation works)")
        else:
            print(f"  WARN: Thread B mentions 'Alice' -- possible isolation issue: {reply3}")

        print()
        print("=== All graph validations passed ===")

    finally:
        await llm.close()


if __name__ == "__main__":
    asyncio.run(main())
