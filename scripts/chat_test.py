#!/usr/bin/env python3
"""End-to-end validation: Auth + ChatCopilot -> Copilot response."""
import asyncio
import sys
from langchain_core.messages import HumanMessage
from app.auth.manager import CopilotAuthManager
from app.providers.copilot import ChatCopilot


async def main():
    auth = CopilotAuthManager()
    model = sys.argv[1] if len(sys.argv) > 1 else "gpt-4.1"
    llm = ChatCopilot(model=model, auth_manager=auth)
    try:
        print(f"Using model: {model}")
        print("Sending prompt: 'Say hello world only.'")
        result = await llm.ainvoke([HumanMessage(content="Say 'hello world' only.")])
        print(f"Response: {result.content}")
        assert result.content, "ERROR: Empty response from Copilot"
        print(f"PASS: Got non-empty AIMessage response ({len(result.content)} chars)")
    finally:
        await llm.close()


if __name__ == "__main__":
    asyncio.run(main())
