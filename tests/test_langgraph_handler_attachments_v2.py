"""Phase 36 D-10/D-14/D-18: LangGraphHandler._prepare_messages_input の unit test.

Plan 36-04 Task 2.

LangGraphHandler の _handle_inner 全体は AsyncPostgresSaver / build_graph /
graph.astream_events と深く連結していて mock しきれないため、
本 plan では handler 内のロジック (per-turn attachments → HumanMessage.additional_kwargs
の注入 + D-18 vision 非対応モデル時の画像 drop + SystemMessage 警告) を
`_prepare_messages_input(job, effective_system_prompt, llm, model, prompt)`
という private helper に抽出し、その helper を直接テストする方針.

handler 本体 (_handle_inner) からは helper を 1 回呼ぶだけにする.
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from langchain_core.messages import HumanMessage


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_llm_vision_true():
    """ChatCopilot の代わり: is_vision_model が True を返す."""
    mock = AsyncMock()
    mock.is_vision_model = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_llm_vision_false():
    """ChatCopilot の代わり: is_vision_model が False を返す (vision 非対応モデル)."""
    mock = AsyncMock()
    mock.is_vision_model = AsyncMock(return_value=False)
    return mock


def _text_att(name: str = "a.txt") -> dict:
    return {
        "kind": "file",
        "name": name,
        "storage_name": f"20260423T120000_{name}",
        "path": f"/shared/thread-files/u/t/20260423T120000_{name}",
        "size": 10,
        "mime_type": "text/plain",
        "ext": "txt",
        "modified_at": "2026-04-23T12:00:00Z",
    }


def _image_att(name: str = "p.png", ext: str = "png") -> dict:
    return {
        "kind": "file",
        "name": name,
        "storage_name": f"20260423T120000_{name}",
        "path": f"/shared/thread-files/u/t/20260423T120000_{name}",
        "size": 999,
        "mime_type": f"image/{ext}",
        "ext": ext,
        "modified_at": "2026-04-23T12:00:00Z",
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_langgraph_handler_injects_additional_kwargs_text_files(mock_llm_vision_true):
    """text ファイルのみ → additional_kwargs にそのまま乗り、警告は追加されない."""
    from app.jobs.handlers.langgraph_handler import LangGraphHandler

    handler = LangGraphHandler()
    atts = [_text_att("a.txt"), _text_att("b.md")]
    messages, sp = await handler._prepare_messages_input(
        {"attachments": atts},
        "base prompt",
        mock_llm_vision_true,
        "claude-sonnet-4.6",
        "hi",
    )
    assert len(messages) == 1
    assert isinstance(messages[0], HumanMessage)
    assert messages[0].content == "hi"
    assert messages[0].additional_kwargs == {"attachments": atts}
    assert sp == "base prompt"  # 警告は追加されない


@pytest.mark.asyncio
async def test_langgraph_handler_no_attachments_passes_empty_kwargs(mock_llm_vision_true):
    """attachments が None → additional_kwargs は空 dict (Pitfall 10 対策)."""
    from app.jobs.handlers.langgraph_handler import LangGraphHandler

    handler = LangGraphHandler()
    messages, sp = await handler._prepare_messages_input(
        {"attachments": None},
        "base",
        mock_llm_vision_true,
        "gpt-4.1",
        "hi",
    )
    assert messages[0].additional_kwargs == {}
    # vision 判定は呼ばれない (early return)
    mock_llm_vision_true.is_vision_model.assert_not_awaited()
    assert sp == "base"


@pytest.mark.asyncio
async def test_langgraph_handler_empty_list_passes_empty_kwargs(mock_llm_vision_true):
    """attachments が [] → additional_kwargs は空 dict."""
    from app.jobs.handlers.langgraph_handler import LangGraphHandler

    handler = LangGraphHandler()
    messages, sp = await handler._prepare_messages_input(
        {"attachments": []},
        "base",
        mock_llm_vision_true,
        "gpt-4.1",
        "hi",
    )
    assert messages[0].additional_kwargs == {}
    mock_llm_vision_true.is_vision_model.assert_not_awaited()


@pytest.mark.asyncio
async def test_langgraph_handler_vision_drop_on_non_vision_model(mock_llm_vision_false):
    """vision 非対応モデル + 画像 attachment → 画像 drop + system_prompt に警告追加."""
    from app.jobs.handlers.langgraph_handler import LangGraphHandler

    handler = LangGraphHandler()
    atts = [_image_att("cat.png", "png")]
    messages, sp = await handler._prepare_messages_input(
        {"attachments": atts},
        "base",
        mock_llm_vision_false,
        "gpt-4.1",
        "説明して",
    )
    # 画像は drop されているので additional_kwargs は empty {}
    assert messages[0].additional_kwargs == {}
    # system prompt に警告追加
    assert "画像非対応モデル警告" in sp
    assert "cat.png" in sp
    assert "gpt-4.1" in sp
    # vision 判定が呼ばれる
    mock_llm_vision_false.is_vision_model.assert_awaited_once_with("gpt-4.1")


@pytest.mark.asyncio
async def test_langgraph_handler_vision_pass_on_vision_model(mock_llm_vision_true):
    """vision 対応モデル + 画像 attachment → そのまま additional_kwargs に乗る + 警告なし."""
    from app.jobs.handlers.langgraph_handler import LangGraphHandler

    handler = LangGraphHandler()
    atts = [_image_att("p.png", "png")]
    messages, sp = await handler._prepare_messages_input(
        {"attachments": atts},
        "base",
        mock_llm_vision_true,
        "claude-sonnet-4.6",
        "hi",
    )
    assert messages[0].additional_kwargs == {"attachments": atts}
    assert "画像非対応モデル警告" not in sp


@pytest.mark.asyncio
async def test_langgraph_handler_mixed_text_and_image_non_vision_drops_only_images(mock_llm_vision_false):
    """text + 画像 mix + vision 非対応 → text は残る、画像だけ drop、警告は画像名のみ."""
    from app.jobs.handlers.langgraph_handler import LangGraphHandler

    handler = LangGraphHandler()
    text_a = _text_att("a.txt")
    img_b = _image_att("b.png", "png")
    img_c = _image_att("c.webp", "webp")
    messages, sp = await handler._prepare_messages_input(
        {"attachments": [text_a, img_b, img_c]},
        "base",
        mock_llm_vision_false,
        "gpt-4.1",
        "hi",
    )
    # text は残る、画像は drop
    assert messages[0].additional_kwargs == {"attachments": [text_a]}
    # 警告には画像名のみが列挙される
    assert "b.png" in sp
    assert "c.webp" in sp
    assert "a.txt" not in sp  # text ファイル名は警告に出ない
