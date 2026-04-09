---
created: 2026-04-09T09:24:10.090Z
title: CanvasChat デプロイ時にチャットエリアへメッセージポスト
area: ui
files:
  - frontend/src/components/CanvasChatApp.tsx
---

## Problem

Canvas Chat でアプリをデプロイした後、次回同じチャットを開いたときにデプロイ済みの HTML を参照・再編集できない。
スレッド履歴には「デプロイしました」という情報が残らないため、どのバージョンの HTML がデプロイされたか追跡できない。

## Solution

デプロイ完了時にチャットエリアへメッセージとしてポストする。

- デプロイ成功後、チャットメッセージとして「デプロイ完了」通知を追加（デプロイ URL + HTML スニペットを含む）
- これにより LangGraph の MessagesState にデプロイ済み HTML が記録され、次回チャットを開いたときに最後にデプロイした HTML をコンテキストとして LLM に渡せる
- CanvasChatApp の deploy ハンドラ内でメッセージ追加処理を呼ぶ（POST /api/chat に system メッセージとして送るか、UI 上のメッセージリストに直接追加するか検討）
