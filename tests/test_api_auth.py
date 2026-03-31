"""Tests for /api/auth/* endpoints (AUTH-03)."""
import pytest


async def test_auth_status_no_token(api_client, mock_auth_manager):
    """GET /api/auth/status with no token returns {authenticated: false}."""
    mock_auth_manager.load_token.return_value = None
    resp = await api_client.get("/api/auth/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["authenticated"] is False
    assert data["expired"] is False


async def test_auth_status_with_token(api_client, mock_auth_manager):
    """GET /api/auth/status with valid token returns {authenticated: true}."""
    mock_auth_manager.load_token.return_value = "ghu_valid"
    resp = await api_client.get("/api/auth/status")
    assert resp.status_code == 200
    assert resp.json()["authenticated"] is True


async def test_auth_status_expired(api_client, mock_auth_manager):
    """GET /api/auth/status when expired returns {expired: true}."""
    mock_auth_manager.load_token.return_value = "ghu_old"
    # Simulate that chat route detected expiry
    from app.api.main import app
    app.state.auth_expired = True
    resp = await api_client.get("/api/auth/status")
    data = resp.json()
    assert data["authenticated"] is False
    assert data["expired"] is True
    app.state.auth_expired = False  # cleanup


async def test_auth_start_returns_codes(api_client, mock_auth_manager):
    """POST /api/auth/start returns user_code and verification_uri."""
    resp = await api_client.post("/api/auth/start")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_code"] == "ABCD-1234"
    assert data["verification_uri"] == "https://github.com/login/device"
    assert "device_code" in data


async def test_auth_poll_pending(api_client, mock_auth_manager):
    """GET /api/auth/poll returns {done: false} when pending."""
    # Start a flow first
    await api_client.post("/api/auth/start")
    resp = await api_client.get("/api/auth/poll")
    assert resp.status_code == 200
    assert resp.json()["done"] is False


async def test_auth_poll_success(api_client, mock_auth_manager):
    """GET /api/auth/poll returns {done: true} when token obtained."""
    mock_auth_manager.check_device_flow.return_value = "ghu_new_token"
    await api_client.post("/api/auth/start")
    resp = await api_client.get("/api/auth/poll")
    assert resp.status_code == 200
    assert resp.json()["done"] is True
