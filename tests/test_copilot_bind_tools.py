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


# ---------------------------------------------------------------------------
# astream_events regression — Issue: SuperChat tools stopped working after
# commit 6d79f36 added ChatCopilot._astream. Inside astream_events, ainvoke
# routes through _astream, which bypassed tool schema injection and JSON
# parsing. Fix: BoundChatCopilot._astream delegates to _agenerate and yields
# a single chunk carrying tool_call_chunks.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bound_copilot_astream_preserves_tool_calls(mock_copilot, mock_tool):
    """BoundChatCopilot._astream() must yield a chunk with tool_call_chunks
    when the underlying LLM returns a JSON tool call — because LangChain
    routes ainvoke through _astream inside astream_events contexts."""
    mock_copilot["response"].data.content = (
        '{"tool": "ping", "args": {"q": "hi"}}'
    )

    bound = BoundChatCopilot(tools=[mock_tool], model="gpt-4.1", github_token="ghu_test")
    chunks = [c async for c in bound._astream([HumanMessage(content="test")])]

    assert len(chunks) == 1
    chunk = chunks[0]
    msg = chunk.message
    # tool_call_chunks → LangChain re-assembles into tool_calls on the receiving end
    assert msg.tool_call_chunks, "expected tool_call_chunks on the streamed chunk"
    assert msg.tool_call_chunks[0]["name"] == "ping"
    assert msg.tool_call_chunks[0]["args"] == '{"q": "hi"}'


@pytest.mark.asyncio
async def test_bound_copilot_astream_events_reconstructs_tool_calls(mock_copilot, mock_tool):
    """End-to-end regression: ainvoke() inside an astream_events context
    must produce an AIMessage with non-empty tool_calls. This exercises
    the exact path SuperChat / ToolEnabledSubAgent uses."""
    from langchain_core.runnables import RunnableLambda

    mock_copilot["response"].data.content = (
        '{"tool": "ping", "args": {"message": "hi"}}'
    )

    bound = BoundChatCopilot(tools=[mock_tool], model="gpt-4.1", github_token="ghu_test")

    async def agent_fn(messages):
        return await bound.ainvoke(messages)

    chain = RunnableLambda(agent_fn)
    final = None
    async for ev in chain.astream_events([HumanMessage("search")], version="v2"):
        if ev.get("event") == "on_chat_model_end":
            final = ev["data"].get("output")

    assert final is not None, "expected on_chat_model_end event to fire"
    assert final.tool_calls, (
        "expected tool_calls on the aggregated message — if empty, "
        "BoundChatCopilot._astream is not injecting tool schemas or "
        "preserving tool_call_chunks through streaming"
    )
    assert final.tool_calls[0]["name"] == "ping"
    assert final.tool_calls[0]["args"] == {"message": "hi"}


# ---------------------------------------------------------------------------
# TestToolSystemPromptTemplate
# ---------------------------------------------------------------------------


class TestToolSystemPromptTemplate:
    """Tests that TOOL_SYSTEM_PROMPT_TEMPLATE enforces mandatory tool usage."""

    def _formatted(self):
        from app.providers.copilot import TOOL_SYSTEM_PROMPT_TEMPLATE
        return TOOL_SYSTEM_PROMPT_TEMPLATE.format(tool_schemas="[ping: test tool]")

    def test_template_contains_mandatory_usage_signal(self):
        """Template must signal that tool usage is mandatory for current/real-time info."""
        text = self._formatted()
        # At least one of these mandatory-use keywords must appear
        mandatory_signals = ["must", "required", "always", "real-time", "current", "MUST", "mandatory"]
        assert any(signal in text for signal in mandatory_signals), (
            f"Template must contain a mandatory usage signal. Got:\n{text}"
        )

    def test_template_contains_no_internal_knowledge_rule(self):
        """Template must instruct model not to answer from internal knowledge alone."""
        text = self._formatted()
        # Phrases indicating internal-knowledge-only is forbidden
        forbidden_patterns = [
            "internal knowledge",
            "do not answer",
            "never answer",
            "without using",
            "without calling",
            "must call",
            "must use",
        ]
        assert any(p in text.lower() for p in forbidden_patterns), (
            f"Template must instruct that internal-knowledge-only answers are forbidden. Got:\n{text}"
        )

    def test_template_contains_json_format_instruction(self):
        """Template must preserve the JSON tool-call format instruction."""
        text = self._formatted()
        assert '{"tool": "<tool_name>", "args":' in text or \
               '"tool": "<tool_name>"' in text, (
            f'Template must contain JSON format instruction. Got:\n{text}'
        )

    def test_tool_schemas_placeholder_survives_format(self):
        """The {tool_schemas} placeholder must be present and correctly substituted."""
        from app.providers.copilot import TOOL_SYSTEM_PROMPT_TEMPLATE
        assert "{tool_schemas}" in TOOL_SYSTEM_PROMPT_TEMPLATE
        result = TOOL_SYSTEM_PROMPT_TEMPLATE.format(tool_schemas="MY_TOOL_SCHEMA")
        assert "MY_TOOL_SCHEMA" in result
        assert "{tool_schemas}" not in result
