"""Tests for Canvas Apps API — deployed filter and canvas/gem endpoint (Phase 16).

Tests:
- test_list_canvas_apps_deployed_filter: GET /api/canvas/apps?deployed=true が deployed=True のみ返す
- test_list_canvas_apps_no_filter: deployed フィルタなしは全アプリを返す
"""
import pytest
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# ヘルパー: canvas_app レコードのモック
# ---------------------------------------------------------------------------

def _make_canvas_row(
    app_id: str,
    github_login: str,
    name: str,
    deployed: bool,
) -> dict:
    """テスト用 canvas_app dict_row を生成する。"""
    return {
        "app_id": app_id,
        "thread_id": None,
        "name": name,
        "html": f"<html><body>{name}</body></html>",
        "source": "canvas",
        "deployed": deployed,
        "deployed_at": datetime.now(timezone.utc) if deployed else None,
        "created_at": datetime.now(timezone.utc),
        "github_login": github_login,
    }


# ---------------------------------------------------------------------------
# テスト: GET /api/canvas/apps?deployed=true
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_canvas_apps_deployed_filter(api_client, jwt_cookie):
    """GET /api/canvas/apps?deployed=true は deployed=True のアプリのみ返す。

    Task 2 実装前は deployed=False のアプリも混入する（フィルタなし）。
    """
    deployed_row = _make_canvas_row("aaa", "user1", "Deployed App", deployed=True)
    not_deployed_row = _make_canvas_row("bbb", "user1", "Draft App", deployed=False)

    mock_cur = AsyncMock()
    mock_cur.fetchall = AsyncMock(return_value=[deployed_row])

    mock_conn_ctx = AsyncMock()
    mock_conn_ctx.__aenter__ = AsyncMock(return_value=mock_conn_ctx)
    mock_conn_ctx.__aexit__ = AsyncMock(return_value=False)
    mock_conn_ctx.cursor = MagicMock(return_value=mock_cur)
    mock_cur.__aenter__ = AsyncMock(return_value=mock_cur)
    mock_cur.__aexit__ = AsyncMock(return_value=False)
    mock_cur.execute = AsyncMock()

    with patch("psycopg.AsyncConnection.connect", return_value=mock_conn_ctx):
        resp = await api_client.get(
            "/api/canvas/apps",
            params={"deployed": "true"},
            cookies={"session": jwt_cookie},
        )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    apps = resp.json()
    # 全アプリが deployed=True であること
    for app in apps:
        assert app["deployed"] is True, (
            f"deployed=False のアプリが混入しています: {app}"
        )
    # deployed_row が含まれること
    app_ids = [a["app_id"] for a in apps]
    assert "aaa" in app_ids


@pytest.mark.asyncio
async def test_list_canvas_apps_no_filter(api_client, jwt_cookie):
    """GET /api/canvas/apps（フィルタなし）は全アプリを返す（deployed/非 deployed 混在）。"""
    deployed_row = _make_canvas_row("ccc", "user1", "Deployed App", deployed=True)
    not_deployed_row = _make_canvas_row("ddd", "user1", "Draft App", deployed=False)

    mock_cur = AsyncMock()
    mock_cur.fetchall = AsyncMock(return_value=[deployed_row, not_deployed_row])

    mock_conn_ctx = AsyncMock()
    mock_conn_ctx.__aenter__ = AsyncMock(return_value=mock_conn_ctx)
    mock_conn_ctx.__aexit__ = AsyncMock(return_value=False)
    mock_conn_ctx.cursor = MagicMock(return_value=mock_cur)
    mock_cur.__aenter__ = AsyncMock(return_value=mock_cur)
    mock_cur.__aexit__ = AsyncMock(return_value=False)
    mock_cur.execute = AsyncMock()

    with patch("psycopg.AsyncConnection.connect", return_value=mock_conn_ctx):
        resp = await api_client.get(
            "/api/canvas/apps",
            cookies={"session": jwt_cookie},
        )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    apps = resp.json()
    # deployed=True と deployed=False の両方が含まれること
    deployed_flags = {a["app_id"]: a["deployed"] for a in apps}
    assert deployed_flags.get("ccc") is True
    assert deployed_flags.get("ddd") is False


@pytest.mark.asyncio
async def test_list_canvas_apps_requires_auth(api_client):
    """GET /api/canvas/apps は JWT なしで 401 を返す。

    Phase 39 UIFIX-04 D-10 Pattern A: api_client fixture が JWT cookie を bake in
    するようになったため、無認証ケースは明示的に cookie を消去して再現する。
    """
    api_client.cookies.clear()
    resp = await api_client.get("/api/canvas/apps")
    assert resp.status_code == 401
