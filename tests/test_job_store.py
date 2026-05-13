"""Tests for app.jobs.job_store (ASYNC-03, ASYNC-05)."""
import pytest
from unittest.mock import AsyncMock

from app.jobs.job_store import JobStore


@pytest.fixture
def mock_redis():
    """AsyncMock Redis client."""
    r = AsyncMock()
    r.set = AsyncMock()
    r.get = AsyncMock(return_value=None)
    return r


@pytest.mark.asyncio
async def test_save_and_get(mock_redis):
    """JobStore.save_result() stores data; get() retrieves it (ASYNC-03)."""
    store = JobStore(mock_redis)

    await store.save_result("j1", "hello")

    mock_redis.set.assert_called_once()
    call_args = mock_redis.set.call_args
    assert call_args[0][0] == "job:j1"

    mock_redis.get = AsyncMock(return_value=b'{"status":"done","result":"hello"}')
    result = await store.get("j1")
    assert result == {"status": "done", "result": "hello"}


@pytest.mark.asyncio
async def test_get_missing(mock_redis):
    """JobStore.get() returns None for an unknown job_id (ASYNC-03)."""
    mock_redis.get = AsyncMock(return_value=None)
    store = JobStore(mock_redis)

    result = await store.get("unknown")
    assert result is None


@pytest.mark.asyncio
async def test_notify_no_queue(mock_redis):
    """JobStore.notify() is a no-op stub and does not raise (Phase 39 UIFIX-03 D-06 — no-op stub 契約)."""
    store = JobStore(mock_redis)
    # Must not raise
    await store.notify("no-such-job", "done")
