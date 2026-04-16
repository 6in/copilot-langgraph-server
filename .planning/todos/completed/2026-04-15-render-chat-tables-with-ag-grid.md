---
created: 2026-04-15T14:16:00.000Z
title: チャットパネルのテーブル表示を Ag-Grid で表示できるようにする
area: ui
files:
  - frontend/src/components/MarkdownMessage.tsx
  - frontend/package.json
---

## Problem

Markdown テーブルを素の `<table>` でレンダリングしていると、ソート・フィルタ・列リサイズ・大量行の仮想スクロールができない。SQL アナリストや分析系 SubAgent が返す結果を実運用レベルで扱うにはインタラクティブなグリッドが欲しい。

関連 todo: `2026-04-15-style-chat-table-rendering.md`（プレーン CSS でのスタイル改善）。本 todo はその上位互換的な位置づけ。

## Solution

react-markdown の `components.table` を差し替えて、テーブルを AG Grid Community (`ag-grid-react` + `ag-grid-community`) でレンダリングする。

検討ポイント:

- **採用バージョン**: AG Grid Community は MIT。Enterprise 機能（行グルーピング等）は使わない前提
- **トリガー条件**: すべてのテーブルを Ag-Grid 化するか、行数・列数が閾値を超えた場合のみ差し替えるか（軽量テーブルは CSS 版で十分なはず）
- **データ変換**: Markdown AST の `<thead>` / `<tbody>` / `<tr>` / `<td>` を `columnDefs` + `rowData` に変換するヘルパーを用意
- **スタイル**: `ag-theme-quartz`（ライト/ダーク両対応）を `ThemeContext` と連動させる
- **サイズ**: コンテナ幅に合わせて auto-fit、行数に応じて高さを決定（最大高さを設定してスクロール）
- **バンドル影響**: AG Grid は 400KB+ のため、`React.lazy` で遅延読み込み
- **フォールバック**: 読み込み失敗時はプレーンテーブルに fallback
- **コード/数値混在セル**: セルレンダラでコードブロック内容も表示できるようにする

依存関係:

```bash
cd frontend && bun add ag-grid-react ag-grid-community
```

検証: Chat / SuperChat / SQL Analyst の応答でテーブルが出るケースをブラウザで確認。
