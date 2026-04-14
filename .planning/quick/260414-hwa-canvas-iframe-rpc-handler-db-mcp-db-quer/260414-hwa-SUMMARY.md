# Quick Task 260414-hwa: Summary

**Description:** Canvas iframe_rpc_handler の DB アクセスを MCP db_query ツール経由に移行する
**Date:** 2026-04-14
**Commit:** 402bfa7

## What Changed

### app/jobs/handlers/iframe_rpc_handler.py
- `_handle_query` を psycopg 直接アクセスから MCP `db_query` ツール呼び出しに置き換え
- `is_select_only` 関数・`_COMMENT_RE`・`_ALLOWED_PREFIXES` を削除（MCP サーバー側に集約）
- `from psycopg.rows import dict_row` import を削除
- DEGRADED 時（`ctx["mcp_tools"]` に db_query なし）は明示的なエラーを返す

### tests/test_iframe_rpc_handler.py
- `is_select_only` の import・parametrized テストを削除
- `_make_ctx` を MCP ツール mock ベースに書き換え
- `_handle_query` テストを新実装（MCP 経由）に追従

## Results

- ユニットテスト: 8 tests passed
- 静的検査: `psycopg`・`dict_row`・`is_select_only` 参照ゼロ
- Smoke test: Worker の MCP tools に `db_query` が含まれることを確認 (`['ping', 'get_current_datetime', 'web_search', 'db_query', 'claude_code']`)

## Architecture Impact

- DB 接続プールが MCP サーバー側に一本化（Worker の `db_pools` は残存、他用途のため）
- SQL 安全性ガード (SELECT-only) の正実装が `mcp_server/tools/db_query.py` に統一
- Canvas iframe QUERY の経路: `IframeRpcHandler → ctx["mcp_tools"]["db_query"] → MCP server → PostgreSQL`
