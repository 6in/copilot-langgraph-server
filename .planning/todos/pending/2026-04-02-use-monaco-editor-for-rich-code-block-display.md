---
created: 2026-04-02T09:48:02.733Z
title: コードブロックをMonacoエディタでリッチ表示（テーマ連動）
area: ui
files:
  - frontend/src/components/MarkdownMessage.tsx
---

## Problem

チャット画面でAIの応答にコードブロックが含まれる場合、横幅が見切れてしまい読みにくい。現在は `react-markdown` + `rehype-highlight` によるシンプルなシンタックスハイライトを使っているが、長い行のコードが切れてしまう問題がある。

## Solution

`@monaco-editor/react` を導入し、コードブロックのレンダリングを Monaco エディタに切り替える。

- `MarkdownMessage.tsx` のカスタム `code` レンダラーで、インラインコードと通常コードを判別
- ブロックコード（```lang ... ```）は Monaco Editor でレンダリング（読み取り専用、高さ自動調整）
- アプリのライト/ダークテーマに連動して Monaco テーマも切り替える（`vs` / `vs-dark`）
- 言語は ```lang の lang 部分から自動検出
