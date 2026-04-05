---
phase: 15-gem-canvas
plan: "04"
subsystem: frontend
tags: [canvas, gem, react, typescript]
requires: [15-02, 15-03]
provides: [CanvasPane, ChatApp-canvas-integration, MessageArea-GemSelector-integration, useChat-gem-id]
affects: [frontend/src/components/ChatApp.tsx, frontend/src/components/MessageArea.tsx, frontend/src/hooks/useChat.ts]
tech-stack:
  added: []
  patterns: [conditional-render, canvas-pane, gem-selector, iframe-sandbox]
key-files:
  created:
    - frontend/src/components/CanvasPane.tsx
  modified:
    - frontend/src/hooks/useChat.ts
    - frontend/src/components/ChatApp.tsx
    - frontend/src/components/MessageArea.tsx
decisions:
  - "iframe sandbox=allow-scripts allow-forms only (no allow-same-origin) — XSS 防止 T-15-08"
  - "GemSelector は cs-chat-container の外に配置 — chatscope スタイル干渉を回避 (W-2)"
  - "parseJobResult ヘルパーを useChat 内に定義 — Canvas JSON 検出をローカルに閉じ込め"
  - "handleResult ヘルパーで 3 つの完了パス（immediate/SSE/polling）を統一"
metrics:
  duration: 2min
  completed: "2026-04-05"
  tasks_completed: 2
  files_modified: 4
---

# Phase 15 Plan 04: CanvasPane + ChatApp Canvas Integration Summary

**One-liner:** CanvasPane コンポーネント（Editor/Preview タブ、Save Changes、Deploy）を実装し、ChatApp に Canvas ペインと GemSelector を統合、useChat に gem_id 送信と Canvas レスポンス検出を追加。

## Tasks Completed

| Task | Name | Commit | Status |
|------|------|--------|--------|
| 1 | CanvasPane + useChat Canvas 対応 + gem_id 送信 | 7b09a93 | Done |
| 2 | ChatApp + MessageArea 統合 | a88fa37 | Done |
| 3 | Gem + Canvas 統合動作確認 | — | Awaiting human verification |

## What Was Built

### CanvasPane.tsx (新規作成)

- 右側パネルコンポーネント: `minWidth: 320px`, `width: 40%`, `borderLeft: 1px solid #d1dbe3`
- ヘッダー: アプリ名（14px semibold）+ Deploy ボタン（#7c6ff7）+ Close ボタン（×）
- タブバー: Editor / Preview — `role="tab"`, `aria-selected`, `aria-controls`
- Editor タブ（`role="tabpanel"` id="canvas-editor-panel"）: monospace textarea + Save Changes ボタン（32px, border style）
- Preview タブ（`role="tabpanel"` id="canvas-preview-panel"）: `<iframe srcDoc sandbox="allow-scripts allow-forms" title="Canvas app preview">` — allow-same-origin なし（T-15-08）
- Deploy 結果: deployUrl → "Open app" リンク + "Copy URL" ボタン; deployError → `role="alert"` エラー表示
- Saving.../Deploying... ローディング状態、disabled 制御

### useChat.ts (修正)

- `UseChatOptions` に `gemId?: string | null` と `onCanvasResponse?: (app: CanvasAppInfo) => void` を追加
- `parseJobResult(raw)` ヘルパー: JSON.parse → `type === 'canvas'` を検出、それ以外はプレーンテキスト
- `handleResult` ヘルパー: immediate/SSE/polling の3つの完了パスを統一処理
- postChat 呼び出しに `gem_id: gemId` を追加（Gem 選択時のみ送信）
- `useCallback` deps に `gemId`, `onCanvasResponse` を追加

### ChatApp.tsx (修正)

- `CanvasPane`, `useCanvas` を import
- `selectedGemId` state（string | null）を追加
- `useCanvas()` hook を呼び出し（canvasApp, setCanvasApp, isSaving, isDeploying, deployUrl, deployError, saveCanvas, deployCanvas, dismissCanvas）
- `useChat` に `gemId: selectedGemId`, `onCanvasResponse: (app) => setCanvasApp(app)` を追加
- `canvasApp && <CanvasPane ...>` の条件付きレンダリングを MessageArea の隣に追加

### MessageArea.tsx (修正)

- `GemSelector` を import
- `MessageAreaProps` に `selectedGemId?: string | null`, `onSelectGem?: (gemId: string | null) => void` を追加
- ルート div ラッパーで囲み、`cs-chat-container` の外に `<GemSelector>` を配置（chatscope スタイル干渉を回避）

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — CanvasPane は useCanvas hook（Plan 03 実装済み）経由で実データを表示する。

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: iframe-xss | frontend/src/components/CanvasPane.tsx | T-15-08: sandbox に allow-same-origin を含めないことで軽減済み。grep 検証: `grep allow-same-origin` はコメント行のみ一致（属性には含まれない）。|

## Self-Check: PASSED

- CanvasPane.tsx: FOUND
- useChat.ts: FOUND
- ChatApp.tsx: FOUND
- MessageArea.tsx: FOUND
- Commit 7b09a93: FOUND
- Commit a88fa37: FOUND
