"""Unit tests for `app.observability.traced_tool.TracedTool` (Phase 31 Plan 03).

Verifies 10 behaviors (RED phase written before implementation exists):

    1.  test_pass_through                       — name/description/args_schema + ainvoke result
    2.  test_emits_tool_call_span               — tool_call span emitted with tool_name/success/privileged
    3.  test_args_result_bytes                  — args_bytes / result_bytes = UTF-8 len of JSON
    4.  test_args_result_prefix_truncation      — TRACE_ARGS_MAX_CHARS / TRACE_RESULT_MAX_CHARS
    5.  test_privileged_from_frozenset          — privileged_tool_names frozenset → attributes.privileged
    6.  test_error_dict_result                  — dict result with 'error' key → success=False + ERROR
    7.  test_exception_propagates               — wrapped _arun raising re-raises + ERROR span
    8.  test_concurrent_gather_siblings         — asyncio.gather siblings share parent_span_id
    9.  test_common_attrs_provider              — explicit provider merges 4 attrs
    9b. test_common_attrs_from_contextvar       — ContextVar fallback when provider is None

Helper:
    `_DummyTool(BaseTool)` — pydantic v2 BaseTool subclass with configurable return or Exception.

All tests rely on `capture_trace_logs` fixture from tests/conftest.py.
"""
from __future__ import annotations

import asyncio
import json

import pytest
from langchain_core.tools import BaseTool

from app.observability.trace import _current_common_attrs, trace_span
from app.observability.traced_tool import TracedTool


# ---------------------------------------------------------------------------
# Helper: minimal BaseTool subclass with injectable return / exception
# ---------------------------------------------------------------------------


class _DummyTool(BaseTool):
    """BaseTool subclass that returns a pre-configured value (or raises if Exception)."""

    name: str = "dummy"
    description: str = "a dummy tool for tests"

    # Pydantic v2 BaseTool は class attribute 宣言のみで値注入する必要があるため、
    # return_value は PrivateAttr 代わりに object.__setattr__ で注入する。
    model_config = {"arbitrary_types_allowed": True}

    def __init__(self, return_value=None, name: str = "dummy", description: str = "a dummy tool for tests", **data):
        super().__init__(name=name, description=description, **data)
        object.__setattr__(self, "_return_value", return_value)

    async def _arun(self, **kwargs):
        rv = getattr(self, "_return_value", None)
        if isinstance(rv, Exception):
            raise rv
        return rv

    def _run(self, **kwargs):
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Test 1: pass-through
# ---------------------------------------------------------------------------


async def test_pass_through(capture_trace_logs):
    """TracedTool exposes wrapped.name / wrapped.description; ainvoke returns wrapped result."""
    dummy = _DummyTool(return_value={"ok": 1})
    wrapped = TracedTool(dummy)

    assert wrapped.name == "dummy"
    assert wrapped.description == "a dummy tool for tests"
    # args_schema pass-through (None for _DummyTool)
    assert wrapped.args_schema is None

    result = await wrapped.ainvoke({"q": "hi"})
    assert result == {"ok": 1}


# ---------------------------------------------------------------------------
# Test 2: tool_call span emitted with core attributes
# ---------------------------------------------------------------------------


async def test_emits_tool_call_span(capture_trace_logs):
    """ainvoke emits 1 tool_call span; tool_name=name, success=True, privileged=False by default."""
    dummy = _DummyTool(return_value={"ok": 1})
    wrapped = TracedTool(dummy)

    async with trace_span(
        "sub_agent",
        trace_id="tid-outer",
        attributes={
            "user_id": "u",
            "app_id": "a",
            "agent_name": "ag",
            "model_name": "m",
        },
    ):
        await wrapped.ainvoke({"q": "hi"})

    spans = capture_trace_logs()
    tool_spans = [s for s in spans if s["operation_name"] == "tool_call"]
    assert len(tool_spans) == 1, f"Expected 1 tool_call span, got {len(tool_spans)}"
    span = tool_spans[0]
    assert span["trace_id"] == "tid-outer"
    assert span["parent_span_id"] is not None, "parent_span_id should be sub_agent's span_id"
    assert span["operation_name"] == "tool_call"
    attrs = span["attributes"]
    assert attrs["tool_name"] == "dummy"
    assert attrs["success"] is True
    assert attrs["privileged"] is False
    # duration_ms は int（0 以上）
    assert isinstance(span["duration_ms"], int)
    assert span["duration_ms"] >= 0


# ---------------------------------------------------------------------------
# Test 3: args_bytes / result_bytes = UTF-8 len of JSON serialization
# ---------------------------------------------------------------------------


async def test_args_result_bytes(capture_trace_logs):
    """args_bytes / result_bytes are len of JSON-serialized UTF-8 bytes."""
    payload = {"data": "x" * 100}
    dummy = _DummyTool(return_value={"out": "y" * 200})
    wrapped = TracedTool(dummy)

    async with trace_span("sub_agent", trace_id="tid-bytes"):
        await wrapped.ainvoke(payload)

    spans = capture_trace_logs()
    tool_spans = [s for s in spans if s["operation_name"] == "tool_call"]
    assert len(tool_spans) == 1
    attrs = tool_spans[0]["attributes"]

    # args は ainvoke で渡した dict を json.dumps したもの
    expected_args_bytes = len(json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8"))
    expected_result_bytes = len(
        json.dumps({"out": "y" * 200}, ensure_ascii=False, default=str).encode("utf-8")
    )

    assert attrs["args_bytes"] == expected_args_bytes
    assert attrs["result_bytes"] == expected_result_bytes


# ---------------------------------------------------------------------------
# Test 4: TRACE_*_MAX_CHARS env var truncation
# ---------------------------------------------------------------------------


async def test_args_result_prefix_truncation(monkeypatch, capture_trace_logs):
    """TRACE_ARGS_MAX_CHARS=10 / TRACE_RESULT_MAX_CHARS=20 truncates the prefix attribute."""
    monkeypatch.setenv("TRACE_ARGS_MAX_CHARS", "10")
    monkeypatch.setenv("TRACE_RESULT_MAX_CHARS", "20")

    long_args = {"q": "a" * 200}
    long_result = "b" * 500
    dummy = _DummyTool(return_value=long_result)
    wrapped = TracedTool(dummy)

    async with trace_span("sub_agent", trace_id="tid-trunc"):
        await wrapped.ainvoke(long_args)

    spans = capture_trace_logs()
    tool_spans = [s for s in spans if s["operation_name"] == "tool_call"]
    assert len(tool_spans) == 1
    attrs = tool_spans[0]["attributes"]

    # args_prefix は 10 文字に truncate される
    assert len(attrs["args_prefix"]) == 10
    # result_prefix は 20 文字に truncate される
    assert len(attrs["result_prefix"]) == 20
    # 元のバイト数は保存される
    assert attrs["args_bytes"] > 10
    assert attrs["result_bytes"] > 20


# ---------------------------------------------------------------------------
# Test 5: privileged_tool_names frozenset
# ---------------------------------------------------------------------------


async def test_privileged_from_frozenset(capture_trace_logs):
    """privileged_tool_names に含まれる name は attributes.privileged=True、含まれなければ False。"""
    dummy = _DummyTool(return_value={"ok": 1})

    # 含まれるケース
    priv = TracedTool(dummy, privileged_tool_names=frozenset({"dummy"}))
    async with trace_span("sub_agent", trace_id="tid-priv"):
        await priv.ainvoke({"q": "hi"})

    spans = capture_trace_logs()
    tool_spans = [s for s in spans if s["operation_name"] == "tool_call"]
    assert len(tool_spans) == 1
    assert tool_spans[0]["attributes"]["privileged"] is True


async def test_privileged_excluded(capture_trace_logs):
    """privileged_tool_names に含まれない name は privileged=False。"""
    dummy = _DummyTool(return_value={"ok": 1})
    npv = TracedTool(dummy, privileged_tool_names=frozenset({"other_tool"}))

    async with trace_span("sub_agent", trace_id="tid-nopriv"):
        await npv.ainvoke({"q": "hi"})

    spans = capture_trace_logs()
    tool_spans = [s for s in spans if s["operation_name"] == "tool_call"]
    assert len(tool_spans) == 1
    assert tool_spans[0]["attributes"]["privileged"] is False


# ---------------------------------------------------------------------------
# Test 6: dict result with 'error' key → success=False + status_code=ERROR
# ---------------------------------------------------------------------------


async def test_error_dict_result(capture_trace_logs):
    """wrapped が {'error':'denied'} を返すと status_code=ERROR + success=False + message に 'denied' を含む。"""
    dummy = _DummyTool(return_value={"error": "denied"})
    wrapped = TracedTool(dummy)

    async with trace_span("sub_agent", trace_id="tid-err"):
        result = await wrapped.ainvoke({"q": "hi"})

    # result はそのまま返る（例外化はしない）
    assert result == {"error": "denied"}

    spans = capture_trace_logs()
    tool_spans = [s for s in spans if s["operation_name"] == "tool_call"]
    assert len(tool_spans) == 1
    span = tool_spans[0]
    assert span["status_code"] == "ERROR"
    assert span["attributes"]["success"] is False
    assert span["status_message"] is not None
    assert "denied" in span["status_message"]


# ---------------------------------------------------------------------------
# Test 7: wrapped raising RuntimeError re-raises + ERROR span emitted
# ---------------------------------------------------------------------------


async def test_exception_propagates(capture_trace_logs):
    """wrapped._arun が RuntimeError を raise → TracedTool._arun も raise、かつ 1 ERROR span emit。"""
    dummy = _DummyTool(return_value=RuntimeError("boom"))
    wrapped = TracedTool(dummy)

    with pytest.raises(RuntimeError, match="boom"):
        async with trace_span("sub_agent", trace_id="tid-exc"):
            await wrapped.ainvoke({"q": "hi"})

    spans = capture_trace_logs()
    tool_spans = [s for s in spans if s["operation_name"] == "tool_call"]
    assert len(tool_spans) == 1
    span = tool_spans[0]
    assert span["status_code"] == "ERROR"
    assert span["status_message"] is not None
    assert "RuntimeError" in span["status_message"]


# ---------------------------------------------------------------------------
# Test 8: asyncio.gather siblings share parent_span_id, have distinct span_id
# ---------------------------------------------------------------------------


async def test_concurrent_gather_siblings(capture_trace_logs):
    """asyncio.gather で 2 個の TracedTool を並行実行 → 兄弟 span 2 個、span_id 相違、parent 同一。"""
    d1 = _DummyTool(return_value={"r": 1}, name="t1")
    d2 = _DummyTool(return_value={"r": 2}, name="t2")
    w1 = TracedTool(d1)
    w2 = TracedTool(d2)

    async with trace_span("sub_agent", trace_id="tid-gather"):
        await asyncio.gather(
            w1.ainvoke({"q": "a"}),
            w2.ainvoke({"q": "b"}),
        )

    spans = capture_trace_logs()
    tool_spans = [s for s in spans if s["operation_name"] == "tool_call"]
    sub_agent_span = next(s for s in spans if s["operation_name"] == "sub_agent")

    assert len(tool_spans) == 2, f"Expected 2 sibling tool_call spans, got {len(tool_spans)}"
    # span_id が相違
    assert tool_spans[0]["span_id"] != tool_spans[1]["span_id"]
    # parent_span_id が両方とも sub_agent の span_id
    assert tool_spans[0]["parent_span_id"] == sub_agent_span["span_id"]
    assert tool_spans[1]["parent_span_id"] == sub_agent_span["span_id"]


# ---------------------------------------------------------------------------
# Test 9: explicit common_attrs_provider
# ---------------------------------------------------------------------------


async def test_common_attrs_provider(capture_trace_logs):
    """common_attrs_provider が渡されると、その 4 値が attributes に merge される。"""
    dummy = _DummyTool(return_value={"ok": 1})
    provider_attrs = {
        "user_id": "u",
        "app_id": "a",
        "agent_name": "ag",
        "model_name": "m",
    }
    wrapped = TracedTool(dummy, common_attrs_provider=lambda: provider_attrs)

    async with trace_span("sub_agent", trace_id="tid-provider"):
        await wrapped.ainvoke({"q": "hi"})

    spans = capture_trace_logs()
    tool_spans = [s for s in spans if s["operation_name"] == "tool_call"]
    assert len(tool_spans) == 1
    attrs = tool_spans[0]["attributes"]
    for k, v in provider_attrs.items():
        assert attrs.get(k) == v, f"{k} missing or wrong (got {attrs.get(k)!r})"


# ---------------------------------------------------------------------------
# Test 9b: ContextVar fallback when provider is None (W2 behaviour)
# ---------------------------------------------------------------------------


async def test_common_attrs_from_contextvar(capture_trace_logs):
    """provider を省略時、_current_common_attrs の値が tool_call span に自動 merge される。"""
    dummy = _DummyTool(return_value={"ok": 1})
    wrapped = TracedTool(dummy)  # provider 省略

    cv_attrs = {
        "user_id": "cv_u",
        "app_id": "cv_a",
        "agent_name": "cv_ag",
        "model_name": "cv_m",
    }
    # trace_span が common attrs を渡されると内部で _current_common_attrs.set() する
    async with trace_span("sub_agent", trace_id="tid-cv", attributes=cv_attrs):
        await wrapped.ainvoke({"q": "hi"})

    spans = capture_trace_logs()
    tool_spans = [s for s in spans if s["operation_name"] == "tool_call"]
    assert len(tool_spans) == 1
    attrs = tool_spans[0]["attributes"]
    for k, v in cv_attrs.items():
        assert attrs.get(k) == v, f"ContextVar attr {k} missing (got {attrs.get(k)!r})"


# ---------------------------------------------------------------------------
# Test 10: _run raises NotImplementedError (async-only scope)
# ---------------------------------------------------------------------------


def test_run_sync_raises():
    """TracedTool._run is explicitly async-only; sync invocation must error."""
    dummy = _DummyTool(return_value={"ok": 1})
    wrapped = TracedTool(dummy)
    with pytest.raises(NotImplementedError):
        wrapped._run()
