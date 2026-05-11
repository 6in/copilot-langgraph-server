"""Phase 36 D-14/D-18/D-20: OrchestratorHandler の attachments 準備 unit test.

Plan 36-04 Task 3.

OrchestratorHandler の handle() / _handle_inner() 全体は per-job MCP client +
SubAgentRegistry + AsyncPostgresSaver + build_orchestrator_graph と深く連結している
ため mock しきれない. 本 plan では「per-turn 添付の取り出し + D-18 vision 非対応
モデル時の画像 drop」のロジックを `_prepare_new_attachments(job, llm, model)`
private helper に抽出し、その helper と AgentState への new_attachments フィールド
追加を unit test する.

handler 本体は state["new_attachments"] = await self._prepare_new_attachments(...)
を呼ぶだけにする. SuperChat SubAgent 側で HumanMessage 構築時に additional_kwargs に
state["new_attachments"] を載せる配線は v6.1 で別途検討 (Plan 07 Open Issues).
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_llm_vision_true():
    mock = AsyncMock()
    mock.is_vision_model = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_llm_vision_false():
    mock = AsyncMock()
    mock.is_vision_model = AsyncMock(return_value=False)
    return mock


# ---------------------------------------------------------------------------
# Tests — _prepare_new_attachments
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_orchestrator_handler_prepares_new_attachments_vision_true(mock_llm_vision_true):
    """vision 対応モデル → text + 画像とも全部残る."""
    from app.jobs.handlers.orchestrator_handler import OrchestratorHandler

    h = OrchestratorHandler()
    atts = [
        {
            "kind": "file", "name": "a.txt", "ext": "txt",
            "path": "/x/a.txt", "size": 1, "mime_type": "text/plain",
            "storage_name": "20260423T120000_a.txt",
            "modified_at": "2026-04-23T12:00:00Z",
        },
        {
            "kind": "file", "name": "b.png", "ext": "png",
            "path": "/x/b.png", "size": 2, "mime_type": "image/png",
            "storage_name": "20260423T120000_b.png",
            "modified_at": "2026-04-23T12:00:00Z",
        },
    ]
    result = await h._prepare_new_attachments(
        {"attachments": atts}, mock_llm_vision_true, "claude-sonnet-4.6",
    )
    assert result == atts
    mock_llm_vision_true.is_vision_model.assert_awaited_once_with("claude-sonnet-4.6")


@pytest.mark.asyncio
async def test_orchestrator_handler_prepares_new_attachments_vision_false_drops_images(mock_llm_vision_false):
    """vision 非対応モデル → text は残る、画像 (png/webp) は drop."""
    from app.jobs.handlers.orchestrator_handler import OrchestratorHandler

    h = OrchestratorHandler()
    atts = [
        {"kind": "file", "name": "a.txt", "ext": "txt"},
        {"kind": "file", "name": "b.png", "ext": "png"},
        {"kind": "file", "name": "c.webp", "ext": "webp"},
        {"kind": "file", "name": "d.jpg", "ext": "jpg"},
        {"kind": "file", "name": "e.JPEG", "ext": "JPEG"},  # 大文字小文字混在
    ]
    result = await h._prepare_new_attachments(
        {"attachments": atts}, mock_llm_vision_false, "gpt-4.1",
    )
    assert [a["name"] for a in result] == ["a.txt"]
    mock_llm_vision_false.is_vision_model.assert_awaited_once_with("gpt-4.1")


@pytest.mark.asyncio
async def test_orchestrator_handler_empty_attachments(mock_llm_vision_true):
    """attachments が None / [] → [] を返す + vision 判定は呼ばれない (early return)."""
    from app.jobs.handlers.orchestrator_handler import OrchestratorHandler

    h = OrchestratorHandler()
    assert await h._prepare_new_attachments(
        {"attachments": None}, mock_llm_vision_true, "gpt-4.1",
    ) == []
    assert await h._prepare_new_attachments(
        {"attachments": []}, mock_llm_vision_true, "gpt-4.1",
    ) == []
    mock_llm_vision_true.is_vision_model.assert_not_awaited()


# ---------------------------------------------------------------------------
# Tests — AgentState.new_attachments field
# ---------------------------------------------------------------------------


def test_agent_state_has_new_attachments_field():
    """Phase 36 D-14/D-20: AgentState TypedDict に new_attachments: list[dict] | None
    フィールドが存在すること.
    """
    from app.orchestrator.state import AgentState

    assert "new_attachments" in AgentState.__annotations__
