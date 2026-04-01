"""Tests for GET /api/job/{job_id} polling endpoint (ASYNC-02)."""
import pytest
from unittest.mock import AsyncMock


async def test_get_job_pending(api_client, mock_job_store):
    """GET /api/job/{id} returns {'status': 'pending'} before completion (ASYNC-02)."""
    mock_job_store.get = AsyncMock(return_value=None)
    resp = await api_client.get("/api/job/j1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "pending"
    assert data["result"] is None


async def test_get_job_done(api_client, mock_job_store):
    """GET /api/job/{id} returns done result after save_result (ASYNC-02)."""
    mock_job_store.get = AsyncMock(return_value={"status": "done", "result": "AI reply"})
    resp = await api_client.get("/api/job/j1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "done"
    assert data["result"] == "AI reply"
