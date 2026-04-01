---
created: 2026-04-01T00:42:13.590Z
title: チャット履歴の削除ボタンの追加
area: ui
files: []
---

## Problem

現在のチャット UI にはスレッド（会話履歴）を削除する手段がない。
不要になったスレッドを整理できず、SQLite の checkpoint データが蓄積し続ける。

具体的に欠けている機能:
- スレッド一覧 or チャット画面上の「削除」ボタン
- バックエンドの DELETE エンドポイント（`DELETE /threads/{thread_id}`）
- SQLite checkpointer からの対象スレッドデータ削除

## Solution

TBD — 以下のアプローチが考えられる:

1. Web UI のスレッド一覧に削除ボタンを追加
2. FastAPI に `DELETE /threads/{thread_id}` エンドポイントを実装
3. `AsyncSqliteSaver` のチェックポイントを対象 `thread_id` で削除
4. 削除後はスレッド一覧を再取得してUIを更新
