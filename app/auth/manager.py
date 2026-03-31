"""CopilotAuthManager — Device Flow OAuth + Fernet token encryption.

AUTH-01: Device Flow for GitHub OAuth token acquisition.
AUTH-02: Fernet-encrypted token persistence to disk.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs

import httpx
from cryptography.fernet import Fernet, InvalidToken

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

GITHUB_DEVICE_CODE_URL = "https://github.com/login/device/code"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
CLIENT_ID = "Iv1.b507a08c87ecfe98"
DEVICE_CODE_EXPIRY_SECS = 900


class CopilotAuthManager:
    """Manages GitHub OAuth authentication for Copilot.

    Responsibilities:
    - Encrypt and persist GitHub tokens to disk using Fernet symmetric encryption.
    - Implement GitHub Device Flow for interactive OAuth.
    - Provide a single get_token() entry point that returns a cached or freshly
      authenticated token.
    """

    def __init__(self, token_path: str = "~/.copilot_sdk/token.enc") -> None:
        self.token_path = Path(token_path).expanduser()
        self.token_path.parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Key management
    # ------------------------------------------------------------------

    def _get_or_create_fernet_key(self) -> bytes:
        """Return Fernet key bytes.

        Priority:
        1. COPILOT_TOKEN_ENC_KEY env var (base64-encoded Fernet key)
        2. Key file at token_path.parent / ".enc_key" (created if missing)
        """
        env_key = os.environ.get("COPILOT_TOKEN_ENC_KEY")
        if env_key:
            return env_key.encode()

        key_path = self.token_path.parent / ".enc_key"
        if key_path.exists():
            return key_path.read_bytes()

        key = Fernet.generate_key()
        key_path.write_bytes(key)
        key_path.chmod(0o600)
        return key

    # ------------------------------------------------------------------
    # Token persistence (AUTH-02)
    # ------------------------------------------------------------------

    def save_token(self, github_token: str) -> None:
        """Encrypt and persist github_token to disk.

        Stores JSON payload: {"github_token": token, "saved_at": iso_timestamp}
        """
        key = self._get_or_create_fernet_key()
        fernet = Fernet(key)

        payload = json.dumps(
            {
                "github_token": github_token,
                "saved_at": datetime.now(tz=timezone.utc).isoformat(),
            }
        ).encode()

        encrypted = fernet.encrypt(payload)
        self.token_path.write_bytes(encrypted)
        self.token_path.chmod(0o600)

    def load_token(self) -> str | None:
        """Decrypt and return the stored token, or None on any error."""
        if not self.token_path.exists():
            return None

        try:
            key = self._get_or_create_fernet_key()
            fernet = Fernet(key)
            encrypted = self.token_path.read_bytes()
            decrypted = fernet.decrypt(encrypted)
            data = json.loads(decrypted.decode())
            return data["github_token"]
        except (InvalidToken, json.JSONDecodeError, KeyError, Exception):
            return None

    # ------------------------------------------------------------------
    # Device Flow OAuth (AUTH-01)
    # ------------------------------------------------------------------

    async def device_login(self) -> str:
        """Perform GitHub Device Flow and return the access token.

        Polls GITHUB_TOKEN_URL with sleep BEFORE each POST (Pitfall 7 prevention).
        Raises RuntimeError on timeout (> DEVICE_CODE_EXPIRY_SECS).
        """
        async with httpx.AsyncClient() as client:
            # Step 1: Request device and user codes
            response = await client.post(
                GITHUB_DEVICE_CODE_URL,
                data={"client_id": CLIENT_ID, "scope": "read:user"},
                headers={"Accept": "application/x-www-form-urlencoded"},
            )

        params = parse_qs(response.text)
        device_code = params["device_code"][0]
        user_code = params["user_code"][0]
        verification_uri = params["verification_uri"][0]
        interval = int(params.get("interval", ["5"])[0])

        print(f"\nOpen: {verification_uri}")
        print(f"Enter code: {user_code}\n")

        start_time = time.time()

        while True:
            # Sleep BEFORE the POST — prevents slow_down feedback loop (Pitfall 7)
            await asyncio.sleep(interval)

            if time.time() - start_time > DEVICE_CODE_EXPIRY_SECS:
                raise RuntimeError(
                    f"Device Flow timed out after {DEVICE_CODE_EXPIRY_SECS} seconds. "
                    "Please restart authentication."
                )

            async with httpx.AsyncClient() as client:
                token_response = await client.post(
                    GITHUB_TOKEN_URL,
                    data={
                        "client_id": CLIENT_ID,
                        "device_code": device_code,
                        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    },
                    headers={"Accept": "application/x-www-form-urlencoded"},
                )

            result = parse_qs(token_response.text)

            if "access_token" in result:
                return result["access_token"][0]

            error = result.get("error", ["unknown"])[0]

            if error == "slow_down":
                interval += 5
            elif error == "authorization_pending":
                pass  # Continue polling
            else:
                raise RuntimeError(f"Device Flow failed with error: {error}")

    # ------------------------------------------------------------------
    # Web-compatible Device Flow (AUTH-03)
    # ------------------------------------------------------------------

    async def start_device_flow(self) -> dict:
        """Start GitHub Device Flow and return codes for the web UI.

        Returns dict with keys: user_code, verification_uri, device_code, interval.
        Does NOT block — returns immediately after getting codes from GitHub.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GITHUB_DEVICE_CODE_URL,
                data={"client_id": CLIENT_ID, "scope": "read:user"},
                headers={"Accept": "application/x-www-form-urlencoded"},
            )
        params = parse_qs(response.text)
        return {
            "user_code": params["user_code"][0],
            "verification_uri": params["verification_uri"][0],
            "device_code": params["device_code"][0],
            "interval": int(params.get("interval", ["5"])[0]),
        }

    async def check_device_flow(self, device_code: str) -> str | None:
        """Make a single poll attempt for Device Flow completion.

        Returns the access_token string if auth completed, None if still pending.
        Raises RuntimeError on terminal errors (e.g., expired_token, access_denied).
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GITHUB_TOKEN_URL,
                data={
                    "client_id": CLIENT_ID,
                    "device_code": device_code,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
                headers={"Accept": "application/x-www-form-urlencoded"},
            )
        result = parse_qs(response.text)

        if "access_token" in result:
            token = result["access_token"][0]
            self.save_token(token)
            return token

        error = result.get("error", ["unknown"])[0]
        if error in ("authorization_pending", "slow_down"):
            return None
        raise RuntimeError(f"Device Flow failed: {error}")

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def get_token(self) -> str:
        """Return a valid GitHub token.

        Tries load_token() first; falls back to device_login().
        """
        cached = self.load_token()
        if cached is not None:
            return cached
        token = await self.device_login()
        self.save_token(token)
        return token
