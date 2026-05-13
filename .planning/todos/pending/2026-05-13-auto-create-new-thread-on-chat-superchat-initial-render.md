---
created: 2026-05-13T13:55:00Z
title: Chat/SuperChat 初回表示時に「新しいチャット」と同じ初期化を自動実行
area: ui
files:
  - frontend/src/components/ChatApp.tsx:60-69,161-165
  - frontend/src/components/SuperChatApp.tsx:141,196-199
  - frontend/src/hooks/useThreads.ts:60-66
  - frontend/src/components/ThreadSidebar.tsx:207,221
---

## Problem

`/chat` または `/superchat/{appSlug}` を最初に開いたとき、スレッド ID が URL に無い状態 (`urlThreadId === undefined`) で「中ぶらりん」になる。

- `useThreads` の `activeThreadId` が null のまま
- メッセージリストは空、入力欄は表示
- ユーザーが最初の発言を送るまで thread は作られない (`handleSend` 内で必要に応じて `createNewThread`)
- 結果として、ThreadSidebar の **「+ 新しいチャット」ボタンをクリックしたのと同じ状態** にしておくのが本来期待される UX

参照:
- ChatApp `handleNewChat` (`ChatApp.tsx:161-165`): `createNewThread()` → `navigate('/chat/${tid}', { replace: true })`
- SuperChatApp `handleNewChat` (`SuperChatApp.tsx:196-199`): `createNewThread()` → `navigate('/superchat/${appSlug}/${tid}', { replace: true })`
- 現状の初回表示 useEffect (`ChatApp.tsx:60-69`): URL `threadId` が undefined の場合は activeThreadId を **クリアしない** だけで、新規作成はしない
- ThreadSidebar の新規ボタンの場所 (`ThreadSidebar.tsx:207, 221`)

## Solution

TBD。検討案:

1. **マウント時の useEffect で `urlThreadId === undefined && activeThreadId === null` を検知 → `handleNewChat` を自動呼び出し** (推奨、最小変更)
   - 連続スレッド作成の防止: dependency array に注意 (`activeThreadId` を依存に入れすぎると無限ループ)
   - スレッド作成 in flight フラグ (`useRef<boolean>(false)`) で 2 重発火防止
2. URL を `/chat` でアクセス → backend 側 redirect で新規スレッド URL を返す
3. ThreadSidebar 表示時にスレッド一覧が空なら自動で「新しいチャット」相当の処理 — ただし「過去スレッドが残っているが選んでいない初回表示」のケースを拾えない

考慮事項:
- Phase 25 React Router で URL が single source of truth に統一済み (Pitfall 5)。URL が無いまま activeThreadId だけセットすると state 不整合になるので、必ず `createNewThread` → `navigate(replace: true)` の順
- GemChat / CanvasChat / Debate にも同様の問題があるかは未確認 (本 todo は Chat/SuperChat のみ scope)
- 「過去スレッドを開いている状態でブラウザバック → /chat に戻った」場合の挙動も注意 (履歴汚染しないよう `replace: true` 必須)

関連:
- 既存 todo に同等の項目なし
- Phase 25 (URL routing) / Phase 39 UIFIX 範囲外
