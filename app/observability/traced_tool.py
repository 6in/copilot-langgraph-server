"""LangChain BaseTool wrapper emitting a `tool_call` span around each ainvoke (Phase 31 D-10..D-12).

Design (RESEARCH §3.1):
- Subclasses `BaseTool`, so it can be dropped into `ToolNode([TracedTool(t,...)])` transparently.
- `name` / `description` / `args_schema` are forwarded from the wrapped tool at `__init__`.
- `_arun` wraps `wrapped.ainvoke(kwargs)` in `async with trace_span("tool_call", ...)`.
- `trace_id` is pulled from `_current_trace_id` ContextVar (set by an outer
  `async with trace_span("sub_agent", trace_id=...)` in Plan 04 / 05). Fallback "unknown"
  is used when there is no outer span (defensive for iframe_rpc legacy paths).
- Common 4 attributes (user_id / app_id / agent_name / model_name) are resolved in order:
    1. explicit `common_attrs_provider` callable (caller-provided)
    2. `_current_common_attrs` ContextVar (set by outer sub_agent span)
    3. empty dict (no common attrs)
- `privileged` boolean is set from `wrapped.name in privileged_tool_names` (frozenset).
  The frozenset is constructed in `worker.startup()` from `sandbox_exposed=false` entries in
  `config/mcp_tools.yaml` (see `orchestrator_handler.py:43`).
- `args_prefix` / `result_prefix` are truncated by `get_args_max_chars()` / `get_result_max_chars()`
  (env var driven, D-11). `args_bytes` / `result_bytes` record the UTF-8 byte length of the
  full JSON serialization.
- If the wrapped tool returns `{"error": ...}` dict, span is marked ERROR with the error as
  status_message and `success=False`. Exceptions are re-raised (trace_span handles ERROR).

Usage:
    from app.observability.traced_tool import TracedTool

    traced_tools = [TracedTool(t, privileged_tool_names=priv) for t in mcp_tools]
    tool_node = ToolNode(traced_tools)
"""
from __future__ import annotations

import json
import logging
from typing import Any, Callable

from langchain_core.tools import BaseTool
from pydantic import ConfigDict, PrivateAttr

from app.observability.config import get_args_max_chars, get_result_max_chars
from app.observability.trace import _current_common_attrs, _current_trace_id, trace_span

logger = logging.getLogger(__name__)


class TracedTool(BaseTool):
    """BaseTool の透過ラッパー。実行前後に tool_call span を emit する。

    Args:
        wrapped: ラップ対象の BaseTool。name / description / args_schema を継承する。
        privileged_tool_names: sandbox_exposed=false のツール名 frozenset。
            wrapped.name がここに含まれれば attributes.privileged=True。
        common_attrs_provider: 呼び出しごとに attributes に merge する共通属性を返す callable。
            指定がない場合は `_current_common_attrs` ContextVar から自動取得する
            (sub_agent span が set した user_id / app_id / agent_name / model_name)。
            指定がある場合は ContextVar より provider を優先する。
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    _wrapped: BaseTool = PrivateAttr()
    _privileged_names: frozenset[str] = PrivateAttr()
    _common_attrs_provider: Callable[[], dict[str, Any]] | None = PrivateAttr()

    def __init__(
        self,
        wrapped: BaseTool,
        privileged_tool_names: frozenset[str] = frozenset(),
        common_attrs_provider: Callable[[], dict[str, Any]] | None = None,
        **data: Any,
    ) -> None:
        super().__init__(
            name=wrapped.name,
            description=wrapped.description,
            args_schema=getattr(wrapped, "args_schema", None),
            **data,
        )
        object.__setattr__(self, "_wrapped", wrapped)
        object.__setattr__(self, "_privileged_names", frozenset(privileged_tool_names))
        object.__setattr__(self, "_common_attrs_provider", common_attrs_provider)

    # ------------------------------------------------------------------
    # BaseTool overrides
    # ------------------------------------------------------------------

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """Phase 31 scope: async only. All tool invocations go through `ainvoke` / `_arun`."""
        raise NotImplementedError(
            "TracedTool supports async execution only. Use ainvoke() / _arun()."
        )

    async def _arun(self, **kwargs: Any) -> Any:
        """Wrap `self._wrapped.ainvoke(kwargs)` in a `tool_call` span."""
        trace_id = _current_trace_id.get() or "unknown"
        args_max = get_args_max_chars()
        result_max = get_result_max_chars()

        args_json = json.dumps(kwargs, ensure_ascii=False, default=str)
        args_bytes = len(args_json.encode("utf-8"))

        # Resolve common 4 attrs: provider (caller) takes priority over ContextVar.
        if self._common_attrs_provider is not None:
            common: dict[str, Any] = dict(self._common_attrs_provider())
        else:
            common = dict(_current_common_attrs.get() or {})

        attributes: dict[str, Any] = {
            **common,
            "tool_name": self._wrapped.name,
            "args_bytes": args_bytes,
            "args_prefix": args_json[:args_max],
            "privileged": self._wrapped.name in self._privileged_names,
        }

        async with trace_span(
            "tool_call", trace_id=trace_id, attributes=attributes
        ) as span:
            result = await self._wrapped.ainvoke(kwargs)
            result_json = json.dumps(result, ensure_ascii=False, default=str)
            result_bytes = len(result_json.encode("utf-8"))
            span.set_attribute("result_bytes", result_bytes)
            span.set_attribute("result_prefix", result_json[:result_max])

            if isinstance(result, dict) and "error" in result:
                span.set_attribute("success", False)
                span.set_status("ERROR", str(result["error"])[:200])
            else:
                span.set_attribute("success", True)

            return result
