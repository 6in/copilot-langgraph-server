---
created: 2026-04-06T14:17:45.555Z
title: Gem チャットの入力エリアレイアウト修正 — スクロール不可・画面外表示を解消
area: ui
files:
  - frontend/src/components/GemChatApp.tsx
  - frontend/src/components/MessageArea.tsx
---

## Problem

Gem でのチャット画面にて、入力エリアがフローティング（固定下部）になっていないため、以下の問題が発生する:
1. メッセージリストがスクロールできない（入力欄が邪魔している可能性）
2. 入力エリアが画面外（ビューポート外）に押し出されて表示される

ChatApp / SuperChatApp では正常に動作しているため、GemChatApp 固有のレイアウト問題と思われる。

## Solution

`GemChatApp.tsx` のレイアウト構造を確認し、`MessageArea` を囲む flex コンテナに `minHeight: 0` / `overflow: hidden` が正しく設定されているか検証する。
07-RESEARCH.md の Pitfall 1（外側 div に明示的な height が必要）を参照し、ChatApp のレイアウト構造に揃える。
