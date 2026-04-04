"""Tests for RouterNode structured logging with correlation_id."""
from __future__ import annotations

import json
import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.orchestrator.context import RPCContext
from app.orchestrator.graph import RouterNode
from app.orchestrator.agent import SubAgentRegistry


def _make_registry(agent_names: list[str]) -> SubAgentRegistry:
    """Create a SubAgentRegistry mock with specified agent names."""
    registry = MagicMock(spec=SubAgentRegistry)
    agents = []
    for name in agent_names:
        agent = MagicMock()
        agent.name = name
        agent.description = f"Description for {name}"
        agents.append(agent)
    registry.all.return_value = agents
    return registry


@pytest.mark.asyncio
async def test_router_log_contains_correlation_id(caplog):
    """RouterNode should emit a JSON log entry containing correlation_id."""
    known_corr_id = "test-correlation-id-12345"
    context = RPCContext(
        user_id="test-user",
        app_id="superchat",
        thread_id="thread-001",
        correlation_id=known_corr_id,
    )
    state = {
        "input": "Hello, which agent should handle this?",
        "output": "",
        "messages": [],
        "next": "",
        "context": context,
        "error": None,
    }

    registry = _make_registry(["general-assistant", "code-helper"])

    node = RouterNode.__new__(RouterNode)
    node._registry = registry
    node._llm = AsyncMock()
    # LLM returns a known agent name
    mock_response = MagicMock()
    mock_response.content = "general-assistant"
    node._llm.ainvoke = AsyncMock(return_value=mock_response)

    with caplog.at_level(logging.INFO, logger="app.orchestrator.graph"):
        result = await node(state)

    # Check that at least one log record was emitted
    assert len(caplog.records) >= 1, "RouterNode should emit at least one log record"

    # Find the routing log entry
    routing_log = None
    for record in caplog.records:
        try:
            entry = json.loads(record.getMessage())
            if entry.get("event") == "routing":
                routing_log = entry
                break
        except (json.JSONDecodeError, AttributeError):
            continue

    assert routing_log is not None, "No JSON routing log entry found in log output"
    assert routing_log["event"] == "routing"
    assert routing_log["correlation_id"] == known_corr_id
    assert routing_log["chosen"] == "general-assistant"
    assert isinstance(routing_log["candidates"], list)
    assert "general-assistant" in routing_log["candidates"]
    assert routing_log["thread_id"] == "thread-001"
    assert "input" in routing_log
    assert routing_log["stage"] == "llm", "LLM path should log stage='llm'"

    # Result should have the chosen agent
    assert result["next"] == "general-assistant"


@pytest.mark.asyncio
async def test_router_log_handles_missing_context(caplog):
    """RouterNode should not crash when state has no context (legacy threads)."""
    # State WITHOUT context key (legacy thread)
    state = {
        "input": "A legacy request without context",
        "output": "",
        "messages": [],
        "next": "",
    }

    registry = _make_registry(["general-assistant"])

    node = RouterNode.__new__(RouterNode)
    node._registry = registry
    node._llm = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = "general-assistant"
    node._llm.ainvoke = AsyncMock(return_value=mock_response)

    # Should not crash
    with caplog.at_level(logging.INFO, logger="app.orchestrator.graph"):
        result = await node(state)

    # Find the routing log entry
    routing_log = None
    for record in caplog.records:
        try:
            entry = json.loads(record.getMessage())
            if entry.get("event") == "routing":
                routing_log = entry
                break
        except (json.JSONDecodeError, AttributeError):
            continue

    assert routing_log is not None, "No JSON routing log entry found in log output"
    assert routing_log["correlation_id"] == "", "Missing context should produce empty correlation_id"
    assert routing_log["thread_id"] == "", "Missing context should produce empty thread_id"
    assert routing_log["stage"] == "llm", "LLM path should log stage='llm'"
    assert result["next"] == "general-assistant"
