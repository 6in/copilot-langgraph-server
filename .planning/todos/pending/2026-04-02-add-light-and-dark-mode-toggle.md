---
created: 2026-04-02T03:30:02.985Z
title: Add light and dark mode toggle
area: ui
files: []
---

## Problem

現状、UI のカラーテーマが固定されている。ユーザーの好みや環境に合わせてライトモード / ダークモードを切り替えられるようにしたい。

## Solution

- UI にテーマ切り替えボタン（トグル）を追加する
- 選択状態を `localStorage` に保存し、再読み込み後も維持する
- システムの `prefers-color-scheme` を初期値として参照する
- Vanilla JS 版・React 版の両方に対応する
