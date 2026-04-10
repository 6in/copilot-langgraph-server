"""Tests for ToolEnabledSubAgent and build_react_graph.

Tests use mock LLM and tools — no Copilot SDK credentials required.
Covers TOOL-01 (ReAct loop), TOOL-02 (recursion limit), TOOL-03 (ToolMessage).
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.messages.tool import ToolCall
from langchain_core.tools import BaseTool

from app.orchestrator.context import RPCContext


def make_state(input_text: str = "test input") -> dict:
    return {
        "input": input_text,
        "output": "",
        "messages": [],
        "next": "",
        "error": None,
        "agent_name": None,
        "context": RPCContext.from_http(user_id="test", app_id="test", thread_id="t1"),
    }


@pytest.fixture
def mock_copilot_cls():
    """Patch ChatCopilot so no Copilot SDK is instantiated."""
    with patch("app.providers.copilot.CopilotClient"), \
         patch("app.providers.copilot.SubprocessConfig"), \
         patch("app.providers.copilot.PermissionHandler"):
        yield


@pytest.mark.asyncio
async def test_tool_enabled_subagent_runs_react_loop(mock_copilot_cls):
    """TOOL-01: ToolEnabledSubAgent.run() executes mini ReAct loop via ToolNode.

    LLM first returns a tool_call, then a plain text response → loop ends.
    ToolMessage must appear in result["messages"] (TOOL-03).
    """
    from app.orchestrator.tool_agent import ToolEnabledSubAgent

    # --- mock tool ---
    mock_tool = MagicMock(spec=BaseTool)
    mock_tool.name = "ping"
    mock_tool.ainvoke = AsyncMock(return_value="pong")
    # ToolNode calls tool.description and tool.args_schema for schema; provide stubs
    mock_tool.description = "A ping tool"
    mock_tool.args_schema = None

    # --- mock LLM ---
    mock_llm = AsyncMock()
    mock_llm.bind_tools = MagicMock(return_value=mock_llm)

    tool_call = ToolCall(name="ping", args={"message": "hi"}, id="c1")
    # 1st call: tool_call response
    # 2nd call: final text response
    mock_llm.ainvoke = AsyncMock(
        side_effect=[
            AIMessage(content="", tool_calls=[tool_call]),
            AIMessage(content="pong result"),
        ]
    )

    agent = ToolEnabledSubAgent(
        name="test-agent",
        description="テスト用エージェント。対象外: なし",
        model="gpt-4.1",
        system_prompt="You are helpful.",
        github_token="ghu_test",
        tools=[mock_tool],
    )
    # Replace _llm_with_tools with our mock (bind_tools was already called in __init__)
    agent._llm_with_tools = mock_llm

    state = make_state("ping test")
    result = await agent.run(state)

    assert result["output"] == "pong result", f"Got: {result['output']}"
    assert result["agent_name"] == "test-agent"
    # TOOL-03: ToolMessage must be in messages
    assert any(isinstance(m, ToolMessage) for m in result["messages"]), (
        "Expected ToolMessage in result['messages']"
    )


@pytest.mark.asyncio
async def test_react_loop_stops_at_limit(mock_copilot_cls):
    """TOOL-02: GraphRecursionError is caught and partial result is returned.

    Uses a small recursion_limit to trigger the limit quickly.
    """
    from app.orchestrator.tool_agent import ToolEnabledSubAgent, build_react_graph
    from langgraph.prebuilt import ToolNode

    mock_tool = MagicMock(spec=BaseTool)
    mock_tool.name = "infinite"
    mock_tool.ainvoke = AsyncMock(return_value="keep going")
    mock_tool.description = "Infinite loop tool"
    mock_tool.args_schema = None

    mock_llm = AsyncMock()
    mock_llm.bind_tools = MagicMock(return_value=mock_llm)

    # Always return a tool call → infinite loop
    tool_call = ToolCall(name="infinite", args={}, id="c2")
    mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="", tool_calls=[tool_call]))

    agent = ToolEnabledSubAgent(
        name="looping-agent",
        description="Loop agent. 対象外: なし",
        model="gpt-4.1",
        system_prompt="Loop forever.",
        github_token="ghu_test",
        tools=[mock_tool],
    )
    agent._llm_with_tools = mock_llm

    # Build graph with small recursion_limit
    tool_node = ToolNode([mock_tool])
    mini_graph = build_react_graph(mock_llm, tool_node)

    # Should NOT raise — GraphRecursionError is caught internally in run()
    # We trigger the limit by patching DEFAULT_RECURSION_LIMIT to a small value
    original_limit = ToolEnabledSubAgent.DEFAULT_RECURSION_LIMIT
    try:
        ToolEnabledSubAgent.DEFAULT_RECURSION_LIMIT = 5
        state = make_state("loop forever")
        result = await agent.run(state)
    finally:
        ToolEnabledSubAgent.DEFAULT_RECURSION_LIMIT = original_limit

    # Partial result returned (output may be fallback message)
    assert "output" in result
    assert result["output"] is not None


@pytest.mark.asyncio
async def test_tool_enabled_subagent_no_tool_call(mock_copilot_cls):
    """TOOL-01: When LLM returns plain text (no tool_calls), result is returned directly.

    ToolNode is not invoked; loop ends immediately at agent node.
    """
    from app.orchestrator.tool_agent import ToolEnabledSubAgent

    mock_llm = AsyncMock()
    mock_llm.bind_tools = MagicMock(return_value=mock_llm)
    mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="direct answer"))

    agent = ToolEnabledSubAgent(
        name="direct-agent",
        description="Direct agent. 対象外: なし",
        model="gpt-4.1",
        system_prompt="Answer directly.",
        github_token="ghu_test",
        tools=[],
    )
    agent._llm_with_tools = mock_llm

    state = make_state("what is 2+2?")
    result = await agent.run(state)

    assert result["output"] == "direct answer"
    assert result["agent_name"] == "direct-agent"
    # No tool messages expected
    tool_msgs = [m for m in result["messages"] if isinstance(m, ToolMessage)]
    assert len(tool_msgs) == 0
