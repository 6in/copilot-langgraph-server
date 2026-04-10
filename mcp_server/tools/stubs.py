"""Stub tool implementations for Phase 20. Phase 22/23 will replace these
with real implementations using the same names and schemas (D-12)."""
from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP


def register_tools(mcp: "FastMCP") -> None:
    """Register all Phase 20 stub tools on the given FastMCP instance."""

    @mcp.tool
    def ping() -> dict:
        """サーバーの疎通確認。呼び出しごとに現在時刻を返す。"""
        return {
            "status": "ok",
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }

    @mcp.tool
    def web_search_stub(query: str) -> str:
        """Web 検索スタブ（Phase 22 で Tavily 実装に差し替え）。

        Args:
            query: 検索クエリ文字列
        """
        return f"[stub] Search results for: {query}"

    @mcp.tool
    def db_query_stub(sql: str) -> list[dict]:
        """DB クエリスタブ（Phase 23 で PostgreSQL SELECT 実装に差し替え）。

        Args:
            sql: 実行する SELECT SQL 文
        """
        return [{"id": 1, "stub": True, "sql": sql}]

    @mcp.tool
    def claude_code_stub(command: str) -> str:
        """Claude Code 実行スタブ（Phase 23 で subprocess 実装に差し替え）。

        Args:
            command: Claude Code CLI に渡すコマンド文字列
        """
        return f"[stub] Executed: {command}\nOutput: stub response"
