---
phase: 25
plan: 01
title: "React Router v6 URL ルーティング実装"
subsystem: frontend
tags: [react-router, url-routing, spa, browser-history]
dependency_graph:
  requires: []
  provides: [URL-01, URL-02, URL-03, URL-04, URL-05]
  affects: [frontend/src/App.tsx, frontend/src/main.tsx, frontend/src/components/ChatApp.tsx, frontend/src/components/SuperChatApp.tsx, frontend/src/components/GemChatApp.tsx, frontend/src/components/CanvasChatApp.tsx, frontend/src/components/DebateChatApp.tsx]
tech_stack:
  added: ["react-router ^7.14.0"]
  patterns: ["BrowserRouter basename", "useParams + switchThread 同期", "useNavigate URL 更新", "Route/Routes 宣言的ルーティング"]
key_files:
  created: []
  modified:
    - frontend/package.json
    - frontend/src/main.tsx
    - frontend/src/App.tsx
    - frontend/src/components/ChatApp.tsx
    - frontend/src/components/SuperChatApp.tsx
    - frontend/src/components/GemChatApp.tsx
    - frontend/src/components/CanvasChatApp.tsx
    - frontend/src/components/DebateChatApp.tsx
    - frontend/src/hooks/useChat.ts
    - docs/nginx.md
key_decisions:
  - "react-router v7.x(declarative mode)を採用 — v6 API 互換のため要件を満たす"
  - "import from 'react-router'のみ使用(react-router-dom は v7 で統合済み)"
  - "BrowserRouter basename は import.meta.env.BASE_URL の末尾スラッシュを除去して設定"
  - "CanvasChatApp の canvasGemId を内部取得に変更し App.tsx の state を廃止"
  - "URL を single source of truth: useParams → switchThread 同期パターンを全 ChatApp に適用"
metrics:
  duration: "約40分"
  completed: "2026-04-14"
  tasks_completed: 6
  files_modified: 10
---

# Phase 25, Plan 01: React Router v6 URL ルーティング実装 Summary

## One-liner

react-router v7.x declarative mode で `/{APP_PREFIX}/{appType}/{threadId?}` URL 構造を導入し、全 ChatApp でスレッド URL 共有・Back/Forward 対応を実現した。

## 追加された依存関係

| パッケージ | バージョン | 用途 |
|-----------|-----------|------|
| `react-router` | ^7.14.0 | BrowserRouter + Routes/Route + useParams/useNavigate |

`react-router-dom` は v7 で `react-router` に統合済みのため追加しない。

## 新しい URL 構造

| URL パターン | コンポーネント |
|-------------|--------------|
| `/orochi/` | MenuScreen |
| `/orochi/chat` | ChatApp（スレッドなし） |
| `/orochi/chat/:threadId` | ChatApp（スレッド指定） |
| `/orochi/superchat/:appSlug` | SuperChatApp（スレッドなし） |
| `/orochi/superchat/:appSlug/:threadId` | SuperChatApp（スレッド指定） |
| `/orochi/gems` | GemsScreen |
| `/orochi/gemchat/:gemId` | GemChatApp（スレッドなし） |
| `/orochi/gemchat/:gemId/:threadId` | GemChatApp（スレッド指定） |
| `/orochi/canvas` | CanvasScreen |
| `/orochi/canvaschat` | CanvasChatApp（スレッドなし） |
| `/orochi/canvaschat/:threadId` | CanvasChatApp（スレッド指定） |
| `/orochi/debate` | DebateChatApp（スレッドなし） |
| `/orochi/debate/:threadId` | DebateChatApp（スレッド指定） |
| `/orochi/*` | Navigate to `/` (メニューへフォールバック) |

## 各 ChatApp で導入した URL 同期パターン

```typescript
// 全 ChatApp 共通パターン
const { threadId: urlThreadId } = useParams<{ threadId?: string }>();
const navigate = useNavigate();

// URL → useThreads 同期
useEffect(() => {
  if (urlThreadId && urlThreadId !== activeThreadId) {
    switchThread(urlThreadId);
  }
}, [urlThreadId, activeThreadId, switchThread]);

// スレッド選択時の URL 更新
const handleSelectThread = (threadId: string) => {
  navigate(`/{appType}/${threadId}`);
};

// 新規スレッド作成時の URL 更新
const handleNewChat = async () => {
  const tid = await createNewThread();
  navigate(`/{appType}/${tid}`, { replace: true });
};
```

### CanvasChatApp の変更点

- `canvasGemId` と `initialThreadId` props を廃止
- マウント時に `getCanvasGemId()` を内部呼び出しで取得
- App.tsx の `canvasGemId` state と `handleOpenCanvasChat` を削除

### SuperChatWrapper / GemChatWrapper（App.tsx 内）

- URL の `appSlug`/`gemId` から非同期で `AppDefinition`/`GemInfo` を解決
- 解決中は `null` 返却（スピナー不要の短時間）
- 解決失敗時は `<Navigate to="/" replace />` でフォールバック

## nginx SPA fallback 設定

`docs/nginx.md` に追記済み。production nginx で deep URL が 404 にならないよう設定が必要:

```nginx
location /orochi/ {
  try_files $uri $uri/ /orochi/index.html;
}
```

開発環境（Vite dev server）は自動 fallback のため不要。

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] useChat.ts の既存 TypeScript 型エラーを修正**
- **Found during:** Task 25-04-01 の TypeScript ビルド確認
- **Issue 1:** `CanvasResult` に `name` プロパティがないが `c.name` で参照していた
- **Issue 2:** `CanvasAppInfo` に必須の `thread_label` フィールドが `onCanvasResponse` 呼び出し時に欠落していた
- **Fix:** `(parsed as { name?: string }).name ?? 'HTMLアプリ'` でアクセス、`thread_label: null` を追加
- **Files modified:** `frontend/src/hooks/useChat.ts`
- **Commit:** `24fd1c2`

**2. [Rule 3 - Blocking] Docker コンテナの bun 不在**
- **Found during:** Task 25-01-01 の bun add 実行時
- **Issue:** 既存の frontend コンテナが `oven/bun` ではなく Node.js イメージで動作していた（コンテナ未再ビルド）
- **Fix:** コンテナ内の `npm install` を使用して依存追加、worktree の `package.json` を直接編集
- **Impact:** 機能的には同等。bun.lockb は更新されないが package.json は正しく更新

## TypeScript ビルド結果

コンテナ内でビルド確認済み:
```
✓ 415 modules transformed.
✓ built in 404ms
```

変更ファイルに起因する TypeScript エラーはなし（useChat.ts の既存エラーは Rule 1 で修正済み）。

## Task 25-04-02 Status

ブラウザ手動確認（URL-01〜URL-11）は checkpoint:human-verify として保留。
TypeScript ビルドは成功済み。開発サーバー起動後にユーザーによる確認が必要。

## Self-Check: PASSED

| 確認項目 | 結果 |
|---------|------|
| frontend/package.json に react-router | FOUND |
| frontend/src/main.tsx に BrowserRouter | FOUND |
| frontend/src/App.tsx に Routes | FOUND |
| frontend/src/components/ChatApp.tsx に useParams | FOUND |
| docs/nginx.md に try_files | FOUND |
| コミット b0b46ac | FOUND |
| コミット 78e2087 | FOUND |
| コミット 866b5c6 | FOUND |
| コミット 4d5f55f | FOUND |
| コミット 233e70a | FOUND |
| コミット 5852815 | FOUND |
| コミット 24fd1c2 | FOUND |
| TypeScript ビルド | PASSED (415 modules, no errors) |
