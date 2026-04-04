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
# Phase 10 Wave 0: Failing tests for mode column, LEFT JOIN, mode upsert
# These tests are SKIPPED until Wave 1-2 implement production code changes.
# ---------------------------------------------------------------------------

@pytest.mark.skip(reason="Phase 10 Wave 0: will pass after Wave 1-2")
async def test_list_threads_mode_filter(api_client, mock_arq_redis, jwt_cookie):
    """GET /api/threads?mode=superchat returns only superchat threads (DB-01, API-02).

    Phase 10 behavior: thread_labels has a mode column; GET /api/threads accepts
    a ?mode query param and filters results accordingly.
    """
    from unittest.mock import patch, AsyncMock, MagicMock

    # --- setup: POST /api/chat with mode='super' creates a superchat thread ---
    superchat_thread_id = "test-superchat-thread-001"
    chat_thread_id = "test-chat-thread-001"

    # Mock psycopg connection for both POST /api/chat upserts and GET /api/threads queries
    mock_conn = AsyncMock()
    mock_cursor = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)
    mock_conn.cursor.return_value.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__aexit__ = AsyncMock(return_value=None)

    # Simulate GET /api/threads?mode=superchat returning the superchat thread
    superchat_row = {
        "thread_id": superchat_thread_id,
        "latest": "abc123",
        "label": "Super Chat 2026-04-04 03:00",
        "updated_at": None,
        "mode": "superchat",
    }
    mock_cursor.fetchall = AsyncMock(return_value=[superchat_row])

    with patch("psycopg.AsyncConnection.connect", return_value=mock_conn):
        # GET /api/threads?mode=superchat should return the superchat thread
        resp = await api_client.get(
            "/api/threads?mode=superchat",
            cookies={"session": jwt_cookie},
        )
    assert resp.status_code == 200
    threads = resp.json()
    assert len(threads) == 1
    assert threads[0]["thread_id"] == superchat_thread_id

    # GET /api/threads?mode=chat should NOT return the superchat thread
    chat_row = {
        "thread_id": chat_thread_id,
        "latest": "def456",
        "label": "Chat 2026-04-04 03:00",
        "updated_at": None,
        "mode": "chat",
    }
    mock_cursor.fetchall = AsyncMock(return_value=[chat_row])

    with patch("psycopg.AsyncConnection.connect", return_value=mock_conn):
        resp = await api_client.get(
            "/api/threads?mode=chat",
            cookies={"session": jwt_cookie},
        )
    assert resp.status_code == 200
    threads = resp.json()
    assert len(threads) == 1
    assert threads[0]["thread_id"] == chat_thread_id
    # Superchat thread must NOT appear in chat mode filter
    assert not any(t["thread_id"] == superchat_thread_id for t in threads)


@pytest.mark.skip(reason="Phase 10 Wave 0: will pass after Wave 1-2")
async def test_list_threads_no_mode_returns_all(api_client, jwt_cookie):
    """GET /api/threads without ?mode returns all threads (backward compat, API-02).

    Validates Pitfall 5 from RESEARCH.md: no mode param must not break existing clients.
    """
    from unittest.mock import patch, AsyncMock

    mock_conn = AsyncMock()
    mock_cursor = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)
    mock_conn.cursor.return_value.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__aexit__ = AsyncMock(return_value=None)

    # Both chat and superchat threads returned when no mode filter
    all_rows = [
        {
            "thread_id": "thread-chat-001",
            "latest": "aaa",
            "label": "Chat 2026-04-04",
            "updated_at": None,
            "mode": "chat",
        },
        {
            "thread_id": "thread-super-001",
            "latest": "bbb",
            "label": "Super Chat 2026-04-04",
            "updated_at": None,
            "mode": "superchat",
        },
    ]
    mock_cursor.fetchall = AsyncMock(return_value=all_rows)

    with patch("psycopg.AsyncConnection.connect", return_value=mock_conn):
        resp = await api_client.get(
            "/api/threads",
            cookies={"session": jwt_cookie},
        )

    assert resp.status_code == 200
    threads = resp.json()
    assert len(threads) == 2
    thread_ids = {t["thread_id"] for t in threads}
    assert "thread-chat-001" in thread_ids
    assert "thread-super-001" in thread_ids


@pytest.mark.skip(reason="Phase 10 Wave 0: will pass after Wave 1-2")
async def test_chat_upsert_mode(api_client, mock_arq_redis, jwt_cookie):
    """POST /api/chat with mode='super' writes mode='superchat' to thread_labels (DB-01, API-01).

    POST /api/chat with mode='simple' (or no mode) writes mode='chat'.
    This tests the upsert SQL includes the mode column.
    """
    from unittest.mock import patch, AsyncMock, call

    # Track all SQL statements executed
    executed_sqls = []

    mock_conn = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)
    mock_conn.commit = AsyncMock()

    async def track_execute(sql, params=None):
        executed_sqls.append((sql, params))

    mock_conn.execute = track_execute

    with patch("psycopg.AsyncConnection.connect", return_value=mock_conn):
        # POST with mode='super' should upsert mode='superchat'
        resp = await api_client.post(
            "/api/chat",
            json={"message": "Hello", "thread_id": "thread-super-upsert-001", "mode": "super"},
            cookies={"session": jwt_cookie},
        )
    assert resp.status_code == 200

    # Find the INSERT into thread_labels
    upsert_calls = [(sql, params) for sql, params in executed_sqls if "thread_labels" in sql]
    assert len(upsert_calls) >= 1, "Expected at least one INSERT into thread_labels"
    # The upsert should include mode='superchat'
    last_upsert_sql, last_upsert_params = upsert_calls[-1]
    assert "mode" in last_upsert_sql.lower(), "Expected mode column in upsert SQL"
    assert "superchat" in last_upsert_params, "Expected 'superchat' value in upsert params"

    # POST without mode should upsert mode='chat'
    executed_sqls.clear()
    with patch("psycopg.AsyncConnection.connect", return_value=mock_conn):
        resp = await api_client.post(
            "/api/chat",
            json={"message": "Hello", "thread_id": "thread-chat-upsert-001"},
            cookies={"session": jwt_cookie},
        )
    assert resp.status_code == 200

    upsert_calls = [(sql, params) for sql, params in executed_sqls if "thread_labels" in sql]
    assert len(upsert_calls) >= 1
    last_upsert_sql, last_upsert_params = upsert_calls[-1]
    assert "mode" in last_upsert_sql.lower()
    assert "chat" in last_upsert_params


@pytest.mark.skip(reason="Phase 10 Wave 0: will pass after Wave 1-2")
async def test_list_threads_left_join(api_client, jwt_cookie):
    """GET /api/threads returns threads from thread_labels even without checkpoints (API-03).

    Phase 10 change: the SQL uses LEFT JOIN instead of INNER JOIN, so threads
    that have a thread_labels row but no checkpoint yet are still returned.
    (Currently INNER JOIN excludes such threads — this test ensures the fix works.)
    """
    from unittest.mock import patch, AsyncMock

    mock_conn = AsyncMock()
    mock_cursor = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)
    mock_conn.cursor.return_value.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__aexit__ = AsyncMock(return_value=None)

    # A thread that exists in thread_labels but has no checkpoint row yet
    # With LEFT JOIN, this should still appear
    thread_no_checkpoint = {
        "thread_id": "thread-labels-only-001",
        "latest": None,  # NULL because no checkpoint
        "label": "New Thread (no checkpoint yet)",
        "updated_at": None,
        "mode": "chat",
    }
    mock_cursor.fetchall = AsyncMock(return_value=[thread_no_checkpoint])

    # Capture the SQL to verify LEFT JOIN is used
    executed_sqls = []
    original_execute = mock_cursor.execute

    async def capture_execute(sql, params=None):
        executed_sqls.append(sql)
        return await original_execute(sql, params)

    mock_cursor.execute = capture_execute

    with patch("psycopg.AsyncConnection.connect", return_value=mock_conn):
        resp = await api_client.get(
            "/api/threads",
            cookies={"session": jwt_cookie},
        )

    assert resp.status_code == 200
    threads = resp.json()
    assert len(threads) == 1
    assert threads[0]["thread_id"] == "thread-labels-only-001"

    # Verify LEFT JOIN is used in the SQL (not INNER JOIN)
    if executed_sqls:
        assert any("LEFT JOIN" in sql.upper() for sql in executed_sqls), \
            "Expected LEFT JOIN in GET /api/threads SQL, but found INNER JOIN or no JOIN"
