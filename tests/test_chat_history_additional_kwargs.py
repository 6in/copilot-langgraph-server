"""Phase 36 Wave 0 A1 risk 検証 — RED = Wave 1 Plan 04 に workaround 追加判断.

検証対象: ``HumanMessage.additional_kwargs["attachments"]`` が
LangGraph ``add_messages`` reducer + checkpointer 経由で round-trip 保存できるか.

実装メモ:
- 実 DB (AsyncPostgresSaver) は CI 不安定 + docker compose 依存があるため
  本テストでは MemorySaver で同等の serialize/deserialize パスを叩く
  (``add_messages`` reducer + checkpointer が ``additional_kwargs`` を扱う
  挙動は MemorySaver でも AsyncPostgresSaver でも共通実装).
- 実 DB 確認は Plan 01 Task 3 (docker compose smoke) の
  ``docs/phase-36-sdk-spike-note.md`` 経路で担保する.
- 4 つのテストが GREEN ⇒ A1 risk 「対応不要」.
  RED ⇒ Wave 1 Plan 04 で ``_wrap_human_message_attachments`` workaround 追加判断.
"""

from __future__ import annotations

from typing import Annotated, TypedDict

import pytest
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

# RESEARCH.md L40-53 の D-14 dict (8 フィールド) を 1:1 コピー
_DICT_V14 = {
    "kind": "file",
    "name": "original.png",
    "storage_name": "20260423T120000_original.png",
    "path": "/shared/thread-files/u/t/20260423T120000_original.png",
    "size": 12345,
    "mime_type": "image/png",
    "ext": "png",
    "modified_at": "2026-04-23T12:00:00Z",
}


class _State(TypedDict):
    messages: Annotated[list, add_messages]


def _identity_node(state: _State) -> _State:
    """add_messages reducer 経由でメッセージを蓄積するだけの最小ノード."""
    return {"messages": []}


def _build_compiled():
    builder = StateGraph(_State)
    builder.add_node("identity", _identity_node)
    builder.add_edge(START, "identity")
    builder.add_edge("identity", END)
    return builder.compile(checkpointer=MemorySaver())


async def _run_roundtrip(initial_msg: HumanMessage) -> HumanMessage:
    """initial_msg を checkpointer 経由で永続化し、復元結果を返す."""
    compiled = _build_compiled()
    config = {"configurable": {"thread_id": "t-test"}}
    await compiled.ainvoke({"messages": [initial_msg]}, config=config)
    snapshot = await compiled.aget_state(config)
    msgs = snapshot.values["messages"]
    assert msgs, "expected at least one message after round-trip"
    return msgs[0]


@pytest.mark.asyncio
async def test_additional_kwargs_roundtrip_with_attachments() -> None:
    """D-14 の 8 フィールド attachments dict が checkpointer 越しに完全保持される."""
    msg = HumanMessage(
        content="解析して",
        additional_kwargs={"attachments": [dict(_DICT_V14)]},
    )

    restored = await _run_roundtrip(msg)

    assert isinstance(restored, HumanMessage)
    assert restored.content == "解析して"
    assert "attachments" in restored.additional_kwargs
    attachments = restored.additional_kwargs["attachments"]
    assert isinstance(attachments, list)
    assert len(attachments) == 1
    assert attachments[0] == _DICT_V14, (
        f"attachments dict drifted across checkpointer: got={attachments[0]} "
        f"expected={_DICT_V14}"
    )


@pytest.mark.asyncio
async def test_additional_kwargs_empty_dict_preserved() -> None:
    """additional_kwargs={} の HumanMessage を保存 → 復元後も {} (None にならない)."""
    msg = HumanMessage(content="empty kwargs", additional_kwargs={})

    restored = await _run_roundtrip(msg)

    assert isinstance(restored, HumanMessage)
    assert restored.content == "empty kwargs"
    assert restored.additional_kwargs == {}, (
        f"empty additional_kwargs should round-trip as {{}}, got {restored.additional_kwargs!r}"
    )


@pytest.mark.asyncio
async def test_additional_kwargs_missing_legacy_message() -> None:
    """既存コード相当 (additional_kwargs 未指定) でも復元時に {} (None-guard)."""
    msg = HumanMessage(content="x")  # additional_kwargs を渡さない

    restored = await _run_roundtrip(msg)

    assert isinstance(restored, HumanMessage)
    assert restored.content == "x"
    # langchain-core BaseMessage は default で {} を入れる契約
    assert restored.additional_kwargs == {}, (
        f"legacy HumanMessage(content=...) should expose additional_kwargs == {{}}, "
        f"got {restored.additional_kwargs!r}"
    )


@pytest.mark.asyncio
async def test_additional_kwargs_image_attachment_shape() -> None:
    """kind=file の画像 attachment が 8 フィールド全て (kind/name/storage_name/path/
    size/mime_type/ext/modified_at) 保持される."""
    image_attachment = {
        "kind": "file",
        "name": "screenshot.png",
        "storage_name": "20260424T010101_screenshot.png",
        "path": "/shared/thread-files/u/t/20260424T010101_screenshot.png",
        "size": 98765,
        "mime_type": "image/png",
        "ext": "png",
        "modified_at": "2026-04-24T01:01:01Z",
    }
    msg = HumanMessage(
        content="この画像を見て",
        additional_kwargs={"attachments": [image_attachment]},
    )

    restored = await _run_roundtrip(msg)

    assert isinstance(restored, HumanMessage)
    attachments = restored.additional_kwargs.get("attachments")
    assert attachments and len(attachments) == 1
    restored_attachment = attachments[0]
    expected_fields = {
        "kind",
        "name",
        "storage_name",
        "path",
        "size",
        "mime_type",
        "ext",
        "modified_at",
    }
    assert set(restored_attachment.keys()) >= expected_fields, (
        f"image attachment missing fields after round-trip: "
        f"got_keys={set(restored_attachment.keys())} expected_at_least={expected_fields}"
    )
    for key in expected_fields:
        assert restored_attachment[key] == image_attachment[key], (
            f"field {key!r} drifted: got={restored_attachment[key]!r} "
            f"expected={image_attachment[key]!r}"
        )
