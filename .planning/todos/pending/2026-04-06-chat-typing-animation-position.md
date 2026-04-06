---
created: 2026-04-06T14:17:45.555Z
title: chat 応答中のアニメーション表示を最後のメッセージの下に移動する
area: ui
files:
  - frontend/src/components/MessageArea.tsx
---

## Problem

チャットで AI が応答中に表示されるアニメーション（Typing Indicator 等）が、最後のメッセージの下ではなく別の位置に表示されており、UX 上不自然に見える。

## Solution

`MessageArea.tsx`（または関連コンポーネント）で、応答待ち中のアニメーション要素をメッセージリストの末尾（最後のユーザーメッセージの直下）に挿入するよう DOM 順序・スクロール挙動を調整する。
chatscope の `TypingIndicator` を使用している場合は配置オプションを確認し、必要に応じてカスタム実装に切り替える。
