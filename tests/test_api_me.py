"""Tests for GET /api/me — GitHub user profile endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


MOCK_GITHUB_USER = {
    "login": "testuser",
    "name": "Test User",
    "avatar_url": "https://avatars.githubusercontent.com/u/1?v=4",
    "id": 1,
}


def _mock_httpx_success():
    """Return a context-manager mock for httpx.AsyncClient that returns MOCK_GITHUB_USER."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_GITHUB_USER

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)

    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    return mock_cm


def _mock_httpx_error(status_code: int = 500):
    """Return a context-manager mock for httpx.AsyncClient that returns an error."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = {"message": "Internal Server Error"}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)

    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    return mock_cm


@pytest.mark.asyncio
async def test_get_me_success(api_client, jwt_cookie):
    with patch("app.api.routes.me.httpx.AsyncClient", return_value=_mock_httpx_success()):
        resp = await api_client.get("/api/me", cookies={"session": jwt_cookie})
    assert resp.status_code == 200
    data = resp.json()
    assert data["login"] == "testuser"
    assert data["name"] == "Test User"
    assert data["avatar_url"].startswith("https://avatars.githubusercontent.com")


@pytest.mark.asyncio
async def test_get_me_no_cookie(api_client):
    """Phase 39 UIFIX-04 D-10 Pattern A: api_client fixture が JWT cookie を bake in
    するようになったため、無認証ケースは明示的に cookie を消去して再現する。"""
    api_client.cookies.clear()
    resp = await api_client.get("/api/me")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Not authenticated"


@pytest.mark.asyncio
async def test_get_me_expired_cookie(api_client):
    from app.auth.jwt_utils import create_jwt
    expired_token = create_jwt("ghu_expired", expires_minutes=-1)
    resp = await api_client.get("/api/me", cookies={"session": expired_token})
    assert resp.status_code == 401
    assert "expired" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_me_github_error(api_client, jwt_cookie):
    with patch("app.api.routes.me.httpx.AsyncClient", return_value=_mock_httpx_error(500)):
        resp = await api_client.get("/api/me", cookies={"session": jwt_cookie})
    assert resp.status_code == 502
    assert resp.json()["detail"] == "GitHub API error"
