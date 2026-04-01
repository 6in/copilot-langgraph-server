"""Tests for SSE endpoint GET /api/chat/{job_id}/stream (ASYNC-04, ASYNC-06)."""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport


async def test_sse_already_done(mock_job_store, mock_arq_redis):
    """SSE endpoint returns immediate done event if job already complete (ASYNC-06)."""
    from app.api.main import app

    mock_job_store.get = AsyncMock(return_value={"status": "done", "result": "done"})
    app.state.job_store = mock_job_store
    app.state.arq_redis = mock_arq_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/chat/j1/stream")

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    text = resp.text
    assert "data:" in text
    # Parse the SSE data line
    for line in text.splitlines():
        if line.startswith("data:"):
            event_data = json.loads(line[len("data:"):].strip())
            assert event_data["status"] == "done"
            break
    else:
        pytest.fail("No data line found in SSE response")


async def test_sse_done_signal(mock_job_store, mock_arq_redis):
    """SSE endpoint yields done event when queue receives done signal (ASYNC-04)."""
    from app.api.main import app

    # Job not done yet
    mock_job_store.get = AsyncMock(return_value=None)

    # Create a real asyncio.Queue that will receive the done signal
    queue: asyncio.Queue = asyncio.Queue()
    mock_job_store.register_sse = MagicMock(return_value=queue)
    mock_job_store.unregister_sse = MagicMock()

    app.state.job_store = mock_job_store
    app.state.arq_redis = mock_arq_redis

    # Put the done event into the queue before making the request
    await queue.put({"status": "done"})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/chat/j1/stream")

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    text = resp.text
    assert "data:" in text
    for line in text.splitlines():
        if line.startswith("data:"):
            event_data = json.loads(line[len("data:"):].strip())
            assert event_data["status"] == "done"
            break
    else:
        pytest.fail("No data line found in SSE response")

    # Verify unregister was called in finally block
    mock_job_store.unregister_sse.assert_called_once_with("j1")
