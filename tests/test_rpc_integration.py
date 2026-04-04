"""Integration tests: RPCContext flows from OrchestratorHandler through the graph (CONTEXT-01, CONTEXT-04).

Tests verify end-to-end wiring:
- OrchestratorHandler injects RPCContext into initial AgentState
- correlation_id from RPCContext appears in RouterNode structured log entries
"""
from __future__ import annotations

import json
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.orchestrator.context import RPCContext


# ---------------------------------------------------------------------------
# test_orchestrator_handler_injects_context
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_orchestrator_handler_injects_context():
    """OrchestratorHandler.handle() constructs RPCContext and injects it into initial AgentState.

    Verifies that:
    - graph.ainvoke is called with an initial dict that has a 'context' key
    - The context is an RPCContext with user_id matching github_login from the job
    - context.app_id == "superchat" (OrchestratorHandler always sets this)
    - context.thread_id matches the job's thread_id
    """
    from app.jobs.handlers.orchestrator_handler import OrchestratorHandler

    thread_id = "integration-thread-001"
    github_login = "test-user"
    job = {
        "job_id": "job-integration-001",
        "prompt": "Run this integration test",
        "github_token": "ghu_test_token",
        "reply_to": {"type": "web", "job_id": "job-integration-001"},
        "thread_id": thread_id,
        "agents": None,
        "github_login": github_login,
    }

    mock_job_store = AsyncMock()
    ctx = {"job_store": mock_job_store}

    # Capture the initial state passed to graph.ainvoke
    captured_initial: dict = {}

    mock_graph = AsyncMock()

    async def capture_ainvoke(initial, config=None):
        captured_initial.update(initial)
        return {
            "output": "Integration result",
            "messages": [],
            "next": "",
        }

    mock_graph.ainvoke = capture_ainvoke

    # Mock registry with at least one agent
    mock_agent = MagicMock()
    mock_agent.name = "general-assistant"
    mock_registry = MagicMock()
    mock_registry.agents = {"general-assistant": mock_agent}
    mock_registry.close = AsyncMock()

    mock_checkpointer = AsyncMock()
    mock_checkpointer.__aenter__ = AsyncMock(return_value=mock_checkpointer)
    mock_checkpointer.__aexit__ = AsyncMock(return_value=None)
    mock_saver_class = MagicMock()
    mock_saver_class.from_conn_string = MagicMock(return_value=mock_checkpointer)

    with patch("app.jobs.handlers.orchestrator_handler.build_orchestrator_graph", return_value=mock_graph), \
         patch("app.jobs.handlers.orchestrator_handler.SubAgentRegistry", return_value=mock_registry), \
         patch("app.jobs.handlers.orchestrator_handler.AsyncPostgresSaver", mock_saver_class):

        handler = OrchestratorHandler()
        await handler.handle(ctx, job)

    # Verify context was injected
    assert "context" in captured_initial, \
        "initial AgentState must contain a 'context' key"
    context = captured_initial["context"]
    assert isinstance(context, RPCContext), \
        f"context must be an RPCContext instance, got {type(context)}"
    assert context.user_id == github_login, \
        f"context.user_id must match github_login={github_login!r}, got {context.user_id!r}"
    assert context.app_id == "superchat", \
        f"context.app_id must be 'superchat', got {context.app_id!r}"
    assert context.thread_id == thread_id, \
        f"context.thread_id must match thread_id={thread_id!r}, got {context.thread_id!r}"

    # Verify error key is also present (required by AgentState)
    assert "error" in captured_initial, \
        "initial AgentState must contain an 'error' key (required by AgentState schema)"
    assert captured_initial["error"] is None, \
        "initial error must be None"


# ---------------------------------------------------------------------------
# test_correlation_id_in_routing_log
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_correlation_id_in_routing_log(caplog):
    """The correlation_id in RPCContext appears in the RouterNode structured routing log.

    Verifies CONTEXT-04: structured application log entries contain correlation_id.
    Simulates OrchestratorHandler constructing RPCContext and passing it to RouterNode.
    """
    from app.orchestrator.context import RPCContext
    from app.orchestrator.graph import RouterNode
    from app.orchestrator.agent import SubAgentRegistry

    # Build a known RPCContext (fixed correlation_id for assertion)
    known_corr_id = "integration-corr-id-99999"
    context = RPCContext(
        user_id="integration-user",
        app_id="superchat",
        thread_id="integration-thread-002",
        correlation_id=known_corr_id,
    )

    # Build a state that mirrors what OrchestratorHandler injects
    state = {
        "input": "Which agent handles this request?",
        "output": "",
        "messages": [],
        "next": "",
        "error": None,
        "context": context,
    }

    # Create a minimal RouterNode with mocked dependencies
    registry = MagicMock(spec=SubAgentRegistry)
    mock_agent = MagicMock()
    mock_agent.name = "general-assistant"
    mock_agent.description = "A general purpose assistant"
    registry.all.return_value = [mock_agent]

    node = RouterNode.__new__(RouterNode)
    node._registry = registry
    node._llm = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = "general-assistant"
    node._llm.ainvoke = AsyncMock(return_value=mock_response)

    with caplog.at_level(logging.INFO, logger="app.orchestrator.graph"):
        result = await node(state)

    # Find the routing JSON log entry
    routing_log = None
    for record in caplog.records:
        try:
            entry = json.loads(record.getMessage())
            if entry.get("event") == "routing":
                routing_log = entry
                break
        except (json.JSONDecodeError, AttributeError):
            continue

    assert routing_log is not None, \
        "RouterNode must emit a JSON log entry with event='routing'"
    assert routing_log.get("correlation_id") == known_corr_id, (
        f"routing log correlation_id must match RPCContext.correlation_id={known_corr_id!r}, "
        f"got {routing_log.get('correlation_id')!r}"
    )
    assert routing_log.get("thread_id") == "integration-thread-002", \
        "routing log thread_id must match RPCContext.thread_id"

    # Sanity check: routing chose the right agent
    assert result["next"] == "general-assistant"
