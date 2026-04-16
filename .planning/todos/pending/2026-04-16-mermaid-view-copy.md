---
created: 2026-04-16T10:10:00.000Z
title: Mermaid View モードの Copy ボタンで画像としてコピーされない
area: ui
files:
  - frontend/src/components/MermaidBlock.tsx
---

## Problem

MermaidBlock の View モードで Copy ボタンをクリックすると、描画されたダイアグラムが画像（PNG）としてクリップボードにコピーされず、Mermaid ソーステキストがコピーされる。

原因: mermaid が生成する SVG に `<foreignObject>`（絵文字・HTML テキスト）が含まれるため、`<img>` 経由で Canvas に描画すると taint される。`canvas.toBlob()` が失敗し、テキストコピーにフォールバックしている。

## Solution

検討中のアプローチ:
1. `html-to-image` / `dom-to-image-more` ライブラリを使い、DOM 要素を直接 PNG に変換（foreignObject 対応）
2. SVG から foreignObject を除去し、ネイティブ SVG `<text>` に変換してから Canvas 描画
3. `text/html` として SVG をクリップボードにコピー（リッチテキストエディタでは貼り付け可能）
4. サーバーサイドで puppeteer/playwright を使い SVG → PNG 変換（重い）
