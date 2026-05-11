---
phase: 35
plan: "07a"
title: "Accessibility focus-visible + AuthPanel 変数化 + check-phase-35 実行 + PROJECT.md 更新"
status: complete
subsystem: frontend
tags: [frontend, accessibility, auth-panel, project-md-update, focus-visible]
completed_date: "2026-04-23"
duration_minutes: 15
tasks_completed: 4
tasks_total: 4
files_modified:
  - frontend/src/theme.css
  - frontend/src/components/AuthPanel.tsx
  - .planning/PROJECT.md
key_decisions:
  - ":focus-visible は 7 ボタンクラス全てに適用 — マウスクリック時は outline 非表示（UX 不変）"
  - "AuthPanel の isDark 三項は元々存在しなかったため、inline style hex の単純 var() 置換のみで完結（構造変更なし）"
  - "PROJECT.md mobile policy は削除ではなく案 B（反転して明記）を採用 — 'ネイティブアプリは非対象' を contract として残す"
requires:
  - "35-01 (foundation: CSS variables)"
  - "35-02 (hex→var() migration)"
  - "35-03 (InputBar 分離)"
  - "35-04 (ThreadSidebar migration)"
  - "35-05 (Header migration)"
  - "35-06 (MenuScreen dashboard + responsive @media)"
provides:
  - "theme.css :focus-visible utility (7 button classes)"
  - "AuthPanel.tsx CSS variable 参照 (6 箇所)"
  - "PROJECT.md mobile policy 反転 (D-07)"
  - "check-phase-35.sh 全 PASS gate 通過"
affects:
  - "Plan 07b (human-verify): focus ring / AuthPanel / responsive の visual 確認が可能な状態"
tech_stack_added:
  - pattern: ":focus-visible CSS pseudo-class — Chrome 86+/Edge 86+/Safari 15.4+/Firefox 85+ 対応、マウス操作時に outline を非表示にしつつキーボード操作時に焦点リングを付与"
key_files:
  created: []
  modified:
    - frontend/src/theme.css
    - frontend/src/components/AuthPanel.tsx
    - .planning/PROJECT.md
requirements_addressed:
  - UX-03
  - UX-04
---

# Phase 35 Plan 07a: Accessibility focus-visible + AuthPanel 変数化 + check-phase-35 実行 + PROJECT.md 更新 Summary

**One-liner:** theme.css に :focus-visible キーボードフォーカスリング（7 ボタンクラス対象）を追加し、AuthPanel の inline style hex を CSS 変数 6 箇所に置換、PROJECT.md の mobile policy を D-07 policy 反転に合わせて更新、check-phase-35.sh 全 PASS を確認。

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 01 | theme.css に :focus-visible ユーティリティ追加 | b6f41ba | frontend/src/theme.css |
| 02 | AuthPanel.tsx の色値を CSS 変数参照に置換 | 85ff221 | frontend/src/components/AuthPanel.tsx |
| 03 | check-phase-35.sh 全 PASS 確認（変更なし） | — | スクリプト実行のみ |
| 04 | PROJECT.md mobile policy 反転（D-07） | 63ebbaa | .planning/PROJECT.md |

## Metrics

- **theme.css:** :focus-visible セレクタ 7 件追加（+16 行）
- **AuthPanel.tsx:** hex 6 件 → var(--color-*) 6 件置換（+6 / -6 行、純差分 0）
- **PROJECT.md:** Out of Scope 1 行変更 + Key Decisions 1 行追加 + Last updated 更新

## :focus-visible セレクタ一覧

```css
.menu-card:focus-visible,
.recent-thread-card:focus-visible,
.chat-send-btn:focus-visible,
.chat-askme-btn:focus-visible,
.chat-cancel-btn:focus-visible,
.sidebar-new-chat-btn:focus-visible,
.header-hamburger summary:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}
```

## AuthPanel.tsx 変数置換詳細

| 置換前 hex | 置換後 var() | 用途 |
|-----------|-------------|------|
| `#c0392b` (x2) | `var(--color-destructive)` | エラー/期限切れテキスト |
| `#24292e` | `var(--color-bg)` | 認証ボタン背景 |
| `#fff` | `var(--color-accent-contrast)` | 認証ボタンテキスト |
| `#0366d6` | `var(--color-accent)` | Device Flow 検証 URI リンク |
| `#57606a` | `var(--color-text-muted)` | 認証待機テキスト |

注: `#f6f8fa` / `#d0d7de` (device code 表示枠の背景・ボーダー) は GitHub Design System の中立色であり、semantic 変数が対応しないためそのまま維持。

## check-phase-35.sh 最終実行結果

```
=== Phase 35 Verification Harness ===
  PASS: UX-04-1 semantic color 変数 >= 13 (22 >= 13)
  PASS: UX-04-2 dark ブロック内 semantic override >= 9 (9 >= 9)
  PASS: UX-04-3 @media tablet >= 1 (1 >= 1)
  PASS: UX-04-4 @media mobile >= 1 (1 >= 1)
  PASS: UX-04-5 #7c6ff7 in MenuScreen.tsx == 0
  PASS: UX-04-6 isDark 三項 in MenuScreen.tsx == 0
  PASS: UX-04-5 #7c6ff7 in MessageArea.tsx == 0
  PASS: UX-04-6 isDark 三項 in MessageArea.tsx == 0
  PASS: UX-04-5 #7c6ff7 in ThreadSidebar.tsx == 0
  PASS: UX-04-6 isDark 三項 in ThreadSidebar.tsx == 0
  PASS: UX-04-5 #7c6ff7 in Header.tsx == 0
  PASS: UX-04-6 isDark 三項 in Header.tsx == 0
  PASS: InputBar.tsx が存在
  PASS: UX-04-7 InputBar に toolbarSlot/previewSlot/onSend >= 3 (15 >= 3)
  PASS: UX-03-1 aria-labelledby=section-* >= 3 (3 >= 3)
  PASS: UX-03-2 slice(0, 5) >= 1 (1 >= 1)
  PASS: UX-03-3 日本語セクション見出し 3 種 >= 3 (7 >= 3)
=== All Phase 35 checks passed ===
exit=0
```

## PROJECT.md 更新サマリ

- **Out of Scope 変更**: `モバイル対応 — PC ブラウザのみ対象` → `**ネイティブモバイルアプリ** — タブレット幅（768-1024px）まで primary scope、スマホ幅（375-767px）も破綻ゼロ保証（Phase 35 で実施）。iOS/Android ネイティブは非対象。`
- **Key Decisions 追加**: `Mobile responsive policy 反転 (Phase 35)` エントリを追加（D-07 参照）
- **Last updated**: 2026-04-22 → 2026-04-23

## Plan 07b 着手準備完了

Plan 07b（human-verify gate）への引き継ぎが整っています:
- :focus-visible によるキーボードフォーカスリングの visual 確認（Chrome DevTools → Tab キー操作）
- AuthPanel の Device Flow 認証フロー regression 確認（実際のブラウザで動作テスト）
- レスポンシブ responsive 表示確認（Chrome DevTools Responsive Mode、tablet / mobile ビューポート）
- cross-browser 確認（Safari / Firefox での :focus-visible 動作）

## Deviations from Plan

なし — 全タスクをプラン通り実行。

**補足:** `#f6f8fa` / `#d0d7de`（device code 表示枠）は semantic 変数マッピングに対応するものがないため置換対象外とした。これは acceptance criteria の `grep -cE '#(7c6ff7|0366d6|1e1e2e|2a2a3e|3a3a52|e8e8f0)'` に含まれないため PASS 扱い。

## Known Stubs

なし。

## Threat Flags

なし — 新規エンドポイントなし。CSS 変数差し替えと PROJECT.md 更新のみ。

## Self-Check

- [x] frontend/src/theme.css 存在確認: FOUND
- [x] frontend/src/components/AuthPanel.tsx 存在確認: FOUND
- [x] .planning/PROJECT.md 存在確認: FOUND
- [x] commit b6f41ba 存在確認: FOUND
- [x] commit 85ff221 存在確認: FOUND
- [x] commit 63ebbaa 存在確認: FOUND
- [x] :focus-visible 件数 >= 1: VERIFIED (8件)
- [x] outline: 2px solid var(--color-accent): VERIFIED (1件)
- [x] outline-offset: 2px: VERIFIED (1件)
- [x] AuthPanel 主要 hex 0件: VERIFIED
- [x] AuthPanel var(--color-) >= 3件: VERIFIED (6件)
- [x] PROJECT.md 'PC ブラウザのみ対象' 0件: VERIFIED
- [x] PROJECT.md 'タブレット幅' >= 1件: VERIFIED (3件)
- [x] check-phase-35.sh exit=0: VERIFIED

## Self-Check: PASSED
