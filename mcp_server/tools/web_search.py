"""Phase 22: Tavily web_search ツール実装。

web_search_stub の本番差し替え。TavilySearchResults を使い、
各結果の content を 1000 文字に切り捨ててコンテキスト超過を防ぐ (SEARCH-02)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP


def register_tools(mcp: "FastMCP") -> None:
    """Phase 22: Tavily web_search ツールを登録する。"""

    @mcp.tool
    def web_search(query: str) -> dict:
        """Web 検索を実行してリアルタイム情報を返す（Tavily API 使用）。

        Args:
            query: 検索クエリ文字列

        Returns:
            {"results": [{"url": "...", "content": "..."}]} or {"error": "..."}
        """
        try:
            from langchain_community.tools.tavily_search import TavilySearchResults

            tavily = TavilySearchResults(max_results=3)
            results: list[dict] = tavily.invoke(query)
            # SEARCH-02: コンテキスト超過防止 — 各結果の content を 1000 文字で切り捨て
            for r in results:
                if isinstance(r, dict) and "content" in r:
                    r["content"] = r["content"][:1000]
            formatted_parts = []
            for i, r in enumerate(results, 1):
                url = r.get("url", "")
                title = r.get("title", "")
                content = r.get("content", "")[:1000]
                formatted_parts.append(f"[{i}] {url}\n{title}\n{content}")

            return {
                "results": results,
                "formatted": "\n\n---\n\n".join(formatted_parts),
                "source_urls": [r.get("url", "") for r in results if r.get("url")],
            }
        except Exception as e:
            return {"error": f"web_search failed: {e}"}
