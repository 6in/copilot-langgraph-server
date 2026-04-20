from __future__ import annotations
"""IframeRpcHandler tracing unit tests (Phase 31 D-08..D-12).

Tests the `request` / `tool_call` span emission from the iframe_rpc execution
path (axis B, route 3). Covers:

- handle() emits a single `request` span with handler="iframe_rpc"
- _handle_query (db_query) emits a `tool_call` span with privileged=false
- _handle_query tool-result {"error": ...} marks the span ERROR + success=false
- _handle_query exception (tool.ainvoke raises) marks span ERROR, handler swallows
- _handle_ai emits a `tool_call` span with tool_name="ai" + model_name
- UNKNOWN method emits only the request span (no tool_call)

The `capture_trace_logs` fixture (tests/conftest.py) collects JSON lines on the
"trace" logger after each test.
"""
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.jobs.handlers.iframe_rpc_handler import IframeRpcHandler


def _make_job(method: str = "QUERY", params: dict | None = None, correlation_id: str | None = None) -> dict:
    """Build a minimal job dict matching the Phase 31 Route shape (Task 2)."""
    return {
        "job_id": "job-1",
        "reply_to": {"type": "web", "job_id": "job-1"},
        "rpc_method": method,
        "rpc_params": params or {},
        "github_token": "ghu_test",
        "github_login": "tester",
        "correlation_id": correlation_id or uuid.uuid4().hex,
        "app_id": "canvas",
    }


def _make_ctx(tool_mock=None, tools_list=None) -> dict:
    """Build a minimal arq ctx for the handler. tool_mock wins over tools_list."""
    job_store = AsyncMock()
    job_store.save_result = AsyncMock()
    tools = tools_list if tools_list is not None else ([tool_mock] if tool_mock else [])
    return {
        "job_store": job_store,
        "mcp_tools": tools,
    }


def _make_notifier():
    notifier = AsyncMock()
    notifier.done = AsyncMock()
    notifier.progress = AsyncMock()
    return notifier


def _make_db_query_tool(return_value=None):
    """Build a mock BaseTool-like object with name == 'db_query' and async ainvoke."""
    tool = MagicMock()
    tool.name = "db_query"
    tool.ainvoke = AsyncMock(return_value=return_value if return_value is not None else {"rows": [{"id": 1}]})
    return tool


# ---------------------------------------------------------------------------
# Test 1: request span on handle()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_request_span_on_handle(capture_trace_logs):
    """handle() with an UNKNOWN method still emits exactly one request span."""
    handler = IframeRpcHandler()
    job = _make_job(method="UNKNOWN_METHOD")
    ctx = _make_ctx()

    with patch(
        "app.jobs.handlers.iframe_rpc_handler.build_notifier",
        return_value=_make_notifier(),
    ):
        await handler.handle(ctx, job)

    spans = capture_trace_logs()
    req_spans = [s for s in spans if s["operation_name"] == "request"]
    assert len(req_spans) == 1, f"expected 1 request span, got {len(req_spans)}: {spans}"

    req = req_spans[0]
    assert req["trace_id"] == job["correlation_id"]
    assert req["attributes"]["app_id"] == "canvas"
    assert req["attributes"]["handler"] == "iframe_rpc"
    assert req["attributes"]["rpc_method"] == "UNKNOWN_METHOD"
    assert req["attributes"]["user_id"] == "tester"


# ---------------------------------------------------------------------------
# Test 2: QUERY emits a tool_call span
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_query_emits_tool_call_span(capture_trace_logs):
    """method=QUERY invokes db_query tool and emits a tool_call span."""
    handler = IframeRpcHandler()
    tool = _make_db_query_tool(return_value={"rows": [{"id": 1}, {"id": 2}]})
    job = _make_job(
        method="QUERY",
        params={"pool_name": "main", "sql": "SELECT * FROM users"},
    )
    ctx = _make_ctx(tools_list=[tool])

    with patch(
        "app.jobs.handlers.iframe_rpc_handler.build_notifier",
        return_value=_make_notifier(),
    ):
        await handler.handle(ctx, job)

    spans = capture_trace_logs()
    tool_spans = [s for s in spans if s["operation_name"] == "tool_call"]
    assert len(tool_spans) == 1, f"expected 1 tool_call span, got {len(tool_spans)}: {spans}"

    t = tool_spans[0]
    assert t["trace_id"] == job["correlation_id"]
    assert t["attributes"]["tool_name"] == "db_query"
    assert t["attributes"]["privileged"] is False
    assert t["attributes"]["app_id"] == "canvas"
    assert t["attributes"]["agent_name"] == "iframe_rpc"
    assert t["attributes"]["user_id"] == "tester"
    assert t["attributes"]["success"] is True
    assert t["status_code"] == "OK"
    # args / result truncated prefixes must be present and non-empty
    assert "args_bytes" in t["attributes"]
    assert "args_prefix" in t["attributes"]
    assert "result_bytes" in t["attributes"]
    assert "result_prefix" in t["attributes"]
    # pool_name must be surfaced as an iframe_rpc-specific attribute
    assert t["attributes"]["pool_name"] == "main"

    # parent/child linkage: tool_call must be a child of the request span
    req_spans = [s for s in spans if s["operation_name"] == "request"]
    assert len(req_spans) == 1
    assert t["parent_span_id"] == req_spans[0]["span_id"]


# ---------------------------------------------------------------------------
# Test 3: QUERY returning an error dict marks span ERROR
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_query_error_dict_sets_error_status(capture_trace_logs):
    """Tool returning {"error": "..."} marks tool_call span ERROR + success=false."""
    handler = IframeRpcHandler()
    tool = _make_db_query_tool(return_value={"error": "permission denied"})
    job = _make_job(
        method="QUERY",
        params={"pool_name": "main", "sql": "INSERT INTO users VALUES (1)"},
    )
    ctx = _make_ctx(tools_list=[tool])

    with patch(
        "app.jobs.handlers.iframe_rpc_handler.build_notifier",
        return_value=_make_notifier(),
    ):
        await handler.handle(ctx, job)

    spans = capture_trace_logs()
    tool_spans = [s for s in spans if s["operation_name"] == "tool_call"]
    assert len(tool_spans) == 1
    t = tool_spans[0]
    assert t["status_code"] == "ERROR"
    assert "permission denied" in (t["status_message"] or "")
    assert t["attributes"]["success"] is False


# ---------------------------------------------------------------------------
# Test 4: QUERY tool.ainvoke raising sets ERROR, handler swallows
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_query_exception_sets_error_status(capture_trace_logs):
    """tool.ainvoke raising marks span ERROR but handler returns {result: False}."""
    handler = IframeRpcHandler()
    tool = MagicMock()
    tool.name = "db_query"
    tool.ainvoke = AsyncMock(side_effect=RuntimeError("boom"))
    job = _make_job(
        method="QUERY",
        params={"pool_name": "main", "sql": "SELECT 1"},
    )
    ctx = _make_ctx(tools_list=[tool])

    with patch(
        "app.jobs.handlers.iframe_rpc_handler.build_notifier",
        return_value=_make_notifier(),
    ):
        result = await handler.handle(ctx, job)

    # Handler swallows the tool exception and reports via save_result
    assert result["status"] == "done"

    saved_call = ctx["job_store"].save_result.call_args
    saved = json.loads(saved_call[0][1])
    assert saved["result"] is False
    assert "boom" in saved["error"]

    spans = capture_trace_logs()
    tool_spans = [s for s in spans if s["operation_name"] == "tool_call"]
    assert len(tool_spans) == 1
    t = tool_spans[0]
    assert t["status_code"] == "ERROR"
    assert t["attributes"]["success"] is False


# ---------------------------------------------------------------------------
# Test 5: AI emits a tool_call span with tool_name="ai"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ai_emits_tool_call_span(capture_trace_logs):
    """method=AI invokes ChatCopilot and emits a tool_call span with tool_name=ai."""
    handler = IframeRpcHandler()
    job = _make_job(
        method="AI",
        params={"model": "haiku", "prompt": "Hello"},
    )
    ctx = _make_ctx()

    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=MagicMock(content="Hi there!"))
    mock_llm.close = AsyncMock()

    with patch(
        "app.jobs.handlers.iframe_rpc_handler.build_notifier",
        return_value=_make_notifier(),
    ), patch(
        "app.jobs.handlers.iframe_rpc_handler.ChatCopilot",
        return_value=mock_llm,
    ):
        await handler.handle(ctx, job)

    spans = capture_trace_logs()
    tool_spans = [s for s in spans if s["operation_name"] == "tool_call"]
    assert len(tool_spans) == 1, f"expected 1 tool_call span, got {len(tool_spans)}: {spans}"

    t = tool_spans[0]
    assert t["trace_id"] == job["correlation_id"]
    assert t["attributes"]["tool_name"] == "ai"
    assert t["attributes"]["privileged"] is False
    assert t["attributes"]["app_id"] == "canvas"
    assert t["attributes"]["agent_name"] == "iframe_rpc"
    assert t["attributes"]["user_id"] == "tester"
    # model_name must be the resolved real ID (not the alias "haiku")
    assert t["attributes"]["model_name"] == "claude-haiku-4-5-20251001"
    assert t["attributes"]["success"] is True
    mock_llm.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# Test 6: UNKNOWN method emits no tool_call span
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unknown_method_no_tool_call_span(capture_trace_logs):
    """An unknown method emits only the request span, never tool_call."""
    handler = IframeRpcHandler()
    job = _make_job(method="UNKNOWN")
    ctx = _make_ctx()

    with patch(
        "app.jobs.handlers.iframe_rpc_handler.build_notifier",
        return_value=_make_notifier(),
    ):
        await handler.handle(ctx, job)

    spans = capture_trace_logs()
    assert len([s for s in spans if s["operation_name"] == "tool_call"]) == 0
    assert len([s for s in spans if s["operation_name"] == "request"]) == 1
