---
created: 2026-04-06T01:45:03.984Z
title: GemChatApp チャット履歴を永続化する
area: ui
files:
  - frontend/src/components/GemChatApp.tsx
  - frontend/src/hooks/useChat.ts
  - app/api/routes/chat.py
---

## Problem

現在の GemChatApp はチャット画面を開き直すと履歴が消える（メモリのみ保持）。
`GemChatApp` は `useChat` フックを使っているが、スレッド管理が ChatApp / SuperChatApp と異なり、gem_id スコープのスレッドが永続化されていない可能性がある。
ユーザーが Gem チャットを再開できるよう、会話履歴が SQLite / PostgreSQL に保存・復元される必要がある。

## Solution

- `GemChatApp` でも `useThreads` を使い、`appId = gem.id`（または `gemchat`）でスレッドを作成・選択する
- バックエンド側で `gem_id` スコープのスレッド一覧が取得できることを確認する
- GemChatApp にサイドバー（またはスレッド選択 UI）を追加するか、前回のスレッドを自動ロードする設計を検討する
- `useChat` の `threadId` が永続スレッドを指すようにする
