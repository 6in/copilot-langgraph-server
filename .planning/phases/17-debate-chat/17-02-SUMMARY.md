---
phase: 17-debate-chat
plan: "02"
subsystem: api
tags: [debate, langgraph, arq, fastapi, pydantic, task-handler]

requires:
  - phase: 17-01
    provides: build_debate_graph factory and DebateState TypedDict

provides:
  - DebateHandler(TaskHandler) — routes task_type='debate' jobs through DebateGraph
  - TASK_HANDLERS['debate'] registration in worker.py
  - ChatRequest extended with participants/pattern/max_turns/current_turn fields
  - process_chat signature and job dict extended for debate fields
  - enqueue_job passes debate fields from ChatRequest body

affects:
  - 17-03-PLAN (frontend DebateChat UI connects via POST /api/chat with task_type=debate)

tech-stack:
  added: []
  patterns:
    - "DebateHandler follows OrchestratorHandler structure: SubAgentRegistry + AsyncPostgresSaver + build_graph + ainvoke"
    - "max_turns capped at min(max_turns, 20) at handler entry — DoS防止 T-17-04"
    - "pattern validated against frozenset allowlist at handler entry — T-17-05"
    - "Pitfall 2: current_turn > 0 sends empty messages list to avoid double-accumulation with checkpointer"

key-files:
  created:
    - app/jobs/handlers/debate_handler.py
    - tests/test_debate_handler.py
  modified:
    - app/api/models.py
    - app/jobs/worker.py
    - app/api/routes/chat.py

key-decisions:
  - "ChatCopilot imported at module top-level in debate_handler.py so unittest.mock.patch works at import time"
  - "gem_ids backfilled into ChatRequest (was missing from models.py despite worker.py having it in signature)"
  - "T-17-03: Gem fetch uses is_public OR github_login DB filter — same pattern as OrchestratorHandler"
  - "T-17-06: KeyError on agent resolution caught and returned as error result (not exception)"
  - "pattern='debate' is the safe default when invalid pattern received — warning logged"

requirements-completed:
  - DEBATE-05
  - DEBATE-03

duration: 15min
completed: "2026-04-06"
---

# Phase 17 Plan 02: DebateHandler + API 拡張 Summary

**DebateHandler(TaskHandler) を実装し TASK_HANDLERS['debate'] に登録 — ChatRequest/process_chat/enqueue_job に討論用フィールド 4 つを追加してバックエンド統合完了**

## Performance

- **Duration:** 15 min
- **Started:** 2026-04-06T08:40:00Z
- **Completed:** 2026-04-06T08:55:49Z
- **Tasks:** 2 (TDD: RED + GREEN + Task 2)
- **Files modified:** 5

## Accomplishments

- DebateHandler を OrchestratorHandler と同構造で実装 — SubAgentRegistry + AsyncPostgresSaver + build_debate_graph + ainvoke
- T-17-04/05/06/03 の全セキュリティ緩和策を実装 (max_turns キャップ・pattern バリデーション・KeyError ハンドリング・Gem フィルター)
- ChatRequest に participants/pattern/max_turns/current_turn/gem_ids を追加 — Pydantic バリデーション付き
- TASK_HANDLERS に "debate": DebateHandler() を登録 — worker.py の変更は最小限
- TDD: 3 件のテストが RED -> GREEN で検証完了

## Task Commits

各タスクをアトミックにコミット:

1. **Task 1 RED: DebateHandler テスト作成** — `f8a18f0` (test)
2. **Task 1 GREEN: DebateHandler 実装** — `836545e` (feat)
3. **Task 2: ChatRequest + process_chat + enqueue_job 拡張** — `9b7b825` (feat)

## Files Created/Modified

- `app/jobs/handlers/debate_handler.py` — DebateHandler(TaskHandler) 新規作成 (167 行)
- `tests/test_debate_handler.py` — DebateHandler ユニットテスト 3 件 (201 行)
- `app/api/models.py` — ChatRequest に participants/pattern/max_turns/current_turn/gem_ids 追加
- `app/jobs/worker.py` — DebateHandler import + TASK_HANDLERS 登録 + process_chat シグネチャ/job dict 拡張
- `app/api/routes/chat.py` — enqueue_job に 5 フィールド追加

## Decisions Made

- ChatCopilot をモジュールトップレベルでインポート — `patch("app.jobs.handlers.debate_handler.ChatCopilot")` がテストで動作するため
- gem_ids を ChatRequest に追加 — worker.py の process_chat シグネチャには既にあったが models.py に欠けていたため補完
- T-17-06: KeyError は例外でなく「エラー結果を save_result して done する」パターンで処理 — ユーザーにわかりやすいエラーを返すため

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] gem_ids を ChatRequest に追加**
- **Found during:** Task 2 (models.py 編集時)
- **Issue:** プランでは「既存の gem_ids フィールドの下に追加」とあったが、ChatRequest には gem_ids が存在しなかった (gem_id は存在)
- **Fix:** gem_ids: list[str] | None = None を ChatRequest に追加
- **Files modified:** app/api/models.py
- **Committed in:** 9b7b825 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 2 — missing field backfill)
**Impact on plan:** 追加は正確性のための必須修正。スコープ拡大なし。

## Issues Encountered

- ワークツリーで `git add` に絶対パスを使うと「outside repository」エラー — ワークツリーの cwd 内での相対パス指定に切り替えて解決

## Threat Surface Scan

脅威モデルの全 4 件の緩和策を実装済み:

| Threat ID | Mitigation | File |
|-----------|-----------|------|
| T-17-03 | `is_public = true OR github_login = %s` DB フィルター | debate_handler.py L88-95 |
| T-17-04 | `min(job.get("max_turns", 3), 20)` | debate_handler.py L55 |
| T-17-05 | `_ALLOWED_PATTERNS = frozenset({"debate","panel","chain"})` ガード | debate_handler.py L28, L61-63 |
| T-17-06 | `KeyError` キャッチ → エラー結果保存 | debate_handler.py L110-116 |

新規ネットワークエンドポイントや信頼境界への変更なし。

## Next Phase Readiness

- DebateHandler はバックエンドで完全稼働可能
- POST /api/chat に `task_type="debate"` + participants/pattern/max_turns を渡せば DebateGraph が起動する
- Phase 17-03 (フロントエンド UI) の準備完了

---
*Phase: 17-debate-chat*
*Completed: 2026-04-06*

## Self-Check: PASSED

- app/jobs/handlers/debate_handler.py: FOUND
- tests/test_debate_handler.py: FOUND
- .planning/phases/17-debate-chat/17-02-SUMMARY.md: FOUND
- Commit f8a18f0: FOUND
- Commit 836545e: FOUND
- Commit 9b7b825: FOUND
