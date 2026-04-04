"""Tests for the arq worker module (ASYNC-07).

Tests verify that process_chat orchestrates correctly:
- graph.ainvoke -> save_result -> notifier.done (success path)
- error path saves error message and still calls notifier.done
- llm.close() is always called in the finally block
- startup/shutdown lifecycle hooks work correctly
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


async def test_process_chat_saves_result():
    """process_chat calls job_store.save_result then notifier.done (success path)."""
    from app.jobs.worker import process_chat

    mock_job_store = AsyncMock()
    ctx = {"job_store": mock_job_store}

    # Mock LangGraph result
    mock_message = MagicMock()
    mock_message.content = "AI reply"
    mock_result = {"messages": [mock_message]}

    mock_graph = AsyncMock()
    mock_graph.ainvoke = AsyncMock(return_value=mock_result)

    mock_llm = AsyncMock()
    mock_checkpointer = AsyncMock()
    mock_checkpointer.__aenter__ = AsyncMock(return_value=mock_checkpointer)
    mock_checkpointer.__aexit__ = AsyncMock(return_value=None)

    with patch("app.jobs.worker.ChatCopilot", return_value=mock_llm), \
         patch("app.jobs.worker.build_graph", return_value=mock_graph), \
         patch("app.jobs.worker.AsyncPostgresSaver.from_conn_string", return_value=mock_checkpointer):

        result = await process_chat(
            ctx,
            job_id="j1",
            thread_id="t1",
            prompt="hello",
            github_token="ghu_test",
            reply_to={"type": "web", "job_id": "j1"},
        )

    mock_job_store.save_result.assert_called_once_with("j1", "AI reply")
    # notifier.done() calls job_store.notify — verify it was called
    mock_job_store.notify.assert_called()
    assert result == {"job_id": "j1", "status": "done"}


async def test_process_chat_error_handling():
    """process_chat saves error message and still calls notifier.done on exception."""
    from app.jobs.worker import process_chat

    mock_job_store = AsyncMock()
    ctx = {"job_store": mock_job_store}

    mock_graph = AsyncMock()
    mock_graph.ainvoke = AsyncMock(side_effect=RuntimeError("boom"))

    mock_llm = AsyncMock()
    mock_checkpointer = AsyncMock()
    mock_checkpointer.__aenter__ = AsyncMock(return_value=mock_checkpointer)
    mock_checkpointer.__aexit__ = AsyncMock(return_value=None)

    with patch("app.jobs.worker.ChatCopilot", return_value=mock_llm), \
         patch("app.jobs.worker.build_graph", return_value=mock_graph), \
         patch("app.jobs.worker.AsyncPostgresSaver.from_conn_string", return_value=mock_checkpointer):

        await process_chat(
            ctx,
            job_id="j2",
            thread_id="t2",
            prompt="error test",
            github_token="ghu_test",
            reply_to={"type": "web", "job_id": "j2"},
        )

    # Verify save_result was called with an error-containing message
    call_args = mock_job_store.save_result.call_args
    assert call_args[0][0] == "j2"
    assert "Error:" in call_args[0][1]
    assert "boom" in call_args[0][1]

    # notifier.done() must still be called even on error
    mock_job_store.notify.assert_called()


async def test_process_chat_closes_llm():
    """llm.close() is called in finally block even when exception occurs."""
    from app.jobs.worker import process_chat

    mock_job_store = AsyncMock()
    ctx = {"job_store": mock_job_store}

    mock_graph = AsyncMock()
    mock_graph.ainvoke = AsyncMock(side_effect=RuntimeError("force error"))

    mock_llm = AsyncMock()
    mock_checkpointer = AsyncMock()
    mock_checkpointer.__aenter__ = AsyncMock(return_value=mock_checkpointer)
    mock_checkpointer.__aexit__ = AsyncMock(return_value=None)

    with patch("app.jobs.worker.ChatCopilot", return_value=mock_llm), \
         patch("app.jobs.worker.build_graph", return_value=mock_graph), \
         patch("app.jobs.worker.AsyncPostgresSaver.from_conn_string", return_value=mock_checkpointer):

        await process_chat(
            ctx,
            job_id="j3",
            thread_id="t3",
            prompt="close test",
            github_token="ghu_test",
            reply_to={"type": "web", "job_id": "j3"},
        )

    mock_llm.close.assert_called_once()


async def test_startup_creates_redis_and_jobstore():
    """startup(ctx) populates ctx['redis_client'] and ctx['job_store']."""
    from app.jobs.worker import startup

    ctx: dict = {}
    mock_redis = AsyncMock()

    # Mock the PostgreSQL checkpointer opened during startup for setup()
    mock_checkpointer = AsyncMock()
    mock_checkpointer.__aenter__ = AsyncMock(return_value=mock_checkpointer)
    mock_checkpointer.__aexit__ = AsyncMock(return_value=None)

    with patch("app.jobs.worker.Redis") as mock_redis_class, \
         patch("app.jobs.worker.AsyncPostgresSaver.from_conn_string", return_value=mock_checkpointer):
        mock_redis_class.from_url = MagicMock(return_value=mock_redis)
        await startup(ctx)

    assert "redis_client" in ctx
    assert "job_store" in ctx
    mock_redis_class.from_url.assert_called_once()
    # Verify checkpointer.setup() was called during startup
    mock_checkpointer.setup.assert_called_once()


async def test_shutdown_closes_redis():
    """shutdown(ctx) calls redis_client.aclose()."""
    from app.jobs.worker import shutdown

    mock_redis = AsyncMock()
    ctx = {"redis_client": mock_redis}

    await shutdown(ctx)

    mock_redis.aclose.assert_called_once()


# ---------------------------------------------------------------------------
# Phase 10 Wave 0: Failing test for OrchestratorHandler with checkpointer
# This test is SKIPPED until Wave 3 implements production code changes.
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="Phase 10 Wave 0: will pass after Wave 3")
async def test_orchestrator_handler_uses_checkpointer():
    """OrchestratorHandler.handle() passes a checkpointer to build_orchestrator_graph (ORC-01).

    Phase 10 behavior: OrchestratorHandler wires AsyncPostgresSaver as checkpointer
    so that SuperChat conversations persist across turns (LangGraph thread continuity).
    Verifies:
    - build_orchestrator_graph is called with a non-None checkpointer argument
    - graph.ainvoke is called with config={"configurable": {"thread_id": thread_id}}
    """
    from app.jobs.handlers.orchestrator_handler import OrchestratorHandler

    thread_id = "test-orchestrator-thread-001"
    job = {
        "job_id": "job-orch-001",
        "prompt": "Hello orchestrator",
        "github_token": "ghu_test_token",
        "reply_to": {"type": "web", "job_id": "job-orch-001"},
        "thread_id": thread_id,
        "agents": None,
    }

    mock_job_store = AsyncMock()
    ctx = {"job_store": mock_job_store}

    # Mock the graph that build_orchestrator_graph returns
    mock_graph = AsyncMock()
    mock_graph.ainvoke = AsyncMock(return_value={
        "output": "Orchestrator reply",
        "messages": [],
        "next": "",
    })

    # Mock the registry with at least one agent
    mock_agent = MagicMock()
    mock_registry = MagicMock()
    mock_registry.agents = {"agent-one": mock_agent}
    mock_registry.close = AsyncMock()

    # Mock AsyncPostgresSaver — will be imported in the handler after Wave 3
    mock_checkpointer = AsyncMock()
    mock_checkpointer.__aenter__ = AsyncMock(return_value=mock_checkpointer)
    mock_checkpointer.__aexit__ = AsyncMock(return_value=None)
    mock_saver_class = MagicMock()
    mock_saver_class.from_conn_string = MagicMock(return_value=mock_checkpointer)

    captured_build_args = {}

    def capture_build_orchestrator_graph(registry, github_token, checkpointer=None, **kwargs):
        captured_build_args["checkpointer"] = checkpointer
        return mock_graph

    with patch("app.jobs.handlers.orchestrator_handler.build_orchestrator_graph", side_effect=capture_build_orchestrator_graph), \
         patch("app.jobs.handlers.orchestrator_handler.SubAgentRegistry", return_value=mock_registry), \
         patch("app.jobs.handlers.orchestrator_handler.AsyncPostgresSaver", mock_saver_class):

        handler = OrchestratorHandler()
        await handler.handle(ctx, job)

    # Verify build_orchestrator_graph was called with a non-None checkpointer
    assert "checkpointer" in captured_build_args, \
        "build_orchestrator_graph must be called with a checkpointer keyword argument"
    assert captured_build_args["checkpointer"] is not None, \
        "checkpointer passed to build_orchestrator_graph must not be None"

    # Verify graph.ainvoke was called with thread_id in config
    mock_graph.ainvoke.assert_called_once()
    call_args = mock_graph.ainvoke.call_args
    # ainvoke is called as ainvoke(initial, config={"configurable": {"thread_id": ...}})
    config = call_args.kwargs.get("config") or (call_args.args[1] if len(call_args.args) > 1 else None)
    assert config is not None, "graph.ainvoke must be called with a config argument"
    assert config.get("configurable", {}).get("thread_id") == thread_id, \
        f"Expected thread_id={thread_id!r} in config.configurable, got: {config}"
