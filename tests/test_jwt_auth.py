"""Tests for JWT utilities (jwt_utils.py) and JWT-based auth endpoints."""
import datetime

import jwt
import pytest
from cryptography.fernet import InvalidToken


# ---------------------------------------------------------------------------
# Unit tests: jwt_utils module
# ---------------------------------------------------------------------------

class TestCreateDecodeJwt:
    def test_roundtrip_returns_expected_fields(self):
        """create_jwt + decode_jwt roundtrip returns correct payload fields."""
        from app.auth.jwt_utils import create_jwt, decode_jwt

        github_token = "ghu_test_token_abc123"
        token = create_jwt(github_token)
        payload = decode_jwt(token)

        assert payload["sub"] == "copilot_user"
        assert "jti" in payload
        assert "github_token" in payload
        assert "exp" in payload
        assert "iat" in payload

    def test_expired_jwt_raises(self):
        """Expired JWT raises ExpiredSignatureError."""
        from app.auth.jwt_utils import create_jwt, decode_jwt

        token = create_jwt("ghu_expired", expires_minutes=-1)
        with pytest.raises(jwt.ExpiredSignatureError):
            decode_jwt(token)

    def test_blocklisted_jti_raises(self):
        """JWT with blocklisted JTI raises InvalidTokenError."""
        from app.auth.jwt_utils import create_jwt, decode_jwt, add_to_blocklist, _blocklist

        token = create_jwt("ghu_to_revoke")
        # First decode succeeds and gives us the JTI
        payload = decode_jwt(token)
        jti = payload["jti"]

        # Add to blocklist
        add_to_blocklist(jti)

        try:
            with pytest.raises(jwt.InvalidTokenError, match="Token revoked"):
                decode_jwt(token)
        finally:
            # Clean up blocklist to avoid cross-test contamination
            _blocklist.discard(jti)

    def test_invalid_signature_raises(self):
        """JWT with wrong signature raises InvalidTokenError."""
        from app.auth.jwt_utils import decode_jwt

        fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0In0.invalid"
        with pytest.raises(jwt.InvalidTokenError):
            decode_jwt(fake_token)


class TestEncryptDecryptGithubToken:
    def test_roundtrip(self):
        """encrypt_github_token + decrypt_github_token roundtrip."""
        from app.auth.jwt_utils import encrypt_github_token, decrypt_github_token

        original = "ghu_abc123xyz"
        encrypted = encrypt_github_token(original)

        assert encrypted != original
        assert isinstance(encrypted, str)

        decrypted = decrypt_github_token(encrypted)
        assert decrypted == original

    def test_encrypted_is_different_each_time(self):
        """Fernet encryption is nondeterministic — same token, different ciphertext."""
        from app.auth.jwt_utils import encrypt_github_token

        token = "ghu_same_token"
        enc1 = encrypt_github_token(token)
        enc2 = encrypt_github_token(token)
        assert enc1 != enc2

    def test_decrypt_invalid_raises(self):
        """Decrypting garbage raises InvalidToken."""
        from app.auth.jwt_utils import decrypt_github_token

        with pytest.raises(Exception):  # cryptography.fernet.InvalidToken
            decrypt_github_token("notvalidbase64ciphertext")


class TestBlocklist:
    def test_add_and_check(self):
        """add_to_blocklist and is_blocked work correctly."""
        from app.auth.jwt_utils import add_to_blocklist, is_blocked, _blocklist

        jti = "test-jti-unique-" + str(id(self))
        assert not is_blocked(jti)
        add_to_blocklist(jti)
        assert is_blocked(jti)
        # Clean up
        _blocklist.discard(jti)

    def test_unknown_jti_not_blocked(self):
        """JTI not in blocklist returns False."""
        from app.auth.jwt_utils import is_blocked

        assert not is_blocked("jti-that-was-never-added-xyz")


# ---------------------------------------------------------------------------
# Integration tests: auth endpoints with JWT cookies
# ---------------------------------------------------------------------------

@pytest.fixture
def jwt_token():
    """A valid JWT token for testing."""
    from app.auth.jwt_utils import create_jwt
    return create_jwt("ghu_integration_test_token")


@pytest.fixture
def expired_jwt_token():
    """An already-expired JWT for testing expiry handling."""
    from app.auth.jwt_utils import create_jwt
    return create_jwt("ghu_expired_token", expires_minutes=-1)


async def test_auth_status_no_cookie(api_client):
    """GET /api/auth/status with no cookie returns authenticated=False.

    Phase 39 UIFIX-04 D-10 Pattern A: api_client fixture が JWT cookie を bake in
    するようになったため、無認証ケースは明示的に cookie を消去して再現する。
    """
    api_client.cookies.clear()
    resp = await api_client.get("/api/auth/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["authenticated"] is False
    assert data["expired"] is False


async def test_auth_status_with_valid_jwt(api_client, jwt_token):
    """GET /api/auth/status with valid JWT cookie returns authenticated=True."""
    resp = await api_client.get(
        "/api/auth/status",
        cookies={"session": jwt_token},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["authenticated"] is True
    assert data["expired"] is False


async def test_auth_status_with_expired_jwt(api_client, expired_jwt_token):
    """GET /api/auth/status with expired JWT cookie returns expired=True."""
    resp = await api_client.get(
        "/api/auth/status",
        cookies={"session": expired_jwt_token},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["authenticated"] is False
    assert data["expired"] is True


async def test_chat_returns_401_without_cookie(api_client):
    """POST /api/chat with no session cookie returns 401.

    Phase 39 UIFIX-04 D-10 Pattern A: api_client fixture が JWT cookie を bake in
    するようになったため、無認証ケースは明示的に cookie を消去して再現する。
    """
    api_client.cookies.clear()
    resp = await api_client.post(
        "/api/chat",
        json={"message": "hello", "thread_id": "test-thread", "model": "gpt-4.1"},
    )
    assert resp.status_code == 401
    data = resp.json()
    assert data["detail"] == "auth_required"


async def test_logout_clears_cookie_and_blocklists(api_client, jwt_token):
    """POST /api/auth/logout blocklists JTI and sets delete-cookie header."""
    from app.auth.jwt_utils import decode_jwt, is_blocked, _blocklist

    payload = decode_jwt(jwt_token)
    jti = payload["jti"]

    try:
        resp = await api_client.post(
            "/api/auth/logout",
            cookies={"session": jwt_token},
        )
        assert resp.status_code == 200

        # JTI should now be in blocklist
        assert is_blocked(jti)

        # Response should delete the session cookie
        # (httpx records Set-Cookie headers)
        set_cookie = resp.headers.get("set-cookie", "")
        assert "session" in set_cookie
    finally:
        _blocklist.discard(jti)
