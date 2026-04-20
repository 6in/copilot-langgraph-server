"""TRACE_* env var ヘルパー。

Phase 31 D-11 方針: `args` / `result` の truncate 閾値は env var で**全ツール一律**に
制御する (`config/mcp_tools.yaml` に per-tool redact 指定は入れない)。

- `TRACE_ARGS_MAX_CHARS` default 500  — tool_call span の `args_prefix` 切り詰め長
- `TRACE_RESULT_MAX_CHARS` default 1000 — tool_call span の `result_prefix` 切り詰め長

不正値 (非 int / 負数) は default にフォールバックして絶対に例外を出さない方針。
"""
from __future__ import annotations

import os

_DEFAULT_ARGS_MAX = 500
_DEFAULT_RESULT_MAX = 1000


def get_args_max_chars() -> int:
    """TRACE_ARGS_MAX_CHARS env var を int で返す (default 500、不正値も default)。"""
    raw = os.environ.get("TRACE_ARGS_MAX_CHARS")
    if not raw:
        return _DEFAULT_ARGS_MAX
    try:
        v = int(raw)
        return v if v >= 0 else _DEFAULT_ARGS_MAX
    except ValueError:
        return _DEFAULT_ARGS_MAX


def get_result_max_chars() -> int:
    """TRACE_RESULT_MAX_CHARS env var を int で返す (default 1000、不正値も default)。"""
    raw = os.environ.get("TRACE_RESULT_MAX_CHARS")
    if not raw:
        return _DEFAULT_RESULT_MAX
    try:
        v = int(raw)
        return v if v >= 0 else _DEFAULT_RESULT_MAX
    except ValueError:
        return _DEFAULT_RESULT_MAX
