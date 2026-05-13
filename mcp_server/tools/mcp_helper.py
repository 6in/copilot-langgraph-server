# DO NOT EDIT — auto-generated from config/mcp_tools.yaml by scripts/generate_mcp_artifacts.py
# To regenerate: python3 scripts/generate_mcp_artifacts.py --target helper
"""mcp_helper — サンドボックス Python コードから MCP ツールを呼び出すヘルパー。

このファイルは config/mcp_tools.yaml の python_wrapper ブロックから自動生成されます。
手書きヘルパー (_call_tool / _clean_content / _INTERNAL_URL / _TIMEOUT) は
mcp_helper_utils.py に分離されています。新規ツール追加時は YAML を編集して
`python3 scripts/generate_mcp_artifacts.py --target all` を実行してください。
"""
from mcp_helper_utils import _call_tool, _clean_content  # noqa: F401


def ping() -> dict:
    """MCP サーバーの疎通確認。呼び出しごとに現在時刻を返す。

    Returns:
        {"status": "ok", "timestamp": "..."}

    Example:
        from mcp_helper import ping
        r = ping()
        print(r["status"])
    """
    return _call_tool("ping")


def search(query: str) -> list[dict]:
    """Web 検索を実行する。

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
    """
    result = _call_tool("web_search", {"query": query})
    if isinstance(result, dict):
        if "error" in result:
            return [{"error": result["error"]}]
        raw_results = result.get("results", [result])
        for r in raw_results:
            if "content" in r:
                r["content"] = _clean_content(r["content"])
        return raw_results
    return [{"error": "unexpected response"}]


def query_db(sql: str, pool: str = "default") -> list[dict]:
    """PostgreSQL に SELECT クエリを実行する。

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
    """
    result = _call_tool("db_query", {"sql": sql, "pool_name": pool})
    if isinstance(result, dict):
        if "error" in result:
            return [{"error": result["error"]}]
        return result.get("rows", [result])
    return [{"error": "unexpected response"}]


def get_datetime() -> dict:
    """現在の日時を JST で取得する。

    Returns:
        {"date": "2026-04-18", "time": "10:30:00", "weekday": "金曜日", ...}

    Example:
        from mcp_helper import get_datetime
        dt = get_datetime()
        print(f"今日は {dt['date']} ({dt['weekday']})")
    """
    return _call_tool("get_current_datetime")


def list_attachments() -> list[dict]:
    """添付ファイル + AI 生成ファイル一覧を返す。引数なし (thread は RPCContext 解決)。

    各エントリには kind フィールドが付与され、user upload と worker 生成を判別できる。
    - kind: "user_upload"  → ユーザーがアップロードした添付 (Phase 36)
    - kind: "generated"    → execute_python / claude_code が生成した出力 (Phase 38)

    Returns:
        [{"name": "report.pdf", "size": 1234, "modified_at": <float epoch sec>,
          "ext": ".pdf", "mime_type": "...", "kind": "user_upload" | "generated"}, ...]
        ファイルが存在しない場合は []

    Example:
        from mcp_helper import list_attachments
        files = list_attachments()
        for f in files:
            print(f["name"], f["kind"], f["size"])
    """
    return _call_tool("attachments_list")


def extract_attachment(filename: str) -> dict:
    """添付ファイルのテキストを抽出する。

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
    """
    return _call_tool("attachments_extract", {"filename": filename})
