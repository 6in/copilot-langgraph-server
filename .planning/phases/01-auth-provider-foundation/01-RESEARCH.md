# Phase 1: Auth + Provider Foundation - Research

**Researched:** 2026-03-31
**Domain:** GitHub Copilot SDK auth (Device Flow / Fernet), langchain-core BaseChatModel, pyproject.toml setup
**Confidence:** MEDIUM (SDK API verified against installed 0.1.19; 0.2.0 target API verified from PyPI docs; auth architecture requires live validation)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUTH-01 | Device Flow で GitHub OAuth 認証を行い、Copilot トークン（`ghu_` prefix）を取得できる | GitHub Device Flow OAuth is well-documented. CLIENT_ID `Iv1.b507a08c87ecfe98` must be validated live. |
| AUTH-02 | 取得したトークンを Fernet で暗号化し、ローカルに保存・再起動後も再利用できる | `cryptography.fernet.Fernet` API is stable. Key management via env var or file. |
| PROV-01 | `ChatCopilot`（`BaseChatModel` 継承）が LangGraph ノード内で `ChatOpenAI` と差し替え可能な形で動作する | Full canonical `BaseChatModel` signatures documented in pitfalls. Pydantic v2 patterns required. |
| PROV-02 | UI またはコンフィグで Copilot 提供モデル（gpt-4.1 等）を選択できる | Model is a `str` field on `ChatCopilot`, passed to `create_session`. |
| PROV-03 | `CopilotClient` の start/stop ライフサイクルをアプリ起動・終了時に正しく管理する | `CopilotClient.start()` / `stop()` async methods verified. Subprocess leak risk documented. |
</phase_requirements>

---

## Summary

Phase 1 builds the two lowest layers of the application — the auth layer and the provider layer — without any web framework or LangGraph graph. Success means a standalone Python script can call `ChatCopilot.ainvoke([HumanMessage("hello")])` and receive a real Copilot response, and that auth tokens survive process restarts.

The most important discovery from hands-on SDK investigation is a **critical API difference between SDK version 0.1.19 (currently installed) and 0.2.0 (the planned target)**. The reference design (`docs/pre/copilot_langgraph_provider.md`) was written against a version where `CopilotClient` accepted `{"github_token": ..., "use_logged_in_user": False}`. In 0.1.19 that dict key is silently dropped — the token never reaches the CLI. In 0.2.0 the token is passed via `SubprocessConfig(github_token=...)`. The plan must target 0.2.0 and must set up the project with `pyproject.toml` + `uv` before implementing anything.

The second key discovery is that the `create_session` API signature changed between 0.1.19 and 0.2.0: in 0.1.19 it takes a `SessionConfig` dict positional argument; in 0.2.0 `on_permission_request` is a **required keyword argument** and model is also a keyword arg. All code examples in the plan must use the 0.2.0 API.

**Primary recommendation:** Set up `pyproject.toml` and install 0.2.0 with `uv` first, then implement `CopilotAuthManager` (auth layer), then `ChatCopilot` (provider layer), validating end-to-end with a script. The project root has no `pyproject.toml` or `.venv` yet — project setup is Wave 0 work.

---

## Project Constraints (from CLAUDE.md)

The following directives from `CLAUDE.md` are binding for this phase:

- **Runtime:** Python 3.12 (not 3.13; not below 3.11)
- **SDK:** `github-copilot-sdk==0.2.0` — pin exact, Technical Preview. Do NOT import `copilot` outside `app/providers/copilot.py`
- **Auth:** Device Flow only. No PAT, no `requests` (sync)
- **LangChain dependency:** `langchain-core` only, NOT the full `langchain` package
- **HTTP client:** `httpx` only (async). Do NOT add `requests`
- **Packaging:** `pyproject.toml` (PEP 621). Do NOT use `requirements.txt`
- **Dev workflow:** `uv add` / `uv sync` for dependency management
- **Pydantic:** v2 patterns required — `model_config = ConfigDict(...)`, `PrivateAttr` for `_client`
- **Async:** All I/O is `async`. Override `_generate` to raise `NotImplementedError`; only `_agenerate` is implemented
- **GSD Workflow:** Do not make direct repo edits outside a GSD workflow

---

## Standard Stack

### Core (Phase 1 only)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `langchain-core` | >=0.3.0 (latest: check) | `BaseChatModel` base class | Provides abstract interface `ChatCopilot` must implement. Slim — no unused integrations. |
| `github-copilot-sdk` | ==0.2.0 | Copilot JSON-RPC client | Bundles CLI binary; `SubprocessConfig(github_token=...)` auth in 0.2.0. Pin exact — Technical Preview. |
| `cryptography` | >=46.0.0 | Fernet symmetric encryption | Used to encrypt `ghu_` token at rest. 46.0.4 is installed system-wide. |
| `httpx` | >=0.28.0 | Async HTTP for Device Flow | GitHub Device Flow OAuth requires POST requests. Already installed (0.28.1). |
| `pytest` | >=8.0 | Test framework | Standard Python test runner. |
| `pytest-asyncio` | >=0.25 | Async test support | Required for `async def` test functions that test `_agenerate`. |

### Packaging

| Tool | Purpose | Notes |
|------|---------|-------|
| `pyproject.toml` | Project metadata + deps | PEP 621. No `requirements.txt`. |
| `uv` | Venv + dep management | 0.8.4 installed at `/home/parallels/.anyenv/envs/pyenv/shims/uv`. Use for all install operations. |

### Installation

```bash
# From project root — creates .venv and installs all deps
uv venv
uv add langchain-core "github-copilot-sdk==0.2.0" cryptography httpx
uv add --dev pytest pytest-asyncio
```

Minimum `pyproject.toml`:

```toml
[project]
name = "copilot-langgraph"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "langchain-core>=0.3.0",
    "github-copilot-sdk==0.2.0",
    "cryptography>=46.0.0",
    "httpx>=0.28.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.25",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Version verification:** `github-copilot-sdk` PyPI latest confirmed as 0.2.0 (2026-03-31). `langchain-core` latest should be verified with `uv add langchain-core` which resolves the latest compatible release.

---

## Architecture Patterns

### Phase 1 Directory Structure

```
copilot-langgraph/
├── app/
│   ├── auth/
│   │   └── manager.py        # CopilotAuthManager
│   └── providers/
│       └── copilot.py        # ChatCopilot(BaseChatModel) — ONLY file importing copilot SDK
├── scripts/
│   └── chat_test.py          # End-to-end validation script (not a test, just a smoke-test runner)
├── tests/
│   ├── conftest.py           # Shared fixtures
│   ├── test_auth.py          # CopilotAuthManager unit tests (mocked httpx)
│   └── test_provider.py      # ChatCopilot unit tests (mocked CopilotClient)
├── pyproject.toml
├── uv.lock
└── .gitignore                # Must include ~/.copilot_sdk/ items
```

### Pattern 1: CopilotAuthManager

Device Flow polling with Fernet encryption. Key points:
- Env var `COPILOT_TOKEN_ENC_KEY` takes priority over file-based key
- `slow_down` polling error: increment interval AND sleep before retrying (reference code bug — see Pitfall 16)
- `load_token()` returns `str | None` — caller must check for None
- Device code expires after 15 minutes — add timeout to polling loop

```python
# app/auth/manager.py
import json, os, asyncio
import httpx
from pathlib import Path
from datetime import datetime, timezone
from cryptography.fernet import Fernet

GITHUB_DEVICE_CODE_URL = "https://github.com/login/device/code"
GITHUB_TOKEN_URL       = "https://github.com/login/oauth/access_token"
CLIENT_ID              = "Iv1.b507a08c87ecfe98"  # Copilot CLI official Client ID
DEVICE_CODE_EXPIRY_SECS = 900  # GitHub device codes expire after 15 min

class CopilotAuthManager:
    def __init__(self, token_path: str = "~/.copilot_sdk/token.enc"):
        self.token_path = Path(token_path).expanduser()
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        self._fernet = Fernet(self._get_or_create_fernet_key())

    def _get_or_create_fernet_key(self) -> bytes:
        key_env = os.environ.get("COPILOT_TOKEN_ENC_KEY")
        if key_env:
            return key_env.encode()
        key_path = self.token_path.parent / ".enc_key"
        if key_path.exists():
            return key_path.read_bytes()
        key = Fernet.generate_key()
        key_path.write_bytes(key)
        key_path.chmod(0o600)
        return key

    def save_token(self, github_token: str) -> None:
        payload = json.dumps({
            "github_token": github_token,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }).encode()
        self.token_path.write_bytes(self._fernet.encrypt(payload))
        self.token_path.chmod(0o600)

    def load_token(self) -> str | None:
        if not self.token_path.exists():
            return None
        try:
            decrypted = self._fernet.decrypt(self.token_path.read_bytes())
            return json.loads(decrypted)["github_token"]
        except Exception:
            return None

    async def device_login(self) -> str:
        async with httpx.AsyncClient() as http:
            r = await http.post(
                GITHUB_DEVICE_CODE_URL,
                data={"client_id": CLIENT_ID, "scope": "read:user"},
                headers={"Accept": "application/json"},
            )
            r.raise_for_status()
            dc = r.json()

        print(f"\nOpen: {dc['verification_uri']}")
        print(f"Enter code: {dc['user_code']}\n")

        interval = dc.get("interval", 5)
        elapsed = 0
        async with httpx.AsyncClient() as http:
            while elapsed < DEVICE_CODE_EXPIRY_SECS:
                await asyncio.sleep(interval)
                elapsed += interval
                r = await http.post(
                    GITHUB_TOKEN_URL,
                    data={
                        "client_id": CLIENT_ID,
                        "device_code": dc["device_code"],
                        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    },
                    headers={"Accept": "application/json"},
                )
                data = r.json()
                if "access_token" in data:
                    self.save_token(data["access_token"])
                    return data["access_token"]
                elif data.get("error") == "slow_down":
                    interval += 5  # sleep already happened above
                elif data.get("error") == "authorization_pending":
                    continue
                else:
                    raise RuntimeError(f"Auth failed: {data}")
        raise RuntimeError("Device code expired before authentication completed")

    async def get_token(self) -> str:
        token = self.load_token()
        if token:
            return token
        return await self.device_login()
```

### Pattern 2: ChatCopilot (BaseChatModel) — SDK 0.2.0 API

**Critical API facts for SDK 0.2.0 (verified from PyPI docs):**
- `CopilotClient(SubprocessConfig(github_token=token, use_logged_in_user=False))` — token via `SubprocessConfig`
- `create_session(on_permission_request=PermissionHandler.approve_all, model=self.model)` — keyword args, `on_permission_request` is **required**
- Response extracted from event listener pattern — `session.on(handler)` + `session.send(options)` + wait for `session.idle`
- OR use `send_and_wait` if available in 0.2.0 (NOT confirmed in docs — must validate after install)
- Session has `disconnect()` method (not `stop()`)
- `CopilotClient.stop()` terminates the process

**Note on `send_and_wait`:** Verified present in 0.1.19 source. Not mentioned in 0.2.0 PyPI README. After installing 0.2.0, verify by inspecting `CopilotSession` before finalizing `_agenerate`. If absent, use `session.on(handler)` + `asyncio.Event` pattern shown in 0.2.0 docs.

```python
# app/providers/copilot.py
# THIS IS THE ONLY FILE THAT IMPORTS FROM copilot SDK
from typing import Any, List, Optional
from pydantic import ConfigDict, PrivateAttr
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.callbacks import (
    CallbackManagerForLLMRun,
    AsyncCallbackManagerForLLMRun,
)

class ChatCopilot(BaseChatModel):
    """GitHub Copilot SDK wrapped as a LangChain BaseChatModel."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    model: str = "gpt-4.1"
    github_token: Optional[str] = None
    auth_manager: Optional[Any] = None  # CopilotAuthManager
    _client: Any = PrivateAttr(default=None)

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        raise NotImplementedError(
            "ChatCopilot is async-only. Use ainvoke() inside an async context."
        )

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        await self._ensure_client()
        prompt = self._messages_to_prompt(messages)

        # SDK 0.2.0 API: create_session uses keyword args
        # NOTE: validate send_and_wait availability after installing 0.2.0
        from copilot import PermissionHandler
        try:
            session = await self._client.create_session(
                on_permission_request=PermissionHandler.approve_all,
                model=self.model,
            )
            response = await session.send_and_wait({"prompt": prompt})
            if response is None or response.data.content is None:
                raise RuntimeError("Copilot returned empty response")
            content = response.data.content
            await session.disconnect()
            return ChatResult(
                generations=[ChatGeneration(message=AIMessage(content=content))]
            )
        except Exception:
            # Reset client on connection-level errors so next call gets a fresh client
            if self._client:
                try:
                    await self._client.stop()
                except Exception:
                    pass
                self._client = None
            raise

    async def _ensure_client(self) -> None:
        if self._client is not None:
            return
        from copilot import CopilotClient, SubprocessConfig  # isolated import
        token = self.github_token
        if token is None:
            if self.auth_manager is None:
                raise ValueError("github_token or auth_manager required")
            token = await self.auth_manager.get_token()
        self._client = CopilotClient(
            SubprocessConfig(github_token=token, use_logged_in_user=False)
        )
        await self._client.start()

    def _messages_to_prompt(self, messages: List[BaseMessage]) -> str:
        parts = []
        for m in messages:
            if isinstance(m, SystemMessage):
                parts.append(f"[System]: {m.content}")
            elif isinstance(m, HumanMessage):
                parts.append(f"[User]: {m.content}")
            elif isinstance(m, AIMessage):
                parts.append(f"[Assistant]: {m.content}")
            else:
                parts.append(str(m.content))
        return "\n".join(parts)

    async def close(self) -> None:
        if self._client:
            await self._client.stop()
            self._client = None

    @property
    def _llm_type(self) -> str:
        return "github-copilot"
```

### Pattern 3: End-to-End Validation Script

```python
# scripts/chat_test.py
import asyncio
from langchain_core.messages import HumanMessage
from app.auth.manager import CopilotAuthManager
from app.providers.copilot import ChatCopilot

async def main():
    auth = CopilotAuthManager()
    llm = ChatCopilot(model="gpt-4.1", auth_manager=auth)
    try:
        result = await llm.ainvoke([HumanMessage(content="Say 'hello world' only.")])
        print("Response:", result.content)
        assert result.content  # non-empty
        print("PASS: got non-empty AIMessage response")
    finally:
        await llm.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### Anti-Patterns to Avoid

- **Do NOT** call `llm._agenerate()` directly from graph nodes — use `await llm.ainvoke()` (public interface)
- **Do NOT** implement `_generate` with `loop.run_until_complete(_agenerate(...))` — raises RuntimeError inside ASGI
- **Do NOT** use `class Config: arbitrary_types_allowed = True` — that is Pydantic v1. Use `model_config = ConfigDict(...)`
- **Do NOT** annotate `_client: Any = None` without `PrivateAttr` — Pydantic v2 may treat it as a model field
- **Do NOT** import `from copilot import ...` in any file except `app/providers/copilot.py`
- **Do NOT** use `github_token` dict key in `CopilotClient({...})` — 0.2.0 requires `SubprocessConfig(github_token=...)`
- **Do NOT** use positional `SessionConfig` dict in `create_session` — 0.2.0 uses keyword args

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Symmetric encryption | Custom XOR / base64 | `cryptography.fernet.Fernet` | Fernet is authenticated encryption; handles IV, HMAC, rotation |
| Async HTTP | `urllib` async wrapper | `httpx.AsyncClient` | httpx is already a dependency; proper connection pooling, redirects, timeouts |
| Token storage schema | Custom JSON with rolling key | `Fernet.encrypt(json.dumps({...}).encode())` | Already designed in reference; proven pattern |
| Device Flow polling | Custom retry logic | Copy the reference pattern exactly (with the slow_down fix) | GitHub's polling protocol is specified; hand-rolling introduces bugs (see Pitfall 16) |
| BaseChatModel abstract interface | Guess the signature | Copy the canonical signature with `stop` and `run_manager` params | LangChain's dispatch machinery expects these params |

---

## SDK Version Delta: 0.1.19 vs 0.2.0

This is the most important research finding for the plan.

| API Surface | 0.1.19 (installed) | 0.2.0 (target) |
|-------------|-------------------|----------------|
| `CopilotClient` constructor | `CopilotClient({"github_token": ..., "use_logged_in_user": False})` — but `github_token` is **silently dropped** | `CopilotClient(SubprocessConfig(github_token=..., use_logged_in_user=False))` |
| CLI binary | Requires system `copilot` CLI (in PATH) | Bundles platform-specific binary in wheel |
| `create_session` | `await client.create_session(SessionConfig({"model": m, "streaming": False}), on_permission_request=handler)` | `await client.create_session(on_permission_request=handler, model=m)` — keyword-only |
| `send_and_wait` | `await session.send_and_wait({"prompt": prompt})` — confirmed in source | NOT in 0.2.0 README; must verify after install. Fallback: `session.on(handler)` + `asyncio.Event` pattern. |
| Session cleanup | `await client.stop()` | `await session.disconnect()` + `await client.stop()` |
| `__version__` in `__init__.py` | `"0.1.0"` (wrong) | Unknown until installed |

**Action required in Wave 0:** Install 0.2.0 with `uv`, then run `python3 -c "from copilot.session import CopilotSession; print(dir(CopilotSession))"` to verify whether `send_and_wait` exists. If it doesn't, use the event-listener pattern from the 0.2.0 README.

---

## Common Pitfalls

### Pitfall 1: `github_token` silently dropped in 0.1.19 / wrong constructor in 0.2.0
**What goes wrong:** Reference code passes `{"github_token": ..., "use_logged_in_user": False}` to `CopilotClient()`. In 0.1.19 that key is silently ignored — the token never reaches the CLI. In 0.2.0 you must use `SubprocessConfig(github_token=...)`.
**How to avoid:** Always use the 0.2.0 `SubprocessConfig` pattern. First step in Wave 0 is to install and verify the correct API.
**Warning signs:** Auth works without a token (because the CLI is already logged in via nodenv); token expiry then causes silent failures.

### Pitfall 2: Pydantic v2 `class Config` vs `model_config`
**What goes wrong:** `class Config: arbitrary_types_allowed = True` is Pydantic v1 syntax. `langchain-core >= 0.3` uses Pydantic v2. `_client: Any = None` without `PrivateAttr` may be treated as a model field.
**How to avoid:** Use `model_config = ConfigDict(arbitrary_types_allowed=True)` and `_client: Any = PrivateAttr(default=None)`.

### Pitfall 3: `_generate` blocking inside ASGI
**What goes wrong:** `loop.run_until_complete(self._agenerate(...))` raises `RuntimeError: This event loop is already running` inside FastAPI (Phase 2+).
**How to avoid:** Implement `_generate` to raise `NotImplementedError`. Force all callers to `ainvoke()`.

### Pitfall 4: `_agenerate` missing `stop` and `run_manager` params
**What goes wrong:** LangChain's dispatch may pass `stop` or `run_manager` via kwargs; if signature doesn't accept them, `TypeError` fires when callbacks are active.
**How to avoid:** Always use the full canonical signature.

### Pitfall 5: `send_and_wait` returns `Optional[SessionEvent]`
**What goes wrong:** `response` can be `None` if no `assistant.message` event was received before `session.idle`. `response.data.content` is also `Optional[str]`. Dereferencing without guards raises `AttributeError`.
**How to avoid:** Check `if response is None or response.data.content is None` and raise a descriptive error.

### Pitfall 6: `CopilotClient` subprocess leak on error
**What goes wrong:** If `_agenerate` raises an exception mid-flight, the `CopilotClient` is left in an unknown state. Subsequent calls reuse a broken client.
**How to avoid:** Wrap `_agenerate` in try/except; call `client.stop()` and reset `_client = None` on any exception so the next call gets a fresh client.

### Pitfall 7: `slow_down` polling bug in Device Flow
**What goes wrong:** Reference code increments `interval` on `slow_down` but uses `continue` before the `asyncio.sleep`, meaning the next iteration skips the sleep — hammering the endpoint.
**How to avoid:** Structure the polling loop so `asyncio.sleep(interval)` always executes at the start of each iteration, before the poll. The corrected pattern is in the code example above.

### Pitfall 8: Fernet key co-located with encrypted token
**What goes wrong:** Storing `.enc_key` in the same `~/.copilot_sdk/` directory as `token.enc` means anyone with filesystem read access can decrypt the token.
**How to avoid:** Prefer `COPILOT_TOKEN_ENC_KEY` env var as primary key source. Add `~/.copilot_sdk/` to `.gitignore`. Never commit `.enc_key`.

### Pitfall 9: CLIENT_ID validation required
**What goes wrong:** `CLIENT_ID = "Iv1.b507a08c87ecfe98"` is documented as the Copilot CLI's official Client ID for non-interactive use. It may be revoked, rate-limited, or require specific OAuth scopes.
**How to avoid:** Validate Device Flow with this CLIENT_ID in Phase 1 before finalizing. If it fails, investigate the Copilot CLI's current auth flow (`copilot --help` on the system CLI, or review SDK 0.2.0 examples).

---

## Code Examples

### Device Flow OAuth polling (corrected)
```python
# Source: docs/pre/copilot_langgraph_provider.md + Pitfall 16 fix
interval = dc.get("interval", 5)
elapsed = 0
while elapsed < DEVICE_CODE_EXPIRY_SECS:
    await asyncio.sleep(interval)   # ALWAYS sleep first
    elapsed += interval
    r = await http.post(GITHUB_TOKEN_URL, data={...}, headers={"Accept": "application/json"})
    data = r.json()
    if "access_token" in data:
        ...
        return data["access_token"]
    elif data.get("error") == "slow_down":
        interval += 5
        # no continue — falls through to next loop iteration (sleep at top)
    elif data.get("error") == "authorization_pending":
        pass  # fall through to next loop iteration
    else:
        raise RuntimeError(f"Auth failed: {data}")
raise RuntimeError("Device code expired")
```

### ChatCopilot with 0.2.0 event-listener fallback
```python
# If send_and_wait is absent in 0.2.0, use this pattern instead:
# Source: github-copilot-sdk 0.2.0 PyPI README
import asyncio
from copilot import PermissionHandler

session = await self._client.create_session(
    on_permission_request=PermissionHandler.approve_all,
    model=self.model,
)
done = asyncio.Event()
last_content: list[str] = []

def on_event(event):
    if event.type.value == "assistant.message":
        last_content.append(event.data.content or "")
    elif event.type.value == "session.idle":
        done.set()

session.on(on_event)
await session.send({"prompt": prompt})
await asyncio.wait_for(done.wait(), timeout=60.0)
await session.disconnect()
content = last_content[-1] if last_content else ""
```

### Fernet encrypt/decrypt
```python
# Source: cryptography.fernet docs (HIGH confidence)
from cryptography.fernet import Fernet

key = Fernet.generate_key()   # 32-byte URL-safe base64 encoded
f = Fernet(key)
token = b"ghu_sometoken"
encrypted = f.encrypt(token)  # bytes with timestamp + HMAC
decrypted = f.decrypt(encrypted)  # raises InvalidToken if tampered
```

### BaseChatModel full canonical signature
```python
# Source: langchain-core API reference (HIGH confidence)
from langchain_core.callbacks import (
    CallbackManagerForLLMRun,
    AsyncCallbackManagerForLLMRun,
)

def _generate(
    self,
    messages: List[BaseMessage],
    stop: Optional[List[str]] = None,
    run_manager: Optional[CallbackManagerForLLMRun] = None,
    **kwargs: Any,
) -> ChatResult: ...

async def _agenerate(
    self,
    messages: List[BaseMessage],
    stop: Optional[List[str]] = None,
    run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
    **kwargs: Any,
) -> ChatResult: ...
```

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | Runtime | Yes | 3.12.3 | — |
| `uv` | Dependency management | Yes | 0.8.4 | `pip` (slower) |
| `copilot` CLI | SDK subprocess target | Yes (nodenv) | 0.0.395 | SDK 0.2.0 bundles own binary — nodenv CLI not needed once 0.2.0 installed |
| `github-copilot-sdk` | PROV-01, PROV-02, PROV-03 | Yes (0.1.19) | 0.1.19 | Must upgrade to 0.2.0 |
| `cryptography` | AUTH-02 | Yes | 46.0.4 | — |
| `httpx` | AUTH-01 | Yes | 0.28.1 | — |
| `langchain-core` | PROV-01 | No — not in project venv | N/A | Install via `uv add` |
| `pytest` / `pytest-asyncio` | Testing | No — not in project venv | N/A | Install via `uv add --dev` |
| Copilot account auth | AUTH-01 validation | Yes (CLI shows `last_logged_in_user: 6in`) | — | Must re-authenticate via Device Flow if token passed via SDK |

**Project venv does not exist yet.** The system Python at `/home/parallels/.anyenv/envs/pyenv/versions/3.12.3/` has the SDK and cryptography/httpx installed globally. Wave 0 must create `pyproject.toml`, run `uv venv`, and `uv sync` to set up the isolated project environment.

**Missing dependencies with no fallback:**
- `langchain-core` (not in project venv) — required before any provider code
- `pyproject.toml` / `.venv` — project setup is entirely missing

**Missing dependencies with fallback:**
- `github-copilot-sdk` 0.2.0: 0.1.19 is available globally but API differs; 0.2.0 must be installed in project venv

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — Wave 0 creates this |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -v` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-01 | Device Flow starts, returns token, saves to disk | integration (manual for browser step; unit for polling logic) | `uv run pytest tests/test_auth.py::test_device_login_polling -x` | No — Wave 0 |
| AUTH-02 | `save_token` / `load_token` round-trip survives process restart | unit | `uv run pytest tests/test_auth.py::test_token_roundtrip -x` | No — Wave 0 |
| AUTH-02 | `load_token` returns `None` when file missing | unit | `uv run pytest tests/test_auth.py::test_load_token_missing -x` | No — Wave 0 |
| PROV-01 | `ChatCopilot` instantiates without error | unit | `uv run pytest tests/test_provider.py::test_instantiation -x` | No — Wave 0 |
| PROV-01 | `_llm_type` returns `"github-copilot"` | unit | `uv run pytest tests/test_provider.py::test_llm_type -x` | No — Wave 0 |
| PROV-01 | `_generate` raises `NotImplementedError` | unit | `uv run pytest tests/test_provider.py::test_sync_raises -x` | No — Wave 0 |
| PROV-01 | `_agenerate` returns `ChatResult` with non-empty `AIMessage` | integration (mocked SDK) | `uv run pytest tests/test_provider.py::test_agenerate_mocked -x` | No — Wave 0 |
| PROV-02 | Model param is passed to `create_session` | unit (mocked SDK) | `uv run pytest tests/test_provider.py::test_model_param -x` | No — Wave 0 |
| PROV-03 | `close()` calls `client.stop()` and resets `_client` | unit (mocked SDK) | `uv run pytest tests/test_provider.py::test_close -x` | No — Wave 0 |
| PROV-03 | Exception in `_agenerate` resets `_client` to `None` | unit (mocked SDK) | `uv run pytest tests/test_provider.py::test_error_resets_client -x` | No — Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `pyproject.toml` — project metadata + deps + pytest config
- [ ] `.venv` — `uv venv && uv sync`
- [ ] `tests/conftest.py` — shared fixtures (e.g., `tmp_path`-based `CopilotAuthManager`)
- [ ] `tests/test_auth.py` — covers AUTH-01, AUTH-02
- [ ] `tests/test_provider.py` — covers PROV-01, PROV-02, PROV-03
- [ ] `app/__init__.py`, `app/auth/__init__.py`, `app/providers/__init__.py` — package init files
- [ ] Verify `send_and_wait` existence in 0.2.0 after install

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `CopilotClient({"github_token": ...})` | `CopilotClient(SubprocessConfig(github_token=...))` | SDK 0.2.0 | Reference code pattern is broken; must use SubprocessConfig |
| `create_session(SessionConfig({...}), on_permission_request=...)` | `create_session(on_permission_request=..., model=...)` keyword-only | SDK 0.2.0 | No positional SessionConfig dict |
| Copilot SDK requires system CLI in PATH | SDK 0.2.0 bundles platform-specific binary | SDK 0.2.0 | No nodenv copilot dependency |
| `class Config: arbitrary_types_allowed` | `model_config = ConfigDict(arbitrary_types_allowed=True)` | langchain-core 0.3 / Pydantic v2 | Reference code pattern is broken for new langchain-core |
| `_client: Any = None` as class annotation | `_client: Any = PrivateAttr(default=None)` | Pydantic v2 | Avoids field vs private attribute confusion |

**Deprecated/outdated (reference doc `docs/pre/copilot_langgraph_provider.md`):**
- `CopilotClient({"github_token": ..., "use_logged_in_user": False})` constructor pattern — broken in 0.2.0
- `class Config:` Pydantic pattern — use `model_config = ConfigDict(...)`
- `_generate` with `loop.run_until_complete` — use `raise NotImplementedError`
- `slow_down` polling loop without proper sleep — race condition in reference code

---

## Open Questions

1. **Does SDK 0.2.0 include `send_and_wait`?**
   - What we know: Present in 0.1.19 source. Not mentioned in 0.2.0 README. The 0.2.0 README only shows `session.on(handler)` + `asyncio.Event` pattern.
   - What's unclear: Was `send_and_wait` removed or just undocumented in 0.2.0?
   - Recommendation: After installing 0.2.0 in Wave 0, run `python3 -c "from copilot.session import CopilotSession; print(hasattr(CopilotSession, 'send_and_wait'))"`. If False, use the event-listener fallback.

2. **Is `CLIENT_ID = "Iv1.b507a08c87ecfe98"` still valid?**
   - What we know: Documented in reference code and SUMMARY.md as Copilot CLI's official Client ID (non-official use).
   - What's unclear: Whether GitHub has changed this or rate-limits third-party usage in 2026.
   - Recommendation: Validate in the first live test in Phase 1. If invalid, check the Copilot CLI's own OAuth flow for the correct Client ID (inspect `copilot auth` subcommand or SDK 0.2.0 examples).

3. **Does SDK 0.2.0 auth flow require the system `copilot` CLI at all?**
   - What we know: 0.2.0 bundles platform-specific binaries. The bundled binary manages its own auth state (separate from the nodenv copilot CLI at `~/.copilot/`).
   - What's unclear: Whether the bundled CLI reuses the same auth token store as the system CLI, or requires its own Device Flow.
   - Recommendation: Assume separate auth — implement the full `CopilotAuthManager` Device Flow. If the bundled CLI auto-authenticates from `~/.copilot/config.json`, that's a bonus; don't rely on it.

---

## Sources

### Primary (HIGH confidence)
- Installed SDK 0.1.19 source (`/home/parallels/.anyenv/envs/pyenv/versions/3.12.3/lib/python3.12/site-packages/copilot/`) — `CopilotClientOptions`, `SessionConfig`, `send_and_wait` source, `SessionEventType`, `Data.content` field verified by direct inspection
- PyPI github-copilot-sdk 0.2.0 description — https://pypi.org/pypi/github-copilot-sdk/0.2.0/json — `SubprocessConfig`, keyword-only `create_session`, bundled binary, no `send_and_wait` in docs
- `docs/pre/copilot_langgraph_provider.md` — primary reference design (pre-dates 0.2.0 API changes)
- `.planning/research/PITFALLS.md` — all pitfalls verified against this phase's scope
- `.planning/research/ARCHITECTURE.md` — directory structure, layer boundaries

### Secondary (MEDIUM confidence)
- langchain-core BaseChatModel API reference: https://python.langchain.com/api_reference/core/language_models/langchain_core.language_models.chat_models.BaseChatModel.html
- cryptography Fernet docs: https://cryptography.io/en/latest/fernet/
- PyPI version list (verified by direct API call): all versions from 0.1.10 to 0.2.0 confirmed

### Tertiary (LOW confidence)
- `CLIENT_ID = "Iv1.b507a08c87ecfe98"` validity in 2026 — referenced in project docs but not independently verified against GitHub's current OAuth app registrations

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified against PyPI directly
- SDK 0.2.0 API: MEDIUM — verified from PyPI package description; `send_and_wait` presence unconfirmed until installed
- Auth architecture: MEDIUM — Device Flow pattern is well-known; CLIENT_ID validity unverified live
- BaseChatModel patterns: HIGH — verified against langchain-core reference docs and PITFALLS.md
- Environment availability: HIGH — direct shell inspection of installed tools

**Research date:** 2026-03-31
**Valid until:** 2026-04-14 (SDK is Technical Preview — 2 weeks max before re-verify)
