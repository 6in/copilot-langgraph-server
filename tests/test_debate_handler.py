"""Unit tests for DebateHandler (Phase 17-02).

TDD RED phase: tests written before implementation.

Tests:
  - test_handle_calls_build_debate_graph: handle() calls build_debate_graph and saves result
  - test_handle_invalid_participants: participants < 2 -> error saved to job_store
  - test_max_turns_capped_at_20: max_turns > 20 -> capped to 20 in build_debate_graph call
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_job(
    participants=None,
    pattern="debate",
    max_turns=3,
    current_turn=0,
    github_token="tok",
    gem_ids=None,
):
    if participants is None:
        participants = ["agent_a", "agent_b"]
    return {
        "job_id": "job-001",
        "thread_id": "thread-001",
        "prompt": "討論してください",
        "github_token": github_token,
        "reply_to": {"type": "web", "job_id": "job-001"},
        "participants": participants,
        "pattern": pattern,
        "max_turns": max_turns,
        "current_turn": current_turn,
        "github_login": "testuser",
        "gem_ids": gem_ids or [],
    }


def _make_ctx(job_store=None):
    if job_store is None:
        job_store = AsyncMock()
        job_store.save_result = AsyncMock()
        job_store.notify = AsyncMock()
        job_store.get = AsyncMock(return_value=None)
    return {"job_store": job_store}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_handle_calls_build_debate_graph():
    """handle() が build_debate_graph を呼び出し、結果を job_store.save_result に保存する。

    Phase 17 以降の経路: handler は graph.astream() を async for で iterate して
    各 state_chunk から AIMessage を all_turns に蓄積する (graph.ainvoke は呼ばれない)。
    AsyncMock では async for 不可なので async generator pattern で書く。
    """
    from app.jobs.handlers.debate_handler import DebateHandler
    from langchain_core.messages import AIMessage

    # debate_handler は AIMessage 実型を見て all_turns に蓄積するので
    # MagicMock ではなく実 AIMessage を使う。
    ai_msg = AIMessage(content="エージェントAの発言", name="agent_a")

    # graph.astream は async for で iterate するため async generator にする。
    # yield する dict は {node_name: state_delta} 形式 (stream_mode='updates' デフォルト)。
    async def _astream_gen(*args, **kwargs):
        yield {"agent_a": {"messages": [ai_msg], "turn": 1}}

    mock_graph = AsyncMock()
    mock_graph.astream = MagicMock(side_effect=_astream_gen)

    mock_registry = MagicMock()
    mock_registry.agents = {"agent_a": MagicMock(), "agent_b": MagicMock()}
    mock_registry.close = AsyncMock()

    mock_checkpointer = AsyncMock()
    mock_checkpointer.__aenter__ = AsyncMock(return_value=mock_checkpointer)
    mock_checkpointer.__aexit__ = AsyncMock(return_value=None)
    mock_checkpointer.setup = AsyncMock()

    job_store = AsyncMock()
    job_store.save_result = AsyncMock()
    job_store.notify = AsyncMock()
    ctx = _make_ctx(job_store)
    job = _make_job(participants=["agent_a", "agent_b"], max_turns=3)

    with (
        patch("app.jobs.handlers.debate_handler.build_debate_graph", return_value=mock_graph) as mock_bdg,
        patch("app.jobs.handlers.debate_handler.SubAgentRegistry", return_value=mock_registry),
        patch("app.jobs.handlers.debate_handler.AsyncPostgresSaver") as mock_saver_cls,
        patch("app.jobs.handlers.debate_handler.ChatCopilot"),
    ):
        mock_saver_cls.from_conn_string.return_value = mock_checkpointer

        handler = DebateHandler()
        result = await handler.handle(ctx, job)

    # build_debate_graph が呼ばれた
    mock_bdg.assert_called_once()

    # mock_graph.astream が呼ばれた (handler は astream のみ使用、ainvoke は呼ばない)
    mock_graph.astream.assert_called_once()

    # save_result が呼ばれた
    job_store.save_result.assert_called_once()
    saved_arg = job_store.save_result.call_args[0][1]
    payload = json.loads(saved_arg)
    assert payload["type"] == "debate_result"
    assert "debate_text" in payload
    assert payload["is_complete"] is True

    assert result["status"] == "done"


@pytest.mark.asyncio
async def test_handle_invalid_participants():
    """participants が 2 名未満の場合、エラーメッセージを job_store に保存して done する。"""
    from app.jobs.handlers.debate_handler import DebateHandler

    job_store = AsyncMock()
    job_store.save_result = AsyncMock()
    job_store.notify = AsyncMock()
    ctx = _make_ctx(job_store)
    job = _make_job(participants=["only_one_agent"])

    handler = DebateHandler()
    result = await handler.handle(ctx, job)

    # save_result が呼ばれ、エラー内容が含まれる
    job_store.save_result.assert_called_once()
    saved_text = job_store.save_result.call_args[0][1]
    assert "participants" in saved_text.lower() or "error" in saved_text.lower() or len(saved_text) > 0

    # done 通知が呼ばれた
    job_store.notify.assert_called()

    assert result["status"] == "done"


@pytest.mark.asyncio
async def test_max_turns_capped_at_20():
    """max_turns=100 の job を渡すと build_debate_graph に渡る max_turns が 20 に切り詰められる。"""
    from app.jobs.handlers.debate_handler import DebateHandler

    mock_ai_message = MagicMock()
    mock_ai_message.__class__.__name__ = "AIMessage"
    mock_ai_message.content = "test"

    fake_result = {
        "messages": [mock_ai_message],
        "turn": 20,
        "max_turns": 20,
        "pattern": "debate",
        "participants": ["a", "b"],
        "current_agent_idx": 0,
        "awaiting_extension": False,
    }

    mock_graph = AsyncMock()
    mock_graph.ainvoke = AsyncMock(return_value=fake_result)

    mock_registry = MagicMock()
    mock_registry.agents = {"a": MagicMock(), "b": MagicMock()}
    mock_registry.close = AsyncMock()

    mock_checkpointer = AsyncMock()
    mock_checkpointer.__aenter__ = AsyncMock(return_value=mock_checkpointer)
    mock_checkpointer.__aexit__ = AsyncMock(return_value=None)
    mock_checkpointer.setup = AsyncMock()

    job_store = AsyncMock()
    job_store.save_result = AsyncMock()
    job_store.notify = AsyncMock()
    ctx = _make_ctx(job_store)
    job = _make_job(participants=["a", "b"], max_turns=100)

    with (
        patch("app.jobs.handlers.debate_handler.build_debate_graph", return_value=mock_graph) as mock_bdg,
        patch("app.jobs.handlers.debate_handler.SubAgentRegistry", return_value=mock_registry),
        patch("app.jobs.handlers.debate_handler.AsyncPostgresSaver") as mock_saver_cls,
        patch("app.jobs.handlers.debate_handler.ChatCopilot"),
    ):
        mock_saver_cls.from_conn_string.return_value = mock_checkpointer

        handler = DebateHandler()
        await handler.handle(ctx, job)

    # build_debate_graph に渡された max_turns が 20 であることを確認
    mock_bdg.assert_called_once()
    args_list = mock_bdg.call_args[0]
    # build_debate_graph(participants, pattern, max_turns, agents, llm, checkpointer)
    assert args_list[2] == 20, f"max_turns should be capped at 20, got {args_list[2]}"
