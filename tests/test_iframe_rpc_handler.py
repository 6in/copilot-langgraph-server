"""Unit tests for IframeRpcHandler."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.jobs.handlers.iframe_rpc_handler import IframeRpcHandler


# ---------------------------------------------------------------------------
# Helper: build a mock ctx
# ---------------------------------------------------------------------------

def _make_ctx(*, rows=None, error=None, no_tool=False):
    job_store = AsyncMock()
    job_store.save_result = AsyncMock()
    job_store.get = AsyncMock()

    if no_tool:
        return {"job_store": job_store, "mcp_tools": []}

    tool = AsyncMock()
    tool.name = "db_query"  # 属性として明示設定（コンストラクタの name は別物）
    if error is not None:
        tool.ainvoke = AsyncMock(return_value={"error": error})
    else:
        tool.ainvoke = AsyncMock(return_value={"rows": rows or [{"id": 1, "name": "test"}]})
    return {"job_store": job_store, "mcp_tools": [tool]}


def _make_notifier():
    notifier = AsyncMock()
    notifier.done = AsyncMock()
    notifier.progress = AsyncMock()
    return notifier


# ---------------------------------------------------------------------------
# _handle_query tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_handle_query_success():
    ctx = _make_ctx(rows=[{"id": 1, "name": "test"}])
    handler = IframeRpcHandler()
    params = {"pool_name": "main", "sql": "SELECT * FROM users", "user": "alice"}
    result = await handler._handle_query(ctx, params)
    assert result["result"] is True
    assert result["rows"] == [{"id": 1, "name": "test"}]
    # MCP ツールが正しい引数で呼ばれたことを確認
    ctx["mcp_tools"][0].ainvoke.assert_awaited_once_with({"sql": "SELECT * FROM users", "pool_name": "main"})


@pytest.mark.asyncio
async def test_handle_query_tool_error():
    ctx = _make_ctx(error="Only SELECT queries are allowed")
    handler = IframeRpcHandler()
    params = {"pool_name": "main", "sql": "INSERT INTO users VALUES (1)", "user": "alice"}
    result = await handler._handle_query(ctx, params)
    assert result["result"] is False
    assert "Only SELECT queries are allowed" in result["error"]


@pytest.mark.asyncio
async def test_handle_query_unknown_pool():
    ctx = _make_ctx(error="Unknown pool: nonexistent")
    handler = IframeRpcHandler()
    params = {"pool_name": "nonexistent", "sql": "SELECT 1", "user": "alice"}
    result = await handler._handle_query(ctx, params)
    assert result["result"] is False
    assert "Unknown pool: nonexistent" in result["error"]


@pytest.mark.asyncio
async def test_handle_query_degraded():
    ctx = _make_ctx(no_tool=True)
    handler = IframeRpcHandler()
    params = {"pool_name": "main", "sql": "SELECT 1", "user": "alice"}
    result = await handler._handle_query(ctx, params)
    assert result["result"] is False
    assert "db_query" in result["error"]
    assert "unavailable" in result["error"]


# ---------------------------------------------------------------------------
# _handle_ai tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_handle_ai_success():
    handler = IframeRpcHandler()
    job = {"github_token": "ghu_test"}
    params = {"model": "claude-sonnet-4-6", "prompt": "Hello!"}

    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content="Hi there!"))
    mock_llm.close = AsyncMock()

    with patch("app.jobs.handlers.iframe_rpc_handler.ChatCopilot", return_value=mock_llm):
        result = await handler._handle_ai(job, params)

    assert result["result"] is True
    assert result["responseText"] == "Hi there!"
    mock_llm.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# handle (top-level dispatch) tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_handle_unknown_method():
    handler = IframeRpcHandler()
    ctx = _make_ctx()
    job = {
        "job_id": "test-job-id",
        "reply_to": {"type": "web", "job_id": "test-job-id"},
        "rpc_method": "UNKNOWN_METHOD",
        "rpc_params": {},
    }

    mock_notifier = _make_notifier()
    with patch("app.jobs.handlers.iframe_rpc_handler.build_notifier", return_value=mock_notifier):
        result = await handler.handle(ctx, job)

    assert result["job_id"] == "test-job-id"
    assert result["status"] == "done"

    saved_call = ctx["job_store"].save_result.call_args
    saved_data = json.loads(saved_call[0][1])
    assert saved_data["result"] is False
    assert "Unknown method" in saved_data["error"]
    assert "UNKNOWN_METHOD" in saved_data["error"]
    mock_notifier.done.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_query_dispatch():
    """handle() routes QUERY method to _handle_query correctly."""
    handler = IframeRpcHandler()
    ctx = _make_ctx(rows=[{"id": 1}])
    job = {
        "job_id": "job-query-1",
        "reply_to": {"type": "web", "job_id": "job-query-1"},
        "rpc_method": "QUERY",
        "rpc_params": {"pool_name": "main", "sql": "SELECT 1", "user": "bob"},
    }

    mock_notifier = _make_notifier()
    with patch("app.jobs.handlers.iframe_rpc_handler.build_notifier", return_value=mock_notifier):
        result = await handler.handle(ctx, job)

    assert result["status"] == "done"
    saved_call = ctx["job_store"].save_result.call_args
    saved_data = json.loads(saved_call[0][1])
    assert saved_data["result"] is True
    mock_notifier.done.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_ai_dispatch():
    """handle() routes AI method to _handle_ai correctly."""
    handler = IframeRpcHandler()
    ctx = _make_ctx()
    job = {
        "job_id": "job-ai-1",
        "reply_to": {"type": "web", "job_id": "job-ai-1"},
        "rpc_method": "AI",
        "rpc_params": {"model": "claude-sonnet-4-6", "prompt": "What is 2+2?"},
        "github_token": "ghu_test_token",
    }

    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content="4"))
    mock_llm.close = AsyncMock()

    mock_notifier = _make_notifier()
    with patch("app.jobs.handlers.iframe_rpc_handler.build_notifier", return_value=mock_notifier), \
         patch("app.jobs.handlers.iframe_rpc_handler.ChatCopilot", return_value=mock_llm):
        result = await handler.handle(ctx, job)

    assert result["status"] == "done"
    saved_call = ctx["job_store"].save_result.call_args
    saved_data = json.loads(saved_call[0][1])
    assert saved_data["result"] is True
    assert saved_data["responseText"] == "4"
    mock_notifier.done.assert_awaited_once()
