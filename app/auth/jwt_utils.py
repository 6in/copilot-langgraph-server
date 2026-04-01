"""JWT utilities for per-user authentication.

Provides:
- JWT creation and validation (PyJWT, HS256)
- Fernet encryption/decryption for GitHub tokens embedded in JWT payloads
- In-memory logout blocklist (clears on server restart — acceptable for personal tool)

Exports:
    create_jwt, decode_jwt,
    encrypt_github_token, decrypt_github_token,
    add_to_blocklist, is_blocked
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path
from uuid import uuid4

import jwt
from cryptography.fernet import Fernet

# ---------------------------------------------------------------------------
# In-memory logout blocklist
# ---------------------------------------------------------------------------
# Stores JTI strings of revoked JWTs.
# NOTE: This set is in-memory only — it clears on server restart.
# Active JWTs issued before restart continue to work until expiry.
# Acceptable trade-off for a personal tool with no Redis dependency.
_blocklist: set[str] = set()


def add_to_blocklist(jti: str) -> None:
    """Add a JWT ID to the revocation blocklist."""
    _blocklist.add(jti)


def is_blocked(jti: str) -> bool:
    """Return True if the JTI has been revoked via logout."""
    return jti in _blocklist


# ---------------------------------------------------------------------------
# JWT secret management
# ---------------------------------------------------------------------------

def _get_jwt_secret() -> str:
    """Return the HS256 signing secret for JWTs.

    Priority:
    1. JWT_SECRET env var (set directly — useful for container deployments)
    2. File at ~/.copilot_sdk/.jwt_secret (auto-created if missing, chmod 0o600)
    """
    env_secret = os.environ.get("JWT_SECRET")
    if env_secret:
        return env_secret

    secret_path = Path("~/.copilot_sdk/.jwt_secret").expanduser()
    secret_path.parent.mkdir(parents=True, exist_ok=True)

    if secret_path.exists():
        return secret_path.read_text().strip()

    # Generate and persist a new 32-byte random hex secret
    new_secret = secrets.token_hex(32)
    secret_path.write_text(new_secret)
    secret_path.chmod(0o600)
    return new_secret


# ---------------------------------------------------------------------------
# Fernet encryption for GitHub tokens inside JWT payloads
# ---------------------------------------------------------------------------

def _get_fernet() -> Fernet:
    """Return a Fernet instance using the shared encryption key.

    Uses the same key strategy as CopilotAuthManager._get_or_create_fernet_key():
    1. COPILOT_TOKEN_ENC_KEY env var (base64-encoded Fernet key)
    2. Key file at ~/.copilot_sdk/.enc_key (auto-created if missing)
    """
    env_key = os.environ.get("COPILOT_TOKEN_ENC_KEY")
    if env_key:
        return Fernet(env_key.encode())

    key_path = Path("~/.copilot_sdk/.enc_key").expanduser()
    key_path.parent.mkdir(parents=True, exist_ok=True)

    if key_path.exists():
        return Fernet(key_path.read_bytes())

    key = Fernet.generate_key()
    key_path.write_bytes(key)
    key_path.chmod(0o600)
    return Fernet(key)


def encrypt_github_token(token: str) -> str:
    """Encrypt a raw GitHub token (ghu_...) with Fernet.

    Returns a base64-encoded ciphertext string safe for JWT payload embedding.
    """
    fernet = _get_fernet()
    return fernet.encrypt(token.encode()).decode()


def decrypt_github_token(encrypted: str) -> str:
    """Decrypt a Fernet-encrypted GitHub token.

    Returns the raw ghu_... token string.
    Raises cryptography.fernet.InvalidToken on decryption failure.
    """
    fernet = _get_fernet()
    return fernet.decrypt(encrypted.encode()).decode()


# ---------------------------------------------------------------------------
# JWT creation and validation
# ---------------------------------------------------------------------------

def create_jwt(github_token: str, expires_minutes: int = 1440) -> str:
    """Create a signed JWT embedding the encrypted GitHub token.

    Payload fields:
    - sub: "copilot_user" (fixed — single-user identity anchor)
    - github_token: Fernet-encrypted ghu_... token
    - jti: UUID4 hex (unique per token, used for blocklist revocation)
    - exp: expiry timestamp (default: 24 hours from now)

    Signed with HS256 using the JWT secret from _get_jwt_secret().
    """
    import datetime

    now = datetime.datetime.now(tz=datetime.timezone.utc)
    payload = {
        "sub": "copilot_user",
        "github_token": encrypt_github_token(github_token),
        "jti": uuid4().hex,
        "exp": now + datetime.timedelta(minutes=expires_minutes),
        "iat": now,
    }
    return jwt.encode(payload, _get_jwt_secret(), algorithm="HS256")


def decode_jwt(token: str) -> dict:
    """Decode and verify a JWT, returning the payload dict.

    Raises:
    - jwt.ExpiredSignatureError: token has expired
    - jwt.InvalidTokenError: signature invalid, malformed, or revoked (blocklisted)

    After successful decode, checks the JTI against the in-memory blocklist.
    """
    payload = jwt.decode(token, _get_jwt_secret(), algorithms=["HS256"])
    jti = payload.get("jti", "")
    if is_blocked(jti):
        raise jwt.InvalidTokenError("Token revoked")
    return payload
