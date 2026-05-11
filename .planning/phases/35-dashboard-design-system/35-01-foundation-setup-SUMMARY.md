---
phase: 35
plan: "01"
title: "Foundation Setup — CSS 変数基盤 + utils 切り出し + 検証ハーネス"
subsystem: frontend
tags: [frontend, theme, css-variables, utility-extraction, design-tokens]
one_liner: "primitive 19 + semantic 13 の 2 層 CSS token を theme.css に追加し、threadGroups utility を分離、Phase 35 grep gate ハーネスを整備"

dependency_graph:
  requires: []
  provides:
    - "frontend/src/theme.css: --color-*, --space-*, --radius-*, --font-*, --gradient-title"
    - "frontend/src/utils/threadGroups.ts: getDateGroup / groupThreads / groupOrder / DateGroup"
    - "scripts/check-phase-35.sh: UX-03/UX-04 grep verification gate"
  affects:
    - "Plan 02: theme.css の primitive/semantic 変数を消費して override hex 置換"
    - "Plan 04: ThreadSidebar.tsx のデザイントークン移行（isDark 三項排除）"
    - "Plan 06: MenuScreen セクション化で threadGroups.ts を共有 import"

tech_stack:
  added: []
  patterns:
    - "2 層 CSS token (primitive → semantic) — :root + [data-theme=\"dark\"] 定義"
    - "utility 抽出パターン — コンポーネント内ロジックを utils/ に分離して複数コンポーネントが共有"

key_files:
  created:
    - frontend/src/utils/threadGroups.ts
    - scripts/check-phase-35.sh
  modified:
    - frontend/src/theme.css
    - frontend/src/components/ThreadSidebar.tsx

decisions:
  - "CSS 変数は既存 397 行の hex 値を一切変更せず先頭付近に追加のみ（D-01: Wave 1 Plan 02 が機械的置換する）"
  - "threadGroups.ts は ThreadSidebar.tsx の L61-87 を 1:1 コピー + export キーワード追加（ADR-0040 ロジック保全）"
  - "check-phase-35.sh は CI 統合しない（D-01 方針）— Wave 3 phase gate で手動実行"

metrics:
  duration_minutes: 15
  tasks_completed: 3
  tasks_total: 3
  files_created: 2
  files_modified: 2
  completed_date: "2026-04-23"
---

# Phase 35 Plan 01: Foundation Setup Summary

## Objective

Phase 35 全 wave が並列/順次実行できる基盤を Wave 0 で確定する。CSS 変数 2 層、threadGroups utility、grep 検証ハーネスの 3 点セットを準備。

## Task Results

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 01 | CSS 変数 2 層追加 | 35cfb38 | frontend/src/theme.css (+93 lines) |
| 02 | threadGroups.ts 抽出 + ThreadSidebar import 化 | b60730d | frontend/src/utils/threadGroups.ts (新規), frontend/src/components/ThreadSidebar.tsx (-28 lines) |
| 03 | check-phase-35.sh 作成 | 971b2c8 | scripts/check-phase-35.sh (新規, 実行可能) |

## CSS 変数追加詳細

### Primitive Layer (19 変数)

| 変数名 | 値 |
|--------|-----|
| --color-purple-300 | #a78bfa |
| --color-purple-500 | #7c6ff7 |
| --color-cyan-400 | #38bdf8 |
| --color-red-500 | #e05252 |
| --color-green-500 | #22c55e |
| --color-blue-600 | #0366d6 |
| --color-neutral-50〜900 | 8 値 |
| --color-dark-bg/surface/elevated/border/text | 5 値 |

### Semantic Layer — Light (13 変数)

`--color-bg`, `--color-surface`, `--color-surface-elevated`, `--color-border`, `--color-text`, `--color-text-muted`, `--color-accent`, `--color-accent-contrast`, `--color-accent-subtle`, `--color-destructive`, `--color-success`, `--color-header-bg`, `--color-header-text`

### Semantic Layer — Dark override (9 変数、`[data-theme="dark"]` ブロック)

`--color-bg`, `--color-surface`, `--color-surface-elevated`, `--color-border`, `--color-text`, `--color-text-muted`, `--color-accent-subtle`, `--color-header-bg`, `--color-header-text`

accent / destructive / success は theme 不変のため dark ブロックで再定義しない（UI-SPEC 準拠）。

### その他トークン

- Spacing: `--space-1..16` (8 値)
- Radius: `--radius-sm/md/lg/full` (4 値)
- Font: `--font-body/label/heading/display/caption` (5 値) + `--font-family-body/display` (2 値)
- Gradient: `--gradient-title`

**合計: primitive 19 + semantic(light) 13 + semantic(dark) 9 + spacing 8 + radius 4 + font 7 + gradient 1 = 61 変数追加**

## threadGroups.ts 消費者（Phase 35 時点）

| ファイル | 用途 |
|---------|------|
| `frontend/src/components/ThreadSidebar.tsx` | スレッド一覧の日付グループ分類（既存機能、import 化） |
| `frontend/src/components/MenuScreen.tsx` | Plan 06 で「最近のスレッド」セクションに追加予定 |

## check-phase-35.sh 初回実行結果

Wave 0 時点での実行結果（期待通りの FAIL、クラッシュなし）:

```
PASS: UX-04-1 semantic color 変数 >= 13 (22 >= 13)
PASS: UX-04-2 dark ブロック内 semantic override >= 9 (9 >= 9)
FAIL: UX-04-3 @media tablet >= 1              ← Plan 06 で追加予定
FAIL: UX-04-4 @media mobile >= 1              ← Plan 06 で追加予定
FAIL: UX-04-5/6 各コンポーネント hardcode/isDark ← Plan 02/04/05 で解消予定
FAIL: InputBar.tsx が存在しない                ← Plan 03 で作成予定
FAIL: UX-03-* MenuScreen セクション化         ← Plan 06 で実装予定
exit=1  ← 意図通り (crash なし)
```

Wave 3 Plan 07a/07b の phase gate で全 PASS を期待する。

## Wave 1 並列実行確認

| Plan | 対象ファイル | 並列可否 |
|------|------------|---------|
| Plan 02 (wave 1) | frontend/src/theme.css のみ | Plan 03/04/05 と並列 OK |
| Plan 03 (wave 1) | InputBar.tsx, MessageArea.tsx | Plan 02/04/05 と並列 OK |
| Plan 04 (wave 1) | ThreadSidebar.tsx のみ | Plan 02/03/05 と並列 OK |
| Plan 05 (wave 1) | Header.tsx のみ | Plan 02/03/04 と並列 OK |

Wave 1 の 4 plans は互いに異なるファイルを占有するため完全並列実行可能。

## Deviations from Plan

None — プランどおり実行。

`bun run lint` / `bun run build` は Docker 環境外（node_modules 未インストール）のため実行不可だったが、CSS 変数追加は TypeScript に影響せず、`bash -n` による syntax check と grep-based acceptance criteria はすべて PASS。

## Self-Check: PASSED

- `frontend/src/theme.css` — FOUND (35cfb38)
- `frontend/src/utils/threadGroups.ts` — FOUND (b60730d)
- `scripts/check-phase-35.sh` — FOUND (971b2c8)
- semantic color vars >= 13: FOUND (22)
- dark block overrides >= 9: FOUND (9)
- ThreadSidebar import from threadGroups: FOUND (1 match)
