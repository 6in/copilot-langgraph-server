---
phase: 35
plan: "02"
title: "theme.css hex → var() 機械置換 + chatscope override 変数駆動化"
subsystem: frontend
tags: [frontend, theme, css-variables, chatscope, dark-mode]
one_liner: "dark override 全ブロックの hex を semantic CSS 変数に機械置換し、!important を据え置いたまま変数駆動ダークモードを確立"

dependency_graph:
  requires:
    - "Plan 01: primitive/semantic CSS token 2 層 (--color-bg 等の定義)"
  provides:
    - "frontend/src/theme.css: [data-theme='dark'] override が全て var(--color-*) 経由で色解決"
  affects:
    - "Plan 03: InputBar.tsx (chat-send-btn / chat-textarea を使う新コンポーネント)"
    - "Plan 04: ThreadSidebar.tsx (sidebar-* クラスの dark override が変数経由)"
    - "Plan 05: Header.tsx (dark header-bg が変数経由)"
    - "Plan 07a/07b: phase gate で override 内 hex 0 件を確認"

tech_stack:
  added: []
  patterns:
    - "2 層 CSS token 消費パターン — primitive/semantic 宣言を source of truth とし、override はその値を var() 参照するだけ"

key_files:
  created: []
  modified:
    - frontend/src/theme.css

decisions:
  - "#252535 (cs-message--incoming) はプリミティブ対応なし → var(--color-surface) (#2a2a3e) で近似 (差分 0x0f 程度、視覚差なし)"
  - "md-table tbody tr:nth-child(even) の #252535 も同様に var(--color-surface) で統一 (2 tone→1 tone への単純化)"
  - "typing-dot の共通ルール (#aaa、dark 非対応) は対象外 — dark override の [data-theme='dark'] .typing-dot のみ置換"
  - "md-table の light ルール内 hex は変更対象外 (dark override ブロック以外)"

metrics:
  duration_minutes: 10
  tasks_completed: 1
  tasks_total: 1
  files_created: 0
  files_modified: 1
  completed_date: "2026-04-23"
---

# Phase 35 Plan 02: theme.css hex → var() Summary

## Objective

Wave 0 Plan 01 で追加した semantic 変数を theme.css 側で実際に消費させ、dark mode 切替が 1 箇所の semantic 値変更で伝播する状態にする。

## Task Results

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 01 | chatscope + sidebar + chat-input-bar + auth + typing-dot + md-table の hex を var() に機械置換 | ab33d0d | frontend/src/theme.css (73 lines changed) |

## 置換詳細 — カテゴリ別

| カテゴリ | 対象ブロック | var() 参照数 | 主な置換 |
|---------|-----------|------------|---------|
| chatscope containers | `.cs-main-container` / `.cs-chat-container` / `.cs-message-list` / `.cs-sidebar--left` / `.cs-message--incoming` / `.cs-message--outgoing` / `.cs-typing-indicator` | 13 | bg/border/text/surface/surface-elevated/text-muted |
| sidebar-* | `.sidebar-content` / `.sidebar-new-chat-btn` / `.sidebar-collapse-btn` / `.sidebar-filter-*` / `.sidebar-thread-*` / `.sidebar-empty-text` | 24 | accent/accent-contrast/bg/border/text/text-muted/destructive/surface-elevated |
| chat-input | `.chat-input-bar` / `.chat-textarea` / `.chat-send-btn` / `.chat-copy-btn` / `.chat-empty-state` | 13 | surface/border/bg/text/text-muted/accent/accent-contrast |
| auth-* | `.auth-panel-root` / `.auth-start-btn` / `.auth-device-code` / `.auth-copy-btn` / `.auth-waiting-text` / `.auth-link` | 15 | bg/surface/border/text/text-muted/accent |
| typing-dot | `[data-theme="dark"] .typing-dot` | 1 | text-muted |
| md-table dark | `.md-table-wrap` / `.md-table` / `.md-table thead th` / `.md-table th,td` / `.md-table tbody tr:nth-child(even)` | 7 | bg/border/surface/surface-elevated/text |
| **合計** | | **73** | |

## !important 数 Before/After

| Before | After | 差分 |
|--------|-------|------|
| 71 | 71 | 0 (据え置き) |

chatscope specificity 勝負に必要な `!important` は一切外していない。

## 残存 hex の確認

| 行 | 内容 | 残存理由 |
|----|------|---------|
| L25-43 | primitive 宣言 (`--color-purple-500: #7c6ff7` 等 19 変数) | source of truth — 変更禁止 |
| L49-60 | semantic light 値 (`--color-surface: #ffffff` 等) | source of truth — 変更禁止 |
| L403 | `.typing-dot { background: #aaa }` | light/共通ルール — dark override 対象外 |
| L425-453 | `.md-table-wrap` / `.md-table` 等の light ルール | `[data-theme="dark"]` 外 — 対象外 |

**override ブロック内に 6-digit hex は 0 件（W-1 gate PASS）**

## 置換漏れ awk gate (W-1) 結果

```bash
awk '/\[data-theme="dark"\]\s*\.(cs-|sidebar-|chat-|auth-|md-)/,/^\}$/' frontend/src/theme.css \
  | grep -cE '#[0-9a-fA-F]{6}\b'
# 結果: 0
```

PASS — override ブロック内に 6-digit hex 残存なし。

## Integration Check

- CSS 構文チェック: `{` / `}` 対称性 69/69 = PASS
- 全 `var(--color-*)` 参照が `:root` / `[data-theme="dark"]` ブロック内で定義済みであることを確認
- `#1e1e2e` 残存: 1 行（primitive 宣言 `--color-dark-bg` のみ）PASS
- `#7c6ff7` 残存: 1 行（primitive 宣言 `--color-purple-500` のみ）PASS
- `bun run build` / `bun run lint`: Docker 環境外のため未実行（Wave 3 Phase gate で確認）

目視 integration check（dark/light toggle）は Wave 3 Plan 07a で実施予定。

## Deviations from Plan

### Auto-fixed Issues

なし。

### 設計判断（deviation 相当）

**1. `#252535` → `var(--color-surface)` への近似**
- **発見:** chatscope `.cs-message--incoming` と md-table `tbody tr:nth-child(even)` に `#252535` が使用されていた
- **問題:** primitive 一覧に `#252535` の定義なし（`--color-dark-surface: #2a2a3e` と `--color-dark-elevated: #313145` の中間値）
- **判断:** 視覚差 (0x0f 相当) は許容範囲内として `var(--color-surface)` (#2a2a3e) で統一
- **影響:** 2-tone → 1-tone への単純化。Plan 07b の cross-browser sweep で必要なら `--color-surface-dim` 追加を検討

## Known Stubs

なし。全置換は実機値を参照しており、placeholder なし。

## Threat Flags

なし。theme.css の変更は CSS 値のみ、新規ネットワークエンドポイントや auth パスの追加なし。

## Self-Check: PASSED

- `frontend/src/theme.css` 変更コミット ab33d0d — FOUND
- `var(--color-bg) !important` >= 1: 6 件 PASS
- `var(--color-surface) !important` >= 1: 6 件 PASS
- `var(--color-accent) !important` >= 2: 6 件 PASS
- `var(--color-border) !important` >= 2: 10 件 PASS
- `var(--color-text) !important` >= 1: 14 件 PASS
- `var(--color-destructive)` >= 1: 1 件 PASS
- `.cs-main-container` セレクタ存在: 1 件 PASS
- `!important` 数 >= 20: 71 件 PASS（据え置き確認）
- W-1 gate (override 内 hex 残存): 0 件 PASS
- `#1e1e2e` 残存 <= 2: 1 件 (primitive 宣言のみ) PASS
- `#7c6ff7` 残存 <= 1: 1 件 (primitive 宣言のみ) PASS
- CSS 括弧対称性 69/69: PASS
