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

AUQ_PROTOCOL = (
    "\n\n## 質問プロトコル\n\n"
    "ユーザーに確認が必要な場合、以下の <ask_user_question> フォーマットのみで応答すること。\n"
    "通常の会話文と混在させてはならない。\n\n"
    "### フォーマット\n\n"
    "<ask_user_question>\n"
    '{"questions": [{"question": "質問テキスト", "header": "ラベル（12文字以内）", '
    '"type": "single|multi|text", '
    '"options": [{"label": "選択肢", "description": "補足説明"}], '
    '"allowFreeText": true, "placeholder": "入力例", "optional": true}]}\n'
    "</ask_user_question>\n\n"
    "### type の使い分け\n"
    "- single: 1つだけ選ぶ（デフォルト）\n"
    "- multi: 複数選べる\n"
    "- text: 自由記述\n\n"
    "### ルール\n"
    "- 選択肢は 2〜4 個に絞ること\n"
    "- 1回のパネルに収める上限は 10 問まで\n"
    "- 確認事項が 10 問を超える場合はテーマ単位で分割して複数ラウンドに分けること\n"
    "- 質問が 1〜3 問程度で済む場合はまとめて 1 回で聞くこと\n"
    "- 回答を受け取ったら作業を進め、追加確認が必要なら再度同フォーマットで質問すること"
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
    parts.append(AUQ_PROTOCOL)
    return "\n".join(parts)
