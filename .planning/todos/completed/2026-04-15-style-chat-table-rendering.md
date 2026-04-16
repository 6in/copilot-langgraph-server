---
created: 2026-04-15T14:14:00.000Z
title: チャットパネルのテーブル表示を CSS できれいに整える
area: ui
files:
  - frontend/src/components/MarkdownMessage.tsx
  - frontend/src/index.css
---

## Problem

チャットパネルで Markdown テーブル（`| col | col |` 形式）をレンダリングした際、デフォルトの HTML `<table>` がそのまま表示されており、罫線・余白・ヘッダー強調などが整っていない。長いセル内容やコード混在時の読みにくさが目立つ。

## Solution

`MarkdownMessage.tsx` がレンダリングする `<table>` / `<thead>` / `<tbody>` / `<th>` / `<td>` にスタイルを当てて、以下を満たす見た目にする:

- テーブル幅は親に対して 100%、はみ出す場合は横スクロール (`overflow-x: auto`)
- ヘッダー行は背景色・太字で視覚的に分離
- ゼブラ行（偶数行に薄い背景）で行追跡しやすく
- セルのパディング・ボーダーを統一
- ダークモードとの整合（`ThemeContext` / CSS 変数）
- 既存の Prose / Markdown スタイルと衝突しないようスコープを限定

アプローチ候補:

1. `index.css` に `.markdown-body table { ... }` を追加
2. react-markdown の `components={{ table: ..., th: ..., td: ... }}` でコンポーネント差し替え + CSS クラス付与
3. Tailwind 的なユーティリティは今のところ導入していないので、プレーン CSS で対応

動作確認は Chat / SuperChat / Gems / DebateChat それぞれでテーブル含む応答を表示して行う。
