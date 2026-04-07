---
phase: "16-canvas-app"
plan: "03"
subsystem: "frontend"
tags: ["navigation", "canvas", "menu", "react", "typescript"]
dependency_graph:
  requires:
    - "16-01 (Canvas Gem auto-register + /api/canvas/gem endpoint)"
  provides:
    - "MenuScreen → CanvasScreen → CanvasChatApp ナビゲーションフロー"
    - "canvasGemId state + getCanvasGemId() 取得・キャッシュ"
  affects:
    - "frontend/src/App.tsx (Screen 型拡張)"
    - "frontend/src/components/MenuScreen.tsx (Canvas FeatureCard)"
tech_stack:
  added: []
  patterns:
    - "gems/gemchat と同じ handleOpen*/handleBackFrom* ナビゲーションパターン"
    - "canvasGemId null safety: canvaschat 画面を canvasGemId && 条件でガード"
key_files:
  created:
    - "frontend/src/components/CanvasScreen.tsx"
    - "frontend/src/components/CanvasChatApp.tsx"
  modified:
    - "frontend/src/App.tsx"
    - "frontend/src/components/MenuScreen.tsx"
    - "frontend/src/api/client.ts"
decisions:
  - "Rule 3 (blocking issue): Plan 02 の CanvasScreen/CanvasChatApp/client.ts 拡張がなければ App.tsx がコンパイルできないため、同一 worktree で先行実装した"
  - "canvasGemId が null のとき canvaschat 画面を表示しない（T-16-09 spoofing mitigation）"
  - "handleOpenCanvasChat は async — getCanvasGemId() 失敗時も canvaschat へ遷移許可（degraded state）"
  - "CanvasChatApp の sidebarCollapsed 時 width を 32px（GemChatApp の 40px から UI-SPEC に合わせて修正）"
  - "drag handle 幅を 4px（UI-SPEC 準拠、GemChatApp の 5px から修正）"
metrics:
  duration: "30min"
  completed_date: "2026-04-07"
  tasks_completed: 2
  files_changed: 5
---

# Phase 16 Plan 03: App.tsx ナビゲーション拡張 + Canvas エントリーポイント追加 Summary

MenuScreen に Canvas FeatureCard を追加し、App.tsx に `'canvas' | 'canvaschat'` Screen 型・canvasGemId state・ナビゲーションハンドラを実装して、MenuScreen → CanvasScreen → CanvasChatApp の完全な遷移フローを実現した。

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | MenuScreen Canvas FeatureCard + onOpenCanvas prop | 653ed62 | MenuScreen.tsx |
| 2 | App.tsx canvas/canvaschat navigation + CanvasScreen + CanvasChatApp | 9d22cad | App.tsx, client.ts, CanvasScreen.tsx, CanvasChatApp.tsx |

## What Was Built

### Task 1: MenuScreen 拡張（D-05, D-06, D-16）

- `MenuScreenProps` に `onOpenCanvas: () => void` を追加
- 関数シグネチャを更新してデストラクチャに `onOpenCanvas` を追加
- Gems カードと 討論チャットカードの間に Canvas FeatureCard を挿入（icon: 🎨、title: "Canvas"、description: "AI チャットで HTML アプリを作成・プレビュー・デプロイ"）

### Task 2: App.tsx 拡張（D-07）

- Screen 型に `'canvas' | 'canvaschat'` を追加
- `activeCanvasAppId` / `canvasGemId` state を追加
- `handleOpenCanvas` / `handleBackFromCanvas` / `handleOpenCanvasChat` (async) / `handleBackFromCanvasChat` ハンドラを追加
- MenuScreen に `onOpenCanvas={handleOpenCanvas}` を渡す
- `canvas` 画面: Header + CanvasScreen レンダリングブロックを追加
- `canvaschat` 画面: `canvasGemId &&` 条件付き Header + CanvasChatApp レンダリングブロックを追加（T-16-09 null safety）

### Rule 3 自動修正: Plan 02 の成果物を先行実装

Plan 02 と Plan 03 は同一 Wave 2 の並行エージェントだが、CanvasScreen.tsx・CanvasChatApp.tsx・client.ts 拡張が存在しないと App.tsx がコンパイルできないため、このworktreeで先行実装した。

- `frontend/src/api/client.ts`: `listCanvasApps(deployed?)` + `getCanvasGemId()` を追加
- `frontend/src/components/CanvasScreen.tsx`: デプロイ済みアプリ一覧 + 新規チャット CTA のハブ画面（D-08〜D-11）
- `frontend/src/components/CanvasChatApp.tsx`: 左右分割チャット + CanvasPane 常時表示（D-01〜D-04, D-14, D-15, D-17）

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Plan 02 の成果物をこのworktreeで先行実装**
- **Found during:** Task 2 開始時
- **Issue:** Plan 02 (Wave 2 並行) が未完了のため CanvasScreen.tsx・CanvasChatApp.tsx が存在せず、App.tsx がコンパイルできない
- **Fix:** CanvasScreen.tsx・CanvasChatApp.tsx を新規作成、client.ts に listCanvasApps/getCanvasGemId を追加
- **Files modified:** frontend/src/components/CanvasScreen.tsx (新規), frontend/src/components/CanvasChatApp.tsx (新規), frontend/src/api/client.ts
- **Commit:** 9d22cad

**2. [Rule 3 - Blocking] git reset --soft による staging area 汚染を修正**
- **Found during:** Task 1 コミット時
- **Issue:** worktree 初期化時の `git reset --soft` で別 worktree の変更が staging area に残っており、不要なファイルがコミットに含まれた
- **Fix:** `git reset --soft HEAD~1` でコミットを取り消し、`git restore --staged` で無関係ファイルをアンステージして再コミット
- **Files modified:** なし（コミット手順の修正のみ）

## Known Stubs

なし — CanvasScreen は `listCanvasApps(true)` で実データを取得、CanvasChatApp は `canvasGemId` (サーバーから取得した UUID) と `useCanvas()` フックで実際の状態管理を行っている。

## Threat Flags

なし — T-16-09 (canvasGemId null safety) は `canvasGemId &&` 条件でミティゲーション済み。

## Self-Check: PASSED

- FOUND: frontend/src/components/CanvasScreen.tsx
- FOUND: frontend/src/components/CanvasChatApp.tsx
- FOUND: 653ed62 (Task 1 commit)
- FOUND: 9d22cad (Task 2 commit)
- TypeScript コンパイル: エラーなし（tsc --noEmit exit 0）
