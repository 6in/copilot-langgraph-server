---
created: 2026-04-16T03:45:00.000Z
title: Canvas Chat のテンプレートに AG Grid の利用コードを追加
area: ui
files:
  - static/apps/
  - app/orchestrator/apps.py
---

## Problem

Canvas Chat で AI が生成する HTML アプリ（Canvas アプリ）のテンプレートに AG Grid の使い方が含まれていない。AI がデータテーブルを含むアプリを生成する際、素の `<table>` で出力してしまい、ソート・フィルタ・セル選択などのインタラクティブ機能が使えない。

## Solution

Canvas アプリのテンプレート HTML / 生成指示に AG Grid Community (MIT) の CDN 読み込みと基本的な使い方を含める:

1. AG Grid の CDN リンクをテンプレートの `<head>` に追加
2. 基本的な grid 初期化コード（`createGrid` / `columnDefs` / `rowData`）のサンプルを含める
3. テーマ設定（`ag-theme-quartz` の light/dark 切り替え）
4. AI への system prompt に「テーブルデータを表示する場合は AG Grid を使え」という指示を追加

参考: チャットパネル側の `ChatAgGridTable.tsx` で使っているパターン（`themeQuartz.withParams`）を HTML 版に変換する形。
