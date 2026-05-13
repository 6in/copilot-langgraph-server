"""Tests for SSE endpoint GET /api/chat/{job_id}/stream (ASYNC-04, ASYNC-06)."""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport


async def test_sse_already_done(mock_job_store, mock_arq_redis, jwt_cookie):
    """SSE endpoint returns immediate done event if job already complete (ASYNC-06).

    (Phase 39 UIFIX-03 D-04 — JWT cookie 注入)
    """
    from app.api.main import app

    mock_job_store.get = AsyncMock(return_value={"status": "done", "result": "done"})
    app.state.job_store = mock_job_store
    app.state.arq_redis = mock_arq_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", cookies={"session": jwt_cookie}) as client:
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


async def test_sse_done_signal(mock_job_store, mock_arq_redis, jwt_cookie):
    """SSE endpoint yields done event when Redis polling detects completion (ASYNC-04).

    (Phase 39 UIFIX-03 D-04 — Redis polling mock 経路で書き直し)
    """
    from app.api.main import app

    # First poll returns pending, second returns done
    mock_job_store.get = AsyncMock(
        side_effect=[None, {"status": "done", "result": "hello"}]
    )
    mock_job_store.get_turns = AsyncMock(return_value=[])
    mock_job_store.get_tokens = AsyncMock(return_value=[])
    mock_job_store.get_tool_event = AsyncMock(return_value=None)

    app.state.job_store = mock_job_store
    app.state.arq_redis = mock_arq_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", cookies={"session": jwt_cookie}) as client:
        resp = await client.get("/api/chat/j1/stream")

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    text = resp.text
    assert "data:" in text
    events = [
        json.loads(line[len("data:"):].strip())
        for line in text.splitlines()
        if line.startswith("data:")
    ]
    assert any(e["status"] == "done" for e in events)
