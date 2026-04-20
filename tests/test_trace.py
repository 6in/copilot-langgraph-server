"""Unit tests for `app.observability.trace` writer abstraction (Phase 31 Plan 02).

Verifies 10 behaviors plus 1 ContextVar propagation case (11 total):

    1. test_emit_basic_span         — basic JSONL emit with core fields
    2. test_span_schema_complete    — SpanDict has exactly 10 top-level fields
    3. test_status_code_on_exception — exception => ERROR status + re-raise
    4. test_trace_span_ids          — 16-hex span_id, caller-supplied trace_id
    5. test_parent_span_propagation — nested ContextVar propagation
    6. test_common_attributes       — user_id / app_id / agent_name / model_name
    7. test_truncate_env_vars       — TRACE_ARGS_MAX_CHARS / TRACE_RESULT_MAX_CHARS
    8. test_prefix_200              — caller-side prefix truncation surfaces in attrs
    9. test_set_status_override     — span.set_status("ERROR", ...) without exception
   10. test_emit_failure_does_not_raise — broken logger.info does not propagate
   11. test_common_attrs_contextvar_propagation — _current_common_attrs set/reset

All tests use the `capture_trace_logs` fixture from tests/conftest.py.
"""
from __future__ import annotations

import re

import pytest

from app.observability.config import get_args_max_chars, get_result_max_chars
from app.observability.trace import SpanDict, _current_common_attrs, trace_span


# ---------------------------------------------------------------------------
# Test 1: basic emit
# ---------------------------------------------------------------------------


async def test_emit_basic_span(capture_trace_logs):
    """A single `async with trace_span(...)` emits exactly one JSON line to logger 'trace'."""
    async with trace_span("routing", trace_id="tid-1"):
        pass

    spans = capture_trace_logs()
    assert len(spans) == 1, f"Expected 1 span, got {len(spans)}"
    s = spans[0]
    assert s["operation_name"] == "routing"
    assert s["trace_id"] == "tid-1"
    assert "span_id" in s and s["span_id"]
    assert "duration_ms" in s and isinstance(s["duration_ms"], int)
    assert s["duration_ms"] >= 0
    assert "start_time" in s and s["start_time"]
    assert "end_time" in s and s["end_time"]
    assert s["status_code"] == "OK"


# ---------------------------------------------------------------------------
# Test 2: schema completeness
# ---------------------------------------------------------------------------


async def test_span_schema_complete(capture_trace_logs):
    """SpanDict must have exactly 10 top-level fields in the emitted JSON."""
    async with trace_span("sub_agent", trace_id="tid-schema", attributes={"agent_name": "a"}):
        pass

    spans = capture_trace_logs()
    assert len(spans) == 1
    s = spans[0]
    expected_keys = {
        "trace_id",
        "span_id",
        "parent_span_id",
        "operation_name",
        "start_time",
        "end_time",
        "duration_ms",
        "status_code",
        "status_message",
        "attributes",
    }
    assert set(s.keys()) == expected_keys, (
        f"Span keys mismatch. Expected {expected_keys}, got {set(s.keys())}"
    )
    # attributes should be a dict
    assert isinstance(s["attributes"], dict)


# ---------------------------------------------------------------------------
# Test 3: exception handling
# ---------------------------------------------------------------------------


async def test_status_code_on_exception(capture_trace_logs):
    """Exception inside the block => status_code=ERROR, status_message prefixed with type;
    the exception is re-raised."""
    with pytest.raises(RuntimeError, match="boom"):
        async with trace_span("tool_call", trace_id="tid-err"):
            raise RuntimeError("boom")

    spans = capture_trace_logs()
    assert len(spans) == 1
    s = spans[0]
    assert s["status_code"] == "ERROR"
    assert s["status_message"] is not None
    assert s["status_message"].startswith("RuntimeError: boom")


# ---------------------------------------------------------------------------
# Test 4: id shapes
# ---------------------------------------------------------------------------


async def test_trace_span_ids(capture_trace_logs):
    """trace_id equals caller input; span_id is 16 hex chars."""
    async with trace_span("routing", trace_id="tid-xyz"):
        pass

    spans = capture_trace_logs()
    assert len(spans) == 1
    s = spans[0]
    assert s["trace_id"] == "tid-xyz"
    assert re.fullmatch(r"[0-9a-f]{16}", s["span_id"]), (
        f"span_id must be 16 hex chars, got {s['span_id']!r}"
    )
    # start_time / end_time should be ISO-8601 UTC microseconds with 'Z'
    iso_re = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z"
    assert re.fullmatch(iso_re, s["start_time"]), f"start_time shape: {s['start_time']!r}"
    assert re.fullmatch(iso_re, s["end_time"]), f"end_time shape: {s['end_time']!r}"


# ---------------------------------------------------------------------------
# Test 5: ContextVar parent propagation
# ---------------------------------------------------------------------------


async def test_parent_span_propagation(capture_trace_logs):
    """Nested trace_span: inner.parent_span_id == outer.span_id; outer.parent is None."""
    async with trace_span("routing", trace_id="tid-nest"):
        async with trace_span("sub_agent", trace_id="tid-nest"):
            pass

    spans = capture_trace_logs()
    assert len(spans) == 2, f"Expected 2 spans, got {len(spans)}"
    # Emit order: inner finishes first (emitted on __aexit__), then outer.
    inner = next(s for s in spans if s["operation_name"] == "sub_agent")
    outer = next(s for s in spans if s["operation_name"] == "routing")
    assert outer["parent_span_id"] is None
    assert inner["parent_span_id"] == outer["span_id"]


# ---------------------------------------------------------------------------
# Test 6: common 4 attributes
# ---------------------------------------------------------------------------


async def test_common_attributes(capture_trace_logs):
    """All 4 common attributes (user_id/app_id/agent_name/model_name) surface under attributes."""
    common = {
        "user_id": "0hya6in",
        "app_id": "superchat",
        "agent_name": "researcher",
        "model_name": "claude-sonnet-4-6",
    }
    async with trace_span("sub_agent", trace_id="tid-common", attributes=common):
        pass

    spans = capture_trace_logs()
    assert len(spans) == 1
    attrs = spans[0]["attributes"]
    for k, v in common.items():
        assert attrs.get(k) == v, f"attribute {k!r} missing or mismatched (got {attrs.get(k)!r})"


# ---------------------------------------------------------------------------
# Test 7: env var helpers
# ---------------------------------------------------------------------------


async def test_truncate_env_vars(monkeypatch):
    """TRACE_ARGS_MAX_CHARS / TRACE_RESULT_MAX_CHARS env vars are respected; defaults otherwise."""
    # With env set
    monkeypatch.setenv("TRACE_ARGS_MAX_CHARS", "10")
    monkeypatch.setenv("TRACE_RESULT_MAX_CHARS", "20")
    assert get_args_max_chars() == 10
    assert get_result_max_chars() == 20

    # Without env (unset)
    monkeypatch.delenv("TRACE_ARGS_MAX_CHARS", raising=False)
    monkeypatch.delenv("TRACE_RESULT_MAX_CHARS", raising=False)
    assert get_args_max_chars() == 500
    assert get_result_max_chars() == 1000


# ---------------------------------------------------------------------------
# Test 8: caller-side prefix truncation visible in attributes
# ---------------------------------------------------------------------------


async def test_prefix_200(capture_trace_logs):
    """If caller writes prefix attribute with [:200], attributes.user_input_prefix length is 200."""
    long_text = "a" * 500
    async with trace_span("routing", trace_id="tid-prefix") as span:
        span.set_attribute("user_input_prefix", long_text[:200])

    spans = capture_trace_logs()
    assert len(spans) == 1
    attrs = spans[0]["attributes"]
    assert "user_input_prefix" in attrs
    assert len(attrs["user_input_prefix"]) == 200


# ---------------------------------------------------------------------------
# Test 9: set_status override (no exception)
# ---------------------------------------------------------------------------


async def test_set_status_override(capture_trace_logs):
    """span.set_status('ERROR', msg) applies even when no exception is raised."""
    async with trace_span("tool_call", trace_id="tid-set-status") as span:
        span.set_status("ERROR", "tool returned error")

    spans = capture_trace_logs()
    assert len(spans) == 1
    s = spans[0]
    assert s["status_code"] == "ERROR"
    assert s["status_message"] == "tool returned error"


# ---------------------------------------------------------------------------
# Test 10: emit failure must not leak
# ---------------------------------------------------------------------------


async def test_emit_failure_does_not_raise(monkeypatch, capture_trace_logs):
    """Even if logger.info is patched to raise, trace_span must not propagate the failure."""
    import app.observability.trace as trace_mod

    def boom(*args, **kwargs):
        raise RuntimeError("logger is broken")

    monkeypatch.setattr(trace_mod.logger, "info", boom)

    # Must not raise to the caller
    async with trace_span("routing", trace_id="tid-broken"):
        pass
    # Test passes simply by not raising


# ---------------------------------------------------------------------------
# Test 11: _current_common_attrs ContextVar propagation (W2)
# ---------------------------------------------------------------------------


async def test_common_attrs_contextvar_propagation(capture_trace_logs):
    """_current_common_attrs is set from common attrs inside sub_agent span and reset on exit."""
    # default is None before any span
    assert _current_common_attrs.get() is None

    common = {
        "user_id": "u1",
        "app_id": "superchat",
        "agent_name": "researcher",
        "model_name": "claude-sonnet-4-6",
    }
    async with trace_span("sub_agent", trace_id="tid-ctxvar", attributes=common):
        inside = _current_common_attrs.get()
        assert inside is not None, "_current_common_attrs should be set inside sub_agent span"
        # Only the 4 common keys should be present in the subset
        assert inside.get("user_id") == "u1"
        assert inside.get("app_id") == "superchat"
        assert inside.get("agent_name") == "researcher"
        assert inside.get("model_name") == "claude-sonnet-4-6"

    # After exit, ContextVar must be reset to None (default)
    assert _current_common_attrs.get() is None


# ---------------------------------------------------------------------------
# Sanity: SpanDict is importable
# ---------------------------------------------------------------------------


def test_spandict_import_symbol():
    """SpanDict must be importable (contract for Plan 03/04/05)."""
    assert SpanDict is not None
