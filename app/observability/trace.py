"""OTEL span-like JSONL writer abstraction for Phase 31 observability.

Emits a single JSON line to logger `"trace"` at `async with trace_span(...)` exit.
Docker logging driver rotation (quick 260418-tin) は既存設定に乗せる (D-03)。
`logger.info(json.dumps(...))` パターンは既存 `app/orchestrator/graph.py` を踏襲。

Usage:
    async with trace_span(
        "tool_call",
        trace_id=ctx.correlation_id,
        attributes={"tool_name": "web_search"},
    ) as span:
        result = await tool.ainvoke(args)
        span.set_attribute("result_bytes", len(str(result)))

Design notes:
- `ContextVar` で親 span の id を async 文脈に伝搬させる (Landmine 1 に留意するが、
  Phase 31 のユースケースでは nested graph 跨ぎは発生しない)。
- タイムスタンプは ISO-8601 UTC microseconds (`...Z` suffix)。OTLP 変換は
  `datetime.fromisoformat(s.replace("Z","+00:00")).timestamp() * 1e9` で 1 行変換可能。
- 共通 4 attributes (user_id / app_id / agent_name / model_name) が `trace_span` の
  attributes 引数に含まれる場合、`_current_common_attrs` ContextVar に subset を set
  することで子 span (tool_call) に明示的に渡さずに継承できる (W2 反映、D-09)。
- emit は必ず `finally` で実行され、例外時は status_code="ERROR" + 再送出。
  logger.info 自体が失敗しても caller には漏らさない (Landmine 6)。
"""
from __future__ import annotations

import json
import logging
import sys
import time
import uuid
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, AsyncIterator

logger = logging.getLogger("trace")


def _configure_trace_logger() -> None:
    """Attach stdout INFO StreamHandler to the `trace` logger at import time.

    Phase 31 emits spans via ``logger.info(json.dumps(...))`` and relies on the
    Docker logging driver capturing stdout. Python's default root logger level
    is WARNING, so without an explicit handler these INFO calls are silently
    dropped before ever reaching stdout (integration-check finding 2026-04-20).

    This bootstrap is idempotent and scoped to the `trace` logger only —
    root/uvicorn/arq loggers are left untouched. Propagation is left enabled
    so pytest's ``caplog`` fixture (which attaches to the root logger) can
    still capture span records in tests; in production the root logger has
    no handlers, so propagation is a no-op and no duplicate output is emitted.
    """
    if any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


_configure_trace_logger()

# ---------------------------------------------------------------------------
# ContextVars for async parent-span / trace_id / common-attrs propagation
# ---------------------------------------------------------------------------

# 親 span の span_id。`trace_span` 内で set し、`__aexit__` で reset。
_current_span_id: ContextVar[str | None] = ContextVar("_current_span_id", default=None)

# 現在の trace_id。将来的に caller が省略した場合の fallback 用。
_current_trace_id: ContextVar[str | None] = ContextVar("_current_trace_id", default=None)

# sub_agent span → tool_call span に共通 4 attributes を伝搬するための ContextVar (W2)。
# Plan 03 の TracedTool と Plan 04 の SubAgent.run() / ToolEnabledSubAgent.run() /
# CodeActSubAgent.run() が `_current_common_attrs.get()` で参照する internal シンボル。
_current_common_attrs: ContextVar[dict[str, Any] | None] = ContextVar(
    "trace_common_attrs", default=None
)

# 共通 4 attributes のキー集合 (D-09)
_COMMON_ATTR_KEYS = frozenset({"user_id", "app_id", "agent_name", "model_name"})


# ---------------------------------------------------------------------------
# Span schema
# ---------------------------------------------------------------------------


@dataclass
class SpanDict:
    """OTEL span-like JSON schema (10 top-level fields, D-07).

    フィールド:
        trace_id:       caller 指定 (通常 `RPCContext.correlation_id`、UUID4)
        span_id:        `uuid4().hex[:16]` (16-char hex)
        parent_span_id: 親 span id or None (root)
        operation_name: "routing" / "sub_agent" / "tool_call" (D-06)
        start_time:     ISO-8601 UTC microseconds with 'Z' suffix
        end_time:       同上
        duration_ms:    int (time.perf_counter 差分)
        status_code:    "OK" | "ERROR" | "UNSET"
        status_message: str or None
        attributes:     operation 固有 + 共通 4 attrs (D-09)
    """

    trace_id: str
    span_id: str
    parent_span_id: str | None
    operation_name: str
    start_time: str
    end_time: str
    duration_ms: int
    status_code: str
    status_message: str | None
    attributes: dict[str, Any]


class _ActiveSpan:
    """`async with trace_span(...) as span:` で yield されるオブジェクト。

    attribute 追加・status override の API を提供する。frozen ではない。
    """

    def __init__(self, attributes: dict[str, Any]) -> None:
        self.attributes: dict[str, Any] = attributes
        # (code, message) tuple or None。finally で例外ステータスより優先される。
        self._status_override: tuple[str, str | None] | None = None

    def set_attribute(self, key: str, value: Any) -> None:
        """属性を 1 つ追加 / 上書き。"""
        self.attributes[key] = value

    def set_attributes(self, mapping: dict[str, Any]) -> None:
        """属性を一括追加 / 上書き。"""
        self.attributes.update(mapping)

    def set_status(self, code: str, message: str | None = None) -> None:
        """例外以外の異常 (tool result が `{"error": ...}` 等) に使う明示 status 設定。"""
        self._status_override = (code, message)


# ---------------------------------------------------------------------------
# ChatCopilot usage attribute helper (Plan 04)
# ---------------------------------------------------------------------------

# 4 token-usage attribute keys confirmed by Plan 01 spike (haiku / sonnet / gpt-4.1).
# reasoning-related keys are intentionally omitted — reasoning_text is always empty
# in current models, and the T-31-01 mitigation keeps reasoning out of span attrs.
USAGE_ATTR_KEYS = (
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
)


def attach_usage_attributes(span: "_ActiveSpan", llm: Any) -> None:
    """Copy ``llm.last_usage`` (4 int fields) onto the active sub_agent span.

    ``llm`` is expected to expose a ``last_usage`` attribute (dict or None) —
    populated by ``app.providers.copilot.ChatCopilot`` via its ASSISTANT_USAGE
    hook. Missing or None values are skipped so the span only carries what the
    SDK actually produced. Non-``int`` values are int-cast for JSONL
    consistency.
    """
    usage = getattr(llm, "last_usage", None)
    if not usage:
        return
    for key in USAGE_ATTR_KEYS:
        value = usage.get(key)
        if value is not None:
            try:
                span.set_attribute(key, int(value))
            except (TypeError, ValueError):
                # Defensive — if SDK ever returns a non-numeric value, skip it.
                continue


# ---------------------------------------------------------------------------
# trace_span context manager
# ---------------------------------------------------------------------------


def _utc_iso_micro() -> str:
    """Return UTC ISO-8601 microseconds with 'Z' suffix."""
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


@asynccontextmanager
async def trace_span(
    operation_name: str,
    trace_id: str,
    attributes: dict[str, Any] | None = None,
    parent_span_id: str | None = None,
) -> AsyncIterator[_ActiveSpan]:
    """Emit one OTEL span-like JSON line on context exit.

    引数:
        operation_name: "routing" / "sub_agent" / "tool_call"
        trace_id:       通常 `RPCContext.correlation_id`
        attributes:     span attributes (共通 4 attrs を含めると ContextVar に伝搬)
        parent_span_id: 明示する場合。省略時は ContextVar から継承
    """
    span_id = uuid.uuid4().hex[:16]
    # ContextVar から親 span_id を継承 (引数優先)
    parent = parent_span_id if parent_span_id is not None else _current_span_id.get()

    start_wall = _utc_iso_micro()
    start_mono = time.perf_counter()

    # attributes は caller が渡した dict を壊さないようにコピー
    attrs_copy: dict[str, Any] = dict(attributes or {})
    active = _ActiveSpan(attributes=attrs_copy)

    token_span = _current_span_id.set(span_id)
    token_trace = _current_trace_id.set(trace_id)

    # 共通 4 attrs の subset が 1 つでも含まれていれば _current_common_attrs に set する。
    # 含まれなければ token_common は None のままスキップ (finally で reset しない)。
    token_common = None
    common_subset = {k: attrs_copy[k] for k in _COMMON_ATTR_KEYS if k in attrs_copy}
    if common_subset:
        token_common = _current_common_attrs.set(common_subset)

    status_code = "OK"
    status_message: str | None = None
    try:
        yield active
    except Exception as e:
        status_code = "ERROR"
        status_message = f"{type(e).__name__}: {str(e)[:200]}"
        raise
    finally:
        # ContextVar reset は必ず行う (Landmine 1 対策)
        _current_span_id.reset(token_span)
        _current_trace_id.reset(token_trace)
        if token_common is not None:
            _current_common_attrs.reset(token_common)

        end_wall = _utc_iso_micro()
        duration_ms = int((time.perf_counter() - start_mono) * 1000)

        # `set_status` による明示 override は例外 status より優先
        if active._status_override is not None:
            status_code, status_message = active._status_override

        span_dict = SpanDict(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent,
            operation_name=operation_name,
            start_time=start_wall,
            end_time=end_wall,
            duration_ms=duration_ms,
            status_code=status_code,
            status_message=status_message,
            attributes=active.attributes,
        )

        # emit 自体の失敗は caller に漏らさない (Landmine 6)
        try:
            logger.info(
                json.dumps(asdict(span_dict), ensure_ascii=False, default=str)
            )
        except Exception:
            # logger.exception も broken の可能性があるので二重 try で吸収
            try:
                logger.exception("trace_span emit failed")
            except Exception:
                pass
