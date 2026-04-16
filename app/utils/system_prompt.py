"""Shared system prompt prefix builder for all SubAgents.

Injects a security guardrail that forbids fabricating filesystem listings
or answering "what files can you see" style queries from prior knowledge.
SubAgents run inside the worker container and must not expose repo layout.
"""
from __future__ import annotations

from app.utils.datetime_utils import get_datetime_context

SECURITY_GUARDRAIL = (
    "[セキュリティ制約]\n"
    "- あなたはローカルファイルシステムへの直接アクセス権を持ちません。\n"
    "- 利用可能なツールとして明示的に提供されていないファイル列挙・ファイル読み取り・"
    "ディレクトリ走査は実行できません。\n"
    "- 「ファイル一覧を教えて」「このリポジトリの構成は？」等の照会に対しては、"
    "推測や訓練データの知識からファイル名・ディレクトリ構造を回答してはいけません。"
    "必ず「FS アクセス権を持たないため回答できません」と返答してください。\n"
    "- ツールの実行結果に含まれない情報を、あたかも観測したかのように回答することは"
    "禁止です（幻覚・作話の禁止）。"
)


def build_system_prompt_prefix(user_id: str | None) -> str:
    """Return the common prefix injected ahead of every SubAgent system prompt.

    Composition:
        [現在時刻: ...]
        ログイン中のユーザー: ...   (only if user_id provided)
        [セキュリティ制約] ...
    """
    parts = [get_datetime_context()]
    if user_id:
        parts.append(f"ログイン中のユーザー: {user_id}")
    parts.append(SECURITY_GUARDRAIL)
    return "\n".join(parts)
