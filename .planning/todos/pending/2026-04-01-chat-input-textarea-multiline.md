---
created: 2026-04-01T00:42:13.590Z
title: チャット入力エリアをテキストエリアに変更し改行・Ctrl+Enter送信を対応
area: ui
files: []
---

## Problem

現在のチャット入力欄は単一行の `<input type="text">` であり、改行を含むメッセージを入力できない。
また送信が Enter キーのみに紐付いており、複数行テキストの入力 UX として不十分。

具体的に欠けている機能:
- 複数行入力に対応した `<textarea>` への変更
- Enter キー単体では改行、Ctrl+Enter / Cmd+Enter で送信するキーバインド
- テキストエリアの高さを入力量に応じて自動伸縮させる（オプション）

## Solution

1. HTML の `<input type="text" id="user-input">` を `<textarea id="user-input">` に変更
2. CSS でテキストエリアのスタイルを調整（resize: none、min-height 等）
3. JS のキーダウンハンドラを修正:
   - `Enter` のみ → 改行（デフォルト動作を許可）
   - `Ctrl+Enter` / `Cmd+Enter`（Mac: `event.metaKey`）→ 送信処理を呼び出す
4. 既存の送信ボタンクリックは引き続き動作させる
