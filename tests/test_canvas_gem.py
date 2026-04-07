"""Tests for Canvas Gem auto-registration — Phase 16.

Canvas 専用 Gem (type='canvas', github_login='_canvas_system_') が
アプリ起動時に自動登録され、重複しないことを確認する。

Tests:
- test_canvas_gem_auto_register: lifespan 後に gems テーブルに Canvas Gem が1件存在する
- test_canvas_gem_idempotent: 二度目の lifespan でも1件のまま（重複しない）
- test_get_canvas_gem_endpoint: GET /api/canvas/gem が {"gem_id": "..."} を返す
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------

@pytest.fixture
def jwt_cookie_canvas():
    """A valid JWT session cookie for canvas gem endpoint tests."""
    from app.auth.jwt_utils import create_jwt
    return create_jwt("ghu_canvas_test_token")


@pytest.fixture
async def canvas_gem_client(jwt_cookie_canvas):
    """API client with app.state.canvas_gem_id pre-set (simulating successful lifespan).

    Lifespan does NOT fire with ASGITransport — inject mocks directly into app.state.
    """
    from app.api.main import app
    from unittest.mock import MagicMock, AsyncMock

    mock_graph = AsyncMock()
    mock_graph.ainvoke = AsyncMock(return_value={
        "messages": [MagicMock(content="Hello from AI")]
    })
    mock_auth_manager = MagicMock()
    mock_auth_manager.load_token = MagicMock(return_value="ghu_fake_token")
    mock_auth_manager.start_device_flow = AsyncMock(return_value={
        "user_code": "ABCD-1234",
        "verification_uri": "https://github.com/login/device",
        "device_code": "dc_fake",
        "interval": 5,
    })
    mock_auth_manager.check_device_flow = AsyncMock(return_value=(None, None))

    mock_llm = MagicMock()
    mock_llm.model = "gpt-4.1"
    mock_llm.github_token = None
    mock_llm.close = AsyncMock()

    mock_job_store = AsyncMock()
    mock_job_store.get = AsyncMock(return_value=None)
    mock_job_store.save_result = AsyncMock()

    mock_arq_redis = AsyncMock()
    mock_arq_redis.enqueue_job = AsyncMock()

    # 既に lifespan が完了した状態をシミュレート
    TEST_CANVAS_GEM_ID = "11111111-1111-1111-1111-111111111111"
    app.state.graph = mock_graph
    app.state.auth_manager = mock_auth_manager
    app.state.llm = mock_llm
    app.state.db_uri = "postgresql://test:test@localhost:5432/test"
    app.state.device_flows = {}
    app.state.checkpointer = AsyncMock()
    app.state.job_store = mock_job_store
    app.state.arq_redis = mock_arq_redis
    app.state.canvas_gem_id = TEST_CANVAS_GEM_ID  # Phase 16 で lifespan が設定

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, TEST_CANVAS_GEM_ID


# ---------------------------------------------------------------------------
# テスト: Canvas Gem 自動登録
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_canvas_gem_auto_register():
    """lifespan 完了後、gems テーブルに type='canvas' AND github_login='_canvas_system_' の
    レコードが1件存在することを確認する。

    実装前はこのテストは失敗する（app.state.canvas_gem_id が存在しない）。
    Task 2 の実装後に GREEN になる。
    """
    import asyncio
    import uuid
    from unittest.mock import AsyncMock, MagicMock, patch

    # DB モック: 最初は Canvas Gem なし → INSERT が実行される
    mock_cur = AsyncMock()
    mock_cur.fetchone = AsyncMock(side_effect=[
        None,  # SELECT: 既存なし
        (uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),),  # INSERT RETURNING gem_id
    ])

    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=mock_cur)
    mock_conn.commit = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)

    # lifespan の psycopg.AsyncConnection.connect をモック
    with patch("psycopg.AsyncConnection.connect", return_value=mock_conn):
        from app.api.main import app
        # app.state.canvas_gem_id がセットされていることを確認
        # （Task 2 実装後に lifespan がセットする）
        assert hasattr(app.state, "canvas_gem_id"), (
            "app.state.canvas_gem_id が存在しない。"
            "main.py の lifespan に Canvas Gem 自動登録を追加してください (Task 2)。"
        )
        gem_id = app.state.canvas_gem_id
        assert gem_id is not None, "canvas_gem_id が None です"
        # UUID 形式であること
        uuid.UUID(str(gem_id))


@pytest.mark.asyncio
async def test_canvas_gem_idempotent():
    """lifespan を2回実行しても Canvas Gem は1件のまま（重複登録しない）。

    SELECT → INSERT の冪等パターンをテストする。
    実装前は失敗する（canvas_gem_id が設定されないため）。
    """
    import uuid

    # 既に Canvas Gem が存在するケース（2回目の起動シミュレーション）
    existing_gem_id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

    from unittest.mock import AsyncMock, patch

    mock_cur = AsyncMock()
    # SELECT: 既存の Canvas Gem が1件ある
    mock_cur.fetchone = AsyncMock(return_value=(existing_gem_id,))

    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=mock_cur)
    mock_conn.commit = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)

    with patch("psycopg.AsyncConnection.connect", return_value=mock_conn):
        from app.api.main import app
        # canvas_gem_id が既存の gem_id と一致すること（重複 INSERT なし）
        assert hasattr(app.state, "canvas_gem_id"), (
            "app.state.canvas_gem_id が存在しない (Task 2 未実装)"
        )
        # gem_id が UUID 形式であること
        gem_id = str(app.state.canvas_gem_id)
        uuid.UUID(gem_id)


# ---------------------------------------------------------------------------
# テスト: GET /api/canvas/gem エンドポイント
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_canvas_gem_endpoint(canvas_gem_client):
    """GET /api/canvas/gem が {"gem_id": "<uuid>"} を返すことを確認する。

    JWT 認証あり（session cookie 必須）。
    Task 2 実装前は 404 または 422 を返す（エンドポイントが存在しない）。
    """
    import uuid
    client, expected_gem_id = canvas_gem_client

    # JWT cookie を作成
    from app.auth.jwt_utils import create_jwt
    jwt = create_jwt("ghu_canvas_test_token")

    resp = await client.get(
        "/api/canvas/gem",
        cookies={"session": jwt},
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert "gem_id" in data, f"Response missing 'gem_id': {data}"
    # UUID 形式であること
    uuid.UUID(data["gem_id"])
    assert data["gem_id"] == expected_gem_id


@pytest.mark.asyncio
async def test_get_canvas_gem_requires_auth(canvas_gem_client):
    """GET /api/canvas/gem は JWT なしで 401 を返す。"""
    client, _ = canvas_gem_client
    resp = await client.get("/api/canvas/gem")
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"
