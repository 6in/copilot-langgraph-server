"""Unit tests for IframeRpcHandler and is_select_only."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.jobs.handlers.iframe_rpc_handler import IframeRpcHandler, is_select_only


# ---------------------------------------------------------------------------
# is_select_only parametrized tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("sql,expected", [
    ("SELECT * FROM users", True),
    ("select count(*) from items", True),  # case insensitive
    ("WITH cte AS (SELECT 1) SELECT * FROM cte", True),
    ("INSERT INTO users VALUES (1)", False),
    ("UPDATE users SET name='x'", False),
    ("DELETE FROM users", False),
    ("DROP TABLE users", False),
    ("SELECT 1; DROP TABLE users", False),  # multiple statements
    ("/* comment */ SELECT 1", True),  # SQL comments stripped
    ("-- comment\nSELECT 1", True),
    ("", False),  # empty string
    ("   ", False),  # whitespace only
])
def test_is_select_only(sql, expected):
    assert is_select_only(sql) == expected


# ---------------------------------------------------------------------------
# Helper: build a mock ctx
# ---------------------------------------------------------------------------

def _make_ctx(pool_name="main"):
    job_store = AsyncMock()
    job_store.save_result = AsyncMock()
    job_store.get = AsyncMock()

    mock_cursor = AsyncMock()
    mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_cursor.__aexit__ = AsyncMock(return_value=False)
    mock_cursor.execute = AsyncMock()
    mock_cursor.fetchall = AsyncMock(return_value=[{"id": 1, "name": "test"}])

    mock_conn = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)
    mock_conn.cursor = MagicMock(return_value=mock_cursor)

    mock_pool = AsyncMock()
    mock_pool.connection = MagicMock(return_value=mock_conn)

    db_pools = {pool_name: mock_pool}

    return {"job_store": job_store, "db_pools": db_pools}, mock_cursor


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
    ctx, mock_cursor = _make_ctx("main")
    handler = IframeRpcHandler()
    params = {"pool_name": "main", "sql": "SELECT * FROM users", "user": "alice"}
    result = await handler._handle_query(ctx, params)
    assert result["result"] is True
    assert result["rows"] == [{"id": 1, "name": "test"}]


@pytest.mark.asyncio
async def test_handle_query_unknown_pool():
    ctx, _ = _make_ctx("main")
    handler = IframeRpcHandler()
    params = {"pool_name": "nonexistent", "sql": "SELECT 1", "user": "alice"}
    result = await handler._handle_query(ctx, params)
    assert result["result"] is False
    assert "Unknown pool" in result["error"]
    assert "nonexistent" in result["error"]


@pytest.mark.asyncio
async def test_handle_query_non_select_rejected():
    ctx, _ = _make_ctx("main")
    handler = IframeRpcHandler()
    params = {"pool_name": "main", "sql": "INSERT INTO users VALUES (1)", "user": "alice"}
    result = await handler._handle_query(ctx, params)
    assert result["result"] is False
    assert "Only SELECT queries are allowed" in result["error"]


# ---------------------------------------------------------------------------
# _handle_ai tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_handle_ai_success():
    handler = IframeRpcHandler()
    job = {"github_token": "ghu_test"}
    params = {"model": "claude-sonnet-4.5", "prompt": "Hello!"}

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
    ctx, _ = _make_ctx()
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

    # The saved result should contain {"result": False, "error": "Unknown method: UNKNOWN_METHOD"}
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
    ctx, mock_cursor = _make_ctx("main")
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
    ctx, _ = _make_ctx()
    job = {
        "job_id": "job-ai-1",
        "reply_to": {"type": "web", "job_id": "job-ai-1"},
        "rpc_method": "AI",
        "rpc_params": {"model": "claude-sonnet-4.5", "prompt": "What is 2+2?"},
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
