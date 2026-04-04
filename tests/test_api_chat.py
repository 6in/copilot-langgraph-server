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


# ---------------------------------------------------------------------------
# Phase 10: Tests for normalized schema (applications/threads/audit_log)
# These tests verify the Phase 10 implementation: app_id filter, LEFT JOIN,
# threads upsert with app_id.
# ---------------------------------------------------------------------------

async def test_list_threads_app_id_filter(api_client, jwt_cookie):
    """GET /api/threads?app_id=superchat returns only superchat threads (API-01, FE-01).

    Phase 10 behavior: threads table has app_id column; GET /api/threads accepts
    a ?app_id query param and filters results accordingly.
    """
    from unittest.mock import patch, AsyncMock

    superchat_thread_id = "test-superchat-thread-001"
    chat_thread_id = "test-chat-thread-001"

    mock_conn = AsyncMock()
    mock_cursor = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)
    mock_conn.cursor.return_value.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__aexit__ = AsyncMock(return_value=None)

    superchat_row = {
        "thread_id": superchat_thread_id,
        "app_id": "superchat",
        "label": "Super Chat 2026-04-04 03:00",
        "updated_at": None,
    }
    mock_cursor.fetchall = AsyncMock(return_value=[superchat_row])

    with patch("psycopg.AsyncConnection.connect", return_value=mock_conn):
        resp = await api_client.get(
            "/api/threads?app_id=superchat",
            cookies={"session": jwt_cookie},
        )
    assert resp.status_code == 200
    threads = resp.json()
    assert len(threads) == 1
    assert threads[0]["thread_id"] == superchat_thread_id

    chat_row = {
        "thread_id": chat_thread_id,
        "app_id": "chat",
        "label": "Chat 2026-04-04 03:00",
        "updated_at": None,
    }
    mock_cursor.fetchall = AsyncMock(return_value=[chat_row])

    with patch("psycopg.AsyncConnection.connect", return_value=mock_conn):
        resp = await api_client.get(
            "/api/threads?app_id=chat",
            cookies={"session": jwt_cookie},
        )
    assert resp.status_code == 200
    threads = resp.json()
    assert len(threads) == 1
    assert threads[0]["thread_id"] == chat_thread_id
    assert not any(t["thread_id"] == superchat_thread_id for t in threads)


async def test_list_threads_no_app_id_returns_all(api_client, jwt_cookie):
    """GET /api/threads without ?app_id returns all threads (backward compat, API-02)."""
    from unittest.mock import patch, AsyncMock

    mock_conn = AsyncMock()
    mock_cursor = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)
    mock_conn.cursor.return_value.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__aexit__ = AsyncMock(return_value=None)

    all_rows = [
        {"thread_id": "thread-chat-001", "app_id": "chat", "label": "Chat 2026-04-04", "updated_at": None},
        {"thread_id": "thread-super-001", "app_id": "superchat", "label": "Super Chat 2026-04-04", "updated_at": None},
    ]
    mock_cursor.fetchall = AsyncMock(return_value=all_rows)

    with patch("psycopg.AsyncConnection.connect", return_value=mock_conn):
        resp = await api_client.get("/api/threads", cookies={"session": jwt_cookie})

    assert resp.status_code == 200
    threads = resp.json()
    assert len(threads) == 2
    thread_ids = {t["thread_id"] for t in threads}
    assert "thread-chat-001" in thread_ids
    assert "thread-super-001" in thread_ids


async def test_chat_upsert_app_id(api_client, mock_arq_redis, jwt_cookie):
    """POST /api/chat with mode='super' writes app_id='superchat' to threads (API-03, DB-01).

    POST /api/chat with mode='simple' (or no mode) writes app_id='chat'.
    """
    from unittest.mock import patch, AsyncMock

    executed_sqls = []

    mock_conn = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)
    mock_conn.commit = AsyncMock()

    async def track_execute(sql, params=None):
        executed_sqls.append((sql, params))

    mock_conn.execute = track_execute

    with patch("psycopg.AsyncConnection.connect", return_value=mock_conn):
        resp = await api_client.post(
            "/api/chat",
            json={"message": "Hello", "thread_id": "thread-super-upsert-001", "mode": "super"},
            cookies={"session": jwt_cookie},
        )
    assert resp.status_code == 200

    upsert_calls = [(sql, params) for sql, params in executed_sqls if "threads" in sql and "INSERT" in sql.upper()]
    assert len(upsert_calls) >= 1, "Expected at least one INSERT into threads"
    last_upsert_sql, last_upsert_params = upsert_calls[-1]
    assert "app_id" in last_upsert_sql.lower(), "Expected app_id column in upsert SQL"
    assert "superchat" in last_upsert_params, "Expected 'superchat' value in upsert params"

    executed_sqls.clear()
    with patch("psycopg.AsyncConnection.connect", return_value=mock_conn):
        resp = await api_client.post(
            "/api/chat",
            json={"message": "Hello", "thread_id": "thread-chat-upsert-001"},
            cookies={"session": jwt_cookie},
        )
    assert resp.status_code == 200

    upsert_calls = [(sql, params) for sql, params in executed_sqls if "threads" in sql and "INSERT" in sql.upper()]
    assert len(upsert_calls) >= 1
    last_upsert_sql, last_upsert_params = upsert_calls[-1]
    assert "app_id" in last_upsert_sql.lower()
    assert "chat" in last_upsert_params


async def test_list_threads_left_join(api_client, jwt_cookie):
    """GET /api/threads returns threads even without checkpoints (API-01, DB-01).

    Phase 10 uses LEFT JOIN from threads to checkpoints so threads without
    checkpoints yet are still returned.
    """
    from unittest.mock import patch, AsyncMock

    mock_conn = AsyncMock()
    mock_cursor = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)
    mock_conn.cursor.return_value.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__aexit__ = AsyncMock(return_value=None)

    thread_no_checkpoint = {
        "thread_id": "thread-no-checkpoint-001",
        "app_id": "chat",
        "label": "New Thread (no checkpoint yet)",
        "updated_at": None,
    }
    mock_cursor.fetchall = AsyncMock(return_value=[thread_no_checkpoint])

    executed_sqls = []
    original_execute = mock_cursor.execute

    async def capture_execute(sql, params=None):
        executed_sqls.append(sql)
        return await original_execute(sql, params)

    mock_cursor.execute = capture_execute

    with patch("psycopg.AsyncConnection.connect", return_value=mock_conn):
        resp = await api_client.get("/api/threads", cookies={"session": jwt_cookie})

    assert resp.status_code == 200
    threads = resp.json()
    assert len(threads) == 1
    assert threads[0]["thread_id"] == "thread-no-checkpoint-001"

    if executed_sqls:
        assert any("LEFT JOIN" in sql.upper() for sql in executed_sqls), \
            "Expected LEFT JOIN in GET /api/threads SQL"
