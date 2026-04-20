---
phase: 31-agent-mcp-observability
plan: 02
subsystem: observability
tags: [tracing, otel-span, jsonl, contextvars, pytest-asyncio, stdlib-only]

# Dependency graph
requires:
  - phase: 11-rpc-context
    provides: RPCContext.correlation_id (UUID4) が trace_id の源泉として流用可能
provides:
  - app.observability.trace.trace_span — async with context manager (OTEL span-like JSONL writer)
  - app.observability.trace.SpanDict — dataclass with 10 top-level fields
  - app.observability.trace._current_common_attrs — ContextVar (Plan 03/04 internal import)
  - app.observability.config.get_args_max_chars / get_result_max_chars — TRACE_* env var accessors
  - tests/conftest.py::capture_trace_logs — pytest fixture (caplog → parsed span dicts)
affects: [31-03, 31-04, 31-05, 31-06, 31-07, 31-08]

# Tech tracking
tech-stack:
  added: []  # stdlib-only (json, logging, time, uuid, contextlib, contextvars, dataclasses, datetime)
  patterns:
    - "OTEL span-like JSON line emit to logger 'trace' (future OTLP差し替え可)"
    - "ContextVar-based async parent-span / trace_id / common-attrs propagation"
    - "Exception-safe emit via finally + 二重 try で Landmine 6 を吸収"
    - "Env var fallback on invalid value (絶対に例外を出さない)"

key-files:
  created:
    - app/observability/__init__.py
    - app/observability/trace.py
    - app/observability/config.py
    - tests/test_trace.py
  modified:
    - tests/conftest.py

key-decisions:
  - "logger 名は \"trace\" 固定 (capture_trace_logs fixture と対応)"
  - "タイムスタンプは ISO-8601 UTC microseconds + Z suffix (jq で読める、OTLP変換1行で済む)"
  - "_current_common_attrs の set は attrs に共通4キーが1つでも含まれれば作動し、含まれない span (tool_call の下位 call 等) は reset を skip して leak を防ぐ"
  - "logger.info 失敗時の二重 try/except は RESEARCH §2.1 の Landmine 6 を厳密に守るための追加安全弁"

patterns-established:
  - "Pattern: `async with trace_span(op, trace_id, attributes) as span:` — duration 自動計測 / 例外時 ERROR status 自動 / ContextVar reset 保証"
  - "Pattern: `_current_common_attrs.get()` を caller 側で参照して子 span に 4 attrs を伝搬させる (Plan 03 TracedTool / Plan 04 *.run の直 import)"
  - "Pattern: env var ヘルパーは空文字・非int・負数すべて default fallback で絶対例外を出さない"

requirements-completed: [D-01, D-03, D-04, D-05, D-06, D-07, D-08, D-09, D-11, D-13]

# Metrics
duration: 7min
completed: 2026-04-19
---

# Phase 31 Plan 02: trace writer abstraction Summary

**OTEL span-like JSONL writer (`app.observability.trace`) を `async with trace_span(...)` context manager + ContextVar ベースの親子伝搬で実装し、Wave 0 テスト基盤 (`tests/test_trace.py` 12 cases + `capture_trace_logs` fixture) を green にした。**

## Performance

- **Duration:** 約 7 分
- **Started:** 2026-04-19T08:33:00Z (approx; worktree reset 後)
- **Completed:** 2026-04-19T08:40:00Z
- **Tasks:** 2 (RED + GREEN)
- **Files created:** 4 / **modified:** 1

## Accomplishments

- `app/observability/trace.py` — 215 行。`trace_span` / `SpanDict` / `_ActiveSpan` / 3 ContextVar / `_utc_iso_micro` を stdlib のみで実装。Landmine 1 (ContextVar reset) / Landmine 6 (logger emit 失敗吸収) を明示的にハンドル。
- `app/observability/config.py` — 40 行。`get_args_max_chars` (default 500) / `get_result_max_chars` (default 1000) env accessors。空文字 / 非 int / 負数はすべて default fallback。
- `app/observability/__init__.py` — `trace_span` / `SpanDict` を public re-export。`_current_common_attrs` は internal シンボルとして `app.observability.trace` から直接 import する契約を docstring に明記。
- `tests/conftest.py` — `capture_trace_logs` fixture 追加 (pytest caplog + `json.loads(record.getMessage())` closure)。
- `tests/test_trace.py` — 11 async testcase + 1 import sanity test = 12 件すべて green。basic emit / schema 10 fields / exception ERROR + re-raise / 16-hex span_id / ISO-8601 regex / nested parent propagation / common 4 attrs / env var truncate / prefix 200 / set_status override / emit 失敗吸収 / `_current_common_attrs` ContextVar set+reset。

## Task Commits

1. **Task 1: add failing tests for trace writer abstraction (RED)** — `31c484d` (test)
2. **Task 2: implement trace writer abstraction (GREEN)** — `33d1075` (feat)

_TDD 手順: RED コミットで `ModuleNotFoundError: No module named 'app.observability'` を確認してから GREEN 実装に移行。_

## Files Created/Modified

- `app/observability/__init__.py` — パッケージ init。`trace_span` / `SpanDict` を re-export。
- `app/observability/trace.py` — writer 本体。`trace_span` context manager + `SpanDict` dataclass + 3 ContextVar + `_utc_iso_micro` + `_ActiveSpan` helper。
- `app/observability/config.py` — `TRACE_ARGS_MAX_CHARS` / `TRACE_RESULT_MAX_CHARS` env var accessors。
- `tests/test_trace.py` — 12 testcase (281 行)。pytest-asyncio auto mode で `@pytest.mark.asyncio` は省略。
- `tests/conftest.py` — 末尾に `capture_trace_logs` fixture を追加 (既存 fixture 群の書式を踏襲)。

## Decisions Made

- **logger 名は `"trace"` 固定**: `capture_trace_logs` fixture が `caplog.set_level(logging.INFO, logger="trace")` で取得する契約と一致。既存の `app.orchestrator.graph` logger とは分離する (Plan 06 で routing 移行時に `"trace"` へ寄せる予定)。
- **タイムスタンプは ISO-8601 UTC microseconds + `Z` suffix**: Research §1.4 の判断に従い、`datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")` の正規形を採用。jq で `select(.start_time > "2026-04-18T12:00")` が直接効く。
- **`_current_common_attrs` の set/reset スコープ**: attrs に共通 4 key (`user_id` / `app_id` / `agent_name` / `model_name`) が 1 つでも含まれるときのみ set。tool_call span のように共通 4 attrs を持たない span は `token_common = None` のまま reset を skip するので、外側 sub_agent span の値を leak なく継承する。
- **Landmine 6 (logger emit 失敗) 対応**: 内側 `try/except Exception` で `logger.exception` にフォールバックし、それすら失敗した場合は二重 `try/except` で完全吸収する。`trace_span` は caller を絶対に巻き込まない契約を厳守。

## Deviations from Plan

None — プラン通り実行。ただし下記の軽微な差分を明記する:

- **Test 件数**: プランは「8+ async testcase」を要求。実際は 11 async + 1 sync (import sanity) = 12 件。プラン記載の 10 ケース (1-10) + Test 11 (ContextVar) + import sanity という構成で、プランの must_haves 全項目を満たす。
- **Landmine 6 の二重吸収**: プラン Step 2 では内側 `try: logger.info(...) except: logger.exception(...)` のみを要求。実装では `logger.exception` 自体が壊れていても漏らさないよう更に外側 `try/except Exception: pass` を入れた (writer の「絶対に caller を止めない」契約を厳密化)。テスト `test_emit_failure_does_not_raise` は `logger.info` のみ壊すので本追加安全弁は実質的に不要だが防御的に残す。

**Total deviations:** 0 (プラン通り、差分は粒度の微調整のみ)

## Issues Encountered

- **既存テスト suite 内に 24 件の失敗**: postgres への到達不能 (test_worker.py)、`async for` mock 不備 (test_graph.py)、401 認証失敗 (test_api_chat.py, test_api_jobs.py, test_sse.py) 等。これらは HEAD (`dd6ab57`) 時点で既存の pre-existing failures であることを確認 (observability モジュールを一時退避して同じ test を走らせ、同じ 24 件が失敗することを確認)。Phase 31 Plan 02 の変更 (writer 新規追加) は影響ゼロ。スコープ境界ルールに従い修正せず、本 SUMMARY に記録のみ。
- **worktree の stash pop による一時的な conflict**: `git stash` / `git stash pop` の運用ミスで古い stash が復活しかけたが、`git reset --hard HEAD` + `git stash drop` で即リカバリ。`/tmp/observability_backup` を経由して作成中の observability ファイルは保全。コミット履歴には影響なし。

## User Setup Required

None - 新規インフラ・env var の運用追加なし。既存の docker logging driver rotation (quick 260418-tin 設定済み) に自動で乗る (D-03)。ただし運用者は必要に応じて以下の env var で truncate 閾値を上書き可能:

- `TRACE_ARGS_MAX_CHARS` (default 500)
- `TRACE_RESULT_MAX_CHARS` (default 1000)

## Next Phase Readiness

- **Plan 03 (TracedTool)**: `from app.observability.trace import trace_span` + `from app.observability.config import get_args_max_chars` + `from app.observability.trace import _current_common_attrs` の 3 行で完全に起動可能。
- **Plan 04 (SubAgent span integration)**: `async with trace_span("sub_agent", trace_id=ctx.correlation_id, attributes={"user_id":..., "app_id":..., "agent_name":..., "model_name":...}) as span:` で囲めばよい。`_current_common_attrs` への set は writer 側で自動実行される。
- **Plan 05 (CodeAct span integration)**: 同上。`execute_python.ainvoke` の周囲に `trace_span("tool_call", ..., attributes={"tool_name":"execute_python","privileged":True})` を配置すれば ContextVar で 4 attrs が継承される。
- **Plan 06 (routing span integration)**: 既存 `graph.py` L47-101 の `logger.info(json.dumps({"event":"routing", ...}))` 4 箇所を `async with trace_span("routing", ...)` に置換。互換 alias は残さない (CONTEXT.md specifics)。
- **既知の制限**: LangGraph nested task での ContextVar 伝搬は `asyncio.create_task()` の Context copy 規約により動作するはずだが、実挙動は Plan 04 の統合テスト (`tests/test_sub_agent_trace.py`) で再確認する。Research Landmine 1 (langchain-ai/langgraph#4826) の nested graph streaming leak は Phase 31 のユースケース範囲外。

## Self-Check

自動チェック結果:

- `app/observability/__init__.py` — FOUND
- `app/observability/trace.py` — FOUND
- `app/observability/config.py` — FOUND
- `tests/test_trace.py` — FOUND
- `tests/conftest.py` の `capture_trace_logs` fixture — FOUND (`grep -q capture_trace_logs` 合致)
- commit `31c484d` (RED) — FOUND in git log
- commit `33d1075` (GREEN) — FOUND in git log
- `uv run pytest tests/test_trace.py -x` — 12 passed
- `grep -q 'logger = logging.getLogger("trace")' app/observability/trace.py` — OK
- `grep -q 'ensure_ascii=False' app/observability/trace.py` — OK
- `python3 -c "import ast; ast.parse(open('tests/test_trace.py').read()); ast.parse(open('tests/conftest.py').read())"` — OK

## Self-Check: PASSED

---
*Phase: 31-agent-mcp-observability*
*Completed: 2026-04-19*
