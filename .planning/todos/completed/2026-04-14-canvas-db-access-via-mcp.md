---
created: 2026-04-14T00:00:00.000Z
title: Canvas DB アクセスを MCP 経由に移行する検討
area: api
files:
  - mcp_server/tools/stubs.py
  - app/api/routes/iframe_rpc.py
  - app/jobs/handlers/iframe_rpc_handler.py
  - app/jobs/worker.py
---

## Problem

現在 Canvas アプリからの DB アクセスは `iframe_rpc_handler.py` が直接 PostgreSQL 接続プールを持って処理している。一方、Worker も別途 DB 接続プールを持っており、アプリ全体で DB 接続プールが複数箇所に分散している。

これにより:
- DB 接続プールの管理が分散して運用コストが上がる
- Canvas の DB アクセスロジックが iframe RPC ハンドラに直書きされており、他のエージェントから再利用できない
- MCP サーバー (`mcp_server/`) がすでに存在するのに Canvas だけ別経路を使っている設計不整合

## Solution

Canvas アプリからの DB アクセスを MCP ツール経由に移行する:

1. `mcp_server/tools/` に `db_query` ツールを本実装する（現在は `db_query_stub` として stub のみ）
2. Worker の `iframe_rpc_handler.py` から直接 DB アクセスを削除し、MCP クライアント経由で `db_query` を呼ぶように変更
3. DB 接続プールを MCP サーバー側に一本化する

**検討事項:**
- セキュリティ: MCP サーバーは内部ネットワーク専用（`mcp-server:8001`）のため、外部からの直接アクセスはない
- SQL インジェクション対策: 既存の `is_select_only()` チェック（`app/utils/sql_safety.py`）を MCP ツール側に移植
- 接続プール: Worker 側の接続プールが不要になれば `worker.startup()` の初期化が簡素化される
- 移行コスト: `iframe_rpc_handler.py` の変更範囲を見積もること（Phase 18/19 で実装済みのロジックに影響）
