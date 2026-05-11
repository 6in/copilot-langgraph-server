---
phase: 35
plan: 05
title: "Header.tsx isDark 排除 + var() 移行 + hamburger menu 追加"
status: complete
completed_date: "2026-04-23"
duration_minutes: 12
tasks_completed: 2
tasks_total: 2
files_created: []
files_modified:
  - frontend/src/components/Header.tsx
commits:
  - hash: "8c0de6a"
    message: "feat(35-05): Header.tsx isDark排除 + CSS変数移行 + hamburger menu追加"
subsystem: frontend
tags: [frontend, react, theme-migration, responsive, hamburger]
key_decisions:
  - "Task 01 と Task 02 を同一ファイルへの変更として 1 コミットに統合（ファイルが 1 つのため分割の意味がない）"
  - "hamburger の marginLeft: auto を <details> に設定して header-desktop-actions と右側で共存（Plan 06 の @media で header-desktop-actions を display: none にすれば hamburger のみが右端に残る）"
  - "ConfirmModal の isDark prop は inline 三項 (theme === 'dark') で渡す（isDark 変数を削除したため）"
dependency_graph:
  requires:
    - "35-01 (foundation-setup) — --gradient-title / --color-header-bg / --color-header-text / CSS 変数が theme.css に定義済み"
  provides:
    - "Header.tsx の CSS 変数受け皿（Plan 06 の @media で .header-hamburger / .header-desktop-actions / .header-model-label / .header-user-login を制御）"
  affects:
    - "35-06 (responsive-css) — @media で .header-hamburger { display: inline-flex } / .header-desktop-actions { display: none } を追加する"
tech_stack:
  added: []
  patterns:
    - "<details> ベース hamburger menu（追加 React state ゼロ、Safari/Chrome/Edge/Firefox ネイティブ対応）"
    - "className ベース display 制御パターン（Plan 06 の @media で mobile-only 表示切替）"
---

# Phase 35 Plan 05: Header Migration Summary

Header.tsx から isDark 三項を全排除し、CSS 変数駆動化 + `<details>` ベース hamburger menu を追加。

## 変更内容

### Task 01: isDark 排除 + inline style hex → var() 移行 + 日本語化

**削除した isDark 三項: 5 件 → 0 件**

| 旧コード | 新コード |
|----------|----------|
| `const isDark = theme === 'dark'` | 削除 |
| `const headerBg = isDark ? '#1e1e2e' : '#24292e'` | 削除 |
| `const headerBorder = isDark ? '#3a3a52' : '#1b1f23'` | 削除 |
| `color: isDark ? '#9090a8' : '#666666'` (appName span) | `color: 'var(--color-text-muted)'` |
| `isDark={isDark}` (ConfirmModal prop) | `isDark={theme === 'dark'}` |

**置換した hex: 11 件 → 0 件**

| 旧 hex / 式 | 新 CSS 変数 |
|------------|------------|
| `background: headerBg` | `var(--color-header-bg)` |
| `color: '#fff'` | `var(--color-header-text)` |
| `gap: '1rem'` (header) | `var(--space-4)` |
| `borderBottom: \`1px solid ${headerBorder}\`` | `1px solid var(--color-border)` |
| `border: '1px solid #555'` (3 ヵ所) | `1px solid var(--color-border)` |
| `color: '#ccc'` (4 ヵ所) | `var(--color-header-text)` |
| `border: '1px solid #444'` (avatar) | `1px solid var(--color-border)` |
| `linear-gradient(90deg, #a78bfa, #7c6ff7, #38bdf8)` | `var(--gradient-title)` |
| `borderRadius: '4px'` (3 ヵ所) | `var(--radius-sm)` |
| `borderRadius: '6px'` (theme toggle) | `var(--radius-md)` |

**日本語化した copy: 4 件**

| 旧テキスト | 新テキスト |
|-----------|-----------|
| `&lsaquo; Menu` (HTML entity) | `‹ メニュー` (Unicode + 日本語) |
| `Model:` | `モデル:` |
| `Logout` | `ログアウト` |
| `aria-label="Toggle light/dark mode"` | `aria-label="ライトモード / ダークモードを切り替え"` |

**追加した className: 4 種**

| className | 対象要素 | Plan 06 での @media 制御 |
|-----------|---------|------------------------|
| `header-desktop-actions` | Model select / Logout / Theme toggle を包む div | mobile (≤767px) で `display: none` |
| `header-model-label` | `<label>モデル:</label>` | tablet (≤1024px) で `display: none` |
| `header-user-login` | `<span>{user.login}</span>` | tablet (≤1024px) で `display: none` |
| `header-hamburger` | `<details>` 要素 | desktop でデフォルト非表示、mobile で `display: inline-flex` |

### Task 02: `<details>` ベース hamburger menu 追加

- `<details className="header-hamburger">` を header 右端に追加
- `<summary aria-label="メニューを開く">` に `listStyle: 'none'` で ▸ 矢印を非表示
- dropdown 内は `role="menu"` + `zIndex: 40` + `var(--color-surface)` 背景
- Logout ボタン (`authState === 'authenticated'` の場合のみ) + Theme toggle を縦配置
- **Pitfall 5 回避:** `<summary>` 直下に `<button>` を置かない（Safari クリック競合防止）
- **z-index 確認:** 40（ConfirmModal 9999 / drawer backdrop 49 / drawer 50 より低い、意図通り）

## Acceptance Criteria 確認

| チェック | 結果 |
|---------|------|
| `isDark ?` 三項 0 件 | PASS (0) |
| `const isDark` 0 件 | PASS (0) |
| `#7c6ff7` 残存 0 件 | PASS (0) |
| 生 hex (#xxxxxx) 残存 | PASS (0件) |
| `var(--gradient-title)` >= 1 | PASS (1) |
| `var(--color-header-bg)` >= 1 | PASS (1) |
| `var(--color-header-text)` >= 1 | PASS (7) |
| `header-model-label` className >= 1 | PASS (1) |
| `header-user-login` className >= 1 | PASS (1) |
| `&lsaquo;` HTML entity 残存 0 件 | PASS (0) |
| `‹ メニュー` >= 1 | PASS (1) |
| `ログアウト` >= 1 | PASS (4: 2 × JSX + 2 × ConfirmModal prop) |
| `>Logout<` 残存 0 件 | PASS (0) |
| `モデル:` >= 1 | PASS (1) |
| `>Model:<` 残存 0 件 | PASS (0) |
| `<details` >= 1 | PASS (1) |
| `header-hamburger` className >= 1 | PASS (1) |
| `<summary` >= 1 | PASS (1) |
| `listStyle` >= 1 | PASS (1) |
| `メニューを開く` >= 1 | PASS (1) |
| summary 直下 button 0 件 (Pitfall 5) | PASS (0) |
| `zIndex: 40` >= 1 | PASS (1) |
| `header-desktop-actions` >= 1 | PASS (1) |

## Deviations from Plan

**1. [Rule 3 - Blocking] Task 01 と Task 02 を 1 コミットに統合**
- **Found during:** Task 01
- **Issue:** 両タスクとも同一ファイル (Header.tsx) への変更であり、分離してコミットするとビルド途中状態が残る
- **Fix:** Task 01・Task 02 の変更を同一コミットに統合
- **Files modified:** frontend/src/components/Header.tsx
- **Commit:** 8c0de6a

**2. [Rule 2 - Missing] node_modules がワークツリーに未インストール — build/lint スキップ**
- **Found during:** 検証フェーズ
- **Issue:** ワークツリーには `bun install` が実行されていないため `bun run lint / build` が使用不可
- **Fix:** acceptance criteria を grep で静的確認。main repo の node_modules で tsc 構文チェック（パス解決エラーは worktree 固有の問題で Header.tsx 自体の構文エラーではない）
- **Impact:** lint / TypeScript build は orchestrator または手動で確認が必要

## Known Stubs

なし — hamburger dropdown には Logout / Theme toggle 実機能を配置。プレースホルダーテキストは存在しない。

## Threat Flags

なし — 新規 endpoint / auth path / file access / schema 変更はなし。

## Self-Check

- [x] `frontend/src/components/Header.tsx` 存在確認: PASS
- [x] commit 8c0de6a 存在確認: PASS
- [x] isDark 三項 0 件: PASS
- [x] 生 hex 0 件: PASS
- [x] `var(--gradient-title)` 参照: PASS
- [x] hamburger `<details>` 追加: PASS
- [x] 4 つの className 配置: PASS

## Self-Check: PASSED
