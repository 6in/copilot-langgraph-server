"""Tests for the arq worker module (ASYNC-07).

Tests verify that process_chat orchestrates correctly:
- graph.ainvoke -> save_result -> notifier.done (success path)
- error path saves error message and still calls notifier.done
- llm.close() is always called in the finally block
- startup/shutdown lifecycle hooks work correctly
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


async def test_process_chat_saves_result():
    """process_chat calls job_store.save_result then notifier.done (success path)."""
    from app.jobs.worker import process_chat

    mock_job_store = AsyncMock()
    ctx = {"job_store": mock_job_store}

    # Mock LangGraph result
    mock_message = MagicMock()
    mock_message.content = "AI reply"
    mock_result = {"messages": [mock_message]}

    mock_graph = AsyncMock()
    mock_graph.ainvoke = AsyncMock(return_value=mock_result)

    mock_llm = AsyncMock()
    mock_checkpointer = AsyncMock()
    mock_checkpointer.__aenter__ = AsyncMock(return_value=mock_checkpointer)
    mock_checkpointer.__aexit__ = AsyncMock(return_value=None)

    with patch("app.jobs.worker.ChatCopilot", return_value=mock_llm), \
         patch("app.jobs.worker.build_graph", return_value=mock_graph), \
         patch("app.jobs.worker.AsyncSqliteSaver.from_conn_string", return_value=mock_checkpointer):

        result = await process_chat(
            ctx,
            job_id="j1",
            thread_id="t1",
            prompt="hello",
            github_token="ghu_test",
            reply_to={"type": "web", "job_id": "j1"},
        )

    mock_job_store.save_result.assert_called_once_with("j1", "AI reply")
    # notifier.done() calls job_store.notify — verify it was called
    mock_job_store.notify.assert_called()
    assert result == {"job_id": "j1", "status": "done"}


async def test_process_chat_error_handling():
    """process_chat saves error message and still calls notifier.done on exception."""
    from app.jobs.worker import process_chat

    mock_job_store = AsyncMock()
    ctx = {"job_store": mock_job_store}

    mock_graph = AsyncMock()
    mock_graph.ainvoke = AsyncMock(side_effect=RuntimeError("boom"))

    mock_llm = AsyncMock()
    mock_checkpointer = AsyncMock()
    mock_checkpointer.__aenter__ = AsyncMock(return_value=mock_checkpointer)
    mock_checkpointer.__aexit__ = AsyncMock(return_value=None)

    with patch("app.jobs.worker.ChatCopilot", return_value=mock_llm), \
         patch("app.jobs.worker.build_graph", return_value=mock_graph), \
         patch("app.jobs.worker.AsyncSqliteSaver.from_conn_string", return_value=mock_checkpointer):

        await process_chat(
            ctx,
            job_id="j2",
            thread_id="t2",
            prompt="error test",
            github_token="ghu_test",
            reply_to={"type": "web", "job_id": "j2"},
        )

    # Verify save_result was called with an error-containing message
    call_args = mock_job_store.save_result.call_args
    assert call_args[0][0] == "j2"
    assert "Error:" in call_args[0][1]
    assert "boom" in call_args[0][1]

    # notifier.done() must still be called even on error
    mock_job_store.notify.assert_called()


async def test_process_chat_closes_llm():
    """llm.close() is called in finally block even when exception occurs."""
    from app.jobs.worker import process_chat

    mock_job_store = AsyncMock()
    ctx = {"job_store": mock_job_store}

    mock_graph = AsyncMock()
    mock_graph.ainvoke = AsyncMock(side_effect=RuntimeError("force error"))

    mock_llm = AsyncMock()
    mock_checkpointer = AsyncMock()
    mock_checkpointer.__aenter__ = AsyncMock(return_value=mock_checkpointer)
    mock_checkpointer.__aexit__ = AsyncMock(return_value=None)

    with patch("app.jobs.worker.ChatCopilot", return_value=mock_llm), \
         patch("app.jobs.worker.build_graph", return_value=mock_graph), \
         patch("app.jobs.worker.AsyncSqliteSaver.from_conn_string", return_value=mock_checkpointer):

        await process_chat(
            ctx,
            job_id="j3",
            thread_id="t3",
            prompt="close test",
            github_token="ghu_test",
            reply_to={"type": "web", "job_id": "j3"},
        )

    mock_llm.close.assert_called_once()


async def test_startup_creates_redis_and_jobstore():
    """startup(ctx) populates ctx['redis_client'] and ctx['job_store']."""
    from app.jobs.worker import startup

    ctx: dict = {}
    mock_redis = AsyncMock()

    with patch("app.jobs.worker.Redis") as mock_redis_class:
        mock_redis_class.from_url = MagicMock(return_value=mock_redis)
        await startup(ctx)

    assert "redis_client" in ctx
    assert "job_store" in ctx
    mock_redis_class.from_url.assert_called_once()


async def test_shutdown_closes_redis():
    """shutdown(ctx) calls redis_client.aclose()."""
    from app.jobs.worker import shutdown

    mock_redis = AsyncMock()
    ctx = {"redis_client": mock_redis}

    await shutdown(ctx)

    mock_redis.aclose.assert_called_once()
