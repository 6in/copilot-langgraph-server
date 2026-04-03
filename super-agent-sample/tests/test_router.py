"""Unit tests for RouterNode (src/graph.py)."""
from __future__ import annotations
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from state import AgentState
from graph import RouterNode


def make_mock_agent(name: str) -> MagicMock:
    """Create a mock SubAgent — avoids MagicMock(name=...) which sets mock name not attribute."""
    agent = MagicMock()
    agent.name = name
    agent.description = f"desc for {name}"
    return agent


def make_mock_registry(names: list[str]):
    """Create a mock SubAgentRegistry with named agents."""
    registry = MagicMock()
    agents = [make_mock_agent(n) for n in names]
    registry.all.return_value = agents
    return registry


@pytest.mark.asyncio
async def test_router_selects_code_reviewer():
    """RouterNode routes to 'code-reviewer' when LLM returns 'code-reviewer'."""
    with patch("graph.ChatCopilot") as MockLLM:
        instance = AsyncMock()
        instance.ainvoke.return_value = MagicMock(content="code-reviewer")
        MockLLM.return_value = instance
        registry = make_mock_registry(["code-reviewer", "sql-analyst"])
        router = RouterNode(registry)
        state: AgentState = {"input": "review my code", "output": "", "messages": [], "next": ""}
        result = await router(state)
    assert result["next"] == "code-reviewer"


@pytest.mark.asyncio
async def test_router_fallback_on_unknown():
    """RouterNode falls back to 'fallback' when LLM returns an unknown agent name."""
    with patch("graph.ChatCopilot") as MockLLM:
        instance = AsyncMock()
        instance.ainvoke.return_value = MagicMock(content="unknown-agent")
        MockLLM.return_value = instance
        registry = make_mock_registry(["code-reviewer", "sql-analyst"])
        router = RouterNode(registry)
        state: AgentState = {"input": "some unknown task", "output": "", "messages": [], "next": ""}
        result = await router(state)
    assert result["next"] == "fallback"


@pytest.mark.asyncio
async def test_router_strips_whitespace():
    """RouterNode strips whitespace from the LLM response before matching."""
    with patch("graph.ChatCopilot") as MockLLM:
        instance = AsyncMock()
        instance.ainvoke.return_value = MagicMock(content="  code-reviewer  \n")
        MockLLM.return_value = instance
        registry = make_mock_registry(["code-reviewer", "sql-analyst"])
        router = RouterNode(registry)
        state: AgentState = {"input": "review this code", "output": "", "messages": [], "next": ""}
        result = await router(state)
    assert result["next"] == "code-reviewer"
