"""Unit tests for CopilotAuthManager (AUTH-01, AUTH-02)."""

import asyncio
import os
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.auth.manager import CopilotAuthManager


# ---------------------------------------------------------------------------
# Token persistence tests (AUTH-02)
# ---------------------------------------------------------------------------


def test_token_roundtrip(tmp_path: Path) -> None:
    """save_token() then load_token() returns the original token."""
    manager = CopilotAuthManager(token_path=str(tmp_path / "token.enc"))
    manager.save_token("ghu_test123")
    result = manager.load_token()
    assert result == "ghu_test123"


def test_load_token_missing(tmp_path: Path) -> None:
    """load_token() returns None when no token file exists."""
    manager = CopilotAuthManager(token_path=str(tmp_path / "nonexistent.enc"))
    result = manager.load_token()
    assert result is None


def test_load_token_corrupted(tmp_path: Path) -> None:
    """load_token() returns None when token file contains garbage bytes."""
    token_path = tmp_path / "token.enc"
    token_path.write_bytes(b"this is not valid fernet ciphertext!!!")
    manager = CopilotAuthManager(token_path=str(token_path))
    result = manager.load_token()
    assert result is None


def test_fernet_key_created(tmp_path: Path) -> None:
    """After init, key file exists at token_path.parent / '.enc_key' with mode 0o600."""
    token_path = tmp_path / "token.enc"
    manager = CopilotAuthManager(token_path=str(token_path))
    # Trigger key creation by calling save_token
    manager.save_token("ghu_x")
    key_path = tmp_path / ".enc_key"
    assert key_path.exists(), "Key file should be created"
    assert oct(key_path.stat().st_mode & 0o777) == oct(0o600), "Key file mode must be 0o600"


def test_fernet_key_env_var(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When COPILOT_TOKEN_ENC_KEY env var is set, it is used instead of the key file."""
    from cryptography.fernet import Fernet

    # Generate a valid Fernet key and set in env
    env_key = Fernet.generate_key().decode()
    monkeypatch.setenv("COPILOT_TOKEN_ENC_KEY", env_key)

    manager = CopilotAuthManager(token_path=str(tmp_path / "token.enc"))
    manager.save_token("ghu_env_token")
    result = manager.load_token()
    assert result == "ghu_env_token"

    # Key file should NOT have been created (env var was used)
    key_path = tmp_path / ".enc_key"
    assert not key_path.exists(), "Key file should not be created when env var is set"


# ---------------------------------------------------------------------------
# Device Flow tests (AUTH-01)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_device_login_polling(tmp_path: Path) -> None:
    """Mock httpx: device_code first, then access_token on second poll."""
    manager = CopilotAuthManager(token_path=str(tmp_path / "token.enc"))

    device_code_response = MagicMock()
    device_code_response.text = (
        "device_code=DEVCODE&user_code=ABCD-1234"
        "&verification_uri=https://github.com/activate"
        "&expires_in=900&interval=5"
    )

    pending_response = MagicMock()
    pending_response.text = "error=authorization_pending"

    token_response = MagicMock()
    token_response.text = "access_token=ghu_polled_token&token_type=bearer"

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    # First call: device code endpoint, second: pending, third: success
    mock_client.post = AsyncMock(
        side_effect=[device_code_response, pending_response, token_response]
    )

    with patch("app.auth.manager.httpx.AsyncClient", return_value=mock_client):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            token = await manager.device_login()

    assert token == "ghu_polled_token"


@pytest.mark.asyncio
async def test_device_login_slow_down(tmp_path: Path) -> None:
    """Mock httpx to return slow_down then access_token; verify interval incremented."""
    manager = CopilotAuthManager(token_path=str(tmp_path / "token.enc"))

    device_code_response = MagicMock()
    device_code_response.text = (
        "device_code=DEVCODE&user_code=SLOW-DOWN"
        "&verification_uri=https://github.com/activate"
        "&expires_in=900&interval=5"
    )

    slow_down_response = MagicMock()
    slow_down_response.text = "error=slow_down"

    token_response = MagicMock()
    token_response.text = "access_token=ghu_slowdown_token&token_type=bearer"

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(
        side_effect=[device_code_response, slow_down_response, token_response]
    )

    sleep_calls: list[float] = []

    async def recording_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    with patch("app.auth.manager.httpx.AsyncClient", return_value=mock_client):
        with patch("asyncio.sleep", side_effect=recording_sleep):
            token = await manager.device_login()

    assert token == "ghu_slowdown_token"
    # After slow_down, the interval should have increased (second sleep > first)
    assert len(sleep_calls) >= 2
    assert sleep_calls[1] > sleep_calls[0], "Interval must increase after slow_down"


@pytest.mark.asyncio
async def test_device_login_timeout(tmp_path: Path) -> None:
    """Mock httpx to always return authorization_pending; verify RuntimeError after timeout."""
    manager = CopilotAuthManager(token_path=str(tmp_path / "token.enc"))

    device_code_response = MagicMock()
    device_code_response.text = (
        "device_code=DEVCODE&user_code=TIMEOUT-TEST"
        "&verification_uri=https://github.com/activate"
        "&expires_in=900&interval=5"
    )

    pending_response = MagicMock()
    pending_response.text = "error=authorization_pending"

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    # First call returns device code, all subsequent return pending
    mock_client.post = AsyncMock(
        side_effect=[device_code_response] + [pending_response] * 200
    )

    # Simulate time passing by manipulating time.time to exceed DEVICE_CODE_EXPIRY_SECS
    original_time = time.time
    call_count = 0

    def fast_time() -> float:
        nonlocal call_count
        call_count += 1
        # After the first few calls, jump past expiry
        if call_count > 3:
            return original_time() + 1000
        return original_time()

    with patch("app.auth.manager.httpx.AsyncClient", return_value=mock_client):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch("app.auth.manager.time.time", side_effect=fast_time):
                with pytest.raises(RuntimeError, match="timed out"):
                    await manager.device_login()


# ---------------------------------------------------------------------------
# get_token caching test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_token_returns_cached(tmp_path: Path) -> None:
    """After save_token, get_token() returns the cached token without device_login."""
    manager = CopilotAuthManager(token_path=str(tmp_path / "token.enc"))
    manager.save_token("ghu_cached_token")

    with patch.object(manager, "device_login", new_callable=AsyncMock) as mock_login:
        token = await manager.get_token()

    assert token == "ghu_cached_token"
    mock_login.assert_not_called()
