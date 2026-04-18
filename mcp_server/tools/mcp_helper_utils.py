"""mcp_helper_utils — 手書き基盤モジュール（scripts/generate_mcp_artifacts.py は生成しない）。

Phase 30 (D-02): 自動生成される mcp_helper.py から分離された手書きロジック。
- _call_tool: MCP サーバーの /internal/call_tool HTTP エンドポイントへ POST
- _clean_content: web_search 専用のテキスト前処理（ナビ・フッター除去）
- _INTERNAL_URL / _TIMEOUT: 接続設定定数

自動生成された mcp_helper.py は以下の 1 行で本モジュールを取り込む:

    from mcp_helper_utils import _call_tool, _clean_content

このモジュールを編集する場合は手動で行う（ジェネレータは触らない）。
関連: docs/mcp-tool-add-manual.md (Plan 06)
"""
from __future__ import annotations

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
