---
created: 2026-04-14T00:00:00.000Z
title: アプリタイトルを "Copilot Chat" から "Orochi Chat" に変更
area: ui
files:
  - frontend/src/components/Header.tsx
  - frontend/src/components/MenuScreen.tsx
  - frontend/index.html
---

## Problem

アプリ全体のタイトルが "Copilot Chat" と表示されているが、社内名称として "Orochi Chat" に統一したい。

## Solution

以下のファイルで "Copilot Chat" を "Orochi Chat" に一括置換する:

- `frontend/src/components/Header.tsx` — ヘッダーのアプリ名表示
- `frontend/src/components/MenuScreen.tsx` — メニュー画面のタイトル
- `frontend/index.html` — `<title>` タグ

`grep -r "Copilot Chat"` で漏れがないか確認してから変更する。
`static/index.html`（Vanilla JS 版）にも同名称があれば合わせて変更する。
