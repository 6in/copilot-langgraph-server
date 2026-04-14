---
created: 2026-04-14T00:00:00.000Z
title: CanvasScreen ホーム画面にインクリメンタルサーチを追加
area: ui
files:
  - frontend/src/components/CanvasScreen.tsx
---

## Problem

Canvas アプリのホーム画面（CanvasScreen）にはアプリ一覧が表示されるが、アプリ数が増えると目的のアプリを探すのが困難になる。現状は検索・フィルタリング機能がなく、スクロールして目視で探すしかない。

## Solution

CanvasScreen にインクリメンタルサーチバーを追加する:

1. テキスト入力欄（検索バー）をアプリ一覧の上部に配置
2. 入力のたびにリアルタイムでアプリ名をフィルタリング表示（`useState` + `filter()`）
3. 検索対象: アプリ名（`app.name`）、必要に応じて説明文も対象に
4. 検索文字列が空の場合は全件表示

実装はシンプルな controlled input + Array.filter で十分。外部ライブラリ不要。
