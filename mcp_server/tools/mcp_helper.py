"""mcp_helper — サンドボックス Python コードから MCP ツールを呼び出すヘルパー。

execute_python サンドボックス内の Python コードから import して使う:

    from mcp_helper import search, query_db, get_datetime

内部的には MCP サーバーの /internal/call_tool エンドポイントに HTTP リクエストを送る。
urllib.request のみ使用（外部依存なし、sandbox allowlist に urllib 追加が必要）。
"""

import json
import urllib.request

_INTERNAL_URL = "http://localhost:8001/internal/call_tool"
_TIMEOUT = 55  # execute_python の 60 秒タイムアウトより短く


def _call_tool(name: str, args: dict | None = None) -> dict:
    """MCP ツールを呼び出して結果を dict で返す。

    エラー時は {"error": "..."} を返す（例外は投げない）。
    """
    payload = json.dumps({"tool": name, "args": args or {}}).encode("utf-8")
    req = urllib.request.Request(
        _INTERNAL_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body.get("result", body)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        return {"error": f"HTTP {e.code}: {error_body}"}
    except Exception as e:
        return {"error": str(e)}


def _clean_content(text: str, max_lines: int = 15) -> str:
    """Web ページのテキストからナビ・フッター・空行を除去して要約する。"""
    if not text:
        return ""
    lines = text.split("\n")
    cleaned = []
    skip_patterns = [
        "cookie", "copyright", "©", "all rights reserved",
        "プライバシー", "利用規約", "個人情報", "広告",
        "twitter", "facebook", "instagram", "youtube", "line",
        "ログイン", "新規登録", "会員登録",
    ]
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if len(stripped) < 3:
            continue
        lower = stripped.lower()
        if any(p in lower for p in skip_patterns):
            continue
        cleaned.append(stripped)
        if len(cleaned) >= max_lines:
            break
    return "\n".join(cleaned)


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
        # content を前処理して返す
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


def ping() -> dict:
    """MCP サーバーの疎通確認。

    Returns:
        {"status": "ok", "timestamp": "..."}
    """
    return _call_tool("ping")
