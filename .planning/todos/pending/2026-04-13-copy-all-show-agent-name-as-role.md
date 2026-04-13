---
created: 2026-04-13T15:21:56.357Z
title: Copy all でエージェント名をロールに表示する
area: ui
files:
  - frontend/src/components/MessageArea.tsx:67
  - frontend/src/types.ts:50-53
---

## Problem

チャット画面の「Copy all」ボタンでメッセージをMarkdownテーブルとしてコピーすると、
AI側のRoleが常に `Assistant` に統一されてしまう（`MessageArea.tsx:67`）。

SuperChatやDebateChatでは `ChatMessage.senderName` にエージェント名が入っている場合がある。
コピー結果でもエージェント名を表示したい。

## Solution

`MessageArea.tsx` の `CopyAllButton` 内の role 判定を以下のように変更する:

```ts
// 現在
const role = m.role === 'user' ? 'User' : 'Assistant';

// 変更後
const role = m.role === 'user' ? 'User' : (m.senderName ?? 'Assistant');
```

`senderName` は `ChatMessage` 型に既に定義済み（`types.ts:53`）。
