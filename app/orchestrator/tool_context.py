"""ツール実行イベントを非同期コンテキスト経由で伝播させる ContextVar ヘルパー。"""
from contextvars import ContextVar
from typing import Awaitable, Callable, Optional

ToolEventCallback = Callable[[str, str], Awaitable[None]]
# args: (tool_name, query)
tool_event_cb: ContextVar[Optional[ToolEventCallback]] = ContextVar('tool_event_cb', default=None)
