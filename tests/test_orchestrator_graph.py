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


def _find_routing_span(records) -> dict | None:
    """Helper: locate the routing span (OTEL schema) on logger 'trace'."""
    for record in records:
        if record.name != "trace":
            continue
        try:
            entry = json.loads(record.getMessage())
            if entry.get("operation_name") == "routing":
                return entry
        except (json.JSONDecodeError, AttributeError):
            continue
    return None


@pytest.mark.asyncio
async def test_router_log_contains_correlation_id(caplog):
    """RouterNode should emit a routing span whose trace_id == correlation_id.

    Phase 31: the legacy ``event: routing`` JSON line was replaced by an
    OTEL span on logger ``trace``. ``correlation_id`` moved to ``trace_id``
    (D-08), and domain-specific values moved under ``attributes``.
    """
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

    with caplog.at_level(logging.INFO, logger="trace"):
        result = await node(state)

    routing_span = _find_routing_span(caplog.records)
    assert routing_span is not None, "No routing span found on logger 'trace'"
    assert routing_span["operation_name"] == "routing"
    assert routing_span["trace_id"] == known_corr_id
    attrs = routing_span["attributes"]
    assert attrs["chosen"] == "general-assistant"
    assert isinstance(attrs["candidates"], list)
    assert "general-assistant" in attrs["candidates"]
    assert attrs["thread_id"] == "thread-001"
    assert "user_input_prefix" in attrs
    assert attrs["stage"] == "llm", "LLM path should record attributes.stage='llm'"

    # Result should have the chosen agent
    assert result["next"] == "general-assistant"


@pytest.mark.asyncio
async def test_router_log_handles_missing_context(caplog):
    """RouterNode should not crash when state has no context (legacy threads).

    The routing span is still emitted but trace_id / thread_id fall back to
    empty strings so legacy threads don't break the writer.
    """
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

    with caplog.at_level(logging.INFO, logger="trace"):
        result = await node(state)

    routing_span = _find_routing_span(caplog.records)
    assert routing_span is not None, "No routing span found on logger 'trace'"
    assert routing_span["trace_id"] == "", "Missing context should produce empty trace_id"
    attrs = routing_span["attributes"]
    # Single-agent stage short-circuits LLM routing — still valid behavior.
    assert attrs["thread_id"] == "", "Missing context should produce empty thread_id"
    assert attrs["stage"] in {"llm", "single"}, (
        f"Expected stage='llm' or 'single', got {attrs.get('stage')!r}"
    )
    assert result["next"] == "general-assistant"
