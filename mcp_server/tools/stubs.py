"""Stub tool implementations. Phase 22 moved web_search to tools/web_search.py
(Tavily implementation). Phase 23 Plan 01 で db_query を tools/db_query.py に差し替え済み。
Phase 23 Plan 02 で claude_code を tools/claude_code.py に差し替え済み。
ping のみ残存（疎通確認ツール）。"""
from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP


def register_tools(mcp: "FastMCP") -> None:
    """Register stub tools on the given FastMCP instance.

    Phase 23 完了後の状況:
    - ping: 継続（疎通確認ツール）
    - get_current_datetime: 追加（全エージェント共通の現在時刻ツール）
    - db_query_stub: Phase 23 Plan 01 で tools/db_query.py に差し替え済み（削除）
    - claude_code_stub: Phase 23 Plan 02 で tools/claude_code.py に差し替え済み（削除）
    """

    @mcp.tool
    def ping() -> dict:
        """サーバーの疎通確認。呼び出しごとに現在時刻を返す。"""
        return {
            "status": "ok",
            "timestamp": datetime.datetime.utcnow().isoformat(),
        }

    @mcp.tool
    def get_current_datetime() -> dict:
        """現在の日時を返す。日付・時刻に関する質問やスケジュール計算に使用する。"""
        try:
            import zoneinfo
            jst = zoneinfo.ZoneInfo("Asia/Tokyo")
        except Exception:
            jst = datetime.timezone(datetime.timedelta(hours=9))
        weekday_ja = ["月", "火", "水", "木", "金", "土", "日"]
        now = datetime.datetime.now(tz=jst)
        return {
            "iso8601": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
            "timezone": "Asia/Tokyo (JST, UTC+9)",
            "weekday": weekday_ja[now.weekday()] + "曜日",
            "formatted": now.strftime("%Y年%m月%d日 %H:%M") + f" ({weekday_ja[now.weekday()]}曜日)",
        }
