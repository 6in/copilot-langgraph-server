"""Tests for /api/chat and /api/threads endpoints (CHAT-01..04, ASYNC-01).

/api/chat is JWT-protected: tests that exercise it must supply a valid session cookie.
Thread CRUD routes are intentionally unprotected (personal tool, local PostgreSQL data only).

Phase 4 change: POST /api/chat now returns {job_id, thread_id} instead of {reply, thread_id}.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock


async def test_post_chat_returns_job_id(api_client, mock_arq_redis, jwt_cookie):
    """POST /api/chat returns job_id and thread_id immediately (ASYNC-01)."""
    resp = await api_client.post(
        "/api/chat",
        json={"message": "Hello", "thread_id": "test-thread-1"},
        cookies={"session": jwt_cookie},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "job_id" in data
    assert data["thread_id"] == "test-thread-1"
    mock_arq_redis.enqueue_job.assert_called_once()


async def test_chat_requires_auth(api_client):
    """POST /api/chat without session cookie returns 401 auth_required."""
    resp = await api_client.post("/api/chat", json={
        "message": "Hello",
        "thread_id": "test-thread-1",
    })
    assert resp.status_code == 401
    assert resp.json()["detail"] == "auth_required"


async def test_chat_rejects_empty_message(api_client, jwt_cookie):
    """POST /api/chat with missing message field returns 422 (CHAT-02)."""
    resp = await api_client.post(
        "/api/chat",
        json={"thread_id": "test-thread-1"},
        cookies={"session": jwt_cookie},
    )
    assert resp.status_code == 422


async def test_chat_enqueue_includes_model(api_client, mock_arq_redis, jwt_cookie):
    """POST /api/chat with model='o3' passes model kwarg to enqueue_job."""
    resp = await api_client.post(
        "/api/chat",
        json={"message": "test", "thread_id": "t1", "model": "o3"},
        cookies={"session": jwt_cookie},
    )
    assert resp.status_code == 200
    call_kwargs = mock_arq_redis.enqueue_job.call_args.kwargs
    assert call_kwargs["model"] == "o3"


async def test_chat_enqueue_includes_github_token(api_client, mock_arq_redis, jwt_cookie):
    """POST /api/chat passes decrypted github_token to enqueue_job kwargs."""
    resp = await api_client.post(
        "/api/chat",
        json={"message": "test", "thread_id": "t1"},
        cookies={"session": jwt_cookie},
    )
    assert resp.status_code == 200
    call_kwargs = mock_arq_redis.enqueue_job.call_args.kwargs
    assert "github_token" in call_kwargs
    assert call_kwargs["github_token"] == "ghu_test_token_for_chat"


async def test_new_thread_returns_uuid(api_client):
    """POST /api/threads returns a valid UUID4 thread_id (CHAT-04)."""
    import uuid
    resp = await api_client.post("/api/threads")
    assert resp.status_code == 200
    data = resp.json()
    assert "thread_id" in data
    # Verify UUID format
    uuid.UUID(data["thread_id"], version=4)
    assert "label" in data
    assert data["label"].startswith("Chat ")


async def test_list_threads_empty(api_client):
    """GET /api/threads returns empty list when no conversations exist."""
    resp = await api_client.get("/api/threads")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_delete_thread_calls_adelete(api_client):
    """DELETE /api/threads/{id} calls checkpointer.adelete_thread (CKPT-04)."""
    from app.api.main import app
    resp = await api_client.delete("/api/threads/test-thread-123")
    assert resp.status_code == 204
    app.state.checkpointer.adelete_thread.assert_called_once_with("test-thread-123")
