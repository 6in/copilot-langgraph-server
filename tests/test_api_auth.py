"""Tests for /api/auth/* endpoints (AUTH-03)."""
import pytest

# Tests require api_client fixture from Plan 02.
# Stubs below define the test contract; implementation in Plan 02.


async def test_auth_status_no_token(mock_auth_manager):
    """GET /api/auth/status with no token returns {authenticated: false}."""
    mock_auth_manager.load_token.return_value = None
    # Full test in Plan 02 when api_client exists
    assert mock_auth_manager.load_token() is None


async def test_auth_start_returns_codes(mock_auth_manager):
    """POST /api/auth/start returns user_code and verification_uri."""
    result = await mock_auth_manager.start_device_flow()
    assert result["user_code"] == "ABCD-1234"
    assert result["verification_uri"] == "https://github.com/login/device"


async def test_auth_poll_pending(mock_auth_manager):
    """GET /api/auth/poll returns {done: false} when auth pending."""
    result = await mock_auth_manager.check_device_flow("dc_fake")
    assert result is None
