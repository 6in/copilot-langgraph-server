---
phase: 31
plan: 08
subsystem: observability / integration
tags:
  - observability
  - integration
  - validation
  - wave-6
requirements:
  - D-02
  - D-08
  - D-10
  - D-16
  - D-17
dependency_graph:
  requires:
    - 31-01-SUMMARY (Copilot SDK reasoning spike)
    - 31-02-SUMMARY (trace writer)
    - 31-03-SUMMARY (TracedTool)
    - 31-04-SUMMARY (SubAgent span + routing + handlers)
    - 31-05-SUMMARY (iframe_rpc trace)
    - 31-06-SUMMARY (trace_query CLI)
    - 31-07-SUMMARY (audit_log 退役 + ADR-0045 + patterns)
  provides:
    - Phase 31 4 経路 end-to-end PASS 判定
    - docs/phase-31-integration-check.md（実ログ + must_haves チェックリスト + 結論）
    - silent failure 3 件の発見と修正（logger 未設定 / _keep_first / correlation_id）
  affects:
    - app/observability/trace.py (Bug 1 fix, commit 1ade308)
    - app/orchestrator/context.py (Bug 2 fix, commit f1a41f0)
    - tests/test_rpc_context.py, tests/test_agent_state.py (Bug 2 test 更新)
    - app/jobs/worker.py (Bug 3 fix, commit d9e0519)
tech_stack:
  added: []
  patterns:
    - "Integration check pattern: unit test green でも実環境の silent failure を surface する 4-route 検証"
    - "Self-bootstrap logger: module import 時に handler を attach して Python default WARNING 問題を解消"
    - "Fresh-context reducer: LangGraph checkpointer の state 復元による stale id 問題を last-wins で回避"
key_files:
  created:
    - docs/phase-31-integration-check.md
  modified:
    - app/observability/trace.py
    - app/orchestrator/context.py
    - app/jobs/worker.py
    - tests/test_rpc_context.py
    - tests/test_agent_state.py
decisions:
  - 4 経路 (Chat / SuperChat+web_search / CodeAct / Canvas iframe_rpc) すべてが trace span を正しく emit することを実環境で確認
  - must_haves m1-m10 を個別に verify、全件 green
  - Wave 6 で発見した silent failure 3 件は Phase 31 scope 内で同セッション内に修正（Bug 1 logger / Bug 2 reducer / Bug 3 correlation_id）
  - 修正に伴う unit test 更新 3 件は新しい semantic を lock する新規テストとして commit
  - ADR-0046 として「integration-check が silent failure を surface するパターン」を記録（Phase 31 scope 終了直前のメタ学び）
metrics:
  duration_minutes: ~90
  completed_date: 2026-04-20
  tasks_completed: 1
  tasks_pending_checkpoint: 0
---

# Phase 31 Plan 08: Integration Check — 4 経路 PASS + 3 bug fix Summary

**One-liner:** docker 実環境で Phase 31 の 4 経路を手動操作し、trace span が期待通り emit されることを確認。副次的に 3 件の silent failure を surface し、いずれも同セッション内で修正・再検証して Wave 6 を PASS で close。

## Objective (達成)

Plan 01–07 が実装した observability 基盤が docker compose 実環境で end-to-end 動作することを確認し、Phase 31 全体 must_haves m1–m10 の充足を verify する。

## Tasks

### Task 1 — 4 経路 integration test + trace tree 確認 (checkpoint:human-verify) ✓

**Status:** ✓ **COMPLETED (2026-04-20)**

各経路の実観察ログと確認項目は `docs/phase-31-integration-check.md` に詳細記録。以下は結論のみ:

| 経路 | span 構成 | 確認結果 |
|------|----------|---------|
| 1. Chat (langgraph) | request | ✅ |
| 2. SuperChat + web_search (orchestrator → TracedTool) | request → routing → sub_agent → tool_call(web_search) | ✅ |
| 3. CodeAct + execute_python (orchestrator → CodeActSubAgent) | request → routing → sub_agent → 5× tool_call(execute_python, privileged=True) | ✅ |
| 4. Canvas iframe_rpc (db_query / ai) | request → tool_call × 3 trace | ✅ |

## 発見された silent failure 3 件 + 修正

Phase 31 unit test はすべて pass していたが、docker 実環境では以下 3 件が silent failure していた。詳細は `docs/phase-31-integration-check.md` 参照。

| # | Bug | 修正 commit | 根本原因 |
|---|-----|-----------|---------|
| 1 | `trace` logger が INFO 出力できず span が 1 件も emit されない | `1ade308` | Python logging の root default=WARNING、`getLogger("trace")` に handler 未 attach |
| 2 | child span が前リクエストの trace_id を引き継ぐ (stale propagation) | `f1a41f0` | `_keep_first` reducer が LangGraph checkpointer 経由で stale context を保持 |
| 3 | Canvas iframe_rpc が 30s timeout で完全停止 | `d9e0519` | Plan 05 が追加した `correlation_id` kwarg を `process_chat()` が受け取れず TypeError で即死 |

いずれも unit test では見えない副作用系の silent failure で、integration check が surface。`docs/phase-31-integration-check.md` の「学び (retrospective)」セクション参照。

## Task Commits (Wave 6 で本 plan の対応)

1. **Bug 1 fix (trace logger self-bootstrap)** — `1ade308` `fix(31): configure trace logger stdout handler at import time`
2. **Bug 2 fix (_keep_first reducer flip)** — `f1a41f0` `fix(31): flip _keep_first reducer to prefer fresh request context`
3. **Bug 3 fix (process_chat correlation_id)** — `d9e0519` `fix(31): thread correlation_id through process_chat to iframe_rpc_handler`
4. **本 SUMMARY.md + integration-check.md** — （次 commit）

## Files Created/Modified

**作成:**
- `docs/phase-31-integration-check.md` (実ログ + must_haves チェックリスト + retrospective)
- `.planning/phases/31-agent-mcp-observability/31-08-SUMMARY.md` (本ファイル)

**修正 (Wave 6 bug fix):**
- `app/observability/trace.py` (+26 行、`_configure_trace_logger()` 追加)
- `app/orchestrator/context.py` (reducer セマンティック反転 + docstring 更新)
- `app/jobs/worker.py` (+5 行、`correlation_id` kwarg 追加 + job dict 転送)
- `tests/test_rpc_context.py` (reducer test 更新 + None-guard test 追加)
- `tests/test_agent_state.py` (reducer 経由の state 伝搬 test 更新)

## Decisions Made

1. **3 bug fix は Wave 6 scope 内で処理** — Phase 31 を partial-PASS で close せず、silent failure を同セッション内で修正してから close。Wave 6 の整合性確保のため。
2. **reducer semantic を last-wins に反転** — LangGraph checkpointer 経由で復元される context が stale になる問題を、reducer 側で明示的に「fresh wins」に反転して解決。ノード側の返り値が context を上書きする理論的リスクはあるが、実コードでは handler のみが context を返すため安全。
3. **trace logger は self-bootstrap 型** — `app/api/main.py` の lifespan で logger を設定するのではなく、`trace.py` module 自身に設定を埋め込む。他の module / framework (arq worker / pytest / ad-hoc script) からの import でも自動的に INFO 出力が有効化される副作用的メリットあり。
4. **ADR-0046 で integration check パターンを記録** — Wave 6 の retrospective を独立した ADR に昇格させ、今後の phase でも integration check gate を必須化する根拠にする。

## Deviations from Plan

### Auto-fixed Issues

**Plan で想定されていなかったが本 plan 実行中に surface した 3 bug:**
- Bug 1 / Bug 2 / Bug 3 (上記「発見された silent failure」参照)
- いずれも計画書外の発見だが、observability 基盤の最低限動作条件であり scope 内として対応。
- unit test 更新 3 件 (test_keep_first_*, test_context_fresh_*, iframe_rpc 関連は影響なし) は reducer semantic 変更に伴う必然的更新。

### Non-deviations（計画書通りの挙動）

- Task 1 の `checkpoint:human-verify` はプラン通り人間操作を経て完了
- must_haves m1–m10 の個別 verify はプラン通り実施

## Auth Gates

なし。

## Known Stubs

なし。Canvas iframe_rpc の 3 経路 (QUERY / AI / 非 SELECT 拒否) すべて real traffic で観察済み。

## TDD Gate Compliance

本 plan は `type: execute`（非 TDD）。TDD gate 対象外。

## Self-Check: PASSED

**ファイル:**
- `docs/phase-31-integration-check.md` → FOUND (書き下ろし完了)
- `.planning/phases/31-agent-mcp-observability/31-08-SUMMARY.md` → FOUND (本ファイル)

**修正 commit (本 plan ではなく Wave 6 内で発見した bug fix 由来):**
- `1ade308` (Bug 1 fix) → FOUND in git log
- `f1a41f0` (Bug 2 fix) → FOUND in git log
- `d9e0519` (Bug 3 fix) → FOUND in git log

**4 経路 end-to-end:**
- 経路 1 Chat request span 観察 → trace `ccc8e82e-...`
- 経路 2 SuperChat web_search 4 層 span 観察 → trace `02fb4e0d-...`
- 経路 3 CodeAct execute_python (privileged=true + usage tokens) 観察 → trace `573ba43d-...`
- 経路 4 Canvas iframe_rpc (3 trace: db_query / ai / security-guard block) 観察 → trace `861c2a90-...`, `b45f170b-...`, `d2613930-...`

**Phase 31 focused tests:** 60/60 passed after all 3 fixes
**Full context tests:** 71/71 passed (Phase 31 + context/state tests after reducer fix)

## Threat Flags

なし。本 plan は検証 + bug fix であり、新規の trust boundary / 外部入力経路 / 認証パスを導入していない。

---

*Phase: 31-agent-mcp-observability*
*Plan: 08*
*Completed: 2026-04-20 (integration PASS + 3 bug fix)*
