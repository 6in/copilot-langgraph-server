---
phase: 39
plan: 01
subsystem: planning-bookkeeping
tags: [polish, baseline, gsd-meta, wave-0]
requirements: [UIFIX-04]
dependency_graph:
  requires: []
  provides:
    - "後続 plan (39-02..39-08) が verify で参照する baseline 数値 (pytest 27 / TS 7 / cwd= 6 / dead code 7)"
    - "deferred-items.md (D-12 上限ポリシーの運用基盤、後続 plan が scope 外発見を積む場所)"
    - "39-VALIDATION.md frontmatter `wave_0_complete: true` (Wave 1 開始の前提条件)"
  affects: []
tech_stack:
  added: []
  patterns:
    - "Phase 38/36 deferred-items.md ヘッダー形式 (本 phase で踏襲)"
    - "Phase 39 D-12 上限ポリシー (実行中の新規発見は deferred-items.md 行き、ついで修正禁止)"
key_files:
  created:
    - .planning/phases/39-ui-polish/39-BASELINE.md
    - .planning/phases/39-ui-polish/deferred-items.md
  modified:
    - .planning/phases/39-ui-polish/39-VALIDATION.md (frontmatter のみ)
decisions:
  - "BASELINE.md の Phase 39 完了時 target を pytest failed ≤ 2 / TS 0 / cwd= 0 / dead code 0 に固定 (後続 plan の verify はこの値を参照)"
  - "CONTEXT.md D-10 主張 '14 failures + 4 errors' を obsolete 認定、実測 27 failed / 0 errors を採用"
  - "RESEARCH.md 主張の TS 追加 4 件は `bun install` 後の re-measurement で 0 件、D-08 の 7 件を維持"
metrics:
  duration_minutes: ~13
  completed: 2026-05-13
  tasks_completed: 2
  files_created: 2
  files_modified: 1
---

# Phase 39 Plan 01: Wave 0 Bookkeeping (baseline + deferred-items scaffold) Summary

D-12 上限ポリシーの運用基盤を整備し、Phase 39 開始時点の pytest / tsc / grep baseline 数値を 39-BASELINE.md に固定。後続 plan の verify が同じ baseline を参照できるようにした。

## What was delivered

### Task 1: pytest / tsc ベースライン数値の固定 (`39-BASELINE.md`)

- 実測コマンド 5 種を順に実行し、出力を `.planning/phases/39-ui-polish/39-BASELINE.md` に転記
- **pytest baseline** (`pytest tests/ --ignore=tests/test_mcp_server.py -q --tb=no`): `27 failed, 397 passed, 13 skipped, 1 xfailed, 1 xpassed, 57 warnings in 35.60s`
- **失敗テスト 27 件のフルリスト** を表形式で記録
- **5 パターン分類** (RESEARCH.md L19-25 と一致):
  - Pattern A (JWT cookie 不足): 7 件 (test_api_chat 3 + test_api_jobs 2 + test_sse 2)
  - Pattern B (psycopg AsyncMock): 4 件 (test_api_chat 3 + test_worker 1)
  - Pattern C (LLM astream AsyncMock): 6 件 (test_graph 3 + test_worker 3)
  - Pattern D (mock 経路): 4 件 (test_debate_handler 1 + test_rpc_integration 1 + test_tool_enabled_subagent 1 + test_worker 1)
  - Pattern E (tool catalog drift): 6 件 (test_tool_catalog_js 1 + test_tool_registry 1 + test_generate_mcp_artifacts 4)
  - 合計 7+4+6+4+6 = 27 ✅
- **TS baseline** (`cd frontend && bun x tsc -b --force`): **7 件** (bulkRemoveThreads 6 + Theme export 1)
- **cwd= grep**: 6 件 (claude_code 系、line 293/316/341/372/394/410)
- **dead code grep** (`register_sse|unregister_sse|self.queues`): 7 件 (line 13/15/18/21/23/35/37)
- **D-10 target reconciliation セクション**: CONTEXT.md "14 failures + 4 errors" を obsolete 認定し、実測 27 failed / 0 errors を採用 (test_install_hooks は 4 passed で既に解消済)
- **Phase 39 完了時の target 表**: pytest ≤ 2 / TS 0 / cwd= 0 / dead code 0 を固定値として記載

### Task 2: deferred-items.md scaffold + VALIDATION frontmatter 更新

- `.planning/phases/39-ui-polish/deferred-items.md` を新規作成。冒頭ヘッダー (Phase 38/36 踏襲) + D-12 上限ポリシー言及 + 空ボディ (項目 0 件)
- `.planning/phases/39-ui-polish/39-VALIDATION.md` frontmatter を 2 行変更:
  - `nyquist_compliant: false` → `nyquist_compliant: true`
  - `wave_0_complete: false` → `wave_0_complete: true`
  - frontmatter 以外の本文は無変更 (`git diff` で確認、変更行は frontmatter 2 行のみ)

## Commits

| Task | Hash | Message |
|------|------|---------|
| 1 | `6dd68a2` | `docs(39-01): pytest/tsc/grep baseline 値を 39-BASELINE.md に固定` |
| 2 | `2d0b37f` | `docs(39-01): deferred-items.md scaffold + VALIDATION frontmatter を wave_0_complete に更新` |

## Verification Results

| 項目 | 結果 |
|------|------|
| `test -f 39-BASELINE.md` | PASS (file exists) |
| `grep -cE 'pytest baseline\|TS baseline\|target' 39-BASELINE.md` | **4** ≥ 1 |
| `grep -c '27 failed' 39-BASELINE.md` | **1** ≥ 1 |
| `grep -c '397 passed' 39-BASELINE.md` | **1** ≥ 1 |
| `grep -c 'error 件数 = 7' 39-BASELINE.md` | **1** ≥ 1 (TS) |
| `grep -c '実測値: 6' 39-BASELINE.md` | **1** ≥ 1 (cwd=) |
| `grep -c 'D-10 target reconciliation' 39-BASELINE.md` | **1** ≥ 1 |
| `grep -c 'Phase 39 完了時の target' 39-BASELINE.md` | **1** ≥ 1 |
| `test -f deferred-items.md` | PASS |
| `grep -c 'Phase 39 — Deferred Items' deferred-items.md` | **1** ≥ 1 |
| `grep -c 'D-12' deferred-items.md` | **1** ≥ 1 |
| `grep -c '^## Plan' deferred-items.md` (項目数) | **0** ✅ |
| `grep -c 'wave_0_complete: true' 39-VALIDATION.md` | **2** (frontmatter + Test Infrastructure 内、本 task は frontmatter のみ変更) |
| `grep -c 'nyquist_compliant: true' 39-VALIDATION.md` | **2** (同上) |
| `git diff` VALIDATION 変更範囲 | frontmatter 2 行のみ ✅ |
| Full suite re-run | `27 failed, 397 passed` (本 plan 開始時と同一、code 未変更を確認) |

## Deviations from Plan

**None** — plan は planning artifact のみ touch し、code / test に変更を加えない設計通りに実行。Rule 1-3 の auto-fix 起動はなし。

唯一発生した予期外の操作:

- **frontend deps 未 install**: tsc baseline 計測時に `frontend/node_modules` が未生成で、`bun x tsc` が `TS2688 (vite/client / node)` を返した。`bun install` を実行して 408 packages を install してから再計測したところ RESEARCH.md 主張の追加 4 件 (`html-to-image` TS2307 + implicit any 3) は解消し、D-08 確定の 7 件のみが残った (これは BASELINE.md の "RESEARCH.md L17 との比較" 節に記載済)。`bun install` は dependency 状態の正規化であり、code/test 改変ではないため Rule 範囲外 (auto-fix attempt にカウントしない)。

## Threat Flags

なし — Wave 0 は planning artifact (BASELINE.md / deferred-items.md / VALIDATION.md frontmatter) のみで外部公開 surface に変更なし。Threat Register T-39-01-01 (BASELINE に secret 流入) は **mitigate 達成**: pytest/tsc/grep の標準出力のみ転記し、env 変数 / JWT secret / cookie 値は記載していない。

## Known Stubs

なし — Wave 0 はコード生成なし。

## Self-Check: PASSED

### Files created
- `[FOUND]` .planning/phases/39-ui-polish/39-BASELINE.md
- `[FOUND]` .planning/phases/39-ui-polish/deferred-items.md

### Files modified
- `[FOUND]` .planning/phases/39-ui-polish/39-VALIDATION.md (frontmatter 2 行のみ)

### Commits verified in git log
- `[FOUND]` 6dd68a2 (Task 1)
- `[FOUND]` 2d0b37f (Task 2)

### Acceptance criteria (Task 1 + Task 2 全 10 項目)
- `[PASS]` BASELINE.md 存在
- `[PASS]` "27 failed" 実測数値記載
- `[PASS]` "397 passed" 実測数値記載
- `[PASS]` "7" (TS error 件数) 記載
- `[PASS]` "6" (cwd= 件数) 記載
- `[PASS]` "Phase 39 完了時の target" セクション存在 + pytest ≤ 2 / tsc 0 / cwd= 0 / dead code 0 記載
- `[PASS]` "D-10 target reconciliation" 1 件以上
- `[PASS]` deferred-items.md 存在 + `# Phase 39 — Deferred Items` 含む
- `[PASS]` deferred-items.md に "D-12" 言及あり
- `[PASS]` deferred-items.md の項目セクション (## Plan N で発見された …) は 0 件
- `[PASS]` VALIDATION frontmatter `wave_0_complete: true` + `nyquist_compliant: true`
- `[PASS]` VALIDATION 本文 (frontmatter 以外) 無変更
