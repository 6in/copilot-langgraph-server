---
created: 2026-04-02T10:43:06.346Z
title: Auto-scroll to bottom on new message received
area: ui
files:
  - frontend/src/components/MessageArea.tsx
---

## Problem

チャット画面でメッセージを送信し、AIの応答が届いた際に、メッセージリストが自動で最下部にスクロールされない。ユーザーが手動でスクロールする必要がある。

## Solution

`MessageArea.tsx`（または`useChat.ts`）で、新しいメッセージ（特にAI応答）が追加されたタイミングで、メッセージリストを末尾にスクロールする処理を実装する。`useEffect` + `ref.scrollToBottom()` または chatscope の `scrollBehavior` プロップを活用する。
