---
phase: 31-agent-mcp-observability
plan: 04
subsystem: observability
tags: [routing, sub-agent, tool-call, request-span, handler, tracedtool, otel]

# Dependency graph
requires:
  - phase: 31-agent-mcp-observability
    plan: 02
    provides: trace_span / _current_common_attrs / SpanDict / attach_usage_attributes
  - phase: 31-agent-mcp-observability
    plan: 03
    provides: TracedTool (BaseTool wrapper emitting tool_call span)
  - phase: 31-agent-mcp-observability
    plan: 01
    provides: "Plan 01 spike: usage 4 フィールド採用 (input/output/cache_read/cache_write tokens) — reasoning 系は emit しない"
provides:
  - "RouterNode.__call__ — routing span (stage=keyword/single/llm, fallback handling)"
  - "SubAgent.run / ToolEnabledSubAgent.run / CodeActSubAgent.run — sub_agent span with usage 4 fields"
  - "ToolEnabledSubAgent — ToolNode wraps every tool with TracedTool (privileged flag flows via ctor)"
  - "CodeActSubAgent — tool_call span around execute_python (privileged=True hardcoded)"
  - "3 handler (orchestrator/langgraph/debate) — request span wrapper + RPCContext at entry"
  - "ChatCopilot.last_usage — ASSISTANT_USAGE hook populates 4 int fields (non-invasive)"
  - "tests/test_sub_agent_trace.py — 11 cases covering routing/sub_agent/tool_call/request"
affects: [31-05, 31-06, 31-07, 31-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "`async with trace_span(\"sub_agent\", trace_id=..., attributes=common) as span:` で 4 共通 attribute を ContextVar 経由で子 tool_call span に継承"
    - "ChatCopilot の session.on() は _agenerate / _astream 両経路で ASSISTANT_USAGE を捕捉 → last_usage dict に格納 (monkey-patch 不要)"
    - "attach_usage_attributes(span, llm) — 共有ヘルパーを app.observability.trace に配置 (agent.py / tool_agent.py / codeact_agent.py から再利用)"
    - "privileged_tool_names を ToolEnabledSubAgent.__init__ に注入 → TracedTool へ伝搬 (SubAgentRegistry 側から)"
    - "_handle_inner 抽出パターン — 既存ハンドラを壊さず request span を被せるため handle() を 2 段化"

key-files:
  created:
    - tests/test_sub_agent_trace.py  # 11 integration cases
  modified:
    - app/orchestrator/graph.py
    - app/orchestrator/tool_agent.py
    - app/orchestrator/codeact_agent.py
    - app/orchestrator/agent.py
    - app/observability/trace.py  # attach_usage_attributes helper + USAGE_ATTR_KEYS
    - app/providers/copilot.py     # last_usage property + _store_usage / _register_usage_hook
    - app/jobs/handlers/orchestrator_handler.py
    - app/jobs/handlers/langgraph_handler.py
    - app/jobs/handlers/debate_handler.py
    - tests/test_routing_keyword.py  # migrated to trace logger schema
    - tests/test_orchestrator_graph.py  # migrated to trace logger schema
    - tests/test_rpc_integration.py  # migrated to trace logger schema

key-decisions:
  - "Plan 01 spike 分岐 (a) を採用 — ASSISTANT_USAGE 4 フィールド露出確認済。ChatCopilot._agenerate と _astream の両方で session.on() フックを設置し last_usage に格納。reasoning 系 attribute は Phase 31 scope 外 (全モデル 0 chars、T-31-01 mitigation)。"
  - "attach_usage_attributes は app/observability/trace.py に置く — tool_agent.py が agent.py を import できない循環回避制約があるため、共有ヘルパーは observability 側に寄せる。"
  - "privileged_tool_names は ToolEnabledSubAgent.__init__ に引数追加 (setter 注入ではなく)。SubAgentRegistry が folder+tools 構築時に frozenset を渡す。__init__ のデフォルトは frozenset() なのでレガシー経路は非互換にならない。"
  - "ハンドラ改修は handle() の本体を _handle_inner に抽出 + 外側で trace_span('request') を張る方式。既存フロー (gem fetch / agents_filter / checkpointer 等) に一切手を入れないため regression リスクが低い。"
  - "既存 test_routing_keyword.py / test_orchestrator_graph.py / test_rpc_integration.py は新 span schema に migration。CONTEXT.md specifics の「互換 alias 残さない」方針に従い旧 event:routing grep は全撤去。"
  - "ToolEnabledSubAgent.run() の GraphRecursionError 捕捉箇所で span.set_status('ERROR', 'recursion_limit_reached') + recursion_limit_reached=True attribute。既存 logger.warning はそのまま残す (運用者は文字列ログも必要)。"

patterns-established:
  - "Pattern: `async with trace_span(\"request\", trace_id=ctx.correlation_id, attributes={handler:..., app_id:..., user_id:...}):` で handler 全体を包む (Plan 05 の iframe_rpc_handler でも同じ型を適用予定)"
  - "Pattern: 4 共通 attribute (user_id/app_id/thread_id + agent_name/model_name) を sub_agent span に渡すだけで、子 tool_call span が ContextVar 経由で継承 — TracedTool 側の common_attrs_provider を一切指定する必要なし"
  - "Pattern: session.on() で ASSISTANT_USAGE → last_usage dict → sub_agent span attach。SDK 経由の usage 取得は ChatCopilot 内部に閉じ、外部 caller は `getattr(llm, 'last_usage', None)` を読むだけ"

requirements-completed: [D-06, D-08, D-09, D-10, D-12, D-13, D-14]

threat-mitigations-applied:
  - T-31-01: "routing span の user_input_prefix を 200 字 truncate (state['input'][:200])。CodeAct の tool_call span も args_prefix/result_prefix を env var 閾値で truncate。reasoning 系 attribute は emit しない。"
  - T-31-02: "SubAgent span に LLM 本文を載せない。message_count のみ (カウントは PII を含まない)。"
  - T-31-03: "TracedTool の privileged 判定は SubAgentRegistry 経由で frozenset を明示注入。CodeAct の execute_python は hardcode privileged=True。integration test (test_tool_enabled_sub_agent_wraps_with_tracedtool / test_codeact_execute_python_span) で両方向を検証。"

# Metrics
duration: ~45min
completed: 2026-04-19
---

# Phase 31 Plan 04: SubAgent / Routing / Handler span integration

**軸 A の 3 層 span (request → routing → sub_agent → tool_call) を同一 trace_id で emit し、既存 `event:routing` ログを OTEL span に一括置換。ToolEnabledSubAgent の ToolNode は TracedTool 経由になり、CodeActSubAgent の execute_python は privileged=true の tool_call span で包まれる。3 handler (orchestrator/langgraph/debate) に request span + RPCContext を追加し、Plan 01 spike 結果に基づき ChatCopilot に ASSISTANT_USAGE hook を実装して last_usage の 4 int フィールドを sub_agent span に emit する。**

## Performance

- **Duration:** 約 45 分
- **Started:** 2026-04-19T09:22:47+09:00
- **Completed:** 2026-04-19 実行時刻
- **Tasks:** 3 (graph routing 置換 / SubAgent span 統合 / handler request span)
- **Files created:** 1 / **modified:** 11 (実装 7 + テスト 3 + conftest なし)
- **Commits:** 5 (RED + 3 feat + 1 test migration)

## Accomplishments

- **Task 1 — graph.py routing 置換 (`819d748`):** RouterNode.__call__ の 4 箇所 `logger.info(json.dumps({event:routing,...}))` と 1 箇所 routing_fallback warning を `async with trace_span("routing", trace_id=ctx.correlation_id, attributes=common)` に一括置換。3 stage (keyword / single / llm) それぞれ 1 span を emit し、LLM fallback は status_code=ERROR + fallback=True attribute で表現。互換 alias は一切残さず (CONTEXT specifics 準拠)。
- **Task 2 — SubAgent 群 span 統合 (`7bb05d7`):**
  - `SubAgent.run()` / `ToolEnabledSubAgent.run()` / `CodeActSubAgent.run()` を `trace_span("sub_agent", ...)` で wrap (4 共通 attribute: user_id / app_id / thread_id / agent_name / model_name)
  - `GemSubAgent` は継承のみで自動的に SubAgent span に包まれる
  - ToolEnabledSubAgent の `ToolNode(tools)` → `ToolNode([TracedTool(t, privileged_tool_names=priv) for t in tools])` に変更。`_llm.bind_tools(tools)` には **元** tools を渡して LLM 側の schema は変えない
  - CodeActSubAgent の `execute_python.ainvoke({"code": code})` を `trace_span("tool_call", privileged=True, tool_name="execute_python", ...)` で包み、args_bytes / result_bytes / success / exit_code / stderr を attribute 化
  - GraphRecursionError → `span.set_status("ERROR", "recursion_limit_reached")` + `recursion_limit_reached=True`
  - ChatCopilot に `last_usage: dict | None` プロパティ + `_store_usage(data)` + `_register_usage_hook(session)` を追加。`_agenerate` (send_and_wait 経路) と `_astream` (streaming 経路) の両方で ASSISTANT_USAGE を捕捉。4 int フィールド (input_tokens / output_tokens / cache_read_tokens / cache_write_tokens) を int cast で格納。
  - `attach_usage_attributes(span, llm)` を `app/observability/trace.py` に配置 (agent.py / tool_agent.py / codeact_agent.py の 3 呼び出し元から共有、循環 import 回避)
  - SubAgentRegistry が folder+tools 構築時に `privileged_tool_names=self._privileged` を ToolEnabledSubAgent に注入
- **Task 3 — handler request span (`fd3115b`):**
  - OrchestratorHandler: handle() の先頭で RPCContext 構築 + `trace_span("request", handler="orchestrator", ...)` で `_handle_inner` を包む
  - LangGraphHandler: **新規 RPCContext 追加** (github_login / app_id="chat" / thread_id)、handler_body を `_handle_inner` に抽出して `trace_span("request", handler="langgraph", agent_type="chatbot", model_name=...)` で包む
  - DebateHandler: **新規 RPCContext 追加** (app_id="debate")、`trace_span("request", handler="debate", pattern=..., max_turns=...)` で包む
  - 既存フローは一切変更せず (gem fetch / agents_filter / checkpointer / astream_events は現状維持)
- **テスト (新規 + migration):**
  - `tests/test_sub_agent_trace.py` 新規 11 cases (610 行) — A-D routing / E-H sub_agent + tool_call + recursion / I-K request span (orchestrator/langgraph/debate) すべて green
  - `tests/test_routing_keyword.py` test_stage_keyword_in_log / test_stage_llm_in_log を新 schema (operation_name=routing on logger "trace") に migration
  - `tests/test_orchestrator_graph.py` test_router_log_contains_correlation_id / test_router_log_handles_missing_context を新 schema に migration
  - `tests/test_rpc_integration.py` test_correlation_id_in_routing_log を新 schema (trace_id = correlation_id) に migration

## Task Commits

1. **Task 1 (RED): add failing tests for sub_agent trace integration** — `22e672c` (test)
2. **Task 1: replace routing log with OTEL span in graph.py** — `819d748` (feat)
3. **Task 2: add sub_agent span + TracedTool wrap to SubAgent variants** — `7bb05d7` (feat)
4. **Task 3: wrap handlers in request span + add RPCContext** — `fd3115b` (feat)
5. **test migration: test_orchestrator_graph → new span schema** — `4c91b82` (test)

## Files Created/Modified

| File | Lines | Role |
|------|------:|------|
| `tests/test_sub_agent_trace.py` | +610 | new — 11 integration testcases |
| `app/orchestrator/graph.py` | +45 / -32 | routing span replacement |
| `app/orchestrator/tool_agent.py` | +55 / -18 | sub_agent span + TracedTool wrap + recursion attr |
| `app/orchestrator/codeact_agent.py` | +92 / -66 | sub_agent span + tool_call span around execute_python |
| `app/orchestrator/agent.py` | +20 / -12 | SubAgent.run sub_agent span + registry privileged injection |
| `app/observability/trace.py` | +34 | attach_usage_attributes helper + USAGE_ATTR_KEYS |
| `app/providers/copilot.py` | +62 | last_usage property + _store_usage + _register_usage_hook + ASSISTANT_USAGE hook in both paths |
| `app/jobs/handlers/orchestrator_handler.py` | +52 / -12 | request span wrapper + _handle_inner extraction |
| `app/jobs/handlers/langgraph_handler.py` | +52 / -3 | RPCContext new + request span + _handle_inner |
| `app/jobs/handlers/debate_handler.py` | +53 / -8 | RPCContext new + request span + _handle_inner |
| `tests/test_routing_keyword.py` | +24 / -14 | migration to new span schema |
| `tests/test_orchestrator_graph.py` | +47 / -43 | migration to new span schema |
| `tests/test_rpc_integration.py` | +16 / -14 | migration to new span schema |

## Decisions Made

- **Token usage BRANCH = (a):** Plan 01 spike は 3 モデルとも ASSISTANT_USAGE 4 フィールドの非 null 露出を確認済。ChatCopilot に session.on() フックを `_register_usage_hook` として実装し `_agenerate` / `_astream` の両方で capture。spike スクリプトの monkey-patch アプローチは本プロダクトコードには持ち込まない (spike は SDK upgrade 回帰テストとして残存)。
- **reasoning 系 attribute は emit しない:** 全モデル 0 chars かつ T-31-01 mitigation として Phase 31 scope 外。docs/phase-31-reasoning-token-spike.md の結論に従う。message_count (int) だけ sub_agent span に attach (PII リスク無し)。
- **attach_usage_attributes は app/observability/trace.py に配置:** agent.py → tool_agent.py の循環 import を避けるため、共有ヘルパーは observability 側に寄せる。USAGE_ATTR_KEYS も public constant として expose。
- **privileged_tool_names は ToolEnabledSubAgent.__init__ 引数追加:** setter 注入より試験容易性が高い。デフォルトは frozenset() なので既存コード (test / from_dir 呼び出し) 互換。SubAgentRegistry の構築箇所で明示的に `self._privileged` を渡す。
- **_handle_inner 抽出パターン:** 3 handler で handle() の本体をそのままコピーして `_handle_inner` に移し、外側で `async with trace_span("request", ...)` だけを追加。既存 try/finally / registry.close / aget_state / astream_events の挙動が変わらないことを保証。
- **routing span の user_input_prefix を 80 → 200 字に拡大:** CONTEXT D-13 の 200 字ルールに準拠。既存 tests/test_routing_keyword.py の test_stage_* は `user_input_prefix` の存在チェックではなく `attributes.stage` で判定するため影響なし。
- **recursion_limit_reached attribute を sub_agent span に追加:** ダッシュボードで GraphRecursionError 件数を集計可能にする。既存 `logger.warning` もそのまま残存 (運用者が文字列 grep で見つけられる)。

## Deviations from Plan

プラン通り実行。軽微な差分:

**1. [Rule 2 — Test schema migration] 追加の既存テスト 2 ファイルを migration**
- **Found during:** Task 1 / Task 3 の regression check
- **Issue:** CONTEXT specifics で「互換 alias は残さない」方針のため、`tests/test_rpc_integration.py::test_correlation_id_in_routing_log` と `tests/test_orchestrator_graph.py::test_router_log_*` の 3 件が旧 `event:routing` JSON 形式を grep していて失敗
- **Fix:** 新 span schema (logger "trace", operation_name=routing, trace_id = correlation_id, attributes.thread_id) に 3 件を migration
- **Files modified:** tests/test_rpc_integration.py, tests/test_orchestrator_graph.py
- **Committed in:** `fd3115b` (rpc_integration), `4c91b82` (orchestrator_graph)

**2. [Rule 2 — Critical functionality] _handle_inner 抽出で既存フローを保護**
- **Found during:** Task 3 設計時
- **Issue:** 3 handler の handle() 本体は複雑 (gem fetch / agents_filter / astream_events / aget_state fallback 等) で、直接 trace_span で包むと indent が深くなり可読性低下
- **Fix:** `async def _handle_inner(self, ...)` に本体を抽出し、handle() は RPCContext 構築 + trace_span wrap + `return await self._handle_inner(...)` の 3 行だけに
- **Files modified:** app/jobs/handlers/orchestrator_handler.py, app/jobs/handlers/langgraph_handler.py, app/jobs/handlers/debate_handler.py
- **Committed in:** `fd3115b`

**Total deviations:** 2 auto-fixed (both Rule 2 — 完全性確保)
**Impact on plan:** プラン意図からの逸脱はなし。どちらも「旧 alias を残さない」「既存フロー regression なし」という CONTEXT/PLAN 上位方針の自然な具体化。

## Issues Encountered

- **既存失敗テスト (scope 外):**
  - `tests/test_rpc_integration.py::test_orchestrator_handler_injects_context` — AsyncMock の graph.astream_events が coroutine を返して `async for` で TypeError。`git stash` で確認したところ本 plan の変更前 (`7bb05d7` コミット前) でも同様に失敗する pre-existing failure。Plan 02 SUMMARY で言及されている 24 件の pre-existing failures の 1 つ。
  - `tests/test_tool_enabled_subagent.py::test_tool_enabled_subagent_runs_react_loop` — `_build_rich_output` 由来の出力変更。これも pre-existing (ADR 0041 関連で phase-20 以前から存在)。
  - 両方ともスコープ境界ルールに従い修正せず、本 SUMMARY に記録のみ。
- **stash pop 事故 (recovery 済み):** git stash 運用ミスで別ブランチの `.planning/` ファイル大量削除が working tree に入ったが、`git reset HEAD` + `git checkout -- .planning/ mcp_server/` で即リカバリ。コミット履歴への影響なし。
- **Docker compose 未起動:** 本 worktree で docker services が down。Plan 03 と同様に host の `uv run pytest` で verification を実行 (observability 単体層は DB/Redis/MCP 依存なし、同等結果)。

## User Setup Required

None — 新規インフラ / env var / DB schema 変更なし。既存の `TRACE_ARGS_MAX_CHARS` / `TRACE_RESULT_MAX_CHARS` env var (Plan 02 導入) がそのまま作用する。docker logs rotation (quick 260418-tin 設定済み) に自動で乗る。

## Next Phase Readiness

**Plan 05 (iframe_rpc_handler の request / tool_call span) が着手可能。**

### 引き継ぎ事項 (Plan 05 向け)

- `app/jobs/handlers/iframe_rpc_handler.py` は **Plan 04 では触っていない** (parallel 31-05 と競合回避のため)。Plan 05 で同じ `_handle_inner` 抽出パターン + `trace_span("request", handler="iframe_rpc", ...)` を適用する。
- iframe_rpc 内の `tool.ainvoke({"sql": ..., "pool_name": ...})` (db_query) は **TracedTool を使わずに直接 `trace_span("tool_call", tool_name="db_query", privileged=False, ...)` で包む** — iframe_rpc は SubAgent 経路ではないため ContextVar 経由の common_attrs 継承は効かず、handler 側で explicit に 4 共通 attribute を attributes に入れる必要あり。
- RPCContext は iframe_rpc でまだ整備されていない可能性あり — `app/api/routes/iframe_rpc.py` の job 構築時に `correlation_id = str(uuid.uuid4())` を付与する小タスクが発生するか Plan 05 冒頭で確認のこと。

### Plan 08 integration validation で検証する項目

- request span (trace_id = correlation_id) → routing span (same trace_id, parent_span_id = request.span_id) → sub_agent span (parent = routing) → tool_call span (parent = sub_agent) の 4 層 tree が実環境で emit されること
- 4 handler それぞれで request span の handler attribute が正しい (orchestrator / langgraph / debate / iframe_rpc)
- ChatCopilot.last_usage が実際に 4 int を sub_agent span に attach している (input_tokens > 0 等)
- ToolEnabledSubAgent 経由の tool_call span が privileged / tool_name / args_bytes / result_bytes を正しく emit

### Known Stubs

なし — 全ての実装はプロダクトコードで動作する完全なもの。reasoning 系 attribute は「意図的に emit しない」判断 (Plan 01 結論) であり stub ではない。

## Self-Check

自動チェック結果:

- `tests/test_sub_agent_trace.py` — FOUND (11 testcases, 610 行)
- `app/providers/copilot.py` に `last_usage` 追加 — FOUND (`grep -q 'last_usage' app/providers/copilot.py` OK)
- `app/observability/trace.py` に `attach_usage_attributes` — FOUND
- `app/orchestrator/graph.py` に `async with trace_span` — FOUND (`grep -c` = 2)
- `! grep -q '"event": "routing"' app/orchestrator/graph.py` — OK (0 hits)
- `! grep -q 'routing_fallback' app/orchestrator/graph.py` — OK (0 hits)
- `app/orchestrator/tool_agent.py` に `TracedTool` — FOUND (6 hits)
- `app/orchestrator/codeact_agent.py` に `privileged.*True` — FOUND (3 hits including docstring + hardcode)
- `app/jobs/handlers/langgraph_handler.py` に `RPCContext` — FOUND (4 hits)
- `app/jobs/handlers/debate_handler.py` に `RPCContext` — FOUND (4 hits)
- 全 7 implementation files に `trace_span` reference 1+ — FOUND
- `uv run pytest tests/test_sub_agent_trace.py tests/test_routing_keyword.py` — 17 passed
- `uv run pytest tests/test_sub_agent_trace.py tests/test_routing_keyword.py tests/test_orchestrator_graph.py tests/test_trace.py tests/test_traced_tool.py` — 44 passed
- commit `22e672c` (RED), `819d748` (graph), `7bb05d7` (sub_agent), `fd3115b` (handlers), `4c91b82` (test migration) — all FOUND in git log

## Self-Check: PASSED

---
*Phase: 31-agent-mcp-observability*
*Plan: 04*
*Completed: 2026-04-19*
