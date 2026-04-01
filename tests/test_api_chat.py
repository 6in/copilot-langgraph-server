"""Tests for /api/chat and /api/threads endpoints (CHAT-01, CHAT-02, CHAT-03, CHAT-04).

/api/chat is JWT-protected: tests that exercise it must supply a valid session cookie.
Thread CRUD routes are intentionally unprotected (personal tool, local SQLite only).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock


async def test_chat_returns_reply(api_client, mock_graph, jwt_cookie):
    """POST /api/chat returns AI reply with same thread_id (CHAT-01)."""
    resp = await api_client.post(
        "/api/chat",
        json={"message": "Hello", "thread_id": "test-thread-1"},
        cookies={"session": jwt_cookie},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["reply"] == "Hello from AI"
    assert data["thread_id"] == "test-thread-1"
    assert data["error"] is None


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


async def test_chat_auth_expired_error(api_client, mock_graph, jwt_cookie):
    """POST /api/chat returns error=auth_expired when SDK raises auth error."""
    mock_graph.ainvoke.side_effect = RuntimeError("Unauthorized: token expired")
    resp = await api_client.post(
        "/api/chat",
        json={"message": "test", "thread_id": "test-thread-1"},
        cookies={"session": jwt_cookie},
    )
    data = resp.json()
    assert data["error"] == "auth_expired"


async def test_chat_with_model_override(api_client, mock_graph, jwt_cookie):
    """POST /api/chat with model field overrides LLM model (D-11)."""
    resp = await api_client.post(
        "/api/chat",
        json={"message": "test", "thread_id": "t1", "model": "o3"},
        cookies={"session": jwt_cookie},
    )
    assert resp.status_code == 200
    # Verify ainvoke was called (model override happens on LLM object)
    mock_graph.ainvoke.assert_called()


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


async def test_chat_markdown_passthrough(api_client, mock_graph, jwt_cookie):
    """POST /api/chat passes through Markdown content unchanged (CHAT-03)."""
    markdown_reply = "# Title\n\n**bold** and `code`\n\n```python\nprint('hello')\n```"
    mock_graph.ainvoke.return_value = {
        "messages": [MagicMock(content=markdown_reply)]
    }
    resp = await api_client.post(
        "/api/chat",
        json={"message": "test", "thread_id": "t1"},
        cookies={"session": jwt_cookie},
    )
    data = resp.json()
    assert data["reply"] == markdown_reply
    assert "```python" in data["reply"]
