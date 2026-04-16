---
created: 2026-04-17T00:00:00.000Z
title: AskUserQuestion の実装
area: ui
files:
  - work/uaw/AskUserQuestion.jsx
  - work/uaw/Chat.jsx
  - work/uaw/system_prompt_auq.md
---

## Problem

AI エージェントがユーザーに質問を投げかける（選択肢提示・確認要求）インタラクションパターンが未実装。現状はエージェントからの一方向応答のみで、対話的なワークフロー（例: 曖昧な指示の明確化、複数案からの選択）に対応できない。

## Solution

`work/uaw/` に実装方針とサンプルコードが既にある:

- `AskUserQuestion.jsx` — 質問 UI コンポーネント
- `Chat.jsx` — チャット統合部分
- `system_prompt_auq.md` — エージェントに AskUserQuestion を使わせるためのシステムプロンプト設計

これらを参考に本プロジェクトのチャット UI + バックエンドに組み込む。
