---
phase: 16-canvas-app
plan: "02"
subsystem: frontend
tags:
  - react
  - typescript
  - canvas
  - chat-ui
dependency_graph:
  requires:
    - "16-01"  # GET /api/canvas/gem + deployed filter backend
  provides:
    - CanvasChatApp component (left-right split chat + CanvasPane)
    - CanvasScreen component (Canvas App hub)
    - listCanvasApps / getCanvasGemId API functions
  affects:
    - frontend/src/api/client.ts
    - frontend/src/components/
tech_stack:
  added: []
  patterns:
    - drag-to-resize (col-resize, mousemove/mouseup on window)
    - useCanvas hook wired to useChat onCanvasResponse
    - gem_id thread isolation via useThreads(undefined, gemId)
key_files:
  created:
    - frontend/src/components/CanvasChatApp.tsx
    - frontend/src/components/CanvasScreen.tsx
  modified:
    - frontend/src/api/client.ts
decisions:
  - "CanvasPane drag handle delta 反転: 右から左へのドラッグで拡大するため、delta を反転して newWidth = max(MIN, startWidth - delta) で計算"
  - "useCanvas の setCanvasApp を useChat の onCanvasResponse に直接渡す — 中間ラッパー不要"
  - "initialThreadId 復元は useEffect ではなく ref + setTimeout(0) で初回のみ実行"
  - "CanvasPane の onClose は常時表示のため () => {} のダミーを渡す (Pitfall 4)"
metrics:
  duration: "5min"
  completed_date: "2026-04-07"
  tasks_completed: 3
  files_changed: 3
---

# Phase 16 Plan 02: CanvasChatApp + CanvasScreen フロントエンド実装 Summary

CanvasChatApp（左右分割チャット+CanvasPane 常時表示）と CanvasScreen（デプロイ済みアプリハブ）の 2 コンポーネントを新規作成し、client.ts に `listCanvasApps` / `getCanvasGemId` を追加した。

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | client.ts 拡張 — listCanvasApps / getCanvasGemId 追加 | 353214e | frontend/src/api/client.ts |
| 2 | CanvasChatApp 新規作成 — 左右分割チャット+Canvas | 44ed3ec | frontend/src/components/CanvasChatApp.tsx |
| 3 | CanvasScreen 新規作成 — Canvas App ハブ画面 | c257f8b | frontend/src/components/CanvasScreen.tsx |

## Key Implementation Details

### CanvasChatApp (D-01〜D-04, D-14, D-15, D-17)

- GemChatApp.tsx を参照実装として、CanvasPane を右側に常時表示するレイアウトを実装
- `handleCanvasDividerMouseDown`: 右パネルのドラッグリサイズ。delta を反転（右から左へドラッグで拡大）
- `useThreads(undefined, canvasGemId)`: gem_id によるスレッド分離（D-17）
- `useChat({ gemId: canvasGemId, onCanvasResponse: setCanvasApp })`: Canvas HTML 抽出ロジック（D-14）
- sidebarCollapsed 時の width を 32px（UI-SPEC 準拠、GemChatApp の 40px を修正）
- drag handle 幅を 4px（UI-SPEC 準拠、GemChatApp の 5px を修正）
- `canvasApp=null` のときプレースホルダー表示（D-02）
- `initialThreadId` を受け取り既存スレッドを復元（D-10）

### CanvasScreen (D-08〜D-11)

- `listCanvasApps(true)` で deployed=true のアプリのみ取得（D-08）
- SkeletonCard x3 ローディング表示（aria-busy="true"）
- 空状態: "まだデプロイ済みアプリがありません"
- CanvasAppCard クリックで `onStartChat(app.thread_id)` を呼び出し（D-10: 既存スレッド復元）
- CTA: "+ 新しいチャットを開始" ボタン（D-09）
- エラー表示: role="alert"（D-11）

### client.ts 拡張

- `listCanvasApps(deployed?)`: deployed パラメータなしで URL に `?deployed=` が付かない設計
- `getCanvasGemId()`: `/api/canvas/gem` から Canvas 専用 gem_id を取得

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] soft-reset で staging に残っていた削除差分が混入**

- **Found during:** Task 1 コミット時
- **Issue:** ブランチを `284c73f` にソフトリセットした際、`24223e5` 以降の削除差分（planning ファイル、テストファイル）が staging に残っており、Task 1 のコミットに誤って含まれた
- **Fix:** `02cfcda` で git show を使って `284c73f` から全ファイルを復元してコミット
- **Files modified:** `.planning/phases/16-canvas-app/*.md`, `tests/test_canvas_api.py`, `tests/test_canvas_gem.py`
- **Commit:** 02cfcda

## Known Stubs

なし。すべての API 呼び出しは実際のエンドポイントに接続済み。CanvasPane へのデータフローも完全に配線済み。

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: XSS | CanvasScreen.tsx | app.name を JSX テキストノードとして挿入 — React 自動エスケープ済み（T-16-08 mitigated） |

## Self-Check: PASSED

- FOUND: frontend/src/components/CanvasChatApp.tsx
- FOUND: frontend/src/components/CanvasScreen.tsx
- FOUND: .planning/phases/16-canvas-app/16-02-SUMMARY.md
- FOUND: commit 353214e (task1 — client.ts)
- FOUND: commit 44ed3ec (task2 — CanvasChatApp)
- FOUND: commit c257f8b (task3 — CanvasScreen)
