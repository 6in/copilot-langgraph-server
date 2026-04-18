// DO NOT EDIT — auto-generated from config/mcp_tools.yaml by scripts/generate_mcp_artifacts.py
// To regenerate: python3 scripts/generate_mcp_artifacts.py --target js

/**
 * Available MCP tools (auto-generated from config/mcp_tools.yaml).
 * Use `call(toolName, params)` to invoke.
 *
 * | Tool                 | Description                                                                                          |
 * | -------------------- | ---------------------------------------------------------------------------------------------------- |
 * | ping                 | MCP サーバーのヘルスチェック（疎通確認・タイムスタンプ取得）                                                                     |
 * | web_search           | Tavily 経由でリアルタイム Web 検索を実行（コンテキスト削減のため content は前処理済み）                                               |
 * | db_query             | PostgreSQL に対して SELECT クエリを実行（SELECT-only ガード付き、db_pools.yaml のプール名を指定可能）                            |
 * | claude_code          | Claude Code CLI をサブプロセスとして実行（env サニタイズ + 60 秒タイムアウト + 4000 文字切り詰め） [privileged]                      |
 * | execute_python       | Python コードをサンドボックス内で実行し stdout/stderr/exit_code を返す（AST allowlist + 512MB + 60 秒タイムアウト） [privileged] |
 * | get_current_datetime | 現在の日時を JST で返す（日付・時刻・曜日・タイムゾーン情報を含む dict）                                                            |
 */
export const AVAILABLE_TOOLS = [
  { name: "ping", description: "MCP サーバーのヘルスチェック（疎通確認・タイムスタンプ取得）" },
  { name: "web_search", description: "Tavily 経由でリアルタイム Web 検索を実行（コンテキスト削減のため content は前処理済み）" },
  { name: "db_query", description: "PostgreSQL に対して SELECT クエリを実行（SELECT-only ガード付き、db_pools.yaml のプール名を指定可能）" },
  { name: "claude_code", description: "Claude Code CLI をサブプロセスとして実行（env サニタイズ + 60 秒タイムアウト + 4000 文字切り詰め）", privileged: true },
  { name: "execute_python", description: "Python コードをサンドボックス内で実行し stdout/stderr/exit_code を返す（AST allowlist + 512MB + 60 秒タイムアウト）", privileged: true },
  { name: "get_current_datetime", description: "現在の日時を JST で返す（日付・時刻・曜日・タイムゾーン情報を含む dict）" },
];
