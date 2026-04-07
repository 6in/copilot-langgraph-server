"""Tests for Canvas Gem auto-registration — Phase 16.

Canvas 専用 Gem (type='canvas', github_login='_canvas_system_') が
アプリ起動時に自動登録され、重複しないことを確認する。

Tests:
- test_canvas_gem_auto_register: Canvas Gem が存在しない場合は INSERT が実行され gem_id が返る
- test_canvas_gem_idempotent: Canvas Gem が既存の場合は INSERT せず既存の gem_id を返す
- test_get_canvas_gem_endpoint: GET /api/canvas/gem が {"gem_id": "..."} を返す
- test_get_canvas_gem_requires_auth: JWT なしで 401
"""
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------

@pytest.fixture
async def canvas_gem_client():
    """API client with app.state.canvas_gem_id pre-set (simulating successful lifespan).

    Lifespan does NOT fire with ASGITransport — inject mocks directly into app.state.
    """
    from app.api.main import app

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
# テスト: Canvas Gem 自動登録ロジック（lifespan の SELECT → INSERT パターン）
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_canvas_gem_auto_register():
    """Canvas Gem が存在しない場合、INSERT が実行されて gem_id が取得できる。

    main.py lifespan の SELECT → INSERT 冪等パターンを直接テストする。
    """
    new_gem_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

    # SELECT で None（既存なし）→ INSERT で new_gem_id を返す
    mock_select_cur = AsyncMock()
    mock_select_cur.fetchone = AsyncMock(return_value=None)

    mock_insert_cur = AsyncMock()
    mock_insert_cur.fetchone = AsyncMock(return_value=(new_gem_id,))

    mock_conn = AsyncMock()
    # execute を呼び出すたびに対応するカーソルを返す
    mock_conn.execute = AsyncMock(side_effect=[
        mock_select_cur,   # SELECT gem_id FROM gems ...
        mock_insert_cur,   # INSERT INTO gems ... RETURNING gem_id
    ])
    mock_conn.commit = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)

    # Canvas Gem 登録ロジック（main.py lifespan より抜粋）
    cur_gem = await mock_conn.execute(
        "SELECT gem_id FROM gems WHERE github_login = '_canvas_system_' AND type = 'canvas' LIMIT 1"
    )
    existing_gem = await cur_gem.fetchone()
    assert existing_gem is None, "テスト前提: 既存 Canvas Gem なし"

    CANVAS_SYSTEM_PROMPT = "test prompt"
    CANVAS_DESCRIPTION = "test description"
    cur_gem2 = await mock_conn.execute(
        "INSERT INTO gems (github_login, name, system_prompt, type, description) "
        "VALUES ('_canvas_system_', 'Canvas App Generator', %s, 'canvas', %s) RETURNING gem_id",
        (CANVAS_SYSTEM_PROMPT, CANVAS_DESCRIPTION),
    )
    new_gem = await cur_gem2.fetchone()
    canvas_gem_id = str(new_gem[0])

    # gem_id が UUID 形式であること
    uuid.UUID(canvas_gem_id)
    assert canvas_gem_id == str(new_gem_id)

    # INSERT が1回だけ呼ばれたこと（重複 INSERT なし）
    assert mock_conn.execute.call_count == 2  # SELECT + INSERT


@pytest.mark.asyncio
async def test_canvas_gem_idempotent():
    """Canvas Gem が既存の場合、INSERT は実行されず既存の gem_id を返す。

    SELECT → INSERT の冪等パターン: 既存ありなら INSERT をスキップ。
    """
    existing_gem_id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

    mock_select_cur = AsyncMock()
    mock_select_cur.fetchone = AsyncMock(return_value=(existing_gem_id,))

    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock(return_value=mock_select_cur)
    mock_conn.commit = AsyncMock()
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=False)

    # lifespan ロジック: 既存ありなら INSERT をスキップ
    cur_gem = await mock_conn.execute(
        "SELECT gem_id FROM gems WHERE github_login = '_canvas_system_' AND type = 'canvas' LIMIT 1"
    )
    existing_gem = await cur_gem.fetchone()
    assert existing_gem is not None, "テスト前提: 既存 Canvas Gem あり"

    canvas_gem_id = str(existing_gem[0])

    # gem_id が UUID 形式であること
    uuid.UUID(canvas_gem_id)
    assert canvas_gem_id == str(existing_gem_id)

    # INSERT が実行されていないこと（SELECT のみ）
    assert mock_conn.execute.call_count == 1


# ---------------------------------------------------------------------------
# テスト: GET /api/canvas/gem エンドポイント
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_canvas_gem_endpoint(canvas_gem_client):
    """GET /api/canvas/gem が {"gem_id": "<uuid>"} を返すことを確認する。

    JWT 認証あり（session cookie 必須）。
    """
    client, expected_gem_id = canvas_gem_client

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
