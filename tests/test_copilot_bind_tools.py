"""Unit tests for ChatCopilot.bind_tools() and BoundChatCopilot.

Covers TOOL-01: bind_tools() + BoundChatCopilot implementation.
All Copilot SDK interactions are mocked — tests do NOT require SDK credentials.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import BaseTool

from app.providers.copilot import ChatCopilot, BoundChatCopilot


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_copilot():
    """Mock CopilotClient, SubprocessConfig, and PermissionHandler at the
    module level inside app.providers.copilot — same pattern as test_provider.py.
    """
    with (
        patch("app.providers.copilot.CopilotClient") as MockClient,
        patch("app.providers.copilot.SubprocessConfig") as MockConfig,
        patch("app.providers.copilot.PermissionHandler") as MockHandler,
    ):
        client_instance = AsyncMock()
        MockClient.return_value = client_instance

        session = AsyncMock()
        client_instance.create_session = AsyncMock(return_value=session)

        response = MagicMock()
        response.data.content = "mocked response"
        session.send_and_wait = AsyncMock(return_value=response)

        yield {
            "client_cls": MockClient,
            "config_cls": MockConfig,
            "handler": MockHandler,
            "client": client_instance,
            "session": session,
            "response": response,
        }


@pytest.fixture
def mock_tool():
    """A mock BaseTool with name='ping', description='test', and a simple JSON schema."""
    tool = MagicMock(spec=BaseTool)
    tool.name = "ping"
    tool.description = "test"
    tool.get_input_jsonschema = MagicMock(
        return_value={"type": "object", "properties": {}}
    )
    return tool


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_bind_tools_returns_bound_copilot(mock_copilot, mock_tool):
    """bind_tools([tool]) returns a BoundChatCopilot instance."""
    provider = ChatCopilot(github_token="ghu_test")
    bound = provider.bind_tools([mock_tool])
    assert isinstance(bound, BoundChatCopilot)


@pytest.mark.asyncio
async def test_bound_copilot_parses_tool_call_json(mock_copilot, mock_tool):
    """BoundChatCopilot._agenerate() parses JSON {tool, args} into AIMessage(tool_calls=[...])."""
    mock_copilot["response"].data.content = '{"tool": "ping", "args": {"message": "hello"}}'

    bound = BoundChatCopilot(tools=[mock_tool], model="gpt-4.1", github_token="ghu_test")
    result = await bound._agenerate([HumanMessage(content="test")])

    assert len(result.generations) == 1
    msg = result.generations[0].message
    assert len(msg.tool_calls) == 1
    assert msg.tool_calls[0]["name"] == "ping"
    assert msg.tool_calls[0]["args"] == {"message": "hello"}


@pytest.mark.asyncio
async def test_bound_copilot_normal_text_response(mock_copilot, mock_tool):
    """BoundChatCopilot._agenerate() returns AIMessage(content=...) for plain text responses."""
    mock_copilot["response"].data.content = "This is a normal response"

    bound = BoundChatCopilot(tools=[mock_tool], model="gpt-4.1", github_token="ghu_test")
    result = await bound._agenerate([HumanMessage(content="hello")])

    assert result.generations[0].message.content == "This is a normal response"
    assert result.generations[0].message.tool_calls == []


@pytest.mark.asyncio
async def test_bound_copilot_injects_system_prompt(mock_copilot, mock_tool):
    """BoundChatCopilot._agenerate() injects tool schemas into the system prompt."""
    mock_copilot["response"].data.content = "normal text"

    bound = BoundChatCopilot(tools=[mock_tool], model="gpt-4.1", github_token="ghu_test")
    await bound._agenerate([HumanMessage(content="hello")])

    # send_and_wait should have been called with a string containing tool info
    call_args = mock_copilot["session"].send_and_wait.call_args
    prompt_str = call_args[0][0]  # first positional argument
    assert "You have access to the following tools" in prompt_str
    assert "ping" in prompt_str


@pytest.mark.asyncio
async def test_bound_copilot_handles_markdown_wrapped_json(mock_copilot, mock_tool):
    """BoundChatCopilot._agenerate() parses JSON wrapped in markdown code blocks."""
    mock_copilot["response"].data.content = '```json\n{"tool": "ping", "args": {}}\n```'

    bound = BoundChatCopilot(tools=[mock_tool], model="gpt-4.1", github_token="ghu_test")
    result = await bound._agenerate([HumanMessage(content="test")])

    assert len(result.generations[0].message.tool_calls) == 1
    assert result.generations[0].message.tool_calls[0]["name"] == "ping"
    assert result.generations[0].message.tool_calls[0]["args"] == {}
