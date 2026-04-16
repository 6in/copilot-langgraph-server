---
created: 2026-04-16T10:20:09.645Z
title: SuperChat の過去のチャットメッセージ送信機能を追加
area: ui
files:
  - frontend/src/components/SuperChatApp.tsx
  - frontend/src/components/MessageArea.tsx
  - frontend/src/hooks/useChat.ts
  - app/orchestrator/graph.py
---

## Problem

SuperChat で過去のチャットメッセージ（ユーザー発言）を再送信する手段がない。長いプロンプトを微修正して再実行したい場合、手動でコピー＆ペーストする必要がある。通常チャットアプリでは「メッセージを編集して再送信」や「メッセージをクリックして入力欄にコピー」といった機能が一般的。

## Solution

過去のユーザーメッセージをクリックまたはアクションメニューから入力欄にセットし、再送信できる機能を追加する。

### 優先実装（#10 自動サマリモードより先に実装）

- メッセージ上のアクション（コピー / 再送信）ボタン
- 再送信時は入力欄にテキストをセットし、ユーザーが編集可能な状態にする
- 送信確定はユーザー操作（自動送信しない）

### 関連

- TODO #10（SuperChat 自動サマリモード）と併用することで、過去の文脈を保ったまま再送信が可能になる
