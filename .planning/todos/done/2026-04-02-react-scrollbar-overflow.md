---
created: 2026-04-02T01:14:46.864Z
title: React版ページ全体に余分な高さが付きスクロールバーが出る
area: ui
files:
  - frontend/src/components/ChatApp.tsx
  - frontend/src/App.tsx
  - frontend/src/main.tsx
---

## Problem

React版のページ全体に約10px程度の余分な高さが付与されており、
ブラウザのスクロールバーが表示されてしまう。
原因は `body` や `html` のデフォルト margin/padding、または
chatscope の MainContainer 外側のラッパー要素の高さ計算ズレと思われる。

## Solution

`index.html` の `<body>` や `html` に `margin: 0; padding: 0; overflow: hidden` を設定するか、
`main.tsx` / `App.tsx` のルート div で `height: 100vh; overflow: hidden` を徹底する。
ブラウザデフォルトの body margin (通常8px) が原因の可能性が高い。
