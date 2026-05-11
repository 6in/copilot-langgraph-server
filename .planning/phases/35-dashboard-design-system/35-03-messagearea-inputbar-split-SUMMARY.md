---
phase: 35
plan: "03"
title: "MessageArea → InputBar 分離 + var() 移行 + isDark 三項排除"
subsystem: frontend
tags: [frontend, react, component-split, controlled-component, phase-36-handoff, design-tokens]
one_liner: "MessageArea の chat-input-bar ブロックを controlled InputBar.tsx (228 行) に分離し、isDark 三項 7 件を排除して全色を var(--color-*) 経由に移行"

dependency_graph:
  requires:
    - "Plan 01: frontend/src/theme.css の CSS 変数定義（--color-*, --space-*, --radius-*）"
  provides:
    - "frontend/src/components/InputBar.tsx: controlled input bar with 3 slot reservations (toolbarSlot/previewSlot/copyAllSlot)"
    - "frontend/src/components/MessageArea.tsx: isDark-free, delegates input rendering to InputBar"
  affects:
    - "Plan 06 (MenuScreen): InputBar の toolbarSlot/previewSlot パターンを参照"
    - "Phase 36: InputBar に toolbarSlot={<AttachmentButton />} / previewSlot={<AttachmentChips />} を差し込むだけで動く"

tech_stack:
  added: []
  patterns:
    - "controlled component pattern — InputBar は value/onChange/onSend 等を全て props で受け取る"
    - "slot reservation pattern — toolbarSlot/previewSlot/copyAllSlot: 空なら何もレンダーしない条件分岐"
    - "opaque callback pattern — onAskMe: () => void は AUQ suffix の存在を InputBar に漏らさない"

key_files:
  created:
    - frontend/src/components/InputBar.tsx
  modified:
    - frontend/src/components/MessageArea.tsx
    - frontend/src/utils/agentColor.ts

decisions:
  - "agentBgColor の引数を isDark: boolean から theme: string に変更（isDark 変数宣言を MessageArea から完全排除するため）"
  - "onAskMe を MessageArea 側で handleAskMeWrapped として実装し、AUQ suffix 付与ロジックを MessageArea に閉じる（Pitfall 4）"
  - "useCurrentTheme は agentBgColor 呼び出しのために MessageArea に残す（isDark 変数は排除済み）"
  - "既存 build エラー（bulkRemoveThreads / html-to-image / MermaidBlock）は pre-existing のためスコープ外"

metrics:
  duration_minutes: 4
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 2
  completed_date: "2026-04-23"
---

# Phase 35 Plan 03: MessageArea → InputBar 分離 Summary

## Objective

MessageArea.tsx の chat-input-bar ブロック（L383-485）を controlled component `InputBar.tsx` として分離し、Phase 36 の `<AttachmentButton>` / `<AttachmentChips>` 差し込みを想定した `toolbarSlot` / `previewSlot` / `copyAllSlot` 3 スロットを予約する。同時に MessageArea / InputBar 両ファイルから isDark 三項分岐を排除し、inline style を CSS 変数参照に置換する。

## Task Results

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 01 | InputBar.tsx 新規作成（controlled component + 3 slot） | dcbeb23 | frontend/src/components/InputBar.tsx (228 行新規) |
| 02 | MessageArea.tsx リファクタ + isDark 三項排除 + var() 移行 | 98a071b | frontend/src/components/MessageArea.tsx (-60 行), frontend/src/utils/agentColor.ts |

## 実装詳細

### InputBar.tsx (228 行)

| 指標 | 値 |
|------|-----|
| 行数 | 228 行 (min_lines: 100 達成) |
| isDark 三項 | 0 件 |
| 生 hex (#xxxxxx) | 0 件 |
| CSS 変数参照 | var(--color-accent), var(--color-accent-contrast), var(--color-success), var(--color-border), var(--color-surface), var(--color-text), var(--space-*), var(--radius-*) |
| スロット | toolbarSlot / previewSlot / copyAllSlot — 空なら何もレンダーしない |
| AUQ 汚染 | 0 件（AUQ_SUFFIX / ask_user_question は含まない — Pitfall 4 準拠） |

**InputBarProps:**
```typescript
export interface InputBarProps {
  value: string;
  onChange: (next: string) => void;
  onSend: (text: string, contextMessages?: ContextMessage[]) => void;
  onCancel?: () => void;
  onAskMe?: () => void;         // opaque — AUQ suffix は知らない
  disabled?: boolean;
  isThinking?: boolean;
  placeholder?: string;
  toolbarSlot?: ReactNode;      // Phase 36: 📎 / ModelSelector
  previewSlot?: ReactNode;      // Phase 36: AttachmentChips
  copyAllSlot?: ReactNode;
}
```

### MessageArea.tsx Before / After

| 指標 | Before | After |
|------|--------|-------|
| 行数 | 489 行 | 429 行 (-60 行) |
| isDark 三項分岐 | 7 件 | 0 件 |
| const isDark 宣言 | 1 件 | 0 件 |
| 生 hex 残存 | 多数 | 0 件 |
| CSS 変数参照 | 0 件 | 17 件 |

### 削除した isDark 三項（7 件）

| 箇所 | 元の値 | 置換後 |
|------|--------|-------|
| resend checkbox label (user) L245 | `isDark ? '#9090a8' : '#888'` | `var(--color-text-muted)` |
| resend checkbox accentColor (user) L250 | `accentColor: '#0366d6'` | `accentColor: 'var(--color-accent)'` |
| resend checkbox label (AI) L305 | `isDark ? '#9090a8' : '#888'` | `var(--color-text-muted)` |
| resend checkbox accentColor (AI) L310 | `accentColor: '#0366d6'` | `accentColor: 'var(--color-accent)'` |
| thinking indicator elapsed color L333 | `isDark ? '#9090a8' : '#888'` | `var(--color-text-muted)` |
| cancel button border L346 | `isDark ? '#3a3a52' : '#d1dbe3'` | `var(--color-border)` |
| cancel button color L350 | `isDark ? '#9090a8' : '#888'` | `var(--color-text-muted)` |

さらに pendingQuestion パネルの `isDark ? '#9090a8' : '#888'` (L393) も置換済み。

### agentColor.ts 修正（Deviation — Rule 1）

`agentBgColor(name: string, isDark: boolean)` → `agentBgColor(name: string, theme: string)` に変更。MessageArea で `isDark` 変数を完全排除するために必要な修正。関数内部は `theme === 'dark'` で同等動作を維持。

### 手動 regression チェックリスト

| 機能 | 確認方法 | 期待動作 |
|------|---------|---------|
| Ctrl+Enter 送信 | `/orochi/chat` でテキスト入力 → Ctrl+Enter | メッセージ送信 |
| AskMe (AUQ) | AskMe ボタンクリック | AUQ suffix 付きで送信 |
| resend checkbox | SuperChat でチェックボックス操作 | コンテキスト制御 |
| Cancel | thinking 中に Cancel | SSE 中断 |
| QuestionPanel | pendingQuestion 受信時 | InputBar 非表示、QP 表示 |
| CopyAll | messages > 0 のとき | copyAllSlot にボタン表示 |

（自動化 build/lint は pre-existing エラーによりスコープ外判定 — 下記参照）

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] agentBgColor の isDark パラメータ型変更**

- **Found during:** Task 02
- **Issue:** `agentBgColor(name, isDark)` を呼ぶには `isDark` 変数が必要で、`const isDark = theme === 'dark'` を残す必要があった
- **Fix:** `agentColor.ts` の `agentBgColor` 引数を `isDark: boolean` → `theme: string` に変更し、MessageArea.tsx では `agentBgColor(msg.senderName, theme)` で呼べるように変更
- **Files modified:** `frontend/src/utils/agentColor.ts`
- **Commit:** 98a071b

### Scoped Out (Pre-existing, Out of Scope)

以下は Plan 03 のファイルと無関係の pre-existing ビルドエラー。スコープ外として放置:

- `bulkRemoveThreads` — `useThreads.ts` の型不一致（Plan 04 スコープ外）
- `html-to-image` module not found — `MermaidBlock.tsx`（Phase 39 スコープ）
- `Theme` not exported — `MermaidBlock.tsx`（Phase 39 スコープ）
- `getDateGroup`, `DateGroup` unused — `ThreadSidebar.tsx`（Plan 04 後続対応）

## Threat Flags

なし — 新規ネットワークエンドポイント・auth パス・スキーマ変更なし。AUQ suffix 漏れ（T-35-11）は InputBar に `AUQ_SUFFIX` / `ask_user_question` が存在しないことで mitigate 済み。

## Known Stubs

なし — toolbarSlot / previewSlot が `undefined` の場合は何もレンダーしない設計であり、空表示がユーザーに露出するスタブはない。Phase 36 差し込み前の正常状態。

## Self-Check: PASSED

- `frontend/src/components/InputBar.tsx` — FOUND (dcbeb23)
- `frontend/src/components/MessageArea.tsx` — FOUND (98a071b), 429 行
- `frontend/src/utils/agentColor.ts` — FOUND (98a071b)
- isDark ternary in MessageArea: 0 件 — PASS
- isDark ternary in InputBar: 0 件 — PASS
- const isDark in MessageArea: 0 件 — PASS
- raw hex in InputBar: 0 件 — PASS
- raw hex in MessageArea: 0 件 — PASS
- AUQ_SUFFIX in MessageArea: 2 件 — PASS
- excludedIndices in MessageArea: 4 件 — PASS
- var(--color-*) in MessageArea: 17 件 — PASS
- QuestionPanel in MessageArea: 3 件 — PASS
- CopyAllButton in MessageArea: 2 件 — PASS
- InputBar export function: 1 件 — PASS
- InputBarProps export interface: 1 件 — PASS
- toolbarSlot/previewSlot/onSend in InputBar: 15 件 — PASS
- copyAllSlot in InputBar: 5 件 — PASS
- var(--color-accent) in InputBar: 1 件 — PASS
- var(--color-success) in InputBar: 2 件 — PASS
- 送信 in InputBar: 3 件 — PASS
- Copilot に何でも... in InputBar: 1 件 — PASS
