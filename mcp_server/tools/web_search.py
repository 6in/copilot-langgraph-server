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
            # SEARCH-02 REVISED: コンテキスト超過防止 — 各結果の content を 500 文字で切り捨て。
            # ReAct ループの 2 回目 LLM 呼び出しでツール結果がプロンプトに含まれるため、
            # 合計サイズを 〜2KB に収めないと Copilot SDK がタイムアウトする。
            max_content = 500
            trimmed = []
            for r in results:
                if not isinstance(r, dict):
                    continue
                trimmed.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", "")[:max_content],
                })

            return {
                "results": trimmed,
                "source_urls": [r["url"] for r in trimmed if r.get("url")],
            }
        except Exception as e:
            return {"error": f"web_search failed: {e}"}
