---
created: 2026-04-16T03:20:00.000Z
title: チャット応答の Markdown 段落スペーシングを縮小
area: ui
files:
  - frontend/src/components/MarkdownMessage.tsx
  - frontend/src/theme.css
---

## Problem

チャットエリアに表示される AI 応答メッセージの Markdown HTML 展開で、段落（`<p>`）間のスペーシングが大きすぎる。見出し・リスト・段落の間隔が広く、1 画面に収まる情報量が少なくなり、スクロール量が増える。

参考画像: `work/image copy.png` — 「今週末の東京おすすめスポット」の応答で見出しと本文の間隔が目立つ。

## Solution

MarkdownMessage のコンポーネント差し替え or theme.css で段落間隔を縮小:

1. `MarkdownMessage.tsx` の `p` コンポーネントの `margin: '0 0 0.4em 0'` を `0 0 0.2em 0` 程度に調整
2. `h1`〜`h3` の上下マージンも react-markdown の components で override
3. `ul` / `ol` の margin-top / margin-bottom を詰める
4. chatscope の `.cs-message__custom-content` 内に限定してスタイルを適用（他の UI に影響しないよう）
5. 各チャットアプリ（Chat / SuperChat / Gems / Canvas / DebateChat）で表示確認
