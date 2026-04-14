# 0030. Canvas DB アクセスを MCP db_query ツール経由に移行

**Date:** 2026-04-14  
**Status:** Accepted

## Context

Phase 18 で実装した Canvas iframe JSON-RPC ブリッジ（`IframeRpcHandler`）は、`QUERY` メソッドの処理に psycopg_pool の接続プールを直接保持していた。Worker の起動時にも別途 DB 接続プールを初期化しており、アプリ全体で DB 接続管理が複数箇所に分散していた。

具体的な問題：
- `iframe_rpc_handler.py` が psycopg_pool を直接インポートし、`ctx["db_pools"]` に依存
- SQL 安全性ガード（`is_select_only`）が `iframe_rpc_handler.py` と `mcp_server/tools/db_query.py` の2箇所に重複実装
- Phase 20/23 で MCP サーバー基盤と `db_query` ツールが整備されたにもかかわらず、Canvas だけが別経路を使い続けていた設計不整合

## Decision

`IframeRpcHandler._handle_query` から直接 DB アクセスを削除し、`ctx["mcp_tools"]` に格納された MCP `db_query` BaseTool を `ainvoke()` で呼び出す方式に切り替えた。

```python
tool = next((t for t in ctx.get("mcp_tools") or [] if t.name == "db_query"), None)
if tool is None:
    return {"result": False, "error": "db_query tool unavailable (MCP DEGRADED)"}
out = await tool.ainvoke({"sql": sql, "pool_name": pool_name})
```

Worker の `db_pools` 初期化コードは今回は温存（他コードへの影響を避けるため段階的移行）。

**langchain-mcp-adapters の返却形式への対応:**  
`tool.ainvoke()` は `dict` ではなく `[{"type": "text", "text": "{...}", "id": "..."}]` のリストを返す。`text` フィールドを JSON パースして `dict` に変換する処理が必要。

```python
if isinstance(out, list):
    text = next((item["text"] for item in out if item.get("type") == "text"), None)
    out = json.loads(text)
```

## Alternatives Considered

**案B: Worker の db_pools を完全廃止**  
`iframe_rpc_handler` の移行に加えて `worker.startup()` の DB プール初期化コードも削除する。より徹底した一本化だが、他のコードへの影響調査が必要なため今回は見送り。

**案C: is_select_only の共有化のみ**  
DB 接続プールはそのままに、`is_select_only` の重複だけを解消する最小変更。問題の根本（DB 接続分散）を解決しないため却下。

## Consequences

**ポジティブ:**
- SQL 安全性ガード（SELECT-only チェック）の正実装が MCP サーバー側に一本化
- Canvas の QUERY 経路が他のエージェントツールと同じ MCP 基盤を通る設計に統一
- `iframe_rpc_handler.py` から psycopg 直接依存がなくなり、ハンドラーが薄くなった

**ネガティブ / 注意点:**
- MCP サーバーが DEGRADED の場合、Canvas の QUERY も失敗する（以前は Worker 独自プールで独立動作していた）
- `tool.ainvoke()` の返却型が `dict` ではなく `list` であることは langchain-mcp-adapters のドキュメントに明記されていない。バージョンアップ時に形式が変わる可能性がある
- Worker の `db_pools` 初期化は残っているため、完全な接続一本化は未完了（TODO として残存）
