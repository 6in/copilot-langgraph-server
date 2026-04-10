---
phase: 20-fastmcp-docker
plan: 02
subsystem: docker-mcp-integration
tags: [docker-compose, mcp, langchain-mcp-adapters, healthcheck]
dependency_graph:
  requires: [20-fastmcp-docker/01]
  provides: [docker-compose.yml mcp-server service, scripts/test_mcp_tools.py]
  affects: [Phase 21 bind_tools integration]
tech_stack:
  added: [langchain-mcp-adapters>=0.2.2]
  patterns: [MultiServerMCPClient streamable_http, Docker healthcheck, service_healthy depends_on]
key_files:
  modified:
    - docker-compose.yml (mcp-server サービス追加、worker depends_on + MCP_SERVER_URL)
    - pyproject.toml (langchain-mcp-adapters>=0.2.2 追加)
    - uv.lock
  created:
    - scripts/test_mcp_tools.py
decisions:
  - "verify_mcp_worker.py は worktree 消失により欠落。test_mcp_tools.py が同等機能を提供"
  - "mcp-server はホストポート非公開 (D-06) — ポート 8001 は Docker 内部ネットワークのみ"
metrics:
  duration: "-"
  completed: "2026-04-10"
  tasks: 3
  files: 3
---

# Phase 20 Plan 02: Docker MCP 統合 Summary

`mcp_server/` を docker-compose に組み込み、worker コンテナから `MultiServerMCPClient`（streamable_http）経由で 4 スタブツールを呼び出せることを実機で検証。全 UAT チェック PASS。

## What Was Built

- **`docker-compose.yml`**: `mcp-server` サービス追加（FastMCP 3.x、`/health` ヘルスチェック、ホストポート非公開）
- **worker 設定**: `depends_on: mcp-server: condition: service_healthy` + `MCP_SERVER_URL=http://mcp-server:8001` 環境変数
- **`pyproject.toml`**: `langchain-mcp-adapters>=0.2.2` を root 依存に追加
- **`scripts/test_mcp_tools.py`**: worker 内から全 4 ツールを呼び出す検証スクリプト

## UAT Results

| # | 確認項目 | 結果 |
|---|---------|------|
| 1 | mcp-server: Up (healthy) / worker: Up | PASS |
| 2 | mcp-server ログ — uvicorn 正常、エラーなし | PASS |
| 3 | 4 ツール呼び出し成功 (ping / web_search_stub / db_query_stub / claude_code_stub) | PASS |
| 4 | ホストポート 8001 非公開（connection refused） | PASS |
| 5 | 既存チャット機能の非退行 | PASS (ブラウザ確認済み) |

## Tool Call Output

```
取得済みツール: ['claude_code_stub', 'db_query_stub', 'ping', 'web_search_stub']
✓ ping()                         → {"status":"ok","timestamp":"..."}
✓ web_search_stub(query=...)     → [stub] Search results for: ...
✓ db_query_stub(sql=...)         → [{"id":1,"stub":true,...}]
✓ claude_code_stub(command=...)  → [stub] Executed: ls -la\nOutput: stub response
結果: 4/4 成功
```

## Deviations from Plan

- `scripts/verify_mcp_worker.py` が worktree 消失により欠落。`scripts/test_mcp_tools.py` が同等機能を代替し UAT をカバー。

## Self-Check: PASSED

- [x] mcp-server コンテナが healthy 状態で起動
- [x] worker が mcp-server の healthcheck 完了後に起動
- [x] MCP_SERVER_URL=http://mcp-server:8001 が worker 環境変数に設定
- [x] 4 スタブツールが LangChain BaseTool として返る
- [x] langchain-mcp-adapters>=0.2.2 が root pyproject.toml に追加
- [x] mcp-server ホストポート非公開 (D-06)
