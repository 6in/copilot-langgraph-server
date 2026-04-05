"""Integration tests for GET /api/apps route — APP-01, APP-02, T-14-01, T-14-02.

Tests run with: uv run pytest tests/test_apps_route.py -x -q
"""
import os
from pathlib import Path
from unittest.mock import patch

import pytest


def _write_app_md(directory: Path, content: str) -> None:
    """Helper to write an APP.md file."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "APP.md").write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Test 1: GET /api/apps returns list of AppInfo with correct structure (APP-02)
# ---------------------------------------------------------------------------

async def test_get_apps_returns_list(api_client, jwt_cookie, tmp_path):
    """GET /api/apps returns list of apps from APP.md files."""
    _write_app_md(
        tmp_path / "chat",
        "---\nname: Chat\ndescription: AI chat\nicon: \U0001f4ac\nagents:\n  - general-assistant\n---\n",
    )
    _write_app_md(
        tmp_path / "superchat",
        "---\nname: SuperChat\ndescription: Multi-agent\nicon: \u26a1\nagents:\n  - code-reviewer\n---\n",
    )

    with patch.dict(os.environ, {"APP_DIR": str(tmp_path)}):
        resp = await api_client.get(
            "/api/apps",
            cookies={"session": jwt_cookie},
        )

    assert resp.status_code == 200
    apps = resp.json()
    assert isinstance(apps, list)
    assert len(apps) == 2

    slugs = {a["slug"] for a in apps}
    assert slugs == {"chat", "superchat"}

    chat = next(a for a in apps if a["slug"] == "chat")
    assert chat["name"] == "Chat"
    assert chat["description"] == "AI chat"
    assert chat["icon"] == "\U0001f4ac"
    assert "general-assistant" in chat["agents"]


# ---------------------------------------------------------------------------
# Test 2: GET /api/apps requires JWT — 401 without cookie (T-14-01)
# ---------------------------------------------------------------------------

async def test_get_apps_requires_jwt(api_client, tmp_path):
    """GET /api/apps without session cookie returns 401 auth_required."""
    with patch.dict(os.environ, {"APP_DIR": str(tmp_path)}):
        resp = await api_client.get("/api/apps")

    assert resp.status_code == 401
    assert resp.json()["detail"] == "auth_required"


# ---------------------------------------------------------------------------
# Test 3: GET /api/apps with empty apps dir returns empty list
# ---------------------------------------------------------------------------

async def test_get_apps_empty_dir(api_client, jwt_cookie, tmp_path):
    """GET /api/apps with empty directory returns []."""
    with patch.dict(os.environ, {"APP_DIR": str(tmp_path)}):
        resp = await api_client.get(
            "/api/apps",
            cookies={"session": jwt_cookie},
        )

    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# Test 4: ChatRequest accepts app_id field (backward compat + new field)
# ---------------------------------------------------------------------------

async def test_chat_request_accepts_app_id(api_client, mock_arq_redis, jwt_cookie):
    """POST /api/chat with app_id field is accepted; app_id flows into enqueue."""
    resp = await api_client.post(
        "/api/chat",
        json={
            "message": "Hello",
            "thread_id": "test-thread-app",
            "app_id": "chat",
        },
        cookies={"session": jwt_cookie},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "job_id" in data
    assert data["thread_id"] == "test-thread-app"

    # Verify enqueue was called (app_id propagation checked separately)
    mock_arq_redis.enqueue_job.assert_called_once()
    call_kwargs = mock_arq_redis.enqueue_job.call_args.kwargs
    assert call_kwargs.get("app_id") == "chat"


# ---------------------------------------------------------------------------
# Test 5: GET /api/apps response structure matches AppInfo schema
# ---------------------------------------------------------------------------

async def test_get_apps_response_has_required_fields(api_client, jwt_cookie, tmp_path):
    """Each app in GET /api/apps response has slug, name, description, icon, agents."""
    _write_app_md(
        tmp_path / "myapp",
        "---\nname: My App\ndescription: test\nicon: X\nagents:\n  - general-assistant\n---\n",
    )

    with patch.dict(os.environ, {"APP_DIR": str(tmp_path)}):
        resp = await api_client.get(
            "/api/apps",
            cookies={"session": jwt_cookie},
        )

    assert resp.status_code == 200
    apps = resp.json()
    assert len(apps) == 1
    app = apps[0]
    for field in ("slug", "name", "description", "icon", "agents"):
        assert field in app, f"Missing field: {field}"
    assert isinstance(app["agents"], list)
