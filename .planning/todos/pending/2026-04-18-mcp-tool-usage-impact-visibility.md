---
created: 2026-04-18T00:00:00Z
updated: 2026-04-18T11:55:00Z
title: エージェント実行・MCP ツール利用の observability 基盤
area: api
files:
  - mcp_server/server.py
  - app/orchestrator/agent.py
  - app/orchestrator/codeact_agent.py
  - app/orchestrator/graph.py
  - app/orchestrator/tool_agent.py
  - app/jobs/handlers/iframe_rpc_handler.py
  - app/jobs/worker.py
  - docker-compose.yml
---

## Problem

エージェント実行と MCP ツール利用の両方について、**誰が・何を・どう処理したか**を追跡できる仕組みが未整備。現状は Python `logging` の JSON line を docker コンテナの stdout に流しているだけで、永続化・集約・可視化がない。

### 現状の可視化欠落

**エージェント実行トレース（今回の議論で判明）:**
- routing 決定ログは `logger.info(json.dumps({"event": "routing", ...}))` で出るが docker logs 限り
- LLM の思考トレース（ReAct ループの各ターン、reasoning tokens）は保存されていない — `BoundChatCopilot` は最終 AIMessage しか返さない
- ReAct の中間 messages は PostgreSQL checkpointer に入っているが、可視化する UI がない
- thread_id / correlation_id は埋まっているので trace 単位で grep は可能だが ephemeral

**MCP ツール呼び出し（元のスコープ）:**
1. ToolEnabledSubAgent（general-assistant）→ Worker → MCP サーバー（langchain-mcp-adapters）
2. CodeActSubAgent（codeact）→ Python sandbox → localhost:8001/internal/call_tool（HTTP 直接）
3. iframe RPC（Canvas JS）→ Worker → ctx["mcp_tools"]

把握したいこと:
- どのエージェント/ユーザーがどのツールを何回呼んだか
- ツール実行の成功/失敗率
- 影響範囲（DB 書き込み、外部 API 呼び出し等）
- privileged ツールの利用状況

## Solution

**2 軸で observability 基盤を整える:**

### 軸 A: エージェント実行トレース

- 各ジョブ（thread_id + correlation_id）のタイムラインを構造化記録
  - routing 決定（stage / chosen / candidates）
  - SubAgent 呼び出し（入力 / 出力 / duration）
  - ReAct ループの各 turn（messages の差分）
  - エラー / fallback
- スレッド単位で実行トレースを閲覧できる admin UI
- OpenTelemetry 互換のトレース出力を検討（Jaeger / Tempo / Grafana）

### 軸 B: MCP ツール監査ログ

- audit_log テーブル（PostgreSQL）にツール呼び出しを記録
  - user_id / agent_name / tool_name / args（redact） / result_size / success / duration / timestamp
- `/internal/call_tool` エンドポイントと ToolEnabledSubAgent の両経路でログを取る
- iframe RPC 経路もカバー（ctx["mcp_tools"] 呼び出しをラップ）
- ツール利用統計 API / ダッシュボード
- privileged ツール（sandbox_exposed=false や claude_code）の利用はアラート

### 軸 AB 共通

- docker logs からの永続化（最低限 Loki / OpenSearch / file log rotation）
- thread_id / correlation_id / user_id / app_id を全レコードに埋める（既に一部対応済み）

## 議論したい論点

1. **OpenTelemetry 導入の是非** — 社内 200 名規模で OTEL Collector + Tempo/Jaeger を入れるか、PostgreSQL の audit_log テーブルで十分か
2. **トレースの粒度** — ReAct の各 turn まで記録するとストレージ肥大。どこで切るか
3. **LLM reasoning tokens** — Copilot SDK が thinking token を露出していない場合、`ChatCopilot._agenerate()` で追加情報を log として吐く余地はあるか
4. **UI 統合** — 既存の React チャット UI にトレース表示を載せるか、別の admin 画面を作るか
5. **PII / 機密情報の redact** — ツール args やメッセージ本文のどこまでを audit_log に残すか

## 関連する ADR・パターン

- ADR 0024: MCP ツールカタログ検証 — sandbox_exposed フラグで privileged 判定
- ADR 0041: CodeAct 直接実行方式 — `/internal/call_tool` 経路の存在
- `app/orchestrator/graph.py` の既存 routing ログ（event: routing / routing_fallback）

## Notes

- 2026-04-18: 元は MCP ツール利用のみのスコープだったが、`/gsd:check-todos` でログ出力先を調べる過程で「エージェント実行トレース全体」に拡張。旧タイトル「MCP ツールの利用と影響範囲を把握できる仕組みを考える」。
