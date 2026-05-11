---
phase: 35
plan: "06"
title: "MenuScreen ダッシュボード化 + レスポンシブ @media 集約"
status: complete
subsystem: frontend
tags: [frontend, react, dashboard, responsive, media-query, chatscope-override]
completed_date: "2026-04-23"
duration_minutes: 25
tasks_completed: 2
tasks_total: 2
files_modified:
  - frontend/src/components/MenuScreen.tsx
  - frontend/src/theme.css
key_decisions:
  - "B-1: useNavigate() 直接呼び出し設計 — RecentThreadCard クリック時は Props 経由ではなく MenuScreen 内で useNavigate() を使い、App.tsx の Props 拡張を回避"
  - "Pitfall 3: client-side sort — backend の ORDER BY に依存せず [...allThreads].sort().slice(0, 5) で保証"
  - "Pitfall 2: incoming bubble 保護 — tablet @media で .cs-message--outgoing のみに 85% cap を当て、.cs-message--incoming は既存 100% を維持"
  - "B-4: theme.css 末尾への @media block 追加のみ — 既存 L82-490 の override block には一切触らず"
requires:
  - "35-01 (foundation: CSS variables / --gradient-title / --color-accent)"
  - "35-02 (hex→var() migration: --color-surface / --color-border / --color-text)"
  - "35-04 (ThreadSidebar: .sidebar-drawer / .sidebar-backdrop className 付与)"
  - "35-05 (Header: .header-hamburger / .header-desktop-actions / .header-model-label className 付与)"
provides:
  - "MenuScreen 3-section dashboard (section-apps / section-recent / section-other)"
  - "RecentThreadCard 内部コンポーネント (client-side sort + slice 5件)"
  - "theme.css responsive @media block (tablet 1024px / mobile 767px)"
affects:
  - "ThreadSidebar.tsx (drawer overlay CSS の受け皿として .sidebar-drawer.open 使用)"
  - "Header.tsx (.header-hamburger / .header-desktop-actions の表示制御)"
tech_stack_added:
  - pattern: "useNavigate() 直接呼び出し (react-router v7 declarative) — MenuScreen 内で thread routing"
  - pattern: "useMemo + sort + slice pattern — client-side recent threads (5件固定)"
  - pattern: "CSS @media block 末尾集約 — responsive override を theme.css 単一ファイルに集約"
key_files:
  created: []
  modified:
    - frontend/src/components/MenuScreen.tsx
    - frontend/src/theme.css
requirements_addressed:
  - UX-03
  - UX-04
---

# Phase 35 Plan 06: MenuScreen ダッシュボード化 + レスポンシブ @media 集約 Summary

**One-liner:** MenuScreen を 3 セクション型ダッシュボード（アプリ / 最近のスレッド / その他）に再構築し、theme.css 末尾に tablet(1024px) / mobile(767px) @media ブロックを集約してレスポンシブ挙動（drawer overlay / hamburger / chatscope bubble cap）を activate。

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 01 | MenuScreen 3-section dashboard + RecentThreadCard | 5a8cb74 | frontend/src/components/MenuScreen.tsx |
| 02 | theme.css 末尾 @media ブロック集約追加 | a472255 | frontend/src/theme.css |

## Metrics

- **MenuScreen.tsx:** before 297 行 → after 438 行 (+141 行)
- **theme.css:** before 491 行 → after 597 行 (+106 行、Phase 35 Plan 06 responsive block)
- **isDark 三項:** 6件 → 0件 (完全排除)
- **hardcoded accent (#7c6ff7):** 1件 → 0件 (var(--gradient-title) に置換)

## UX-03 Acceptance Criteria Results

| ID | Criterion | Result |
|----|-----------|--------|
| UX-03-1 | aria-labelledby="section-*" 3件以上 | PASS (3件) |
| UX-03-2 | slice(0, 5) スペース付き | PASS (1件) |
| UX-03-3 | 日本語見出し (アプリケーション/最近/その他) | PASS (7件) |
| UX-03-4 | 「使いたいアプリを選んで始めましょう」 | PASS (1件) |
| UX-03-5 | listThreads() 呼び出し | PASS (2件) |
| UX-03-6 | RecentThreadCard (定義+使用) | PASS (4件) |

## UX-04 Acceptance Criteria Results

| ID | Criterion | Result |
|----|-----------|--------|
| UX-04-3 | @media (max-width: 1024px) 存在 | PASS (1件) |
| UX-04-4 | @media (max-width: 767px) 存在 | PASS (1件) |
| UX-04-5 | #7c6ff7 排除 (0件) | PASS |
| UX-04-6 | isDark 三項排除 (0件) | PASS |
| Pitfall 2 | .cs-message--incoming に 85% 漏れなし | PASS (100% 維持) |
| Pitfall 7 | drawer z-index=50, backdrop=49 (ConfirmModal 9999 より低い) | PASS |

## theme.css Responsive Block Summary

```
.sidebar-drawer { position: relative; }   /* desktop default */
.header-hamburger { display: none; }      /* desktop default */

@media (max-width: 1024px) {
  .menu-screen, .menu-card-grid           /* padding/grid 縮小 */
  .header-model-label, .header-user-login /* 非表示 */
  .sidebar-drawer (fixed + transform)     /* overlay 化 */
  .sidebar-drawer.open (translateX(0))    /* open 時表示 */
  .sidebar-backdrop (z-index: 49)         /* dim overlay */
  .cs-message--outgoing (max-width: 85%) /* bubble cap */
  .chat-input-row (flex-wrap)             /* InputBar 縦積み許容 */
}

@media (max-width: 767px) {
  .menu-screen, .menu-card-grid, .menu-recent-grid  /* 1列固定 */
  .header-hamburger (display: inline-flex)           /* 表示 */
  .header-desktop-actions (display: none)            /* 非表示 */
  .cs-message--outgoing (max-width: 100%)            /* mobile 全幅 */
  .sidebar-drawer (min(80vw, 320px))                 /* 幅調整 */
}
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] useEffect 内の同期 setState 排除 (eslint react-hooks/set-state-in-effect)**
- **Found during:** Task 01 lint 検証
- **Issue:** `useEffect` 内で `setLoading(true)` / `setError(null)` を同期呼び出しするとカスケードレンダーが起きる（eslint エラー）
- **Fix:** cleanup cancellation flag (`cancelled = true`) パターンに統一し、setState を非同期コールバック内のみに移動
- **Files modified:** frontend/src/components/MenuScreen.tsx
- **Commit:** 5a8cb74 (Task 01 コミットに含む)

## Known Stubs

なし — MenuScreen の 3 セクション構造は完全に実装済み。最近スレッドは listThreads() から実データを取得。

## Threat Flags

なし — 新規エンドポイントなし。client-side routing のみ（app_id は backend 返却値、JWT 認証済み）。

## Self-Check

- [x] frontend/src/components/MenuScreen.tsx 存在確認: FOUND
- [x] frontend/src/theme.css 存在確認: FOUND
- [x] commit 5a8cb74 存在確認: FOUND
- [x] commit a472255 存在確認: FOUND
- [x] isDark 三項 0件: VERIFIED
- [x] #7c6ff7 0件: VERIFIED
- [x] slice(0, 5) 1件: VERIFIED
- [x] @media 1024px / 767px: VERIFIED
- [x] .cs-message--incoming に 85% 漏れなし: VERIFIED (100% 維持)

## Self-Check: PASSED
