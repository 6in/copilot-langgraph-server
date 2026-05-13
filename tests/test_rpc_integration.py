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

    Phase 31 以降の経路: handler は graph.astream_events で SSE token を流したあと、
    最終結果が取れなかった場合のみ graph.aget_state → graph.ainvoke fallback に流れる。
    capture したい initial state は ainvoke の引数で取れるので、astream_events は空
    async generator、aget_state は None で fallback を発火させる。

    agents_filter を ['general-assistant'] で指定するのは APP.md superchat agents の
    自動ロード ([\"code-reviewer\", ...]) と registry.agents={\"general-assistant\":...}
    の不一致による \"No matching agents\" を回避するため。
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
        # APP.md からの agents 上書きを回避するため明示指定
        "agents": ["general-assistant"],
        "github_login": github_login,
    }

    mock_job_store = AsyncMock()
    ctx = {"job_store": mock_job_store}

    # Capture the initial state passed to graph.ainvoke (fallback 経路)
    captured_initial: dict = {}

    mock_graph = AsyncMock()

    async def _empty_events_gen(*args, **kwargs):
        if False:  # pragma: no cover
            yield None

    async def capture_ainvoke(initial, config=None):
        captured_initial.update(initial)
        return {
            "output": "Integration result",
            "messages": [],
            "next": "",
        }

    mock_graph.astream_events = MagicMock(side_effect=_empty_events_gen)
    mock_graph.aget_state = AsyncMock(return_value=None)
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
    mock_checkpointer.setup = AsyncMock()
    mock_saver_class = MagicMock()
    mock_saver_class.from_conn_string = MagicMock(return_value=mock_checkpointer)

    # Vision check 用 ChatCopilot を mock (実 SDK 起動回避)
    mock_vision_llm = AsyncMock()
    mock_vision_llm.is_vision_model = AsyncMock(return_value=True)
    mock_vision_llm.close = AsyncMock()

    with patch("app.jobs.handlers.orchestrator_handler.build_orchestrator_graph", return_value=mock_graph), \
         patch("app.jobs.handlers.orchestrator_handler.SubAgentRegistry", return_value=mock_registry), \
         patch("app.jobs.handlers.orchestrator_handler.AsyncPostgresSaver", mock_saver_class), \
         patch("app.providers.copilot.ChatCopilot", return_value=mock_vision_llm), \
         patch("app.jobs.handlers.orchestrator_handler.scan_thread_attachments", return_value=[]):

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
    """The correlation_id in RPCContext becomes the routing span's trace_id.

    Phase 31: the legacy ``event: routing`` JSON line was replaced by the
    OTEL span-like writer (logger name "trace"). Instead of grepping for
    ``event == 'routing'`` on ``app.orchestrator.graph``, we now look for a
    span with ``operation_name == 'routing'`` on ``trace`` whose
    ``trace_id`` matches ``RPCContext.correlation_id`` (D-08).
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

    with caplog.at_level(logging.INFO, logger="trace"):
        result = await node(state)

    # Find the routing span on the "trace" logger.
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

    assert routing_span is not None, \
        "RouterNode must emit an OTEL span with operation_name='routing' on logger 'trace'"
    assert routing_span.get("trace_id") == known_corr_id, (
        f"routing span trace_id must match RPCContext.correlation_id={known_corr_id!r}, "
        f"got {routing_span.get('trace_id')!r}"
    )
    assert routing_span["attributes"].get("thread_id") == "integration-thread-002", \
        "routing span attributes.thread_id must match RPCContext.thread_id"

    # Sanity check: routing chose the right agent
    assert result["next"] == "general-assistant"
