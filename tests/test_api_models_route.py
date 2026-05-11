"""Phase 36 D-07/D-16 — GET /api/models の integration test.

JWT 認証 + TTL 1h キャッシュ + 503 graceful の 5 ケース.
ChatCopilot.list_models をモックして既知 dict を返させ、route layer の挙動を検証.
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_llm_list():
    """ChatCopilot.list_models のスタブ.

    2 モデル (vision 対応 / 非対応) を返す AsyncMock を生成.
    各テストの先頭で `app.state.llm = mock_llm_list` で差し替えて使う.
    """
    mock = AsyncMock()
    mock.list_models = AsyncMock(return_value=[
        {
            "id": "claude-sonnet-4.6",
            "name": "Claude Sonnet 4.6",
            "vision": True,
            "vision_limits": {
                "max_prompt_images": 5,
                "max_prompt_image_size": 10485760,
                "supported_media_types": ["image/png", "image/jpeg", "image/webp"],
            },
            "billing_multiplier": 1.0,
        },
        {
            "id": "gpt-4.1",
            "name": "GPT-4.1",
            "vision": False,
            "vision_limits": None,
            "billing_multiplier": 0.0,
        },
    ])
    return mock


def _reset_cache():
    """各テスト先頭で TTL キャッシュをクリアする (テスト順序依存を排除)."""
    from app.api.routes import models as models_module
    models_module._cache.at = 0.0
    models_module._cache.payload = []


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_models_returns_list_from_llm(api_client, jwt_cookie, mock_llm_list):
    """JWT cookie 持ちで GET /api/models → 200 + D-14 dict list."""
    _reset_cache()
    api_client._transport.app.state.llm = mock_llm_list

    resp = await api_client.get("/api/models", cookies={"session": jwt_cookie})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["id"] == "claude-sonnet-4.6"
    assert data[0]["vision"] is True
    assert data[0]["vision_limits"]["max_prompt_images"] == 5
    assert data[1]["id"] == "gpt-4.1"
    assert data[1]["vision"] is False
    assert data[1]["vision_limits"] is None


@pytest.mark.asyncio
async def test_get_models_requires_auth(api_client, mock_llm_list):
    """cookie なしで GET /api/models → 401 auth_required."""
    _reset_cache()
    api_client._transport.app.state.llm = mock_llm_list

    resp = await api_client.get("/api/models")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "auth_required"


@pytest.mark.asyncio
async def test_get_models_ttl_cache_hit(api_client, jwt_cookie, mock_llm_list):
    """1 回目で list_models 呼出、2 回目は cache hit で SDK は呼ばれない."""
    _reset_cache()
    api_client._transport.app.state.llm = mock_llm_list

    resp1 = await api_client.get("/api/models", cookies={"session": jwt_cookie})
    assert resp1.status_code == 200
    assert mock_llm_list.list_models.await_count == 1

    resp2 = await api_client.get("/api/models", cookies={"session": jwt_cookie})
    assert resp2.status_code == 200
    # cache hit なので list_models は呼ばれない
    assert mock_llm_list.list_models.await_count == 1
    # cache から返るので payload は同じ
    assert resp2.json() == resp1.json()


@pytest.mark.asyncio
async def test_get_models_cache_expires_after_ttl(api_client, jwt_cookie, mock_llm_list):
    """cache 期限切れで再度 list_models が呼ばれる."""
    _reset_cache()
    api_client._transport.app.state.llm = mock_llm_list

    resp1 = await api_client.get("/api/models", cookies={"session": jwt_cookie})
    assert resp1.status_code == 200
    # at を 3700s 前に強制変更 → 期限切れ
    import time as _time
    from app.api.routes import models as models_module
    models_module._cache.at = _time.time() - 3700

    resp2 = await api_client.get("/api/models", cookies={"session": jwt_cookie})
    assert resp2.status_code == 200
    assert mock_llm_list.list_models.await_count == 2


@pytest.mark.asyncio
async def test_get_models_failure_returns_503_when_cache_empty(api_client, jwt_cookie):
    """list_models 例外 + cache 空 → 503 で具体エラーを返す."""
    _reset_cache()

    failing = AsyncMock()
    failing.list_models = AsyncMock(side_effect=RuntimeError("SDK down"))
    api_client._transport.app.state.llm = failing

    resp = await api_client.get("/api/models", cookies={"session": jwt_cookie})
    assert resp.status_code == 503
    assert "models list unavailable" in resp.json()["detail"]
    assert "SDK down" in resp.json()["detail"]
