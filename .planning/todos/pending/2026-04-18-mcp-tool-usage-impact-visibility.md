---
created: 2026-04-18T00:00:00Z
title: MCP ツールの利用と影響範囲を把握できる仕組みを考える
area: api
files:
  - mcp_server/server.py
  - app/orchestrator/agent.py
  - app/orchestrator/codeact_agent.py
  - app/jobs/handlers/iframe_rpc_handler.py
---

## Problem

MCP ツールの呼び出し経路が複数あり、どのエージェントがどのツールをどの頻度で使っているか、
影響範囲がどこまで及ぶかが把握しにくい。

現在の呼び出し経路:
1. ToolEnabledSubAgent（general-assistant）→ Worker → MCP サーバー（langchain-mcp-adapters）
2. CodeActSubAgent（codeact）→ Python sandbox → localhost:8001/internal/call_tool（HTTP 直接）
3. iframe RPC（Canvas JS）→ Worker → ctx["mcp_tools"]

把握したいこと:
- どのエージェント/ユーザーがどのツールを何回呼んだか
- ツール実行の成功/失敗率
- 影響範囲（DB 書き込み、外部 API 呼び出し等）
- privileged ツールの利用状況

## Solution

- 監査ログ（audit_log テーブル）にツール呼び出しを記録
- /internal/call_tool エンドポイントにログ追加
- ToolEnabledSubAgent のツール呼び出しにもログ追加
- ダッシュボードまたは API でツール利用統計を可視化
- privileged ツールの利用はアラート or 管理者通知
