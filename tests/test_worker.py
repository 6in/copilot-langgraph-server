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


# ====================================================================
# Phase 24 (MCP-03): ToolRegistry validation in startup()
# ====================================================================

import sys
import types


def _make_mcp_stub(fake_client):
    """langchain_mcp_adapters が未インストール環境向けの sys.modules スタブを作る。"""
    stub_mod = types.ModuleType("langchain_mcp_adapters")
    stub_client_mod = types.ModuleType("langchain_mcp_adapters.client")
    stub_client_mod.MultiServerMCPClient = MagicMock(return_value=fake_client)
    stub_mod.client = stub_client_mod
    return stub_mod, stub_client_mod


@pytest.mark.asyncio
async def test_startup_tool_registry_validate_pass(tmp_path):
    """MCP 接続成功 + YAML 一致 → startup が完了して ctx['mcp_tools'] が設定される。"""
    from app.jobs.worker import startup

    yaml_file = tmp_path / "mcp_tools.yaml"
    yaml_file.write_text("tools:\n  - name: ping\n")

    from langchain_core.tools import tool as tool_decorator

    @tool_decorator
    def ping(message: str = "") -> str:
        """Ping."""
        return "pong"

    fake_client = MagicMock()
    fake_client.get_tools = AsyncMock(return_value=[ping])

    stub_mod, stub_client_mod = _make_mcp_stub(fake_client)

    mock_checkpointer = AsyncMock()
    mock_checkpointer.__aenter__ = AsyncMock(return_value=mock_checkpointer)
    mock_checkpointer.__aexit__ = AsyncMock(return_value=None)

    mock_pool = AsyncMock()

    with patch.dict(sys.modules, {
            "langchain_mcp_adapters": stub_mod,
            "langchain_mcp_adapters.client": stub_client_mod,
         }), \
         patch("app.jobs.worker.AsyncPostgresSaver") as mock_saver, \
         patch("app.jobs.worker.AsyncConnectionPool", return_value=mock_pool), \
         patch("app.jobs.worker.Redis") as mock_redis, \
         patch("app.jobs.worker.MCP_TOOLS_CONFIG", str(yaml_file)):
        mock_saver.from_conn_string.return_value = mock_checkpointer
        mock_redis.from_url.return_value = MagicMock()

        ctx: dict = {}
        await startup(ctx)

    assert any(t.name == "ping" for t in ctx["mcp_tools"])


@pytest.mark.asyncio
async def test_startup_tool_registry_validate_fail_propagates(tmp_path):
    """MCP 接続成功 + YAML 不一致 → RuntimeError が伝播（DEGRADED で握りつぶされない）。"""
    from app.jobs.worker import startup

    yaml_file = tmp_path / "mcp_tools.yaml"
    yaml_file.write_text("tools:\n  - name: ping\n  - name: web_search\n")

    from langchain_core.tools import tool as tool_decorator

    @tool_decorator
    def ping(message: str = "") -> str:
        """Ping."""
        return "pong"

    fake_client = MagicMock()
    fake_client.get_tools = AsyncMock(return_value=[ping])  # web_search missing

    stub_mod, stub_client_mod = _make_mcp_stub(fake_client)

    mock_checkpointer = AsyncMock()
    mock_checkpointer.__aenter__ = AsyncMock(return_value=mock_checkpointer)
    mock_checkpointer.__aexit__ = AsyncMock(return_value=None)

    mock_pool2 = AsyncMock()

    with patch.dict(sys.modules, {
            "langchain_mcp_adapters": stub_mod,
            "langchain_mcp_adapters.client": stub_client_mod,
         }), \
         patch("app.jobs.worker.AsyncPostgresSaver") as mock_saver, \
         patch("app.jobs.worker.AsyncConnectionPool", return_value=mock_pool2), \
         patch("app.jobs.worker.Redis") as mock_redis, \
         patch("app.jobs.worker.MCP_TOOLS_CONFIG", str(yaml_file)):
        mock_saver.from_conn_string.return_value = mock_checkpointer
        mock_redis.from_url.return_value = MagicMock()

        ctx: dict = {}
        with pytest.raises(RuntimeError, match="mcp_tools.yaml"):
            await startup(ctx)


@pytest.mark.asyncio
async def test_startup_mcp_connection_failure_still_degraded(tmp_path):
    """MCP 接続失敗 → DEGRADED モード（mcp_tools=[], RuntimeError 伝播せず）。"""
    from app.jobs.worker import startup

    yaml_file = tmp_path / "mcp_tools.yaml"
    yaml_file.write_text("tools:\n  - name: ping\n")

    fake_client = MagicMock()
    fake_client.get_tools = AsyncMock(side_effect=ConnectionError("mcp down"))

    stub_mod, stub_client_mod = _make_mcp_stub(fake_client)

    mock_checkpointer = AsyncMock()
    mock_checkpointer.__aenter__ = AsyncMock(return_value=mock_checkpointer)
    mock_checkpointer.__aexit__ = AsyncMock(return_value=None)

    mock_pool3 = AsyncMock()

    with patch.dict(sys.modules, {
            "langchain_mcp_adapters": stub_mod,
            "langchain_mcp_adapters.client": stub_client_mod,
         }), \
         patch("app.jobs.worker.AsyncPostgresSaver") as mock_saver, \
         patch("app.jobs.worker.AsyncConnectionPool", return_value=mock_pool3), \
         patch("app.jobs.worker.Redis") as mock_redis, \
         patch("app.jobs.worker.MCP_TOOLS_CONFIG", str(yaml_file)):
        mock_saver.from_conn_string.return_value = mock_checkpointer
        mock_redis.from_url.return_value = MagicMock()

        ctx: dict = {}
        await startup(ctx)  # must not raise

    assert ctx["mcp_tools"] == []
