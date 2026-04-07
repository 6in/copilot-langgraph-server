---
created: 2026-04-07T14:51:15.531Z
title: Fix agent name and color in chat history
area: ui
files:
  - app/api/routes/chat.py:410-420
  - frontend/src/hooks/useThreads.ts
  - frontend/src/components/MessageArea.tsx
---

## Problem

チャット履歴（スレッド読み込み時）でエージェント名が表示されず、バルーンの色も変わっていない。

新規メッセージ送信時は `orchestrator_result` JSON を `useChat.ts` でパースして `senderName` を設定しているが、履歴ロード時は `chat.py` の `/api/threads/{id}/messages` エンドポイントが LangGraph チェックポイントから `AIMessage.name` を読んで `senderName` を返す仕組み。

`agent.py` で `AIMessage(name=self.name)` を設定したのは今回の修正以降のメッセージのみ。それ以前の履歴はすべて `name=None` のため表示されない。

## Solution

1. `chat.py` の `/api/threads/{id}/messages`: `msg.name` で `senderName` を設定する処理は実装済み（line ~415）。新規メッセージは自動的に反映されるはずだが、動作確認が必要。
2. 既存履歴（修正前のメッセージ）への対応は不要（遡及修正は現実的ではない）。
3. 履歴ロード後に `senderName` が正しく `ChatMessage` に含まれているか `useThreads.ts` / `useChat.ts` のマッピングを確認する。
4. `MessageArea.tsx` の色付きバブルは `senderName` があれば自動適用されるので、源泉は 3 の解決で十分なはず。
