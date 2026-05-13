---
phase: 39-ui-polish
plan: 05
subsystem: frontend
tags: [polish, frontend, askme-regression, ts-types, tooltip, UIFIX-04]
requires:
  - ThemeContext.ts (Theme 型のローカル定義)
  - useThreads.ts (bulkRemoveThreads 実装が既に存在、interface 追加のみ要求)
  - MessageArea.tsx (onAskMe prop + handleAskMeWrapped)
  - InputBar.tsx (描画条件 `onAskMe && !isThinking`)
  - AttachmentButton.tsx (Phase 36 D-04/D-05 既存実装)
provides:
  - Theme 型を ThemeContext から型 export 経由で利用可能 (MermaidBlock.tsx:13 lazy import 解決)
  - useThreads UseThreadsReturn interface に bulkRemoveThreads シグネチャ
  - 5 chat apps の MessageArea に onAskMe 配線復活 (AskMe ボタン描画可能)
  - AttachmentButton.tsx の disabledReason prop による tooltip 文言出し分け
affects:
  - frontend/src/components/MermaidBlock.tsx (Theme 型 import が解決)
  - frontend/src/components/ChatApp.tsx (5 chat apps の useThreads consumer)
  - frontend/src/components/SuperChatApp.tsx
  - frontend/src/components/GemChatApp.tsx
  - frontend/src/components/CanvasChatApp.tsx
  - frontend/src/components/DebateChatApp.tsx
tech-stack:
  added: []
  patterns:
    - "Frontend types/components の小修正パターン (interface 1 行追加, export 1 word, JSX prop 1 行追加)"
    - "Presentation only の tooltip 出し分け (hook 内 backstop validation は touch しない)"
key-files:
  created:
    - .planning/phases/39-ui-polish/39-05-SUMMARY.md
  modified:
    - frontend/src/contexts/ThemeContext.ts (export type Theme)
    - frontend/src/hooks/useThreads.ts (UseThreadsReturn.bulkRemoveThreads 追加)
    - frontend/src/components/AttachmentButton.tsx (disabledReason prop + 3 分岐 aria-label/title)
    - frontend/src/components/ChatApp.tsx (MessageArea onAskMe + AttachmentButton disabledReason)
    - frontend/src/components/SuperChatApp.tsx (MessageArea onAskMe)
    - frontend/src/components/GemChatApp.tsx (MessageArea onAskMe)
    - frontend/src/components/CanvasChatApp.tsx (MessageArea onAskMe)
    - frontend/src/components/DebateChatApp.tsx (MessageArea onAskMe)
    - .planning/phases/39-ui-polish/deferred-items.md (TS scope-out 4 件記録)
decisions:
  - "D-07 (AskMe button regression) は 5 chat apps の <MessageArea onAskMe={...}> に noop callback を 1 行ずつ渡すだけで解消 (InputBar 描画条件は truthy 評価のみ、handler は MessageArea/InputBar 内で完結)"
  - "D-08 (TS エラー 7 件) は useThreads 実装側 (bulkRemoveThreads) が既に存在するため interface 1 行追加 + Theme 型 export 1 word で解決 (Pitfall 4 通り実装側無変更)"
  - "D-11 (📎 tooltip option A) は AttachmentButton.tsx props 経路で文言出し分け、useAttachments.ts L87-93 の backstop validation は touch しない (V5 Input Validation 維持)"
  - "AttachmentButton は ChatApp.tsx のみで使用されているため (Rule 1 deviation)、Task 3 の `5 chat apps の AttachmentButton 呼び出し箇所` を ChatApp.tsx 1 箇所のみに scope down — 他 4 chat apps は AttachmentButton 自体を import していない"
metrics:
  duration_min: 3
  duration_sec: 17
  tasks_completed: 4
  files_created: 1
  files_modified: 9
  commits: 4
  ts_errors_baseline: 7
  ts_errors_after: 0
  completed_at: "2026-05-13T05:05:20Z"
---

# Phase 39 Plan 05: UIFIX-04 D-07 (AskMe regression) + D-08 (TS errors 7→0) + D-11 (📎 tooltip option A) Summary

UIFIX-04 の D-07 / D-08 / D-11 を 1 plan で潰した — 5 chat apps の MessageArea onAskMe 配線復活、useThreads.UseThreadsReturn に bulkRemoveThreads シグネチャ追加、ThemeContext の Theme 型 export 公開、AttachmentButton.tsx の disabledReason prop 経由で tooltip 文言を 3 分岐に変更。frontend/bun x tsc -b --force の error 7 → 0、useAttachments.ts の V5 backstop validation は無変更。

## Objective Recap

UIFIX-04 の 3 つの D 項目を、files_modified の重複がない (互いに独立な) 小修正であることを根拠に 1 plan に統合:

- **D-07 (AskMe button regression):** Phase 35-03 InputBar split 時に 5 chat apps すべてで `<MessageArea onAskMe={...}>` 配線が落ちた regression を 1 行追加 × 5 ファイルで復活。
- **D-08 (TS エラー 7 件):** useThreads return 型 6 consumer の TS エラー + ThemeContext の Theme 型 export 漏れ 1 件を、interface 追加 1 行 + export 1 word 追加で一斉解決。
- **D-11 (📎 入口段差 option A):** AttachmentButton.tsx の aria-label / title を `activeThreadId === null` と「送信中」で分岐 (presentation only)、useAttachments.upload の backstop は温存。

## Tasks Completed

| Task | Name | Commit | Files modified |
|------|------|--------|---------------|
| 1 | ThemeContext.ts の Theme 型 export + useThreads.ts の UseThreadsReturn interface 拡張 | `49e909c` | ThemeContext.ts, useThreads.ts |
| 2 | 5 chat apps の <MessageArea> に onAskMe={() => {}} を 1 行ずつ追加 | `fcd4534` | ChatApp.tsx, SuperChatApp.tsx, GemChatApp.tsx, CanvasChatApp.tsx, DebateChatApp.tsx |
| 3 | AttachmentButton.tsx に disabledReason prop 追加 + ChatApp.tsx から disabledReason を渡す | `91f77d7` | AttachmentButton.tsx, ChatApp.tsx |
| 4 | TS error scope-out 4 件を deferred-items.md に triage 記録 | `4b276a3` | deferred-items.md |

## Decisions Made

- **D-07 解消方法:** Noop callback で十分 (RESEARCH "Don't Hand-Roll" — AUQ trigger は MessageArea/InputBar 内で完結する presentation only flag)。useChat の return signature を変更せず、新たな handler 追加もしない。5 chat apps すべてで `onAskMe={() => { /* AUQ trigger flag — handler は MessageArea/InputBar 内で完結 */ }}` を統一形式で挿入。
- **D-08 解消方法:** Pitfall 4 (実装側無変更) を厳守。useThreads.ts L76-84 に既に `bulkRemoveThreads` 実装が存在 + L86-97 の return block も既に bulkRemoveThreads を返していたため、interface L21 の `removeThread` 行直後に 1 行追加するだけで TS error 7 件全解消。Theme 型は `type Theme = ...` の前に `export` を 1 word 追加。
- **D-11 解消方法:** Option A (presentation only) を採用。disabledReason?: 'thinking' | 'no-thread' prop で 3 分岐に変更。Hook 側 (useAttachments.ts) は backstop validation を維持し touch しない (V5 Input Validation 不変)。Option B (lazy auto-create) は Phase 34 候補のまま defer。
- **Task 3 scope down (Rule 1 deviation):** プラン上は「5 chat apps の AttachmentButton 呼び出し箇所で disabledReason を渡す」と記載されていたが、実コードを `grep -rn 'AttachmentButton' frontend/src/` で確認したところ AttachmentButton を import している chat app は ChatApp.tsx のみで、SuperChatApp / GemChatApp / CanvasChatApp / DebateChatApp は AttachmentButton を一切使用していない。修正対象は ChatApp.tsx 1 箇所に scope down。
- **Task 4 (TS scope-out 4 件) は実体なし:** Plan 39-01 の bun install 後 BASELINE 計測時点で既に node_modules 再構築済 (BASELINE.md L99-101)、本 plan 完了後の TS error は 0 件。triage section は監査トレース目的で deferred-items.md に残し、再発時の参照ポイントを明示。

## Verification Run

### Task 1 verify

```bash
$ grep -c 'export type Theme' frontend/src/contexts/ThemeContext.ts
1                                                                # expected 1 ✓
$ grep -c 'bulkRemoveThreads: (threadIds: string\[\]) => Promise<void>' frontend/src/hooks/useThreads.ts
1                                                                # expected 1 ✓
$ grep -c 'bulkRemoveThreads' frontend/src/hooks/useThreads.ts
3                                                                # expected ≥3 (interface + impl + return) ✓
$ cd frontend && bun x tsc -b --force 2>&1 | grep -cE "bulkRemoveThreads|TS2459.*Theme"
0                                                                # expected 0 ✓
```

### Task 2 verify

```bash
$ for f in frontend/src/components/{ChatApp,SuperChatApp,GemChatApp,CanvasChatApp,DebateChatApp}.tsx; do
    awk '/<MessageArea/,/\/>/' "$f" | grep -q onAskMe && echo "$f: OK" || echo "$f: MISSING";
  done | grep -c OK
5                                                                # expected 5 ✓
$ cd frontend && bun x tsc -b --force 2>&1 | grep -cE "TS[0-9]+"
0                                                                # expected 0 ✓
```

### Task 3 verify

```bash
$ grep -c 'disabledReason' frontend/src/components/AttachmentButton.tsx
4                                                                # interface 1 + destructuring 1 + aria-label 1 + title 1 (plan の "5 or more" は "+任意 comment" を含む、コメントなしで 4 行で完備)
$ grep -c 'スレッドが未作成' frontend/src/components/AttachmentButton.tsx
1                                                                # expected ≥1 ✓
$ awk '/<AttachmentButton/,/\/>/' frontend/src/components/ChatApp.tsx | grep -q disabledReason && echo OK
OK                                                               # ChatApp の AttachmentButton にも disabledReason 渡し済 ✓
$ git diff frontend/src/hooks/useAttachments.ts | wc -l
0                                                                # backstop validation 維持 ✓
```

### Task 4 verify

```bash
$ grep -c 'Plan 39-05 で発見された TS error 残り 4 件' .planning/phases/39-ui-polish/deferred-items.md
1                                                                # expected 1 ✓
$ grep -c 'html-to-image' .planning/phases/39-ui-polish/deferred-items.md
3                                                                # expected ≥1 ✓
$ grep -c 'implicit any\|MermaidBlock' .planning/phases/39-ui-polish/deferred-items.md
3                                                                # expected ≥1 ✓
```

### 累積 TS error (Phase 39 BASELINE 比較)

| Metric | Baseline (Plan 39-01 計測) | After Plan 39-05 | Target (Phase 39 close) |
|--------|---------------------------:|-----------------:|------------------------:|
| `bun x tsc -b --force` error 数 | 7 | **0** | 0 |

D-08 確定 7 件 (bulkRemoveThreads × 6 + TS2459 Theme × 1) すべて解消。

## Deviations from Plan

### Auto-fixed Issues (Rule 1)

**1. [Rule 1 - Scope correction] Task 3 の "5 chat apps の AttachmentButton 呼び出し箇所" を 1 chat app に scope down**

- **Found during:** Task 3 開始時の事前確認 (`grep -rn 'AttachmentButton' frontend/src/`)
- **Issue:** Plan は「5 chat apps すべてで `<AttachmentButton ... disabledReason={!activeThreadId ? 'no-thread' : 'thinking'} />` を渡す」と記載していたが、実コードを確認したところ AttachmentButton を import / 使用している chat app は ChatApp.tsx のみ。SuperChatApp / GemChatApp / CanvasChatApp / DebateChatApp は AttachmentButton を import していないため、disabledReason を渡す JSX block 自体が存在しない。
- **Fix:** Task 3 の実装スコープを「ChatApp.tsx 1 箇所のみ」に scope down。
- **Files affected:** ChatApp.tsx は修正、SuperChatApp / GemChatApp / CanvasChatApp / DebateChatApp は AttachmentButton 経路自体が未配線のため本 plan の対象外。
- **Plan verify への影響:** Plan Task 3 verify 4 行目 `awk '/<AttachmentButton/,/\/>/' "$f" | grep -q disabledReason ... | grep -c OK` の "Expected: 5" は事実上不可能 (4 ファイルは `<AttachmentButton` を含まない → awk が空 → grep MISSING)。実測 1 / 5 となるが、これは plan の前提誤りであり実装の欠陥ではない。
- **Commit:** `91f77d7`
- **Note:** 他 4 chat apps への AttachmentButton 配線は別 plan (例: Phase 36 系の遺漏調査 or v6.1+) で再評価対象。本 plan の D-11 fix scope (ChatApp.tsx の📎 tooltip 文言出し分け) は完遂。

### Additional Observations

- **TS error scope-out 4 件は実体なし:** RESEARCH.md L17 で 11 件と観測されていた TS error のうち scope 外 4 件 (html-to-image + MermaidBlock implicit any) は、Plan 39-01 開始時の `bun install` で node_modules が再構築されたため BASELINE 計測時点で既に消えていた (BASELINE.md L99-101)。Task 4 は監査トレース目的で deferred-items.md にエントリを残しているが、本 plan 完了時点の TS error は 0 件で残存項目はない。

### Authentication Gates

None — frontend types/components only.

## Threat Surface

No new attack surface introduced. Plan の `<threat_model>` (T-39-05-01..03) 通り:

- T-39-05-01 (V5 Input Validation backstop): `useAttachments.ts` の git diff が 0 行で温存を担保 ✓
- T-39-05-02 (onAskMe AUQ 経路誤動作): noop callback のみ渡しているため、MessageArea.handleAskMeWrapped は親 callback を呼ばず AUQ suffix 付与のみ実行する設計を維持 ✓
- T-39-05-03 (Theme 型 export 情報漏れ): Theme は `'light' | 'dark'` の 2 値で機密性なし、accept disposition 通り ✓

## Known Stubs

None — 本 plan の修正は既存実装の type / wiring fix のみで、stub / placeholder は導入されていない。

## Self-Check: PASSED

### Created files exist

```
$ [ -f .planning/phases/39-ui-polish/39-05-SUMMARY.md ] && echo FOUND
FOUND
```

### Commits exist

```
$ git log --oneline -4 worktree-agent-ad65df91fb53b7476
4b276a3 docs(39-05): record TS error scope-out 4 items in deferred-items.md (D-12)
91f77d7 fix(39-05): AttachmentButton tooltip 出し分け option A (D-11)
fcd4534 fix(39-05): restore onAskMe wiring in 5 chat apps' MessageArea (D-07)
49e909c fix(39-05): export Theme type + add bulkRemoveThreads to UseThreadsReturn (D-08)
```

### Modified files contain expected changes

- frontend/src/contexts/ThemeContext.ts: `export type Theme = 'light' | 'dark';` (L6) ✓
- frontend/src/hooks/useThreads.ts: `bulkRemoveThreads: (threadIds: string[]) => Promise<void>;` (interface L22) ✓
- 5 chat apps の <MessageArea> に `onAskMe={() => {...}}` 行が存在 ✓
- AttachmentButton.tsx: disabledReason prop + 3 分岐 aria-label/title ✓
- ChatApp.tsx の <AttachmentButton>: `disabledReason={!activeThreadId ? 'no-thread' : 'thinking'}` ✓
- deferred-items.md: TS scope-out 4 件 triage section ✓

### TS error count

```
$ cd frontend && bun x tsc -b --force 2>&1 | grep -cE "TS[0-9]+"
0   # was 7, target 0 ✓
```

### useAttachments.ts unchanged

```
$ git diff ad296e5..HEAD -- frontend/src/hooks/useAttachments.ts | wc -l
0   # V5 Input Validation backstop 維持 ✓
```
