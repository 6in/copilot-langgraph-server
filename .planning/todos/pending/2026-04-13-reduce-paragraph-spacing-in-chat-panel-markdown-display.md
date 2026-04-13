---
created: 2026-04-13T13:03:10.290Z
title: Chat パネルの Markdown パラグラフ間隔を詰める
area: ui
files:
  - frontend/src/components/MarkdownMessage.tsx
---

## Problem

Chat パネルの Markdown 表示において、パラグラフ（`<p>` タグ）間のマージンが大きく、メッセージ全体が間延びした印象になっている。特に箇条書きや短い段落が続く場合に視認性が低下する。

## Solution

`MarkdownMessage.tsx` で適用している CSS（またはインラインスタイル）の `p` セレクタの `margin-bottom` / `margin-top` を縮小する。
`@chatscope/chat-ui-kit-react` のデフォルトスタイルを上書きしている箇所があれば合わせて調整する。
目安: `margin-bottom: 0.4em` 程度まで削減し、読みやすさを維持しながら間隔を圧縮する。
