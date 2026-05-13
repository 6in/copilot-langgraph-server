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
    """POST /api/chat without session cookie returns 401 auth_required.

    Phase 39 UIFIX-04 D-10 Pattern A: api_client fixture が JWT cookie を bake in
    するようになったため、無認証ケースは明示的に cookie を消去して再現する。
    """
    api_client.cookies.clear()
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


# ---------------------------------------------------------------------------
# Phase 36 Plan 03 Task 1: ChatRequest.attachments + arq enqueue_job 経由
# ---------------------------------------------------------------------------

def test_chat_request_accepts_attachments_field():
    """Phase 36 D-14: ChatRequest が attachments=[D-14 dict, ...] を valid に受ける。"""
    from app.api.models import ChatRequest
    atts = [{"kind": "file", "path": "/x", "name": "x.txt"}]
    req = ChatRequest(message="hi", thread_id="t", attachments=atts)
    assert req.attachments == atts


def test_chat_request_attachments_optional():
    """Phase 36 D-14: attachments=None (省略時のデフォルト) が valid。"""
    from app.api.models import ChatRequest
    req = ChatRequest(message="hi", thread_id="t")
    assert req.attachments is None


async def test_post_chat_forwards_attachments_to_enqueue_job(
    api_client, mock_arq_redis, jwt_cookie,
):
    """Phase 36 D-14: POST /api/chat body.attachments が enqueue_job(attachments=...) に流れる。"""
    atts = [{
        "kind": "file", "name": "sample.png",
        "storage_name": "20260423T120000_sample.png",
        "path": "/shared/thread-files/u/t-1/20260423T120000_sample.png",
        "size": 123, "mime_type": "image/png", "ext": "png",
        "modified_at": "2026-04-23T12:00:00Z",
    }]
    resp = await api_client.post(
        "/api/chat",
        json={
            "message": "これを見て", "thread_id": "t-1", "model": "claude-sonnet-4.6",
            "attachments": atts,
        },
        cookies={"session": jwt_cookie},
    )
    assert resp.status_code == 200, resp.text
    call_kwargs = mock_arq_redis.enqueue_job.call_args.kwargs
    assert call_kwargs.get("attachments") == atts


async def test_post_chat_without_attachments_passes_none(
    api_client, mock_arq_redis, jwt_cookie,
):
    """Phase 36 D-14: attachments を含まない既存 body は enqueue_job(attachments=None) で呼ばれる (後方互換)。"""
    resp = await api_client.post(
        "/api/chat",
        json={"message": "hi", "thread_id": "t-1"},
        cookies={"session": jwt_cookie},
    )
    assert resp.status_code == 200, resp.text
    call_kwargs = mock_arq_redis.enqueue_job.call_args.kwargs
    assert "attachments" in call_kwargs
    assert call_kwargs["attachments"] is None


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
    """DELETE /api/threads/{id} calls checkpointer.adelete_thread (CKPT-04).

    Phase 39 UIFIX-04 D-10 Pattern B — psycopg AsyncConnection.cursor() を
    `mock_conn.cursor = MagicMock(return_value=cursor_ctx)` 形式の async
    context manager で mock する (実装は `async with conn.cursor() as cur:` を
    使うため、cursor() は同期呼び出しで ACM を返す必要がある)。
    fetchone は ownership check を通すため jwt_cookie fixture と同じ
    github_login='unknown' を返す。
    """
    from unittest.mock import patch, AsyncMock, MagicMock
    from app.api.main import app

    mock_cursor = AsyncMock()
    mock_cursor.execute = AsyncMock(return_value=None)
    mock_cursor.fetchone = AsyncMock(return_value={"github_login": "unknown"})

    cursor_ctx = AsyncMock()
    cursor_ctx.__aenter__ = AsyncMock(return_value=mock_cursor)
    cursor_ctx.__aexit__ = AsyncMock(return_value=None)

    mock_conn = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)
    mock_conn.cursor = MagicMock(return_value=cursor_ctx)
    mock_conn.commit = AsyncMock()

    with patch("psycopg.AsyncConnection.connect", return_value=mock_conn):
        resp = await api_client.delete("/api/threads/test-thread-123")
    assert resp.status_code == 204
    app.state.checkpointer.adelete_thread.assert_called_once_with("test-thread-123")


# ---------------------------------------------------------------------------
# Phase 10: Tests for normalized schema (applications/threads). audit_log removed in Phase 31.
# These tests verify the Phase 10 implementation: app_id filter, LEFT JOIN,
# threads upsert with app_id.
# ---------------------------------------------------------------------------

async def test_list_threads_app_id_filter(api_client, jwt_cookie):
    """GET /api/threads?app_id=superchat returns only superchat threads (API-01, FE-01).

    Phase 10 behavior: threads table has app_id column; GET /api/threads accepts
    a ?app_id query param and filters results accordingly.

    Phase 39 UIFIX-04 D-10 Pattern B — psycopg AsyncConnection.cursor() を
    同期呼び出し + async context manager で mock する。
    `mock_conn.cursor.return_value.__aenter__` 形式は `mock_conn.cursor` が
    AsyncMock として coroutine を返してしまい、`async with conn.cursor() as cur:`
    が AsyncMock 内部の coroutine を await し損ねて fetchall が空 MagicMock を
    返す問題があったため `MagicMock(return_value=cursor_ctx)` 形式へ修正。
    """
    from unittest.mock import patch, AsyncMock, MagicMock

    superchat_thread_id = "test-superchat-thread-001"
    chat_thread_id = "test-chat-thread-001"

    mock_cursor = AsyncMock()
    mock_cursor.execute = AsyncMock(return_value=None)

    cursor_ctx = AsyncMock()
    cursor_ctx.__aenter__ = AsyncMock(return_value=mock_cursor)
    cursor_ctx.__aexit__ = AsyncMock(return_value=None)

    mock_conn = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)
    mock_conn.cursor = MagicMock(return_value=cursor_ctx)

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
    """GET /api/threads without ?app_id returns all threads (backward compat, API-02).

    Phase 39 UIFIX-04 D-10 Pattern B — psycopg AsyncConnection.cursor() を
    同期呼び出し + async context manager で mock する (see test_list_threads_app_id_filter)。
    """
    from unittest.mock import patch, AsyncMock, MagicMock

    mock_cursor = AsyncMock()
    mock_cursor.execute = AsyncMock(return_value=None)

    cursor_ctx = AsyncMock()
    cursor_ctx.__aenter__ = AsyncMock(return_value=mock_cursor)
    cursor_ctx.__aexit__ = AsyncMock(return_value=None)

    mock_conn = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)
    mock_conn.cursor = MagicMock(return_value=cursor_ctx)

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

    Phase 39 UIFIX-04 D-10 Pattern B — psycopg AsyncConnection.cursor() を
    同期呼び出し + async context manager で mock する (see test_list_threads_app_id_filter)。
    """
    from unittest.mock import patch, AsyncMock, MagicMock

    mock_cursor = AsyncMock()

    cursor_ctx = AsyncMock()
    cursor_ctx.__aenter__ = AsyncMock(return_value=mock_cursor)
    cursor_ctx.__aexit__ = AsyncMock(return_value=None)

    mock_conn = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)
    mock_conn.cursor = MagicMock(return_value=cursor_ctx)

    thread_no_checkpoint = {
        "thread_id": "thread-no-checkpoint-001",
        "app_id": "chat",
        "label": "New Thread (no checkpoint yet)",
        "updated_at": None,
    }
    mock_cursor.fetchall = AsyncMock(return_value=[thread_no_checkpoint])

    executed_sqls = []

    async def capture_execute(sql, params=None):
        executed_sqls.append(sql)
        return None

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


# Phase 37: delete_thread がフォルダを rm する

def _make_delete_app_state(github_login: str, thread_owner: str):
    """DELETE /api/threads テスト用の app.state セットアップとモック群を返すヘルパー。

    conftest.py の api_client fixture と同じ app.state セットアップを行う。
    github_login: JWT に埋め込む login 名
    thread_owner: threads テーブルの SELECT 結果として返す github_login
    """
    from unittest.mock import AsyncMock, MagicMock
    from app.api.main import app
    from app.auth.jwt_utils import create_jwt

    # app.state を conftest.api_client と同様にセットアップ
    mock_checkpointer = AsyncMock()
    mock_checkpointer.adelete_thread = AsyncMock(return_value=None)
    app.state.checkpointer = mock_checkpointer
    app.state.db_uri = "postgresql://test:test@localhost:5432/test"
    if not hasattr(app.state, "graph"):
        app.state.graph = MagicMock()
    if not hasattr(app.state, "job_store"):
        app.state.job_store = AsyncMock()
    if not hasattr(app.state, "arq_redis"):
        app.state.arq_redis = AsyncMock()

    token = create_jwt("ghu_test_token", github_login=github_login)

    # psycopg cursor mock — async context manager を正しく構成する
    mock_cursor = AsyncMock()
    mock_cursor.execute = AsyncMock(return_value=None)
    mock_cursor.fetchone = AsyncMock(return_value={"github_login": thread_owner})

    # cursor() は async context manager: async with conn.cursor() as cur
    cursor_ctx = AsyncMock()
    cursor_ctx.__aenter__ = AsyncMock(return_value=mock_cursor)
    cursor_ctx.__aexit__ = AsyncMock(return_value=None)

    mock_conn = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)
    mock_conn.cursor = MagicMock(return_value=cursor_ctx)
    mock_conn.commit = AsyncMock()

    return app, token, mock_conn, mock_checkpointer


@pytest.mark.asyncio
async def test_delete_thread_removes_folder():
    """FIN-04 SC-5 / D-03: DELETE /api/threads/{id} が shutil.rmtree を呼ぶ。

    フォルダが存在しない thread を削除しても 204 を返す (ignore_errors=True)。
    """
    from unittest.mock import patch
    from httpx import AsyncClient, ASGITransport

    app, token, mock_conn, _ = _make_delete_app_state("testuser", "testuser")

    with patch("psycopg.AsyncConnection.connect", return_value=mock_conn):
        with patch("app.api.routes.chat.shutil.rmtree") as mock_rm:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.delete(
                    "/api/threads/test-thread-123",
                    cookies={"session": token},
                )

    assert resp.status_code == 204
    # rmtree が 1 回呼ばれた (フォルダ不在でも ignore_errors=True で吸収)
    mock_rm.assert_called_once()
    # 第 1 引数が testuser/test-thread-123 を含むパス (realpath 解決後)
    call_args = mock_rm.call_args
    called_path = call_args.args[0] if call_args.args else call_args.kwargs.get("path", "")
    assert "testuser" in called_path
    assert "test-thread-123" in called_path
    # ignore_errors=True が kwargs に含まれる
    assert call_args.kwargs.get("ignore_errors") is True


@pytest.mark.asyncio
async def test_delete_thread_rejects_path_traversal():
    """W-01: github_login に `..` が混入しても rmtree が実行されず 204 を返す。"""
    from unittest.mock import patch
    from httpx import AsyncClient, ASGITransport

    app, token, mock_conn, _ = _make_delete_app_state("../../etc", "../../etc")

    with patch("psycopg.AsyncConnection.connect", return_value=mock_conn):
        with patch("app.api.routes.chat.shutil.rmtree") as mock_rm:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.delete(
                    "/api/threads/malicious",
                    cookies={"session": token},
                )

    assert resp.status_code == 204
    # realpath prefix assert が失敗 → rmtree は呼ばれない
    mock_rm.assert_not_called()
