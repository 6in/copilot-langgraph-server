# Phase 20: FastMCP Docker サービス基盤 - Context

**Gathered:** 2026-04-10
**Status:** Ready for planning

<domain>
## Phase Boundary

mcp-server を Docker サービスとして追加し、worker コンテナから streamable-http で接続確認できる基盤を作る。
スタブツール群（ping / web_search_stub / db_query_stub / claude_code_stub）が LangChain `BaseTool` リストとして取得でき、`/health` エンドポイントが 200 OK を返せば完了。

ツールの本番実装（Tavily 連携、DB クエリ、Claude Code 実行）は対象外。bind_tools + ToolNode 統合も Phase 21 以降。

</domain>

<decisions>
## Implementation Decisions

### コード配置
- **D-01:** top-level `mcp_server/` ディレクトリに FastMCP アプリを配置する（`app/` とは完全分離）
- **D-02:** 将来の独立リポジトリ分離・スケールアウトを見越した構造にする

### 依存管理
- **D-03:** `mcp_server/pyproject.toml` を独立した uv プロジェクトとして用意する（親の `pyproject.toml` とは別）
- **D-04:** ベースイメージは `ghcr.io/astral-sh/uv:python3.12-bookworm-slim`（他コンテナと同一、一貫性を保つ）

### Docker サービス構成
- **D-05:** docker-compose.yml に `mcp-server` サービスを追加する
- **D-06:** ホストポートは公開しない（`redis` と同様に内部ネットワーク専用）。worker からは `mcp-server:8001` でアクセス
- **D-07:** `worker` サービスが `mcp-server` に依存する（`depends_on`）

### HTTP トランスポート
- **D-08:** `streamable-http` トランスポートを使用する（FastMCP デフォルト、ROADMAP.md に明記済み）
- **D-09:** エンドポイントパスは `/mcp`（streamable-http 標準）

### スタブツール設計
- **D-10:** Phase 20 で用意するスタブツールは 4 つ: `ping` / `web_search_stub` / `db_query_stub` / `claude_code_stub`
- **D-11:** 各スタブは正しい引数スキーマ（名前・型・説明）を持ち、固定のモックレスポンスを返す
  - `ping` → `{"status": "ok", "timestamp": ...}`
  - `web_search_stub(query: str)` → 固定テキスト結果
  - `db_query_stub(sql: str)` → モック行データ
  - `claude_code_stub(command: str)` → 固定出力文字列
- **D-12:** 本番実装は各スタブを Phase 22/23 で差し替える設計（同名・同スキーマで上書き）

### ヘルスチェック
- **D-13:** `GET /health` → `{"status": "ok"}` を返す（Docker ヘルスチェック用）
- **D-14:** docker-compose の `healthcheck` で `/health` を確認し、`worker` が `mcp-server` を待つ

### Claude's Discretion
- FastMCP アプリのエントリポイントファイル名（例: `server.py` or `main.py`）
- `mcp_server/pyproject.toml` の具体的な依存バージョン（fastmcp, langchain-core 等）
- ツールモジュールの分割方法（単一ファイル vs tools/ ディレクトリ）

</decisions>

<specifics>
## Specific Ideas

- 将来の独立デプロイ・スケールアウトを見越した top-level 配置を明示的に選択した
- スタブは Phase 22/23 の本番実装と同名・同スキーマで上書き可能な設計にすること
- `MultiServerMCPClient.get_tools()` で取得した結果が LangChain `BaseTool` のリストであることを worker 側で検証すること

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### MCP 要件
- `.planning/REQUIREMENTS.md` § MCP サーバー基盤 — MCP-01, MCP-02 の受け入れ基準
- `.planning/ROADMAP.md` § Phase 20 — Goal / Success Criteria / Depends on

### Docker 構成参考
- `docker-compose.yml` — 既存サービス (postgres / redis / api / worker / frontend) の構成パターン

### 外部ドキュメント
- FastMCP 公式ドキュメント（https://gofastmcp.com）— streamable-http トランスポート、`@mcp.tool` デコレーター
- langchain-mcp-adapters（MultiServerMCPClient） — worker 側での MCP ツール取得パターン

No external ADRs — 要件は上記と decisions セクションで完結している。

</canonical_refs>

<code_context>
## Existing Code Insights

### Established Patterns
- **Docker サービス追加パターン**: `docker-compose.yml` の既存サービスは `uv:python3.12-bookworm-slim` + `uv run` コマンドで統一されている → mcp-server も同パターンに倣う
- **ヘルスチェックパターン**: postgres は `pg_isready`、redis は `service_started` → mcp-server は HTTP ヘルスチェック（`/health` エンドポイント）
- **内部ポート非公開**: redis はホストポート非公開（コメントあり）→ mcp-server も同様

### Integration Points
- `worker` コンテナが `MultiServerMCPClient` で `http://mcp-server:8001/mcp` に接続する
- `worker` の `docker-compose.yml` 定義に `depends_on: mcp-server: condition: service_healthy` を追加する
- `worker` の環境変数に `MCP_SERVER_URL=http://mcp-server:8001` を追加する

### Reusable Assets
- 既存の `app/` コードは mcp-server からは参照しない（独立サービス）

</code_context>

<deferred>
## Deferred Ideas

- **本番モード Docker Compose 整備** — Deferred (v5.1+) に明示的に記載済み。Phase 20 対象外。
- **config.yaml ツールルーティング (MCP-03)** — Phase 24 のスコープ
- **langchain-mcp-adapters の worker 側統合 (TOOL-01)** — Phase 21 のスコープ

</deferred>

---

*Phase: 20-fastmcp-docker*
*Context gathered: 2026-04-10*
