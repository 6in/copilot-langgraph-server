"""Phase 31 observability 層 — OTEL span-like JSONL writer + TracedTool wrapper。

Public API:
    trace_span  — `async with trace_span("op", trace_id=...) as span:` context manager
    SpanDict    — OTEL-like span dataclass (10 fields, D-07)
    TracedTool  — BaseTool wrapper emitting tool_call span around ainvoke (Plan 03)

内部シンボル (Plan 03/04 の直 import 用):
    from app.observability.trace import _current_common_attrs

主要方針は `.planning/phases/31-agent-mcp-observability/31-CONTEXT.md` D-05 / D-07 参照。
"""
from __future__ import annotations

from app.observability.trace import SpanDict, trace_span
from app.observability.traced_tool import TracedTool

__all__ = ["SpanDict", "TracedTool", "trace_span"]
