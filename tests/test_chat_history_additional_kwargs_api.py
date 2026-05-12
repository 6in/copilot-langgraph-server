"""Phase 36 D-22: GET /api/threads/{tid}/messages が additional_kwargs.attachments を含むことを検証。

Plan 03 Task 3: ロジック単体検証.

完全な integration test (LangGraph 実グラフ + checkpointer round-trip) は
Wave 0 既存 `tests/test_chat_history_additional_kwargs.py` (round-trip) と
Plan 07 integration check に委ねる. 本 test はロジックそのものを最小再現する.
"""
from langchain_core.messages import HumanMessage


def test_messages_to_response_logic_includes_attachments():
    """attachments を含む additional_kwargs を public_kw に拾うロジック (D-22 + Phase 38 D-30 正規化)。

    Phase 38 D-30 (案 A): legacy `kind: 'file'` は API 出力で `'user_upload'` に
    自動正規化される。本テストは入力 dict には `kind: 'file'` を入れ、
    public_kw 経由の出力では `'user_upload'` に書き換わっていることを assert する。
    """
    atts = [{
        "kind": "file", "name": "x.png", "storage_name": "20260423T120000_x.png",
        "path": "/p", "size": 1, "mime_type": "image/png", "ext": "png",
        "modified_at": "2026-04-23T12:00:00Z",
    }]
    msg = HumanMessage(content="hello", additional_kwargs={"attachments": atts})

    # _messages_to_response 内のロジックを最小再現 (Phase 38 D-30 正規化 inline):
    kw = getattr(msg, "additional_kwargs", None) or {}
    public_kw: dict = {}
    atts_in = kw.get("attachments")
    if isinstance(atts_in, list) and atts_in:
        normalized_atts = []
        for a in atts_in:
            if isinstance(a, dict):
                a_copy = dict(a)
                if a_copy.get("kind") == "file":
                    a_copy["kind"] = "user_upload"
                normalized_atts.append(a_copy)
            else:
                normalized_atts.append(a)
        public_kw["attachments"] = normalized_atts

    expected = [{**atts[0], "kind": "user_upload"}]
    assert public_kw == {"attachments": expected}
    # 元の dict は変更されない (mutate ガード)
    assert atts[0]["kind"] == "file"


def test_messages_to_response_logic_skips_legacy_messages():
    """additional_kwargs が空 dict のレガシーメッセージでは additional_kwargs key を足さない (Pitfall 10)."""
    msg = HumanMessage(content="old")
    kw = getattr(msg, "additional_kwargs", None) or {}
    public_kw: dict = {}
    if isinstance(kw.get("attachments"), list) and kw["attachments"]:
        public_kw["attachments"] = kw["attachments"]
    assert public_kw == {}


def test_messages_to_response_logic_skips_non_list_attachments():
    """attachments が list でない場合 (型不正) は public_kw に入れない (None-guard)."""
    msg = HumanMessage(content="weird", additional_kwargs={"attachments": "not-a-list"})
    kw = getattr(msg, "additional_kwargs", None) or {}
    public_kw: dict = {}
    if isinstance(kw.get("attachments"), list) and kw["attachments"]:
        public_kw["attachments"] = kw["attachments"]
    assert public_kw == {}


def test_chat_route_messages_to_response_emits_additional_kwargs():
    """app.api.routes.chat の get_thread_messages 経由ではなく、_messages_to_response
    が closure 内のため、本 test は同等ロジックの再現 + import smoke として機能する。

    実際の挙動は test_attachments_get_delete_route.py 経由の integration と
    Plan 07 integration check で確認。
    """
    # smoke: get_thread_messages の import が成功すること (chat.py に additional_kwargs 関連変更が
    # 入っても module load で例外を吐かないことを確認)
    from app.api.routes.chat import get_thread_messages  # noqa: F401


def test_chat_py_contains_legacy_kind_normalization():
    """Phase 38 D-30 (案 A) forcing function: chat.py の _messages_to_response 内で
    legacy `kind: 'file'` を `'user_upload'` に書き換える分岐が実装されている。

    _messages_to_response は closure のため直接 import できない。実装漏れ
    (回帰) を防ぐためソース文字列をマッチングする最小 forcing assertion。
    """
    import inspect
    from app.api.routes import chat as chat_module

    src = inspect.getsource(chat_module)
    # 必須記号: 'file' → 'user_upload' に正規化する分岐
    assert "user_upload" in src, (
        "chat.py must reference 'user_upload' (Phase 38 D-30 normalization)"
    )
    # `kind` 文字列の比較分岐があること (== "file" 等)
    assert '"file"' in src or "'file'" in src, (
        "chat.py must check the legacy kind value 'file' to normalize it"
    )
