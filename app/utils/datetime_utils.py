"""Date/time utilities shared across handlers and orchestrator agents."""
import datetime
import zoneinfo


def get_datetime_context() -> str:
    """現在の日時文字列を返す（JST）。システムプロンプトへの注入用。

    例: [現在時刻: 2026-04-13 13:00 JST (月曜日)]
    """
    weekday_ja = ["月", "火", "水", "木", "金", "土", "日"]
    now = datetime.datetime.now(tz=zoneinfo.ZoneInfo("Asia/Tokyo"))
    wd = weekday_ja[now.weekday()]
    return f"[現在時刻: {now.strftime('%Y-%m-%d %H:%M')} JST ({wd}曜日)]"
