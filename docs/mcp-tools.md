<!-- DO NOT EDIT — auto-generated from config/mcp_tools.yaml by scripts/generate_mcp_artifacts.py -->
<!-- To regenerate: python3 scripts/generate_mcp_artifacts.py --target docs -->

# MCP Tools Catalog

このドキュメントは `config/mcp_tools.yaml` から自動生成されます。ツールを追加・変更する場合は YAML を編集し、`python3 scripts/generate_mcp_artifacts.py --target all` を実行してください。

新規ツール追加手順は [docs/mcp-tool-add-manual.md](./mcp-tool-add-manual.md) を参照。

## ツール一覧

| Tool | Privileged | Sandbox Helper | Description |
| ---- | ---------- | -------------- | ----------- |
| `ping` | no | `mcp_helper.ping()` | MCP サーバーのヘルスチェック（疎通確認・タイムスタンプ取得） |
| `web_search` | no | `mcp_helper.search()` | Tavily 経由でリアルタイム Web 検索を実行（コンテキスト削減のため content は前処理済み） |
| `db_query` | no | `mcp_helper.query_db()` | PostgreSQL に対して SELECT クエリを実行（SELECT-only ガード付き、db_pools.yaml のプール名を指定可能） |
| `claude_code` | yes | — | Claude Code CLI をサブプロセスとして実行（env サニタイズ + 60 秒タイムアウト + 4000 文字切り詰め） |
| `execute_python` | yes | — | Python コードをサンドボックス内で実行し stdout/stderr/exit_code を返す（AST allowlist + 512MB + 60 秒タイムアウト） |
| `get_current_datetime` | no | `mcp_helper.get_datetime()` | 現在の日時を JST で返す（日付・時刻・曜日・タイムゾーン情報を含む dict） |
| `attachments_list` | no | `mcp_helper.list_attachments()` | 現在の thread に添付されたファイルの一覧 (名前・サイズ・更新日時・拡張子) を返す |
| `attachments_extract` | no | `mcp_helper.extract_attachment()` | 指定ファイル (PDF/docx/xlsx/pptx) のテキストを MarkItDown で抽出して返す (最大 50,000 文字、60 秒タイムアウト) |

## `ping`

MCP サーバーのヘルスチェック（疎通確認・タイムスタンプ取得）

**Sandbox Helper:** `def ping() -> dict`

```
MCP サーバーの疎通確認。呼び出しごとに現在時刻を返す。

Returns:
    {"status": "ok", "timestamp": "..."}

Example:
    from mcp_helper import ping
    r = ping()
    print(r["status"])
```

## `web_search`

Tavily 経由でリアルタイム Web 検索を実行（コンテキスト削減のため content は前処理済み）

**Sandbox Helper:** `def search(query: str) -> list[dict]`

```
Web 検索を実行する。

Args:
    query: 検索クエリ

Returns:
    [{"title": "...", "url": "...", "content": "..."}, ...]
    content は前処理済み（ナビ・フッター除去、最大15行）。
    エラー時は [{"error": "..."}]

Example:
    from mcp_helper import search
    results = search("Python 3.12 新機能")
    for r in results:
        print(f"- {r['title']}: {r['url']}")
        print(r['content'])
```

## `db_query`

PostgreSQL に対して SELECT クエリを実行（SELECT-only ガード付き、db_pools.yaml のプール名を指定可能）

**Sandbox Helper:** `def query_db(sql: str, pool: str = "default") -> list[dict]`

```
PostgreSQL に SELECT クエリを実行する。

Args:
    sql: SELECT 文（SELECT/WITH のみ許可）
    pool: プール名（デフォルト: "default"）

Returns:
    [{"col1": val1, "col2": val2}, ...]
    エラー時は [{"error": "..."}]

Example:
    from mcp_helper import query_db
    rows = query_db("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
    for r in rows:
        print(r['table_name'])
```

## `claude_code`

Claude Code CLI をサブプロセスとして実行（env サニタイズ + 60 秒タイムアウト + 4000 文字切り詰め）

**Privileged:** このツールは広範な権限を持ちます。SubAgent が `tools:` に宣言すると SubAgentRegistry が WARNING を出します。

**Sandbox Helper:** なし (sandbox 非公開)

## `execute_python`

Python コードをサンドボックス内で実行し stdout/stderr/exit_code を返す（AST allowlist + 512MB + 60 秒タイムアウト）

**Privileged:** このツールは広範な権限を持ちます。SubAgent が `tools:` に宣言すると SubAgentRegistry が WARNING を出します。

**Sandbox Helper:** なし (sandbox 非公開)

## `get_current_datetime`

現在の日時を JST で返す（日付・時刻・曜日・タイムゾーン情報を含む dict）

**Sandbox Helper:** `def get_datetime() -> dict`

```
現在の日時を JST で取得する。

Returns:
    {"date": "2026-04-18", "time": "10:30:00", "weekday": "金曜日", ...}

Example:
    from mcp_helper import get_datetime
    dt = get_datetime()
    print(f"今日は {dt['date']} ({dt['weekday']})")
```

## `attachments_list`

現在の thread に添付されたファイルの一覧 (名前・サイズ・更新日時・拡張子) を返す

**Sandbox Helper:** `def list_attachments() -> list[dict]`

```
添付ファイル一覧を返す。引数なし (thread は RPCContext 解決)。

Returns:
    [{"name": "report.pdf", "size": 1234, "modified_at": <float epoch sec>, "ext": ".pdf", "mime_type": "..."}, ...]
    ファイルが存在しない場合は []

Example:
    from mcp_helper import list_attachments
    files = list_attachments()
    for f in files:
        print(f["name"], f["size"])
```

## `attachments_extract`

指定ファイル (PDF/docx/xlsx/pptx) のテキストを MarkItDown で抽出して返す (最大 50,000 文字、60 秒タイムアウト)

**Sandbox Helper:** `def extract_attachment(filename: str) -> dict`

```
添付ファイルのテキストを抽出する。

Args:
    filename: ファイル名 (basename のみ。パス区切り文字不可)

Returns:
    {"filename": "...", "content": "...", "error": null, "truncated": false, "truncated_chars": 0}
    エラー時: {"filename": "...", "content": null, "error": {"code": "...", "message": "..."}, ...}
    error.code: password | corrupt | size_over | unsupported | extract_timeout

Example:
    from mcp_helper import extract_attachment
    r = extract_attachment("report.pdf")
    if r["error"] is None:
        print(r["content"][:500])
```
