# Phase 23: DB クエリ + Claude Code 実行ツール - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning

<domain>
## Phase Boundary

MCP サーバーの `db_query_stub` と `claude_code_stub` を本番実装に差し替える。
エージェントが PostgreSQL データを安全に SELECT 参照でき、Claude Code CLI をサブプロセスとして実行できる状態にする。

**スコープ外:** DB 書き込み（INSERT/UPDATE/DELETE）、Claude Code CLI のストリーミング応答、Canvas からの MCP ツール呼び出し（v5.1）

</domain>

<decisions>
## Implementation Decisions

### DB コネクション管理

- **D-01:** MCP サーバーが独自の psycopg 接続プールを保持する（worker の db_pools とは独立）
- **D-02:** 接続情報は `config/db_pools.yaml` を MCP サーバーと worker で共有する（docker-compose で volume マウント）
- **D-03:** `is_select_only` ガードは `app/jobs/handlers/iframe_rpc_handler.py` から移植・再利用する（既存の T-18-01 実装）

### claude_code インターフェース設計

- **D-04:** ツール引数は `prompt: str` と `cwd: str` の 2 つ。内部で `claude --print <prompt>` を `cwd` 配下で実行する
- **D-05:** 返り値は構造化レスポンス: `{"output": str, "exit_code": int, "truncated": bool, "file_path": str | None}`
- **D-06:** stdout は 4000 文字で切り捨て (`truncated=True`)。超過分はフルテキストを Docker volume 共有ディレクトリへ書き出し、`file_path` にパスを返す
- **D-07:** mcp-server と worker が共有できる Docker volume（例: `/shared/claude-code-outputs/`）を docker-compose.yml に追加する

### 環境変数サニタイズ

- **D-08:** 許可リスト方式を採用。claude サブプロセスに渡す環境変数は以下のみ:
  - `PATH`, `HOME`, `LANG`, `LC_ALL`, `TERM`
  - それ以外は一切引き継がない（CLAUDECODE, ANTHROPIC_API_KEY, DATABASE_URL 等を含む）
- **D-09:** `subprocess.run` または `asyncio.create_subprocess_exec` に `env=allowlist_env` を明示的に渡す

### タイムアウト・プロセス管理

- **D-10:** タイムアウトは 60 秒（CODE-03 要件）
- **D-11:** タイムアウト発生時は SIGTERM → 猶予 5 秒 → SIGKILL のエスカレーション方式でゾンビプロセスを防ぐ

### ツールファイル配置

- **D-12:** Phase 22 の `mcp_server/tools/web_search.py` と同一パターンで実装:
  - `mcp_server/tools/db_query.py` — `db_query` ツール本番実装
  - `mcp_server/tools/claude_code.py` — `claude_code` ツール本番実装
  - `mcp_server/server.py` に `register_tools` をインポートして登録（stubs の差し替え）

### Claude's Discretion

- psycopg プール初期化のライフサイクル管理方法（FastMCP の lifespan フック等）
- db_pools.yaml のパース方法（pyyaml or tomllib）
- claude CLI 実行可否チェック（起動時 `claude --version` 確認等）
- 共有 volume のパス名と docker-compose サービス名

</decisions>

<specifics>
## Specific Ideas

- `is_select_only` は既存実装（`iframe_rpc_handler.py`）をそのまま使う。独自再実装しない
- claude_code 出力ファイルはジョブ ID またはタイムスタンプでユニーク名にする（衝突防止）
- web_search.py のレスポンス形式（`{"results": [...], "formatted": "..."}` 構造）を参考にして一貫性を保つ

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### 既存実装（再利用対象）
- `app/jobs/handlers/iframe_rpc_handler.py` — `is_select_only` ガード実装（T-18-01）と psycopg pool 利用パターン
- `mcp_server/tools/web_search.py` — Phase 22 のツール実装パターン（register_tools, エラーハンドリング）
- `mcp_server/tools/stubs.py` — 差し替え対象のスタブ（同名・同スキーマで上書き）
- `mcp_server/server.py` — ツール登録方法（register_tools インポート）

### 設定ファイル
- `config/db_pools.yaml` — DB 接続設定（MCP サーバーが参照する）
- `docker-compose.yml` — mcp-server サービス定義・volume マウント追加対象

### 要件
- `.planning/REQUIREMENTS.md` — DB-01, DB-02, CODE-01, CODE-02, CODE-03

</canonical_refs>

<deferred>
## Deferred Ideas

- Canvas アプリからの MCP ツール呼び出し — v5.1 対象（Out of Scope）
- claude_code ツールのストリーミング応答 — Copilot SDK Technical Preview では未対応
- DB 書き込み権限のロールベース制御 — 将来の RLS 対応フェーズへ

</deferred>

---

*Phase: 23-db-claude-code*
*Context gathered: 2026-04-13*
