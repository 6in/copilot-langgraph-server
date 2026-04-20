---
phase: 31-agent-mcp-observability
plan: 03
subsystem: observability
tags: [tracing, tool-call, wrapper, basetool, contextvars, pydantic-v2, pytest-asyncio]

# Dependency graph
requires:
  - phase: 31
    plan: 02
    provides: trace_span / _current_trace_id / _current_common_attrs / get_args_max_chars / get_result_max_chars
provides:
  - app.observability.traced_tool.TracedTool — BaseTool wrapper emitting tool_call span
  - app.observability.TracedTool — public re-export
affects: [31-04, 31-05]

# Tech tracking
tech-stack:
  added: []  # stdlib + pydantic v2 (PrivateAttr / ConfigDict) + langchain_core.tools.BaseTool (既存)
  patterns:
    - "BaseTool サブクラスで wrapped を保持し name/description/args_schema を forward するクラス wrapping パターン"
    - "ContextVar (_current_trace_id / _current_common_attrs) 優先度ルールによる caller-less 自動伝搬"
    - "dict 結果の 'error' key 検出 → span.set_status('ERROR') + success=False (iframe_rpc / _call_tool と同じ判定)"
    - "UTF-8 byte 数 (len(json.encode('utf-8'))) で args_bytes / result_bytes を記録する方針 (日本語対応 D-07)"

key-files:
  created:
    - app/observability/traced_tool.py
    - tests/test_traced_tool.py
  modified:
    - app/observability/__init__.py

key-decisions:
  - "TracedTool は langchain_core.tools.BaseTool のサブクラス (LangGraph ToolNode が BaseTool として受け取れる)"
  - "trace_id は _current_trace_id.get() から ContextVar 経由で引く (caller は async with trace_span('sub_agent', trace_id=...) で外側を包む想定)、外側がない場合は \"unknown\" でフォールバック"
  - "common 4 attrs は explicit provider > ContextVar > 空 dict の優先度で解決 (W2 反映、Plan 04/05 は引数指定なしで ContextVar 経由の自動継承を使う想定)"
  - "args_bytes / result_bytes は JSON serialize 後の UTF-8 byte 数 (日本語プロンプトで体感サイズと一致させる)"
  - "args_prefix / result_prefix は get_args_max_chars() / get_result_max_chars() で制御、env var で全ツール一律 (D-11)"
  - "dict 結果の 'error' key 検出時は success=False + status_code='ERROR' + status_message に error 値の 200 字 prefix"
  - "_run は NotImplementedError (Phase 31 スコープは async 限定、全経路が tool.ainvoke で呼ばれる)"

patterns-established:
  - "Pattern: `TracedTool(wrapped, privileged_tool_names=frozenset({...}))` で BaseTool を透過ラップ"
  - "Pattern: `ToolNode([TracedTool(t, privileged_tool_names=priv) for t in tools])` で ToolNode に差し替え (Plan 04 で適用予定)"
  - "Pattern: async with trace_span('sub_agent', trace_id=ctx.correlation_id, attributes={user_id:..., app_id:..., agent_name:..., model_name:...}): tool.ainvoke(...) で ContextVar 経由の自動継承"

requirements-completed: [D-10, D-11, D-12]

threat-mitigations-applied:
  - T-31-01: "args_prefix / result_prefix を env var で truncate (default 500 / 1000)、元サイズは args_bytes / result_bytes に記録"
  - T-31-02: "TRACE_ARGS_MAX_CHARS を運用時に絞れる env var を提供 (Plan 06 の docs/trace-query-recipes.md でチューニング指針記載予定)"
  - T-31-03: "privileged 判定は caller 提供の frozenset で行い、test_privileged_from_frozenset / test_privileged_excluded で boolean 両方向を検証"

# Metrics
duration: 15min
completed: 2026-04-19
---

# Phase 31 Plan 03: TracedTool wrapper Summary

**`app.observability.traced_tool.TracedTool` (`langchain_core.tools.BaseTool` サブクラス) を 128 行で実装し、wrapped tool の `ainvoke` を `async with trace_span("tool_call", ...)` で囲んで args_bytes / result_bytes / privileged / success を自動記録。tests/test_traced_tool.py 12 cases + tests/test_trace.py 既存 12 cases が全 green。Plan 04 で `ToolNode([TracedTool(t, privileged_tool_names=priv) for t in tools])` に差し替えるだけで tool_call span が自動 emit される。**

## Performance

- **Duration:** 約 15 分
- **Started:** 2026-04-19T09:14:00Z (worktree reset 後)
- **Completed:** 2026-04-19T09:29:00Z
- **Tasks:** 2 (RED + GREEN)
- **Files created:** 2 / **modified:** 1

## Accomplishments

- `app/observability/traced_tool.py` — 128 行。`TracedTool(BaseTool)` サブクラス。`__init__` で `wrapped.name / description / args_schema` を forward、`_wrapped / _privileged_names / _common_attrs_provider` を `PrivateAttr` で保持。`_arun` は `kwargs` を JSON 化してから `async with trace_span("tool_call", ...)` で wrap し、前半で `tool_name / args_bytes / args_prefix / privileged + common 4 attrs` を set、後半で `result_bytes / result_prefix / success` を set。dict 結果の `error` key 検出時は `span.set_status("ERROR", ...)` + `success=False`。例外は再送出 (`trace_span` が `finally` で ERROR 記録)。`_run` は NotImplementedError。
- `app/observability/__init__.py` — `TracedTool` を re-export。`__all__ = ["SpanDict", "TracedTool", "trace_span"]`。
- `tests/test_traced_tool.py` — 358 行・12 testcase。pass-through / tool_call span emit / args_result_bytes (UTF-8 長一致) / prefix truncation (env var) / privileged frozenset (in / not-in) / error dict / 例外再送出 / asyncio.gather 兄弟 span (parent_span_id 共有) / explicit provider / ContextVar fallback / `_run` sync NotImplementedError。

## Task Commits

1. **Task 1: add failing tests for TracedTool wrapper (RED)** — `32cda64` (test)
2. **Task 2: implement TracedTool wrapper with tool_call span emission (GREEN)** — `33d93b4` (feat)

_TDD 手順: RED コミットで `ModuleNotFoundError: No module named 'app.observability.traced_tool'` を確認してから GREEN 実装に移行。_

## Files Created/Modified

- `app/observability/traced_tool.py` (created, 128 行) — `TracedTool(BaseTool)` wrapper class。
- `app/observability/__init__.py` (modified, +2 行) — `TracedTool` を public re-export に追加。
- `tests/test_traced_tool.py` (created, 358 行) — `_DummyTool` helper + 12 testcase。

## Decisions Made

- **BaseTool サブクラスによる class wrapping を採用**: `_wrap_agent_run` (graph.py) は async 関数 wrapping だが、`TracedTool` は `BaseTool` のインターフェース (`name` / `description` / `args_schema` / `_arun` / `_run`) すべてが必要なのでクラス継承が素直。LangGraph ToolNode は `isinstance(tool, BaseTool)` でチェックするため、`MagicMock(spec=BaseTool)` ではなく実サブクラスにする必要があった (PATTERNS.md 注記)。
- **pydantic v2 `PrivateAttr` + `object.__setattr__` で wrap 対象を保持**: `BaseTool` は pydantic v2 `BaseModel` なので通常属性で `self._wrapped = ...` を代入すると validator に引っかかる。`_wrapped: BaseTool = PrivateAttr()` で private field 宣言 + `object.__setattr__(self, "_wrapped", wrapped)` で注入。
- **trace_id は ContextVar 優先、fallback \"unknown\"**: RESEARCH §3.1 の推奨に従い `_current_trace_id.get()` から引く。caller は外側の `async with trace_span("sub_agent", trace_id=ctx.correlation_id)` で自動的に ContextVar を set する。Plan 04/05 の統合時に caller 側の contract がシンプルになる (TracedTool に trace_id 引数を増やす必要なし)。
- **common attrs 解決の優先度**: 明示的 `common_attrs_provider` > `_current_common_attrs` ContextVar > 空 dict。Plan 04 は provider を省略して ContextVar 経由で自動継承する想定だが、単体テスト / 特殊ケース向けに provider を差し込めるオプションも残す (W2 反映の柔軟性)。
- **args_bytes / result_bytes は UTF-8 byte 数**: `len(json.dumps(..., ensure_ascii=False).encode("utf-8"))`。日本語プロンプトで運用者が見る size 感覚と一致させる。multibyte char は文字数ではなく byte 数で 1 件 > 1 byte になるため、alert rule の size threshold 設定時に実態と一致する。
- **dict result の error 判定**: `isinstance(result, dict) and "error" in result` → `span.set_status("ERROR", str(result["error"])[:200])` + `success=False`。これは既存 `iframe_rpc_handler.py:146-149` / `_call_tool` の判定と同じ規約 (PATTERNS.md shared pattern D) に揃えた。
- **`_run` は NotImplementedError**: langchain_core BaseTool は sync `_run` も要求するが、Phase 31 の全 tool 経路 (ToolNode / tool.ainvoke / CodeActTool) は async のみ。明示的 NotImplementedError で誤用時に即座に失敗させる。

## Deviations from Plan

None — プラン通り実行。軽微な差分を明記:

- **Test 件数**: プランは「8+ async testcase」を要求。実装は async 10 + sync 1 = 11 testcase + 1 sibling (`test_privileged_excluded`) = 12 件。`test_privileged_excluded` は Task 1 の Test 5 (`test_privileged_from_frozenset`) を「含むケース」と「含まないケース」に分割したもの。両方向の boolean を検証するほうが regression 防止に効く判断で分割した。
- **`_DummyTool` の設計**: プラン記載の skeleton では `object.__setattr__` を使うが pydantic v2 で `_return_value` を安定して注入するため `class attribute` 宣言を省略して `__init__` でのみ `object.__setattr__` を呼ぶ形にした (class attribute 宣言があると pydantic の field validator に引っかかる)。

**Total deviations:** 0 (プラン通り、差分は粒度の微調整のみ)

## Issues Encountered

- **docker compose services が up していなかった**: `docker compose ps` で NAME カラムが空だったため、verification は docker compose exec ではなく host の `uv run pytest` で実行。`.venv` は `uv run` が自動で build (107 packages) した。テストは pure Python + pytest-asyncio で DB / Redis / MCP server 依存なし、同等の結果を得られる。Phase 31 Plan 03 は observability 単体層のため docker 起動は verification に必須ではない。
- **worktree base mismatch**: 初回起動時 `git merge-base HEAD <expected>` が `c7319d2c...` を返し、expected `448a4002...` と不一致。Worktree_branch_check に従い `git reset --hard 448a4002...` で修正。コミット履歴には影響なし (worktree 専用 branch `worktree-agent-ad20446d`)。

## User Setup Required

None - 新規インフラ・env var の運用追加なし。Plan 02 で既出の `TRACE_ARGS_MAX_CHARS` / `TRACE_RESULT_MAX_CHARS` env var がそのまま作用する。

## Next Phase Readiness

- **Plan 04 (SubAgent span integration)**: `from app.observability import TracedTool` + `from app.observability.trace import trace_span` で起動可能。`ToolEnabledSubAgent.__init__` L252 `self._tool_node = ToolNode(tools)` の直前で `traced = [TracedTool(t, privileged_tool_names=priv) for t in tools]; self._tool_node = ToolNode(traced)` に書き換える。`run()` 周囲を `async with trace_span("sub_agent", trace_id=ctx.correlation_id, attributes={...common 4 attrs...}):` で包めば ContextVar 経由で tool_call span が自動 inheritance される (common_attrs_provider 省略可)。
- **Plan 05 (CodeAct / iframe_rpc)**: 同じ `TracedTool(...)` パターンが `execute_python` や iframe_rpc の tool.ainvoke 呼び出しに適用可能。外側で `trace_span("sub_agent", ...)` を張れば `_current_common_attrs` 経由で 4 attrs 継承。
- **既知の制限**: `common_attrs_provider` を明示する場合は `[Rule 2]` として引数で渡せるが、通常は省略して ContextVar 経由で統一する方針 (caller の contract をシンプルに保つ)。
- **引き継ぎ contract**:
    - `TracedTool(wrapped, privileged_tool_names=frozenset(), common_attrs_provider=None)` のシグネチャは Plan 04/05 で変更しない。
    - `privileged_tool_names` は worker startup で `ctx["mcp_privileged_tool_names"]` として既に frozenset が計算されている (orchestrator_handler.py:43)。
    - `_current_trace_id` / `_current_common_attrs` は Plan 02 で export 済の internal ContextVar (`from app.observability.trace import ...` で直 import)。

## Self-Check

自動チェック結果:

- `app/observability/traced_tool.py` — FOUND (128 行)
- `app/observability/__init__.py` に `TracedTool` export — FOUND
- `tests/test_traced_tool.py` — FOUND (358 行, 12 testcases)
- commit `32cda64` (test RED) — FOUND in git log
- commit `33d93b4` (feat GREEN) — FOUND in git log
- `uv run pytest tests/test_traced_tool.py -x` — 12 passed
- `uv run pytest tests/test_trace.py -x` — 12 passed (非破壊)
- `grep -q "from langchain_core.tools import BaseTool" app/observability/traced_tool.py` — OK
- `grep -q "privileged" app/observability/traced_tool.py` — OK
- `grep -q "get_args_max_chars\|get_result_max_chars" app/observability/traced_tool.py` — OK
- `from app.observability import TracedTool` — OK
- `python3 -c "import ast; ast.parse(open('tests/test_traced_tool.py').read())"` — OK

## Self-Check: PASSED

---
*Phase: 31-agent-mcp-observability*
*Completed: 2026-04-19*
