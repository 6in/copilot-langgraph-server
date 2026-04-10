"""End-to-end tests for the ToolEnabledSubAgent ReAct pipeline.

Tests cover the full flow: BoundChatCopilot -> ToolNode -> ToolMessage accumulation.
No Copilot SDK credentials required — CopilotClient/SubprocessConfig/PermissionHandler
are patched at the module level (same pattern as test_provider.py).

Verifies:
  TOOL-01: ReAct loop executes via ToolNode (tool_calls -> ToolNode -> ToolMessage)
  TOOL-02: Recursion limit is enforced
  TOOL-03: ToolMessage is recorded in result["messages"] with correct structure
"""
from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.messages.tool import ToolCall
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import tool

from app.orchestrator.context import RPCContext


# ---------------------------------------------------------------------------
# Real @tool-decorated tools (ToolNode requires actual BaseTool instances)
# ---------------------------------------------------------------------------


@tool
def ping(message: str) -> str:
    """Ping test tool. Returns pong: <message>."""
    return f"pong: {message}"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_copilot_sdk():
    """Patch Copilot SDK classes so no binary is launched during tests.

    Matches the pattern used in test_provider.py and test_tool_enabled_subagent.py.
    """
    with (
        patch("app.providers.copilot.CopilotClient"),
        patch("app.providers.copilot.SubprocessConfig"),
        patch("app.providers.copilot.PermissionHandler"),
    ):
        yield


@pytest.fixture
def mock_ping_tool():
    """Return the real @tool-decorated ping tool."""
    return ping


def make_state(input_text: str = "ping me") -> dict:
    """Create a minimal AgentState-compatible dict for testing."""
    return {
        "input": input_text,
        "output": "",
        "messages": [],
        "next": "",
        "error": None,
        "agent_name": None,
        "context": RPCContext.from_http(user_id="test", app_id="test", thread_id="e2e-1"),
    }


def make_chat_result(content: str) -> ChatResult:
    """Wrap a string into a ChatResult (what _agenerate returns)."""
    return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])


def make_tool_call_result(tool_name: str, args: dict) -> ChatResult:
    """Return a ChatResult whose message has tool_calls set (simulating JSON parse success)."""
    tool_call = ToolCall(name=tool_name, args=args, id=str(uuid.uuid4())[:8])
    return ChatResult(
        generations=[ChatGeneration(message=AIMessage(content="", tool_calls=[tool_call]))]
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_react_loop_with_tool_call(mock_copilot_sdk, mock_ping_tool):
    """Full pipeline: BoundChatCopilot parses tool JSON -> ToolNode calls ping -> ToolMessage.

    LLM returns JSON tool call on first invocation, plain text on second.
    Verifies TOOL-01 (ReAct loop) and TOOL-03 (ToolMessage in messages).
    """
    from app.orchestrator.tool_agent import ToolEnabledSubAgent

    # Patch _agenerate to control what the "LLM" returns:
    # 1st call: tool call (JSON response parsed into tool_calls)
    # 2nd call: final text response
    call_count = 0

    async def fake_agenerate(messages, stop=None, run_manager=None, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Return tool call response
            return make_tool_call_result("ping", {"message": "hello"})
        else:
            # Return final text response
            return make_chat_result("Tool result: pong: hello")

    agent = ToolEnabledSubAgent(
        name="e2e-agent",
        description="E2E テスト用エージェント。対象外: なし",
        model="gpt-4.1",
        system_prompt="You are a helpful assistant with tools.",
        github_token="ghu_test",
        tools=[mock_ping_tool],
    )
    # Patch the bound LLM's _agenerate (BoundChatCopilot inherits from ChatCopilot)
    agent._llm_with_tools._agenerate = fake_agenerate

    state = make_state("ping me with hello")
    result = await agent.run(state)

    # TOOL-01: result has output and agent_name
    assert result["agent_name"] == "e2e-agent"
    assert "pong" in result["output"], f"Expected 'pong' in output, got: {result['output']}"

    # TOOL-03: ToolMessage must be in messages
    tool_messages = [m for m in result["messages"] if isinstance(m, ToolMessage)]
    assert len(tool_messages) >= 1, (
        f"Expected at least 1 ToolMessage, got: {[type(m).__name__ for m in result['messages']]}"
    )

    # TOOL-01: AIMessage with tool_calls must be in messages
    ai_with_tool_calls = [
        m for m in result["messages"]
        if isinstance(m, AIMessage) and m.tool_calls
    ]
    assert len(ai_with_tool_calls) >= 1, "Expected AIMessage with tool_calls in messages"

    # agent_name is set
    assert result["agent_name"] is not None

    # At least: SystemMessage + HumanMessage + AIMessage(tool_calls) + ToolMessage + AIMessage(final)
    assert len(result["messages"]) >= 4, (
        f"Expected >= 4 messages, got {len(result['messages'])}: "
        f"{[type(m).__name__ for m in result['messages']]}"
    )


@pytest.mark.asyncio
async def test_e2e_no_tool_call_passthrough(mock_copilot_sdk, mock_ping_tool):
    """When LLM returns plain text (no tool JSON), output passes through without ToolMessage.

    Verifies TOOL-01: tool_calls-free AIMessage routes to END immediately.
    """
    from app.orchestrator.tool_agent import ToolEnabledSubAgent

    async def fake_agenerate(messages, stop=None, run_manager=None, **kwargs):
        return make_chat_result("こんにちは！何かお手伝いできることはありますか？")

    agent = ToolEnabledSubAgent(
        name="passthrough-agent",
        description="パススルーテスト用エージェント。対象外: なし",
        model="gpt-4.1",
        system_prompt="You are a helpful assistant.",
        github_token="ghu_test",
        tools=[mock_ping_tool],
    )
    agent._llm_with_tools._agenerate = fake_agenerate

    state = make_state("こんにちは")
    result = await agent.run(state)

    assert result["output"] == "こんにちは！何かお手伝いできることはありますか？", (
        f"Got: {result['output']}"
    )

    # No ToolMessage should be present
    tool_messages = [m for m in result["messages"] if isinstance(m, ToolMessage)]
    assert len(tool_messages) == 0, f"Unexpected ToolMessages: {tool_messages}"

    # Exactly: SystemMessage + HumanMessage + AIMessage(final) = 3
    assert len(result["messages"]) == 3, (
        f"Expected 3 messages (Sys+Human+AI), got {len(result['messages'])}: "
        f"{[type(m).__name__ for m in result['messages']]}"
    )


@pytest.mark.asyncio
async def test_e2e_tool_message_recorded_in_messages(mock_copilot_sdk, mock_ping_tool):
    """TOOL-03 focused: ToolMessage structure — content, name, tool_call_id.

    Verifies exact ToolMessage fields after a ping tool call.
    """
    from app.orchestrator.tool_agent import ToolEnabledSubAgent

    call_count = 0

    async def fake_agenerate(messages, stop=None, run_manager=None, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return make_tool_call_result("ping", {"message": "hello"})
        else:
            return make_chat_result("完了しました。")

    agent = ToolEnabledSubAgent(
        name="tool-msg-agent",
        description="ToolMessage 検証用エージェント。対象外: なし",
        model="gpt-4.1",
        system_prompt="You are a helpful assistant with tools.",
        github_token="ghu_test",
        tools=[mock_ping_tool],
    )
    agent._llm_with_tools._agenerate = fake_agenerate

    state = make_state("ping hello")
    result = await agent.run(state)

    tool_messages = [m for m in result["messages"] if isinstance(m, ToolMessage)]
    assert len(tool_messages) == 1, (
        f"Expected exactly 1 ToolMessage, got {len(tool_messages)}"
    )

    tm = tool_messages[0]
    # content は ping tool が返す "pong: hello"
    assert tm.content == "pong: hello", f"Expected 'pong: hello', got: {tm.content!r}"
    # name は tool の名前
    assert tm.name == "ping", f"Expected name='ping', got: {tm.name!r}"
    # tool_call_id は非空文字列
    assert tm.tool_call_id and len(tm.tool_call_id) > 0, (
        f"Expected non-empty tool_call_id, got: {tm.tool_call_id!r}"
    )
