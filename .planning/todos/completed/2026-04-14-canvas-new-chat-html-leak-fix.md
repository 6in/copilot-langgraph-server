---
created: 2026-04-14T00:00:00.000Z
title: CanvasChat New Chat 時に前回の HTML がプロンプトに漏れる不具合修正
area: ui
files:
  - frontend/src/components/CanvasChatApp.tsx
  - frontend/src/hooks/useChat.ts
---

## Problem

Canvas アプリで「New Chat」を押して新しいアプリを作成しようとすると、前のスレッドで最後に表示していた HTML がシステムプロンプト（またはユーザーメッセージ）として次のリクエストに渡されてしまう。

これにより:
- 新規チャットなのに「既存の HTML を改修する」指示として AI が解釈してしまう
- ユーザーは「ゼロから新しいアプリを作りたい」のに、前回の HTML を引き継いだ回答が返ってくる
- 期待する動作は「空の状態から新規作成」

## Solution

`CanvasChatApp.tsx` の New Chat ハンドラ（または `useChat.ts` のリセット処理）で、新規スレッド作成時に現在表示中の HTML をプロンプトコンテキストから除去する。

具体的には:
1. `createNewThread()` 呼び出し後に `currentHtml` state を空文字にリセットする
2. `handleSend` 内で HTML をプロンプトに埋め込む際、`activeThreadId` が新規（直前に作成された）スレッドの場合はスキップする
3. または `isNewThread` フラグを持ち、最初のメッセージ送信後にクリアする

根本原因の調査: `CanvasChatApp.tsx` の `handleSend` 内で `currentHtml` をプロンプトに append している箇所（Phase 260409-h78 で実装）を確認し、新規スレッドかどうかの判定を追加する。
