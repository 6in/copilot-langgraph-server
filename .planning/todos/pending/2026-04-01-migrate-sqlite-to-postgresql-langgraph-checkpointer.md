---
created: 2026-04-01T08:45:37.319Z
title: 会話保存をSQLiteからPostgreSQLへ移行しLangGraphチェックポインターを活用する
area: database
files:
  - app/graph/builder.py
  - app/api/main.py
---

## Problem

現在の会話履歴は `langgraph-checkpoint-sqlite`（AsyncSqliteSaver）を使って SQLite ファイルに保存している。以下の課題がある:

- SQLite はシングルプロセス向けで、Worker を別プロセス化（フェーズ4の非同期アーキテクチャ）するとマルチプロセスからの同時書き込みで競合が起きやすい
- 将来的にマルチユーザー化・スケールアウトする際に PostgreSQL への移行が必要になる
- LangGraph の Checkpointer 機能を正しく使えば、メッセージ履歴管理を自前実装せずにフレームワークに任せられる

## Solution

- `langgraph-checkpoint-postgres`（または `langgraph-checkpoint-postgresql`）パッケージの `AsyncPostgresSaver` へ切り替える
- 接続先は Docker Compose で立ち上げた PostgreSQL コンテナを想定
- `AsyncSqliteSaver` → `AsyncPostgresSaver` に差し替えるだけでチェックポインター API は互換
- `thread_id` をキーとした会話履歴は LangGraph の `MessagesState` + Checkpointer が自動管理するため、`JobStore` 側で会話履歴を二重管理しないよう整理する
- マイグレーションツール（Alembic 等）は不要（LangGraph がスキーマを自動作成）
- 非同期アーキテクチャ移行（PoC の非同期イベント処理パターン todo）と合わせて実装するのが自然
