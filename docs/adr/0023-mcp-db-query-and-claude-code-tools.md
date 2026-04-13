# 0023. MCP ツール本番実装 — db_query（SELECT-only ガード）と claude_code（サブプロセス + env sanitization）

**Date:** 2026-04-13  
**Status:** Accepted

## Context

Phase 20–22 で FastMCP サーバー基盤と web_search ツールが整い、エージェントがリアルタイム情報を取得できるようになった。次のニーズは「データベースの参照」と「Claude Code CLI の実行」であり、それぞれ異なるセキュリティリスクを持つ。

- **db_query**: エージェントが PostgreSQL を読めると便利だが、INSERT/UPDATE/DELETE を許すと社内データを破壊できる。
- **claude_code**: Claude Code CLI をサブプロセスとして実行すると強力だが、呼び出し元の環境変数（`CLAUDECODE=1`、`ANTHROPIC_API_KEY` など）を子プロセスに継承させると再帰呼び出しや認証情報漏洩が起きる。

また、mcp_server コンテナは Python slim ベースで libpq を持たない環境であり、claude CLI を動かすには Node.js が必要で、どちらも依存管理に工夫が必要だった。

## Decision

### db_query ツール

- `is_select_only()` 関数で SQL を字句解析し、SELECT / WITH 始まりのみ通過させる。コメント除去・大文字正規化・複文検出（`;` セミコロン）を組み合わせる。
- 接続プールは `psycopg[pool,binary]` の `AsyncConnectionPool` を使用し、FastMCP の `lifespan` フックで open/close を管理する。接続設定は `config/db_pools.yaml` から `yaml.safe_load()` で読み込む。
- `psycopg[pool]`（C extension）ではなく `psycopg[pool,binary]`（pure Python binary wheel）を使用する。mcp-server コンテナには libpq が存在しないため binary wheel が必須。

### claude_code ツール

- `asyncio.create_subprocess_exec("claude", "--print", prompt, ...)` でサブプロセスを起動する。
- env sanitization: 子プロセスに渡す環境変数を `ALLOWED_ENV_KEYS = frozenset({"PATH", "HOME", "LANG", "LC_ALL", "TERM"})` に限定する。`os.environ` から allowlist に含まれるキーだけを抽出して渡す。
- タイムアウトエスカレーション: 60 秒で `asyncio.wait_for` タイムアウト → SIGTERM 送信 → 5 秒猶予 → SIGKILL → `await proc.wait()` でゾンビ回収。
- stdout が 4000 文字を超えた場合は切り捨て、超過分を `_save_overflow_output()` で共有ボリューム（`claude-code-outputs`）に書き出す。レスポンスには `file_path` として参照先を返す。

### Dockerfile / docker-compose

- Node.js は nodesource リポジトリ経由ではなく `nodejs.org/dist/` からバイナリを直接ダウンロードして `/usr/local` に展開する。
- `claude-code-outputs` named volume を mcp-server（RW）と worker（RO）の両方にマウントする。

## Alternatives Considered

### psycopg[pool]（C extension）の使用
`mcp_server/pyproject.toml` 初期実装では `psycopg[pool]>=3.3.0` としていたが、コンテナ起動時に `ImportError: no pq wrapper available` が発生した。mcp-server の Python slim イメージには `libpq-dev` が含まれないため、binary wheel（C extension 不要）が必要。`psycopg[pool,binary]` に変更して解決。

### register_tools 内ローカル関数として claude_code を定義
計画段階では `register_tools` の内部ネスト関数として `@mcp.tool` デコレータを付ける設計だったが、テストで `from tools.claude_code import claude_code` を使うと `ImportError` が発生する。モジュールレベルの async 関数として定義し、`register_tools` 内で `mcp.tool(claude_code)` として登録する方式に変更。

### nodesource リポジトリ経由の Node.js インストール
Dockerfile で `curl -fsSL https://deb.nodesource.com/setup_20.x | bash` を試みたが、arm64 環境でネットワーク競合が発生し 13 分以上かかっても完了しなかった。`nodejs.org` から arm64 バイナリを直接ダウンロードする方式に切り替えることで安定した。

### コメント・複文を使った SQL インジェクション回避
`is_select_only()` は `--` / `/* */` コメントを除去したうえで先頭トークンを確認するため、`-- SELECT \n INSERT INTO` のような迂回を防ぐ。ただし CTE（`WITH ... INSERT INTO SELECT`）を使ったデータ書き込みは現時点では検出できない既知の穴であり、社内限定・低リスクとして ACCEPTED とした。

## Consequences

**ポジティブ:**
- エージェントが PostgreSQL を安全に参照できる（SELECT-only ガードをテスト 9 ケースで検証済み）。
- Claude Code CLI が MCP ツール経由で呼び出せる。env sanitization と timeout escalation により再帰呼び出し・ゾンビプロセスのリスクを低減。
- mcp-server の全ツール（ping / web_search / db_query / claude_code）が 25 テスト green で動作確認済み。

**注意点・落とし穴:**
- `psycopg[pool,binary]` は必須。`psycopg[pool]` に戻すと mcp-server コンテナが起動しない。
- `claude_code` 関数はモジュールレベルで定義する必要がある。`register_tools` 内のローカル関数として定義すると `import` できずテストが壊れる。
- Node.js インストールは `nodejs.org` バイナリ直接ダウンロード方式。nodesource は arm64 で不安定なため使わない。
- `CLAUDECODE=1` を環境変数に持つシェルから worker を起動すると、allowlist 外のため claude CLI サブプロセスには渡らない（意図した動作）。テスト `test_claude_code_env_sanitized` で assert 済み。
- `claude-code-outputs` volume は worker から read-only でマウントされる。worker が出力ファイルを書き込もうとすると権限エラーになる（mcp-server のみが書き込み可）。
