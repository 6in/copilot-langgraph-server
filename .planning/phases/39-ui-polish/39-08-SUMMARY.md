---
phase: 39-ui-polish
plan: 08
subsystem: testing
tags: [pytest, mock-pattern, astream, async-generator, psycopg, langgraph]

# Dependency graph
requires:
  - phase: 39-ui-polish
    provides: Wave 1 (Plan 01-04) baseline 27 件、Plan 06 で Pattern E 6 件解消、Plan 07 で Pattern A/B test_api_* 系を解消
provides:
  - "test_graph.py: chatbot_node の astream 経路に対応した async generator mock pattern"
  - "test_worker.py: process_chat → LangGraphHandler dispatch アーキに合わせた mock 構成 + AsyncConnectionPool mock"
  - "test_debate_handler.py: graph.astream の async generator mock pattern"
  - "test_rpc_integration.py: orchestrator_handler の astream_events/aget_state fallback 経路に合わせた mock"
  - "test_tool_enabled_subagent.py: _build_rich_output の tool 履歴連結を考慮した assertion"
affects: [phase-40+, mock-pattern-handbook]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pattern C: llm.astream() を MagicMock(side_effect=async_gen_func) で mock"
    - "Pattern D: graph.astream_events/aget_state fallback 経路の組み合わせ mock"
    - "Pattern B: AsyncConnectionPool を return_value=mock_pool で patch (pool.open 回避)"

key-files:
  created:
    - .planning/phases/39-ui-polish/39-08-SUMMARY.md
  modified:
    - tests/test_graph.py
    - tests/test_worker.py
    - tests/test_debate_handler.py
    - tests/test_rpc_integration.py
    - tests/test_tool_enabled_subagent.py
    - .planning/phases/39-ui-polish/39-BASELINE.md

key-decisions:
  - "test_process_chat_* の patch path を app.jobs.worker.* から app.jobs.handlers.langgraph_handler.* へ移行 (process_chat は handler dispatch のみで LLM を直接扱わないため)"
  - "test_orchestrator_handler_uses_checkpointer / test_orchestrator_handler_injects_context で agents_filter を明示指定し APP.md からの自動ロードによる 'No matching agents' を回避"
  - "test_handle_calls_build_debate_graph の assertion を ainvoke から astream に変更 (実装は astream のみ使用、ainvoke 経路は無い)"
  - "test_tool_enabled_subagent_runs_react_loop の assertion を完全一致から含有チェックに変更 (_build_rich_output が tool 履歴を連結するため)"
  - "Pattern B test_worker 1 件は AsyncContextManager パターン適用ではなく AsyncConnectionPool 単純 mock パターンで対応 (実装は async with ではなく直接 await pool.open(...) を呼ぶため)"

patterns-established:
  - "Pattern C async generator mock: MagicMock(side_effect=async_gen_func) を使うと call_args_list が保持されて呼び出し履歴の検証が可能"
  - "Pattern D fallback mock: graph.astream_events を空 async generator、aget_state を None にして graph.ainvoke fallback を確実に発火させる"
  - "ChatCopilot patch path: orchestrator_handler 経由のテストでは app.providers.copilot.ChatCopilot を patch する (lazy import 経路のため orchestrator_handler module には存在しない)"

requirements-completed: [UIFIX-04]

# Metrics
duration: 10min
completed: 2026-05-13
---

# Phase 39 Plan 08: UIFIX-04 D-10 Pattern C/D/B 統合修正 Summary

**LLM mock astream を async generator pattern に書き換え、process_chat の handler dispatch アーキに mock 経路を追従、Pattern B 全 4 件を完遂 (target failed: 27 → 0 への到達は Plan 07 マージ依存で 8 件保留)**

## Performance

- **Duration:** 10 min
- **Started:** 2026-05-13T05:11:39Z
- **Completed:** 2026-05-13T05:21:27Z
- **Tasks:** 4
- **Files modified:** 6 (test 5 + docs 1)

## Accomplishments

- Pattern C 6 件解消: test_graph.py 3 件 + test_worker.py 3 件 (`async for` requires `__aiter__` 系のエラー一掃)
- Pattern D 4 件解消: test_worker.py 1 件 + test_debate_handler.py 1 件 + test_rpc_integration.py 1 件 + test_tool_enabled_subagent.py 1 件 (mock 経路/assertion の現実装追従)
- Pattern B test_worker 1 件解消 (Plan 07 の test_api_chat 3 件と合わせて Pattern B 全 4 件を scope 内完遂)
- production code (`app/`) は完全に不変、test only の修正
- 39-BASELINE.md に Plan 08 完了時の実測値を追記

## Task Commits

各タスクを個別にコミット:

1. **Task 1: test_graph.py の astream mock を async generator に書き換え** — `86394fa` (test)
2. **Task 2: test_worker.py の mock 経路を handler dispatch アーキに合わせて更新** — `de9684e` (test)
3. **Task 3: debate/rpc_integration/tool_enabled_subagent の mock 経路修正** — `6bbc004` (test)
4. **Task 4: 39-BASELINE.md に Plan 08 完了時の実測値を追記** — `9d55baa` (docs)

## Files Created/Modified

- `tests/test_graph.py` — mock_llm fixture に `MagicMock(side_effect=_astream_gen)` で astream を追加、test_messages_accumulate の assertion を astream.call_args_list 経由に変更し SystemMessage filter
- `tests/test_worker.py` — test_process_chat_* 3 件の patch path を `app.jobs.handlers.langgraph_handler.*` に移行、astream_events/aget_state/ainvoke fallback の mock 構成、test_startup_creates_redis_and_jobstore に AsyncConnectionPool patch を追加、test_orchestrator_handler_uses_checkpointer に agents_filter と ChatCopilot mock を追加
- `tests/test_debate_handler.py` — test_handle_calls_build_debate_graph の graph.astream を async generator pattern に書き換え、assertion を astream.assert_called_once に変更
- `tests/test_rpc_integration.py` — test_orchestrator_handler_injects_context に astream_events fallback 経路の mock 構成 + agents_filter 明示 + ChatCopilot mock を追加
- `tests/test_tool_enabled_subagent.py` — test_tool_enabled_subagent_runs_react_loop の assertion を完全一致から含有チェックに変更 (`_build_rich_output` の tool 履歴連結を考慮)
- `.planning/phases/39-ui-polish/39-BASELINE.md` — Plan 08 完了時の実測値セクションを追記 (baseline 27 → 8 件残、Plan 07 worktree マージ後 0 件到達見込み)

## Decisions Made

- **patch path 戦略の転換**: Phase 11+ で process_chat は LangGraphHandler に dispatch する設計に変わったが、テストは旧 `app.jobs.worker.ChatCopilot / build_graph / AsyncPostgresSaver` を patch していた。これらは worker module には存在せず handler module に属するため、patch path を `app.jobs.handlers.langgraph_handler.*` に移行した。
- **agents_filter 明示指定**: orchestrator_handler は agents=None 時に APP.md (superchat) から `["code-reviewer", "sql-analyst", ...]` を自動ロードする。テストの registry.agents={"agent-one":...} と不一致になり "No matching agents" で早期失敗するため、`job["agents"]=["agent-one"]` で APP.md ロードを skip させる方針を採用。
- **astream_events fallback 経路**: handler は `astream_events` で SSE token を流したあと、結果が取れなかった場合のみ `aget_state` → `ainvoke` fallback に流れる。テストでは astream_events を空 async generator、aget_state を None にして ainvoke fallback を確実に発火させる構成にした。
- **Pattern B 統合判断**: plan は `__aenter__`/`__aexit__` AsyncContextManager パターンの追加を期待していたが、test_worker.py の Pattern B 該当箇所 (test_startup_creates_redis_and_jobstore) は実装が `await pool.open(...)` を直接呼ぶため AsyncConnectionPool 単純 mock パターンが正しい解。AsyncContextManager は AsyncPostgresSaver で既に適用されており plan の grep 条件 (`__aenter__|asynccontextmanager` ≥ 1) は満たす。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_messages_accumulate の assertion が `ainvoke.call_args_list` を見ていた**
- **Found during:** Task 1
- **Issue:** 実装は `llm.astream()` のみを使用するため `mock_llm.ainvoke.call_args_list[1]` は空で IndexError。さらに astream 引数には SystemMessage が prepend されるため `len == 3` も成立しない。
- **Fix:** `mock_llm.astream.call_args_list[1][0][0]` で履歴を取得し、SystemMessage を filter してから Human/AI/Human の 3 件を検証する形に変更。
- **Files modified:** tests/test_graph.py
- **Verification:** `pytest tests/test_graph.py -v` で 4 件全 pass
- **Committed in:** 86394fa (Task 1 commit)

**2. [Rule 1 - Bug] test_handle_calls_build_debate_graph の assertion が `ainvoke` を見ていた**
- **Found during:** Task 3
- **Issue:** 実装の debate_handler は `graph.astream(...)` のみを使用し `ainvoke` は呼ばない。
- **Fix:** `mock_graph.astream.assert_called_once()` に書き換え、yield する dict も `{node_name: {messages: [AIMessage], turn: N}}` の updates 形式に。
- **Files modified:** tests/test_debate_handler.py
- **Verification:** `pytest tests/test_debate_handler.py -v` で 3 件全 pass
- **Committed in:** 6bbc004 (Task 3 commit)

**3. [Rule 1 - Bug] test_tool_enabled_subagent_runs_react_loop の output 完全一致 assertion が壊れていた**
- **Found during:** Task 3
- **Issue:** `_build_rich_output` が tool 実行履歴 (ToolMessage の content) + "---" + 最終 AIMessage を連結するため、`result["output"] == "pong result"` は不成立。
- **Fix:** `"pong result" in result["output"]` (最終 AI 応答) + `"pong" in result["output"]` (ツール結果) + ToolMessage 存在の 3 点を検証する含有チェックに変更。
- **Files modified:** tests/test_tool_enabled_subagent.py
- **Verification:** `pytest tests/test_tool_enabled_subagent.py -v` で 3 件全 pass
- **Committed in:** 6bbc004 (Task 3 commit)

**4. [Rule 3 - Blocking] test_startup_creates_redis_and_jobstore が実 DB に接続して PoolTimeout (30s)**
- **Found during:** Task 2
- **Issue:** Phase 18 で startup() に AsyncConnectionPool 初期化が追加されたが、テストが AsyncConnectionPool を mock しておらず実 postgres ホスト解決に失敗 → 30 秒タイムアウト。
- **Fix:** `patch("app.jobs.worker.AsyncConnectionPool", return_value=mock_pool)` を追加し、`mock_pool.open` を AsyncMock 化。
- **Files modified:** tests/test_worker.py
- **Verification:** `pytest tests/test_worker.py::test_startup_creates_redis_and_jobstore -v` で 0.3s 以内に pass
- **Committed in:** de9684e (Task 2 commit)

**5. [Rule 2 - Missing Critical] orchestrator_handler 経路で ChatCopilot 実 SDK 起動の防止**
- **Found during:** Task 2, Task 3
- **Issue:** orchestrator_handler は L260 で lazy `from app.providers.copilot import ChatCopilot` し vision check 用 LLM インスタンスを生成する。これを mock しないと実 Copilot SDK に到達して起動失敗。
- **Fix:** `patch("app.providers.copilot.ChatCopilot", return_value=mock_vision_llm)` を 2 テストに追加 (test_orchestrator_handler_uses_checkpointer / test_orchestrator_handler_injects_context)。
- **Files modified:** tests/test_worker.py, tests/test_rpc_integration.py
- **Verification:** 両テスト pass、外部 SDK アクセスなし
- **Committed in:** de9684e, 6bbc004

---

**Total deviations:** 5 auto-fixed (3 Rule 1 bug, 1 Rule 3 blocking, 1 Rule 2 missing critical)
**Impact on plan:** All deviations are within plan scope (test mock の現実装追従)、production code は完全に不変。Pattern B 完遂と target failed = 0 (Plan 07 マージ後) の方針も維持。

## Issues Encountered

- **target failed: 27 → 0 が Plan 08 単独では到達しない**: 残 8 件 (test_api_chat 6 件 + test_api_jobs 2 件) はすべて Plan 07 担当の Pattern A/B。Plan 07 worktree (commit 84295fc..ae78211) は本 plan の base (f470ee1) に未マージのため、Plan 08 完了時点では Plan 07 担当分が残る。Phase 39 close 時点で両 worktree マージ後に 0 件到達する設計 (39-BASELINE.md 末尾「Plan 08 完了時の実測値」セクション参照)。Plan 4 の verify ステップは Phase close 時点を想定した期待値だったため、本 SUMMARY ではその差分を明示記録した。

## User Setup Required

None - test only の修正、外部設定不要。

## Next Phase Readiness

- Plan 07 worktree マージ後、phase close の verify ステップ (`pytest tests/ --ignore=tests/test_mcp_server.py` failed = 0) が達成される見込み。
- 本 plan で確立した async generator mock pattern (`MagicMock(side_effect=async_gen_func)`) と astream_events fallback mock 構成は、Phase 40+ で LangGraph 経路を新規 mock する際の標準パターンとして再利用できる。
- patterns.md への追記候補: 「LangGraph handler mock pattern」「async generator mock pattern」「ChatCopilot lazy import patch path」(本 plan の scope ではないが、phase 39 close 時に手動追記検討)。

## Self-Check: PASSED

- [x] tests/test_graph.py 3 件 (test_messages_accumulate / test_single_message_response / test_thread_isolation) pass — 確認済
- [x] tests/test_worker.py 5 件 (test_process_chat_saves_result / test_process_chat_error_handling / test_process_chat_closes_llm / test_startup_creates_redis_and_jobstore / test_orchestrator_handler_uses_checkpointer) pass — 確認済
- [x] tests/test_debate_handler.py::test_handle_calls_build_debate_graph pass — 確認済
- [x] tests/test_rpc_integration.py::test_orchestrator_handler_injects_context pass — 確認済
- [x] tests/test_tool_enabled_subagent.py::test_tool_enabled_subagent_runs_react_loop pass — 確認済
- [x] `git diff app | wc -l` = 0 (production code 不変) — 確認済
- [x] Pattern B AsyncContextManager 痕跡 (`grep -cE '__aenter__|asynccontextmanager' tests/test_worker.py`) = 6 (≥ 1) — 確認済
- [x] Commits 86394fa, de9684e, 6bbc004, 9d55baa すべて git log に存在 — 確認済

---
*Phase: 39-ui-polish*
*Plan: 08*
*Completed: 2026-05-13*
