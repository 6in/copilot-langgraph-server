"""Tests for RouterNode 2-stage keyword routing (ROUTING-02) and stage field (ROUTING-03)."""
from __future__ import annotations

import json
import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.orchestrator.context import RPCContext
from app.orchestrator.graph import RouterNode
from app.orchestrator.agent import SubAgentRegistry


def _make_registry_with_keywords(agents_config: list[dict]) -> SubAgentRegistry:
    """Create a mock registry with agents that have keywords.

    agents_config: list of dicts with keys: name, description, keywords
    """
    registry = MagicMock(spec=SubAgentRegistry)
    agents = []
    for cfg in agents_config:
        agent = MagicMock()
        agent.name = cfg["name"]
        agent.description = cfg.get("description", f"Description for {cfg['name']}")
        agent.keywords = cfg.get("keywords", [])
        agents.append(agent)
    registry.all.return_value = agents
    return registry


def _make_state(input_text: str) -> dict:
    """Create a minimal AgentState dict for testing."""
    return {
        "input": input_text,
        "output": "",
        "messages": [],
        "next": "",
        "context": RPCContext(
            user_id="test-user",
            app_id="superchat",
            thread_id="thread-001",
            correlation_id="corr-keyword-test",
        ),
        "error": None,
    }


@pytest.mark.asyncio
async def test_single_keyword_match_skips_llm():
    """Single keyword match should route immediately without calling LLM."""
    registry = _make_registry_with_keywords([
        {"name": "code-reviewer", "keywords": ["コードレビュー"]},
        {"name": "sql-analyst", "keywords": ["SQL"]},
    ])

    node = RouterNode.__new__(RouterNode)
    node._registry = registry
    node._llm = MagicMock()
    node._llm.ainvoke = AsyncMock()

    result = await node(_make_state("コードレビューして"))

    node._llm.ainvoke.assert_not_called()
    assert result["next"] == "code-reviewer"


@pytest.mark.asyncio
async def test_no_keyword_match_uses_llm():
    """Zero keyword matches should fall through to LLM routing."""
    registry = _make_registry_with_keywords([
        {"name": "code-reviewer", "keywords": ["コードレビュー"]},
        {"name": "sql-analyst", "keywords": ["SQL"]},
        {"name": "general-assistant", "keywords": []},
    ])

    node = RouterNode.__new__(RouterNode)
    node._registry = registry
    node._llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "general-assistant"
    node._llm.ainvoke = AsyncMock(return_value=mock_response)

    result = await node(_make_state("今日の天気は？"))

    node._llm.ainvoke.assert_called_once()
    assert result["next"] == "general-assistant"


@pytest.mark.asyncio
async def test_multi_keyword_match_uses_llm():
    """Multiple agents matching the same keyword should fall through to LLM."""
    registry = _make_registry_with_keywords([
        {"name": "agent-a", "keywords": ["Python"]},
        {"name": "agent-b", "keywords": ["Python"]},
    ])

    node = RouterNode.__new__(RouterNode)
    node._registry = registry
    node._llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "agent-a"
    node._llm.ainvoke = AsyncMock(return_value=mock_response)

    result = await node(_make_state("Pythonのコード"))

    node._llm.ainvoke.assert_called_once()


@pytest.mark.asyncio
async def test_keyword_match_case_insensitive():
    """Keyword matching must be case-insensitive for English terms."""
    registry = _make_registry_with_keywords([
        {"name": "code-reviewer", "keywords": ["Python"]},
    ])

    node = RouterNode.__new__(RouterNode)
    node._registry = registry
    node._llm = MagicMock()
    node._llm.ainvoke = AsyncMock()

    result = await node(_make_state("python code review"))

    node._llm.ainvoke.assert_not_called()
    assert result["next"] == "code-reviewer"


@pytest.mark.asyncio
async def test_stage_keyword_in_log(caplog):
    """Keyword-stage routing must emit a routing span with attributes.stage='keyword'.

    Phase 31: the legacy `event: routing` JSON line was replaced by the
    OTEL span-like writer in `app/observability/trace.py` (logger name
    "trace"). The assertions now read the span's ``operation_name`` and
    ``attributes.stage`` instead of the flat ``event``/``stage`` keys.
    """
    registry = _make_registry_with_keywords([
        {"name": "code-reviewer", "keywords": ["コードレビュー"]},
        {"name": "sql-analyst", "keywords": ["SQL"]},
    ])

    node = RouterNode.__new__(RouterNode)
    node._registry = registry
    node._llm = MagicMock()
    node._llm.ainvoke = AsyncMock()

    with caplog.at_level(logging.INFO, logger="trace"):
        await node(_make_state("コードレビューして"))

    routing_span = None
    for record in caplog.records:
        if record.name != "trace":
            continue
        try:
            entry = json.loads(record.getMessage())
            if entry.get("operation_name") == "routing":
                routing_span = entry
                break
        except (json.JSONDecodeError, AttributeError):
            continue

    assert routing_span is not None, "No routing span found in trace logger"
    assert routing_span["attributes"]["stage"] == "keyword", (
        f"Expected stage='keyword', got {routing_span['attributes'].get('stage')}"
    )


@pytest.mark.asyncio
async def test_stage_llm_in_log(caplog):
    """LLM-stage routing (no keyword match) must emit a routing span with stage='llm'."""
    registry = _make_registry_with_keywords([
        {"name": "code-reviewer", "keywords": ["コードレビュー"]},
        {"name": "general-assistant", "keywords": []},
    ])

    node = RouterNode.__new__(RouterNode)
    node._registry = registry
    node._llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "general-assistant"
    node._llm.ainvoke = AsyncMock(return_value=mock_response)

    with caplog.at_level(logging.INFO, logger="trace"):
        await node(_make_state("今日の天気は？"))

    routing_span = None
    for record in caplog.records:
        if record.name != "trace":
            continue
        try:
            entry = json.loads(record.getMessage())
            if entry.get("operation_name") == "routing":
                routing_span = entry
                break
        except (json.JSONDecodeError, AttributeError):
            continue

    assert routing_span is not None, "No routing span found in trace logger"
    assert routing_span["attributes"]["stage"] == "llm", (
        f"Expected stage='llm', got {routing_span['attributes'].get('stage')}"
    )
