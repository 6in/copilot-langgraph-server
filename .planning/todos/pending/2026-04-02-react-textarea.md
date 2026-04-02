---
created: 2026-04-02T01:14:46.864Z
title: React版チャット入力フィールドをtextareaに変更
area: ui
files:
  - frontend/src/components/MessageArea.tsx
---

## Problem

React版（chatscope）の MessageInput コンポーネントが単行の input になっており、
Vanilla JS 版の `<textarea>` と異なる。長いプロンプトを入力するとき不便。

## Solution

chatscope の `MessageInput` は `as` プロパティや `sendButton` 等をサポートしているが、
ネイティブの textarea に差し替えるか、chatscope の設定で複数行を有効にする。
`MessageInput` の `multiline` prop（もしくは相当する設定）を調べて対応する。
