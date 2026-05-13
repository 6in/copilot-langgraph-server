---
phase: 39
plan: 04
subsystem: backend-jobs
tags: [polish, dead-code, sse, jobstore, test, redis-polling]
requirements: [UIFIX-03]
dependency_graph:
  requires:
    - phase: 39-01
      provides: "pytest 27 / dead-code grep 7 の baseline 値、Wave 0 完了状態"
  provides:
    - "JobStore.queues / register_sse / unregister_sse 撤去済 (Redis polling 一択を確定)"
    - "notify() の no-op stub (notifier.py 4 経路の表面 API 互換維持)"
    - "test_sse 2 件の green 化 (Pattern A 失敗から脱却、Phase 4 SSE 由来 dead path のテスト依存解消)"
  affects: []
tech_stack:
  added: []
  patterns:
    - "Phase 39 / UIFIX-03 D-04: production SSE は Redis polling 一択、in-memory queue 経路は dead code として撤去"
    - "Phase 39 / UIFIX-03 D-06: 削除候補メソッドを完全削除せず no-op stub で残置することで上流 (notifier.py) の表面 API を温存"
    - "Pattern A (JWT cookie 不足) 解消: 既存 jwt_cookie fixture を AsyncClient cookies={\"session\": ...} で注入 (新規 fixture を作らない、D-12 上限ポリシー準拠)"
key_files:
  created:
    - .planning/phases/39-ui-polish/39-04-SUMMARY.md
  modified:
    - app/jobs/job_store.py
    - tests/test_sse.py
    - tests/test_job_store.py
    - tests/conftest.py
decisions:
  - "D-06 (planner 裁量): notify() は no-op stub で残置を採用。完全削除案は notifier.py:28,37 の書き換え波及があり、stub 案が D-05 (notifier.py 無変更) と両立する最小工数だった"
  - "D-04 plan の expected count '23 以下' (-4 件) は planner 側の数値誤算と判断。test_register_and_notify / test_unregister_sse は baseline 27 で passing であり、削除しても failure 数は減らない。実測 27 → 25 (-2、test_sse 2 件分のみ) が正しい結果"
patterns_established:
  - "上流呼び出し互換のため delete ではなく no-op stub で残置するパターン (Pitfall 3: signature を必ず固定 `async def notify(self, job_id: str, status: str, **extra) -> None: return None`)"
  - "テスト失敗が 'hang' に見えるが実は 401 だったケース — RESEARCH 段階で pretest による実測切り分け済 (RESEARCH.md L15)"
metrics:
  duration_minutes: 6
  completed: 2026-05-13
  tasks_completed: 4
  files_created: 1
  files_modified: 4
---

# Phase 39 Plan 04: UIFIX-03 (test_sse hang + JobStore dead code) Summary

**JobStore の Phase 4 由来 in-memory queue 経路 (`queues` / `register_sse` / `unregister_sse`) を撤去し、`notify()` は notifier.py 表面 API 互換のため no-op stub で残置。test_sse 2 件は JWT cookie 注入 + Redis polling mock 経路で書き直して green 化。**

## Performance

- **Duration:** 約 6 分
- **Started:** 2026-05-13T04:59:51Z
- **Completed:** 2026-05-13T05:06:07Z
- **Tasks:** 4 (Task 1-3 が実装、Task 4 が read-only 検証)
- **Files modified:** 4 (job_store.py / test_sse.py / test_job_store.py / conftest.py)

## Accomplishments

- **D-04 達成**: `app/jobs/job_store.py` の `register_sse` / `unregister_sse` / `self.queues` / `import asyncio` を完全削除 (grep `register_sse|unregister_sse|self.queues` 実測 7 → 0)
- **D-06 達成**: `notify()` を no-op stub 化、シグネチャは Pitfall 3 通り `async def notify(self, job_id: str, status: str, **extra) -> None: return None` で完全互換
- **D-05 達成**: `app/jobs/notifier.py` は git diff 0 行で温存、handlers 4 経路 (langgraph / orchestrator / debate / iframe_rpc) からの `progress() / done() / send_token() / send_turn()` 呼び出しは AttributeError を起こさず silent success
- **test_sse 2 件 green 化**: `test_sse_already_done` と `test_sse_done_signal` は実測で 401 失敗だったため、既存 `jwt_cookie` fixture を `AsyncClient(cookies={"session": jwt_cookie})` で注入し解消。後者は Redis polling mock 経路 (`get_turns` / `get_tokens` / `get_tool_event` の AsyncMock stub) で書き直し
- **test_job_store cleanup**: `test_register_and_notify` / `test_unregister_sse` の dead code テスト 2 件削除、`test_notify_no_queue` は no-op stub 契約テストとして docstring を更新し残置
- **conftest cleanup**: `mock_job_store` fixture から `register_sse` / `unregister_sse` の MagicMock 2 行を削除 (他 fixture は無変更)

## Task Commits

各 task を atomically commit:

1. **Task 1: JobStore dead code 削除 + notify() no-op stub 化** — `532d757` (refactor)
2. **Task 2: test_sse.py に jwt_cookie 注入 + polling mock 経路で書き直し** — `b3314bd` (test)
3. **Task 3: test_job_store dead code 削除 + conftest 整理** — `5163b9d` (test)
4. **Task 4: notifier.py 無変更確認** — read-only、コミットなし (git diff = 0 で確認)

## Files Created/Modified

### Created

- `.planning/phases/39-ui-polish/39-04-SUMMARY.md` — 本ファイル

### Modified

- `app/jobs/job_store.py` — `queues` 属性 / `register_sse` / `unregister_sse` メソッド / `import asyncio` を削除、`notify()` を no-op stub 化、クラス docstring を更新 (-17 / +13 行)
- `tests/test_sse.py` — 両テスト関数シグネチャに `jwt_cookie` 引数追加、`AsyncClient` に `cookies={"session": jwt_cookie}` 注入、`test_sse_done_signal` に `get_turns` / `get_tokens` / `get_tool_event` の polling mock 追加 (-6 / +15 行、imports L1-6 無変更)
- `tests/test_job_store.py` — `test_register_and_notify` / `test_unregister_sse` 関数 2 件削除 (decorator 含む)、`test_notify_no_queue` docstring 更新 (-22 / +1 行)
- `tests/conftest.py` — `mock_job_store` fixture から `store.register_sse = MagicMock()` / `store.unregister_sse = MagicMock()` の 2 行削除 (-2 / 0 行、他 fixture 無変更)

## Verification Results

### Task 1 grep checks (acceptance criteria)

| 計測項目 | Expected | 実測 |
|---|---:|---:|
| `grep -cE 'register_sse\|unregister_sse\|self\.queues' app/jobs/job_store.py` | 0 | 0 ✅ |
| `grep -c 'No-op stub' app/jobs/job_store.py` | ≥ 1 | 1 ✅ |
| `grep -cE 'async def notify\(self, job_id: str, status: str, \*\*extra\) -> None' app/jobs/job_store.py` | 1 | 1 ✅ |
| `grep -c 'import asyncio' app/jobs/job_store.py` | 0 | 0 ✅ |
| `grep -c 'class JobStore' app/jobs/job_store.py` | 1 | 1 ✅ |
| 残存メソッド 9 (save_result/get/push_turn/push_token/get_tokens/get_turns/push_tool_event/clear_tool_event/get_tool_event) | ≥ 9 | 9 ✅ |

### Task 2 acceptance

| 計測項目 | Expected | 実測 |
|---|---:|---:|
| `pytest tests/test_sse.py -v` | 2 passed | 2 passed ✅ |
| `grep -c 'jwt_cookie' tests/test_sse.py` | ≥ 2 | 4 ✅ (シグネチャ 2 + AsyncClient cookies 2) |
| `grep -c 'cookies=' tests/test_sse.py` | 2 | 2 ✅ |
| `grep -cE 'mock_job_store\.get_(turns\|tokens\|tool_event)' tests/test_sse.py` | 3 | 3 ✅ |
| `grep -c 'assert.*401' tests/test_sse.py` | 0 | 0 ✅ |
| imports L1-6 無変更 | 無変更 | git diff で L1-6 範囲に変更なし ✅ |

### Task 3 acceptance

| 計測項目 | Expected | 実測 |
|---|---:|---:|
| `grep -cE 'test_register_and_notify\|test_unregister_sse' tests/test_job_store.py` | 0 | 0 ✅ |
| `grep -cE 'store\.register_sse\|store\.unregister_sse' tests/conftest.py` | 0 | 0 ✅ |
| `pytest tests/test_job_store.py -v` | 3 passed | 3 passed ✅ (test_save_and_get / test_get_missing / test_notify_no_queue) |
| pytest 全体 failures | ≤ 23 | **25** (planner 数値誤算、下記 Deviations 参照) |
| `tests/conftest.py` 他 fixture 無変更 | 無変更 | git diff で L46-L55 範囲内のみ変更 ✅ |

### Task 4 acceptance (read-only)

| 計測項目 | Expected | 実測 |
|---|---:|---:|
| `git diff ad296e5..HEAD -- app/jobs/notifier.py | wc -l` | 0 | 0 ✅ |
| `grep -cE 'async def (progress\|done\|send_token\|send_turn)' app/jobs/notifier.py` | 4 (planner 期待) | **8** (BaseNotifier 抽象 4 + WebNotifier 具象 4、planner 期待は具象のみで集計したが grep は両方マッチ。表面 API 4 種が WebNotifier に存在することは確認済) |
| `grep -c 'self\.job_store\.notify' app/jobs/notifier.py` | 2 | 2 ✅ |
| `grep -c 'class WebNotifier' app/jobs/notifier.py` | 1 | 1 ✅ |
| `grep -c 'class BaseNotifier' app/jobs/notifier.py` | 1 | 1 ✅ |

### Phase 39 baseline 進捗

| Metric | Baseline (39-BASELINE.md) | Phase 39 target | 本 plan 完了時 |
|---|---:|---:|---:|
| pytest failed (`tests/ --ignore=tests/test_mcp_server.py`) | 27 | ≤ 2 | **25** (-2 件、test_sse 2 件分) |
| `grep -cE 'register_sse\|unregister_sse\|self.queues' app/jobs/job_store.py` | 7 | 0 | **0** ✅ (target 達成) |
| `grep -c 'test_register_and_notify\|test_unregister_sse' tests/test_job_store.py` | (未計測) | 0 | **0** ✅ (target 達成) |

## Decisions Made

1. **D-06 (planner 裁量): notify() を no-op stub で残置**
   - 完全削除案は `notifier.py:28,37` の `self.job_store.notify(...)` 呼び出しを AttributeError 化する。notifier.py 書き換えは D-05 (表面 API 温存) と矛盾するため不採用。
   - stub 案: signature を Pitfall 3 通り `async def notify(self, job_id: str, status: str, **extra) -> None: return None` で固定、handlers 4 経路は silent success で互換維持。

2. **新規 fixture を作らず既存 jwt_cookie を再利用**
   - conftest.py L8-12 の `jwt_cookie` fixture (Phase 35 由来) はそのまま再利用、新規 `auth_cookies` fixture は追加しない (D-12 上限ポリシーの「scope 外発見はついで修正禁止、必要なら deferred-items.md」に準拠)。
   - RESEARCH.md Code Examples L451 では `auth_cookies` 名で例示されていたが、実装は既存 `jwt_cookie` 名を採用し fixture 増殖を回避。

3. **削除候補が 2 件 (register_sse / unregister_sse 専用テスト) で済む確認**
   - `test_notify_no_queue` は元々 "no registered SSE queue does not raise" の契約で、no-op stub の契約 ("呼んでも raise しない") と等価。docstring を D-06 参照に更新するだけで残置可能と判断。

## Deviations from Plan

### 1. Planner 期待値の数値誤算 (Rule 4 相当 — 報告のみ、実装変更なし)

**Found during:** Task 3 verify ステップ

**Issue:** Plan の Task 3 acceptance criteria は `pytest tests/ --ignore=tests/test_mcp_server.py -q --tb=no` の failed 数が **23 以下** を期待していた (27 - 2 test_sse - 2 test_job_store = 23)。実測は **25** (27 - 2 test_sse - 0 削除分)。

**Root cause:** `test_register_and_notify` と `test_unregister_sse` は baseline 27 件失敗リスト (BASELINE.md L26-56) に含まれていない。これらは baseline 時点で **passing** だった (`register_sse` が当時存在したため green)。削除しても failure 数は減らず、collection 数のみ -2。

**Impact:** D-04 / D-05 / D-06 の substantive 契約 (dead code grep 0 / notifier diff 0 / no-op stub) はすべて達成。pytest baseline 短縮幅が planner 期待 (-4) と実測 (-2) で乖離する数値報告のみの差分。Phase 39 close 条件 (pytest ≤ 2) は本 plan 単独でなく Wave 3 で D-10 plan 6/7 を含めて達成する設計なので、本 plan の貢献度 -2 は問題なし。

**Action:** 実装変更なし。SUMMARY.md にて planner 期待値の誤算を明示し、actual delta (-2) を記録。

### 2. Task 4 notifier.py grep 期待値の集計誤差 (Rule 4 相当 — 報告のみ)

**Found during:** Task 4 verify ステップ

**Issue:** Plan の Task 4 acceptance criteria は `grep -cE 'async def (progress|done|send_token|send_turn)' app/jobs/notifier.py` の出力が **4** を期待していた。実測は **8** (BaseNotifier 抽象 4 + WebNotifier 具象 4)。

**Root cause:** notifier.py は ABC `BaseNotifier` (L4-17) と具象 `WebNotifier` (L20-37) で同じ 4 メソッド名を持つ。`grep -cE` は両方の `async def` ヘッダーをカウントするため自然と 8 件。

**Impact:** D-05 (notifier.py 無変更) の substantive 契約は `git diff = 0` で確認済。「表面 API 4 種が WebNotifier に存在し handlers 4 経路から呼ばれている」事実は実測 8 件のうち WebNotifier 側 4 件で確認済。

**Action:** 実装変更なし。

---

**Total deviations:** 2 (両方 planner 数値期待値の誤算、SUMMARY での報告のみ)
**Impact on plan:** 本 plan の substantive 契約 (D-04 / D-05 / D-06) はすべて満たし、Phase 39 全体の進捗 (UIFIX-03 完了 + baseline 27 → 25) も整合的に達成。

## Issues Encountered

### Wave 0 → Wave 1 worktree base mismatch

**Encountered at:** plan 開始時点

**Issue:** worktree の HEAD が `gsd/phase-39-ui-polish` の最新 (`ad296e5`) ではなく、main の 35/36 マージ後 (`e5c2454`) を指していた。`.planning/phases/39-ui-polish/` 配下のファイルが見えず初回 Read が失敗。

**Resolution:** プロンプトの `<worktree_branch_check>` セクションに従い `git reset --hard ad296e5d4da83a409b3322e5d0d82263f9fc35ac` を実行し、worktree base を Phase 39 Wave 0 完了状態に合わせた。以降 .planning/phases/39-ui-polish/* のファイル参照は正常動作。

## User Setup Required

None — backend-only / test-only changes。手動設定は不要。

## Next Phase Readiness

- **Wave 2 plan (39-07 / 39-08) は conftest.py を更に編集予定。本 plan の conftest 差分 (mock_job_store 2 行削除のみ) は L46-L55 範囲内に限局しており、Wave 2 の編集と衝突する可能性は低い (Wave 2 が他 fixture を触る場合は merge 後の確認推奨)。**
- **UIFIX-03 完了**: pytest baseline の Pattern A (JWT cookie 不足) のうち test_sse 2 件分 (= 7 件中 2 件) を本 plan で潰した。残り 5 件 (test_api_chat 3 + test_api_jobs 2) は Wave 3 の plan 39-06 / 39-07 が D-10 範囲で潰す設計。
- **dead code 撤去**: `register_sse` / `unregister_sse` / `self.queues` は完全消滅。Phase 4 SSE 導入時の in-memory queue 経路を v6.0 で正式に retire したことになる。`notifier.py` の Redis pub/sub 専用再設計 (中・大案) は deferred-items.md の v6.1+ 持ち越し項目として既登録 (RESEARCH.md L98)。

## Self-Check

- ✅ `app/jobs/job_store.py`: dead code grep 0、notify signature 完全互換、9 メソッド残存
- ✅ `tests/test_sse.py`: 2 件 green、imports L1-6 無変更
- ✅ `tests/test_job_store.py`: 3 件 green (2 削除済)、`test_notify_no_queue` は no-op stub 契約テストとして残置
- ✅ `tests/conftest.py`: mock_job_store fixture L46-L55 範囲内のみ -2 行、他 fixture 無変更
- ✅ `app/jobs/notifier.py`: `git diff ad296e5..HEAD` = 0 (D-05 表面 API 温存)
- ✅ commits: 532d757 (Task 1 refactor) / b3314bd (Task 2 test) / 5163b9d (Task 3 test)
- ✅ pytest 全体: 25 failed (baseline 27 から -2、test_sse 2 件分)、新規 regression なし

## Self-Check: PASSED

---
*Phase: 39-ui-polish*
*Plan: 04*
*Completed: 2026-05-13*
