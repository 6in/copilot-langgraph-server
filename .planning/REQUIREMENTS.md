# Requirements: v5.0 Agent Tool Platform

**Milestone:** v5.0 Agent Tool Platform
**Created:** 2026-04-10

---

## v5.0 Requirements

### MCP サーバー基盤

- [ ] **MCP-01**: mcp-server が Docker サービスとして起動し、worker コンテナから HTTP 接続できる
- [ ] **MCP-02**: `@mcp.tool` でツールを定義し、スタブが正常に呼び出し・応答できる
- [ ] **MCP-03**: `config/mcp_tools.yaml` でツール名 → MCP メソッドのマッピングを管理できる

### LangGraph bind_tools 統合

- [ ] **TOOL-01**: OrchestratorGraph の SubAgent が `bind_tools` + `ToolNode` でツールを呼び出せる
- [ ] **TOOL-02**: tool_calls ループが最大 10 ステップで自動停止する
- [ ] **TOOL-03**: ツール呼び出し結果が `ToolMessage` として会話履歴に記録される

### Web 検索ツール

- [ ] **SEARCH-01**: エージェントが Web 検索を呼び出してリアルタイム情報を取得できる
- [ ] **SEARCH-02**: 検索結果が LLM が消化できるサイズに制限される

### DB クエリツール

- [ ] **DB-01**: エージェントが SELECT クエリで PostgreSQL のデータを取得できる
- [ ] **DB-02**: SELECT 以外のクエリ（INSERT/UPDATE/DELETE）はブロックされる

### Claude Code 実行ツール

- [ ] **CODE-01**: エージェントが Claude Code CLI をサブプロセスとして実行し結果を取得できる
- [ ] **CODE-02**: `CLAUDECODE=1` 等の危険な環境変数が引き継がれない
- [ ] **CODE-03**: タイムアウト（60秒）と zombie プロセス対策が実装される

---

## Future Requirements（v5.1+）

- Canvas アプリから MCP ツール呼び出し（FastAPI ブリッジ経由）
- 汎用 HTTP ツール（GitHub API, Slack API 等）
- RAG / ナレッジ検索（pgvector）
- 監査ログ DB 永続化
- エージェント管理 UI
- RETRY / 回復メカニズム

---

## Out of Scope (v5.0)

- 外部 MCP サーバーへの接続（Tavily 公式 MCP サーバー等）— 自前実装で統一
- Canvas アプリからのツール呼び出し — FastAPI ブリッジは v5.1
- ストリーミングツール応答 — Copilot SDK Technical Preview では未対応

---

## Traceability

| REQ-ID | Phase | Status |
|--------|-------|--------|
| MCP-01 | Phase 20 | Not started |
| MCP-02 | Phase 20 | Not started |
| MCP-03 | Phase 24 | Not started |
| TOOL-01 | Phase 21 | Not started |
| TOOL-02 | Phase 21 | Not started |
| TOOL-03 | Phase 21 | Not started |
| SEARCH-01 | Phase 22 | Not started |
| SEARCH-02 | Phase 22 | Not started |
| DB-01 | Phase 23 | Not started |
| DB-02 | Phase 23 | Not started |
| CODE-01 | Phase 23 | Not started |
| CODE-02 | Phase 23 | Not started |
| CODE-03 | Phase 23 | Not started |
