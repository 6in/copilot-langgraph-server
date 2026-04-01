"""Tests for /api/auth/* endpoints (AUTH-03).

Updated for JWT-cookie based auth: auth status is now derived from the
session cookie, not from auth_manager.load_token().
"""
import pytest


async def test_auth_status_no_cookie(api_client):
    """GET /api/auth/status with no cookie returns {authenticated: false}."""
    resp = await api_client.get("/api/auth/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["authenticated"] is False
    assert data["expired"] is False


async def test_auth_status_with_valid_jwt_cookie(api_client):
    """GET /api/auth/status with valid JWT cookie returns {authenticated: true}."""
    from app.auth.jwt_utils import create_jwt
    jwt_token = create_jwt("ghu_test_token")
    resp = await api_client.get("/api/auth/status", cookies={"session": jwt_token})
    assert resp.status_code == 200
    assert resp.json()["authenticated"] is True
    assert resp.json()["expired"] is False


async def test_auth_status_with_expired_jwt(api_client):
    """GET /api/auth/status with expired JWT returns {expired: true}."""
    from app.auth.jwt_utils import create_jwt
    expired_token = create_jwt("ghu_expired", expires_minutes=-1)
    resp = await api_client.get("/api/auth/status", cookies={"session": expired_token})
    assert resp.status_code == 200
    data = resp.json()
    assert data["authenticated"] is False
    assert data["expired"] is True


async def test_auth_start_returns_codes_and_flow_id(api_client, mock_auth_manager):
    """POST /api/auth/start returns user_code, verification_uri, and flow_id."""
    resp = await api_client.post("/api/auth/start")
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_code"] == "ABCD-1234"
    assert data["verification_uri"] == "https://github.com/login/device"
    assert "device_code" in data
    assert "flow_id" in data
    assert len(data["flow_id"]) == 32  # uuid4().hex is 32 chars


async def test_auth_poll_pending(api_client, mock_auth_manager):
    """GET /api/auth/poll returns {done: false} when pending."""
    # Start a flow first to get flow_id
    start_resp = await api_client.post("/api/auth/start")
    flow_id = start_resp.json()["flow_id"]

    resp = await api_client.get(f"/api/auth/poll?flow_id={flow_id}")
    assert resp.status_code == 200
    assert resp.json()["done"] is False


async def test_auth_poll_success_sets_cookie(api_client, mock_auth_manager):
    """GET /api/auth/poll returns {done: true} and sets session cookie on success."""
    mock_auth_manager.check_device_flow.return_value = "ghu_new_token"
    start_resp = await api_client.post("/api/auth/start")
    flow_id = start_resp.json()["flow_id"]

    resp = await api_client.get(f"/api/auth/poll?flow_id={flow_id}")
    assert resp.status_code == 200
    assert resp.json()["done"] is True

    # Session cookie should be set
    set_cookie = resp.headers.get("set-cookie", "")
    assert "session" in set_cookie
    assert "HttpOnly" in set_cookie


async def test_auth_poll_no_flow_id_match(api_client):
    """GET /api/auth/poll with unknown flow_id returns error."""
    resp = await api_client.get("/api/auth/poll?flow_id=nonexistent_flow_id")
    assert resp.status_code == 200
    data = resp.json()
    assert data["done"] is False
    assert "error" in data


async def test_logout_clears_cookie(api_client):
    """POST /api/auth/logout sets delete-cookie header and blocklists JTI."""
    from app.auth.jwt_utils import create_jwt, is_blocked, _blocklist, decode_jwt

    jwt_token = create_jwt("ghu_logout_test")
    payload = decode_jwt(jwt_token)
    jti = payload["jti"]

    try:
        resp = await api_client.post(
            "/api/auth/logout",
            cookies={"session": jwt_token},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        # JTI should be blocklisted
        assert is_blocked(jti)

        # Cookie should be cleared
        set_cookie = resp.headers.get("set-cookie", "")
        assert "session" in set_cookie
    finally:
        _blocklist.discard(jti)
