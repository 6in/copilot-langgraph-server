---
created: 2026-04-18T00:00:00Z
title: チャット履歴クリック時に白画面 — ReactMarkdown に object が渡される
area: ui
files:
  - frontend/src/components/MarkdownMessage.tsx:397
  - frontend/src/components/MessageArea.tsx:294
  - app/api/routes/chat.py:402
---

## Problem

SuperChat でチャット履歴をクリックして表示しようとすると画面が真っ白になる。

エラー: `Uncaught Assertion: Unexpected value [object Object] for children prop, expected string`

ReactMarkdown の `children` prop に string ではなく object が渡されている。
LangGraph チェックポイントから復元されたメッセージの `content` が string ではなく
object（ToolMessage の content や AIMessage の structured content）の場合に発生。

CodeActSubAgent 導入後に顕在化 — チェックポイントに ToolMessage や
structured content が蓄積され、履歴ロード時に `_messages_to_response` が
`msg.content` をそのまま返すため。

## Solution

- `_messages_to_response()` (chat.py:402) で `msg.content` が string でない場合に `json.dumps()` or `str()` で変換
- または `MarkdownMessage` コンポーネントで content が string でない場合のガード追加
- ToolMessage は履歴表示から除外するか、整形して表示
