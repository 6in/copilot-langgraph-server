---
phase: 31-agent-mcp-observability
plan: 05
subsystem: observability
tags: [tracing, iframe-rpc, tool-call, correlation-id, canvas, contextvars, pytest-asyncio]

# Dependency graph
requires:
  - phase: 31
    plan: 02
    provides: trace_span / _current_trace_id / _current_common_attrs / get_args_max_chars / get_result_max_chars
  - phase: 31
    plan: 03
    provides: TracedTool wrapper と privileged=false 判定の前例 (ここでは直接は使わず、共通スキーマのみ踏襲)
  - phase: 11
    plan: 02
    provides: RPCContext.from_http() (user_id / app_id / thread_id / correlation_id)
provides:
  - iframe_rpc 経路 (軸 B 経路 3) に request + tool_call span 発火
  - correlation_id / app_id="canvas" を route → arq → handler へ一貫伝搬
  - db_query / AI 両 RPC method を統一スキーマで計測 (privileged=false + pool_name / model_name)
  - 旧フリーテキスト log `iframe-rpc QUERY user=... pool=...` の廃止と span attribute 代替
affects: [31-06, 31-07, 31-08]

# Tech tracking
tech-stack:
  added: []  # 既存 app.observability.* (Plan 02) と app.orchestrator.context (Phase 11) を組み合わせて使うだけ
  patterns:
    - "handler 単位で async with trace_span('request') + 内側 async with trace_span('tool_call') の 2 層 span パターン"
    - "RPCContext.from_http(..., thread_id='') で iframe_rpc の thread_id 不在を明示 (他 handler と I/F を揃える)"
    - "config/mcp_tools.yaml の sandbox_exposed=true → privileged=false を明示 hardcode (db_query)"
    - "旧フリーテキスト log を span attribute (user_id / pool_name / rpc_method) に吸収する移行パターン"

key-files:
  created:
    - tests/test_iframe_rpc_trace.py
  modified:
    - app/api/routes/iframe_rpc.py
    - app/jobs/handlers/iframe_rpc_handler.py

key-decisions:
  - "correlation_id は route (app/api/routes/iframe_rpc.py) で str(uuid.uuid4()) 生成 — body から受け取らない (T-31-04 accept)"
  - "app_id='canvas' は route で hardcode (iframe_rpc は Canvas 固有経路で、他 app からの流入は想定しない)"
  - "handler._handle_query / _handle_ai のシグネチャに trace_id と user_id を追加。既存 test 非破壊のため default 値 ('', 'unknown') を付与"
  - "request span attributes: user_id / app_id / thread_id='' / handler='iframe_rpc' / rpc_method — 他 handler の 'sub_agent' span と区別するため operation_name='request' を採用"
  - "tool_call span の agent_name は 'iframe_rpc' 固定 (SubAgent 概念がない経路なので handler 名で代替)"
  - "AI 経路は tool_name='ai' / model_name=<resolved real ID> / privileged=false (LLM one-shot は MCP catalog 外だが同 trust zone なので non-privileged)"
  - "db_query tool_call span に pool_name / row_count を iframe_rpc 固有の運用 attribute として追加 (Plan 06 の per-pool 集計に使える)"
  - "旧 logger.info('iframe-rpc QUERY user=%s pool=%s', ...) は完全削除 — docstring で旧 log の代替先 (span attribute) を明示"

patterns-established:
  - "Pattern: iframe_rpc 固有の 2 層 span (request→tool_call) で handler 全体を観測対象に"
  - "Pattern: handler メソッドに trace_id / user_id をオプショナル引数として追加 (既存 unit test の直接呼び出し互換を維持)"
  - "Pattern: span attributes に運用固有のキー (pool_name / row_count) を載せて Plan 06 の jq クエリに素通しさせる"

requirements-completed: [D-08, D-09, D-10, D-11, D-12, D-14]

threat-mitigations-applied:
  - T-31-01: "args_prefix / result_prefix を TRACE_ARGS_MAX_CHARS / TRACE_RESULT_MAX_CHARS で truncate (default 500 / 1000)"
  - T-31-02: "AI result_prefix は get_result_max_chars() (default 1000) で truncate。全文は docker logs のみに滞留 (checkpointer 非経由)"
  - T-31-04: "correlation_id は route 側で UUID4 強制生成、body からは受け取らない設計"

# Metrics
duration: 15min
completed: 2026-04-19
---

# Phase 31 Plan 05: iframe_rpc tracing integration Summary

**Canvas iframe RPC 経路 (軸 B 経路 3) を Phase 31 observability 基盤に統合した。`iframe_rpc` route が correlation_id と app_id="canvas" を arq ジョブ payload に付与し、`IframeRpcHandler.handle()` は request span で wrap、`_handle_query` (db_query) / `_handle_ai` (AI one-shot) が tool_call span として privileged=false・pool_name・resolved model_name まで記録する。旧フリーテキスト log `iframe-rpc QUERY user=... pool=...` は完全削除し、user_id / pool_name は span attribute 経由で集計可能になった。**

## Performance

- **Duration:** 約 15 分
- **Started:** 2026-04-19T11:20:00Z (approx; worktree reset + context read 後)
- **Completed:** 2026-04-19T11:35:00Z
- **Tasks:** 3 (RED + GREEN route + GREEN handler)
- **Files created:** 1 / **modified:** 2

## Accomplishments

- `tests/test_iframe_rpc_trace.py` — 281 行・6 async testcase。pytest-asyncio auto mode。
  - test_request_span_on_handle — UNKNOWN method でも request span 1 件・trace_id=correlation_id を検証
  - test_query_emits_tool_call_span — db_query tool_call の全 attributes + parent_span_id linkage 検証
  - test_query_error_dict_sets_error_status — tool result `{"error": ...}` で span ERROR + success=false
  - test_query_exception_sets_error_status — tool.ainvoke 例外時も span ERROR、handler は swallow して save_result
  - test_ai_emits_tool_call_span — ChatCopilot mock 経由で tool_name="ai" / model_name="claude-haiku-4-5-20251001"
  - test_unknown_method_no_tool_call_span — UNKNOWN method は request span のみ (tool_call 無し)
- `app/api/routes/iframe_rpc.py` — `correlation_id = str(uuid.uuid4())` 生成 + `enqueue_job(..., correlation_id=correlation_id, app_id="canvas")` の 2 フィールド追加 (3 行)。
- `app/jobs/handlers/iframe_rpc_handler.py` — 163 挿入 / 52 削除 (モジュール全体で +111 行)。
  - 3 箇所の `async with trace_span` (request / QUERY tool_call / AI tool_call)
  - RPCContext 構築 (I/F parity)
  - args/result の UTF-8 byte 数 + truncated prefix 記録
  - 旧 free-text log 完全削除
  - `_handle_query` / `_handle_ai` に trace_id / user_id オプショナル引数追加 (既存 unit test 互換)
- 44 件のテスト (iframe_rpc_handler 8 + iframe_rpc_route 6 + iframe_rpc_trace 6 + trace 12 + traced_tool 12) が全 green。
- 既存全 suite との比較では **新規失敗ゼロ、6 件 passing が増加** (pre-existing 30 failures → 24 failures)。追加 6 件はすべて本プランの新規 trace tests。

## Task Commits

1. **Task 1: add failing tests for iframe_rpc trace span emission (RED)** — `d00962a` (test)
2. **Task 2: add correlation_id + app_id to iframe_rpc enqueue payload** — `8b089f8` (feat)
3. **Task 3: wrap iframe_rpc_handler in request + tool_call spans (GREEN)** — `7100e4c` (feat)

_TDD 手順: RED コミットで 6 cases すべて失敗 (request span 発火なし) を確認してから、route → handler の順で GREEN 実装。Task 2 は既存 `test_iframe_rpc_route.py` が `call_args.kwargs["..."]` アクセスパターンのため kwargs 増加を自動的に許容、patch 不要。Task 3 は `_handle_query` / `_handle_ai` のシグネチャ変更に伴う既存 unit test 破壊を default 引数で最小侵襲的に回避。_

## Files Created/Modified

- `tests/test_iframe_rpc_trace.py` (created, 281 行) — IframeRpcHandler の span 発火 unit test 6 件。
- `app/api/routes/iframe_rpc.py` (modified, +3 行) — correlation_id + app_id を enqueue_job payload に付与。
- `app/jobs/handlers/iframe_rpc_handler.py` (modified, +111 行 net) — request / tool_call span 3 箇所 + RPCContext + args/result prefix 記録 + 旧 log 削除 + 既存 test 互換の default 引数。

## Decisions Made

- **correlation_id の生成は route 側で強制**: body から受け取らない (T-31-04 accept)。`str(uuid.uuid4())` で UUID4 文字列を生成し、job payload に載せる。`RPCContext.from_http()` は handler 内で独立に構築し、I/F parity (他 handler も from_http で組んでいる) のために残す。trace_id は `correlation_id or rpc_ctx.correlation_id` の 2 段 fallback で legacy payload (tests, replay) にも耐える。
- **app_id="canvas" は route hardcode**: iframe_rpc 経路は Canvas 固有で、他 app からの流入は設計上あり得ない。将来 Gems 等に拡張する可能性は現時点で Deferred Ideas の範疇なので、hardcode で最小侵襲を選ぶ。Plan 06 の recipe で `select(.attributes.app_id == "canvas")` が確実に効く。
- **handler メソッドのシグネチャ拡張に default 値**: `_handle_query(ctx, params, trace_id: str = "", user_id: str = "unknown")` / `_handle_ai(job, params, trace_id: str = "", user_id: str = "unknown")` とすることで既存 `tests/test_iframe_rpc_handler.py` の 3 箇所 (`handler._handle_query(ctx, params)` 直接呼び出し) が非破壊。プラン原文では positional 必須だったが、Rule 3 (blocking) により default を追加。trace_id="" の場合 span の trace_id も "" になるが、route 経由の通常実行では必ず埋まるので実害なし。
- **tool_call span の agent_name は "iframe_rpc" 固定**: iframe_rpc 経路には SubAgent 概念がない (LangGraph ToolEnabledSubAgent 非経由)。agent_name 属性を空にすると Plan 06 の recipe で `group_by(.attributes.agent_name)` が `null` グループを作ってしまうので、handler 名そのものを値として入れる。他 handler (orchestrator_handler 等) は SubAgent.name を使うので、iframe_rpc は唯一の「handler 名 = agent_name」ケース。
- **AI 経路は tool_name="ai" / privileged=false**: LLM one-shot は MCP catalog に登録されていないツールだが、iframe_rpc sandbox の同 trust zone 内なので `privileged=false` で統一。model_name には resolve_model の結果 (real ID) を入れる。エイリアス "haiku" ではなく "claude-haiku-4-5-20251001" が span 属性に入ることでモデル別集計が一意に取れる。
- **pool_name / row_count を span attribute に追加**: D-09 の共通 4 attrs 以外に、iframe_rpc 固有の運用 attribute として pool_name (QUERY の pool ごと集計) と row_count (レスポンス size の目安) を載せる。D-10 の必須 attribute (tool_name / args_bytes / result_bytes / duration_ms / success / privileged) は全て揃っている。
- **旧 free-text log を完全削除**: `logger.info("iframe-rpc QUERY user=%s pool=%s", ...)` (旧 L120) は Phase 31 Plan 06 の jq recipe で置換可能。CONTEXT.md specifics「互換 alias は残さない」方針に従い削除。docstring には削除したことと代替 (span attribute) を明示。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] handler メソッドのシグネチャ拡張で既存 unit test 破壊**
- **Found during:** Task 3 (handler 実装後の test_iframe_rpc_handler.py 実行)
- **Issue:** プラン原文通り `_handle_query(self, ctx, params, trace_id, user_id)` / `_handle_ai(self, job, params, trace_id, user_id)` と positional 必須で実装したところ、既存 `tests/test_iframe_rpc_handler.py::test_handle_query_success` 等 3 箇所が `TypeError: _handle_query() missing 2 required positional arguments: 'trace_id' and 'user_id'` で破壊。
- **Fix:** 両メソッドの trace_id / user_id に default 値 (`trace_id: str = ""` / `user_id: str = "unknown"`) を付与。通常の route 経由では `handle()` が常に trace_id / user_id を渡すので挙動は変わらない。直接 unit test 経由で呼ぶ場合は span.trace_id="" / user_id="unknown" で emit される (テストでは capture_trace_logs を使わないので span 自体は観測されない)。
- **Files modified:** app/jobs/handlers/iframe_rpc_handler.py (2 メソッド signature 変更のみ)
- **Verification:** `uv run pytest tests/test_iframe_rpc_handler.py tests/test_iframe_rpc_route.py tests/test_iframe_rpc_trace.py -x` で 20 passed
- **Committed in:** 7100e4c (Task 3 の single commit に統合)

---

**Total deviations:** 1 auto-fixed (Rule 3 - blocking; 既存 test 非破壊の success criteria を満たすための最小侵襲)
**Impact on plan:** Success criteria「既存テストスイート非破壊」を達成するための必須対応。スコープは iframe_rpc_handler 内のみで外部影響ゼロ。plan の interfaces 契約は「route → handler 間で correlation_id / app_id を運ぶ」ことなので、handler 内部メソッドのシグネチャは契約外。

## Issues Encountered

- **Docker compose bind mount が worktree を含まない**: `.:/app` は主ワーキングツリー `/home/parallels/workspaces/copilot-langgraph` のみを映すため、worktree 側の変更は docker compose exec -T api uv run pytest では見えない。host の `uv run pytest` (worktree 内) で実行した。プロジェクトの pyproject.toml は worktree でも有効 (.venv を新規作成して 107 packages install)、pytest-asyncio auto mode も同じ設定で動作。テストは pure Python + mock なので postgres/Redis/MCP server 依存なし。Plan 02 / 03 でも同じ issue を Issues Encountered に記載済み、Phase 31 の observability 層は worktree 内 uv run で verify 可能。
- **全 suite に pre-existing failures 24 件**: test_api_chat.py (401 認証失敗 6 件) / test_api_jobs.py (401 2 件) / test_sse.py (401 2 件) / test_graph.py (`async for` mock 不備 3 件) / test_worker.py (postgres 到達不能 5 件) / test_orchestrator_graph.py (stage="single" vs "llm" 差分 1 件) / test_provider.py (timeout kwarg 差分 1 件) / test_rpc_integration.py (astream_events mock 不備 1 件) / test_debate_handler.py (assertion 差分 1 件) / test_mcp_server.py (1 件) / test_tool_enabled_subagent.py (1 件)。Plan 02 / 03 の SUMMARY で既に報告済みで、本プランの変更 (iframe_rpc 3 ファイル) とは独立。stash 検証で stash 前 (私の変更込) **24 failed / 312 passed**、stash 後 (変更なし) **30 failed / 306 passed** — 私の新規 test 6 件ぶん passing が増えており、回帰ゼロを確認。スコープ境界ルール (Executor 指示) に従い修正せず、Deferred Items 記載対象なし (複数 Plan で既報)。

## User Setup Required

None — 新規インフラ・env var の運用追加なし。Plan 02 で既出の `TRACE_ARGS_MAX_CHARS` / `TRACE_RESULT_MAX_CHARS` env var がそのまま作用する (iframe_rpc 経路は db_query / AI の args/result_prefix truncate で活用)。

## Next Phase Readiness

- **Plan 06 (CLI recipes / docs/trace-query-recipes.md)**: 以下の iframe_rpc 固有クエリ例を載せる準備が整った。
  - `jq 'select(.attributes.handler == "iframe_rpc" and .attributes.app_id == "canvas")'` — Canvas 経由の全 RPC
  - `jq 'select(.attributes.tool_name == "db_query" and .attributes.privileged == false) | .attributes.pool_name'` — 非特権 DB 経路の pool 別集計
  - `jq 'select(.attributes.tool_name == "ai" and .attributes.app_id == "canvas") | .attributes.model_name'` — Canvas から呼ばれた model 別集計
  - `jq 'select(.operation_name == "request" and .attributes.handler == "iframe_rpc" and .status_code == "ERROR")'` — Canvas 経由の失敗 request
- **Plan 04 (orchestrator / langgraph / debate handler 統合) との整合**: 4 handler すべてで `operation_name="request"` → 内側 `operation_name="tool_call"` の 2 層 span + trace_id = correlation_id が一貫する。iframe_rpc は operation_name="request" を採用、他 3 handler が "sub_agent" を採用する差分はあるが、CONTEXT.md D-06 で「3 層: routing / SubAgent / tool_call」と定めた範囲内。iframe_rpc は SubAgent 概念がないので "request" が妥当。
- **Deferred Items**: なし (Plan 05 のスコープ内でクリーン完了)。
- **引き継ぎ contract**:
    - iframe_rpc route は `correlation_id` と `app_id="canvas"` を job payload に載せる (変更しない)
    - handler._handle_query / _handle_ai の trace_id / user_id default 値 ('', 'unknown') は維持 (既存 unit test 互換)
    - tool_call span の privileged 判定は `sandbox_exposed` 参照ではなく db_query / ai で hardcode (Phase 31 スコープ内では sandbox_exposed の frozenset 読み込みは orchestrator_handler / ToolEnabledSubAgent 側で統一、iframe_rpc は ad hoc)

## Self-Check

自動チェック結果:

- `tests/test_iframe_rpc_trace.py` — FOUND (281 行)
- 6 async testcase (`grep -cE 'async def test_' tests/test_iframe_rpc_trace.py`) — 6 OK
- `app/api/routes/iframe_rpc.py` に `correlation_id = str(uuid.uuid4())` — FOUND
- `app/api/routes/iframe_rpc.py` に `correlation_id=correlation_id` — FOUND
- `app/api/routes/iframe_rpc.py` に `app_id="canvas"` — FOUND
- `app/jobs/handlers/iframe_rpc_handler.py` の `async with trace_span` — 3 箇所 (request + QUERY + AI)
- `app/jobs/handlers/iframe_rpc_handler.py` に `RPCContext` — FOUND
- `app/jobs/handlers/iframe_rpc_handler.py` に `iframe-rpc QUERY user=%s pool=%s` (旧 format specifier) — ABSENT ✓
- commit `d00962a` (test RED) — FOUND in git log
- commit `8b089f8` (feat route) — FOUND in git log
- commit `7100e4c` (feat handler) — FOUND in git log
- `uv run pytest tests/test_iframe_rpc_trace.py -x` — 6 passed
- `uv run pytest tests/test_iframe_rpc_handler.py tests/test_iframe_rpc_route.py tests/test_iframe_rpc_trace.py tests/test_trace.py tests/test_traced_tool.py` — 44 passed
- 全 suite 回帰検証 (stash 比較) — 新規失敗ゼロ、新規 passing 6 件 (本プランの test_iframe_rpc_trace.py)
- `python3 -c "import ast; ast.parse(open('tests/test_iframe_rpc_trace.py').read())"` — OK

## Self-Check: PASSED

---
*Phase: 31-agent-mcp-observability*
*Completed: 2026-04-19*
