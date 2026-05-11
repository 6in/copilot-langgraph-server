---
phase: 35
plan: "04"
title: "ThreadSidebar.tsx isDark 排除 + var() 移行 + drawer state 追加"
subsystem: frontend
tags: [frontend, react, theme-migration, drawer, isDark-removal, css-variables]
one_liner: "ThreadSidebar の isDark 三項 8 件を全排除し inline hex を CSS 変数参照に置換、drawer open/close state と Escape ハンドラを追加して Plan 06 の @media 受け皿を整備"

dependency_graph:
  requires:
    - "Plan 01: frontend/src/theme.css に --color-accent / --color-accent-subtle / --color-destructive 等の semantic token が定義済み"
    - "Plan 01: frontend/src/utils/threadGroups.ts が存在し ThreadSidebar で import 済み"
  provides:
    - "frontend/src/components/ThreadSidebar.tsx: CSS 変数駆動 + drawer state (drawerOpen/onDrawerOpenChange) + .sidebar-drawer/.sidebar-backdrop className"
  affects:
    - "Plan 05: Header.tsx に hamburger ボタン追加時、ThreadSidebar の onDrawerOpenChange prop を受け取る"
    - "Plan 06: theme.css に @media (max-width: 1024px) { .sidebar-drawer { position: fixed; ... } } を追加すると tablet/mobile で drawer 活性化"

tech_stack:
  added: []
  patterns:
    - "Controlled/Uncontrolled drawer pattern — propDrawerOpen が渡された場合は controlled、渡さない場合は内部 internalDrawerOpen で動作。既存呼び出し箇所変更不要"
    - "CSS 変数移行 — isDark 三項を削除し、全色を semantic CSS 変数（--color-accent / --color-accent-subtle / --color-destructive / --color-border 等）で参照"

key_files:
  created: []
  modified:
    - frontend/src/components/ThreadSidebar.tsx

decisions:
  - "ConfirmModal への isDark prop は theme === 'dark' をインライン評価で渡す（案 A）— isDark 変数は削除、theme 変数のみ残す"
  - "未使用 import getDateGroup / DateGroup を除去（Plan 01 Task 02 で切り出した際に残った）"
  - "drawer の CSS スタイル（position: fixed / transform）は本 Plan では実装しない — Plan 06 に委譲"

metrics:
  duration_minutes: 6
  tasks_completed: 2
  tasks_total: 2
  files_created: 0
  files_modified: 1
  completed_date: "2026-04-23"
---

# Phase 35 Plan 04: ThreadSidebar Migration Summary

## Objective

ThreadSidebar.tsx の isDark 三項分岐（8 件）を全排除し、inline style を CSS 変数参照に置換する。同時に tablet/mobile で使用する drawer 挙動の state + Escape ハンドラ + backdrop 要素を追加する。

## Task Results

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 01 | isDark 三項排除 + inline hex → var() 移行 + 日本語化 | 761c1ab | frontend/src/components/ThreadSidebar.tsx |
| 02 | drawer state + Escape ハンドラ + backdrop DOM (Task 01 と同一コミット) | 761c1ab | frontend/src/components/ThreadSidebar.tsx |

## 変更詳細

### isDark 三項排除（Task 01）

**削除した isDark 三項: 8 件 → 0 件**

| 箇所 | 削除した三項 | 置換後 |
|------|------------|--------|
| select mode toggle button bg | `isDark ? '#3a3a52' : '#e8f0fe'` | `var(--color-accent-subtle)` |
| select mode toggle button color | `isDark ? '#e8e8f0' : '#0366d6'` | `var(--color-accent)` |
| 全選択/全解除 button border | `isDark ? '#3a3a52' : '#d1dbe3'` | `var(--color-border)` |
| 全選択/全解除 button color | `isDark ? '#9090a8' : '#555'` | `var(--color-text-muted)` |
| 選択数カウント span color | `isDark ? '#9090a8' : '#888'` | `var(--color-text-muted)` |
| date group header color | `isDark ? '#808090' : '#888'` | `var(--color-text-muted)` |
| date group separator line (left) | `isDark ? '#3a3a52' : '#e0e0e0'` | `var(--color-border)` |
| date group separator line (right) | `isDark ? '#3a3a52' : '#e0e0e0'` | `var(--color-border)` |

**削除した const isDark: 1 件 → 0 件**

`const isDark = theme === 'dark';` を削除。ConfirmModal prop は `isDark={theme === 'dark'}` のインライン評価に移行（案 A）。

### inline hex → var() 置換（Task 01）

**置換した hex 件数（重複含む）: 約 20 件**

| 旧 hex | 置換後 CSS 変数 | 箇所 |
|--------|--------------|------|
| `#0366d6` | `var(--color-accent)` | New Chat ボタン background |
| `#fff` | `var(--color-accent-contrast)` | New Chat / bulk delete ボタン color |
| `#ddd` / `#d1dbe3` | `var(--color-border)` | 各種 border |
| `#e05252` | `var(--color-destructive)` | bulk delete ボタン background |
| `#e8f0fe` | `var(--color-accent-subtle)` | active thread item / select mode 背景 |
| `#555` / `#999` / `#888` | `var(--color-text-muted)` | muted text / icon |
| `#333` 系 | `var(--color-text)` | primary text |
| (filter input) | `var(--color-surface)` + `var(--color-border)` | background / border |
| `'6px'` | `var(--radius-md)` | New Chat ボタン border-radius |
| `'4px'` | `var(--radius-sm)` | 各種小ボタン border-radius |

### 日本語化（Task 01）

**変更した copy 件数: 5 件**

| 旧テキスト | 新テキスト |
|-----------|----------|
| `+ New Chat` | `+ 新しいチャット` |
| `Filter conversations...` (placeholder) | `会話を絞り込む...` |
| `N / M matches` | `N / M 件一致` |
| `No conversations yet` | `まだ会話がありません` |
| `No matches` | `一致する会話がありません` |

### drawer state + DOM 構造追加（Task 02）

**追加した要素:**

- `drawerOpen?: boolean` / `onDrawerOpenChange?: (open: boolean) => void` — ThreadSidebarProps に追加（controlled mode prop）
- `const [internalDrawerOpen, setInternalDrawerOpen]` — uncontrolled mode 用内部 state
- `const drawerOpen = propDrawerOpen ?? internalDrawerOpen` — controlled/uncontrolled resolver
- `const setDrawerOpen = (next: boolean) => { ... }` — resolver に応じた setter
- `useEffect` (Escape ハンドラ) — `drawerOpen` が true の間のみ keydown リスナー登録
- `.sidebar-backdrop` div — `drawerOpen && (...)` 条件レンダー、backdrop click で drawer 閉じ
- `<aside className="sidebar-drawer [open]">` — collapsed / expanded 両パスを包む wrapper

**既存コンポーネント呼び出し箇所の変更: 不要**

`drawerOpen` / `onDrawerOpenChange` は optional prop のため、既存の ChatApp / SuperChatApp / GemChatApp 等の呼び出し側を変更しなくても従来通り動作する。

### ConfirmModal 継続性確認（T-35-16 対処）

```tsx
// 変更前
<ConfirmModal ... isDark={isDark} />

// 変更後
<ConfirmModal ... isDark={theme === 'dark'} />
```

ConfirmModal の呼び出しは 2 件とも維持。isDark prop 値は等価。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 未使用 import の除去**
- **Found during:** Task 01 ビルド検証
- **Issue:** `getDateGroup` / `type DateGroup` が Plan 01 Task 02 で threadGroups.ts に移したあと、ThreadSidebar.tsx の import 文に残っていた（未使用）
- **Fix:** import を `{ groupThreads, groupOrder }` のみに絞り込み
- **Files modified:** frontend/src/components/ThreadSidebar.tsx L14
- **Commit:** 761c1ab（Task 01/02 と同一コミット）

## Known Stubs

なし — drawer の `position: fixed` / `transform` / backdrop 背景色は Plan 06 で theme.css に追加予定（仕様通りの defer、stub ではない）。

## Threat Flags

なし — 新規 network endpoint / auth path / file access / schema 変更なし。

## Self-Check: PASSED

**ファイル存在確認:**
- `frontend/src/components/ThreadSidebar.tsx` — FOUND (761c1ab)

**コミット確認:**
- `761c1ab` — FOUND

**Acceptance Criteria 最終確認:**

| Gate | 期待値 | 実測値 | 結果 |
|------|--------|--------|------|
| `isDark \?` 件数 | 0 | 0 | PASS |
| `const isDark` 件数 | 0 | 0 | PASS |
| `#7c6ff7` 件数 | 0 | 0 | PASS |
| `#0366d6` 件数 | 0 | 0 | PASS |
| `var(--color-accent)` 件数 | >=1 | 3 | PASS |
| `var(--color-accent-subtle)` 件数 | >=1 | 2 | PASS |
| `var(--color-destructive)` 件数 | >=1 | 1 | PASS |
| `var(--color-surface)` 件数 | >=1 | 1 | PASS |
| `var(--color-text)` 件数 | >=1 | 2 | PASS |
| `+ 新しいチャット` 件数 | 1 | 1 | PASS |
| `会話を絞り込む` 件数 | 1 | 1 | PASS |
| `まだ会話がありません` 件数 | 1 | 1 | PASS |
| threadGroups import 維持 | 1 | 1 | PASS |
| `drawerOpen` 件数 | >=3 | 15 | PASS |
| `setDrawerOpen` 件数 | >=1 | 4 | PASS |
| `Escape` 件数 | >=1 | 3 | PASS |
| `sidebar-backdrop` 件数 | >=1 | 2 | PASS |
| `sidebar-drawer` 件数 | >=1 | 2 | PASS |
| `role={drawerOpen` 件数 | >=1 | 2 | PASS |
| `aria-label={drawerOpen` 件数 | >=1 | 2 | PASS |
| `useEffect` 件数 | >=1 | 2 | PASS |

**ビルド:** Docker 環境外のため `bun run build` は node_modules 不在で実行不可（Plan 01 SUMMARY と同条件）。ThreadSidebar.tsx 固有のエラーは tsc 単体チェックで 0 件であることを確認。残存エラーはすべて既存の他コンポーネント問題（bulkRemoveThreads 型エラー / MermaidBlock html-to-image 未インストール）。
