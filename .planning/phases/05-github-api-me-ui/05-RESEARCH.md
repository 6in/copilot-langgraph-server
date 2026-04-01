# Phase 5: GitHubユーザー情報取得＆ヘッダー表示 - Research

**Researched:** 2026-04-01
**Domain:** GitHub REST API / FastAPI / Vanilla JS UI
**Confidence:** HIGH

## Summary

Phase 5 adds a `/api/me` endpoint that retrieves the authenticated GitHub user's profile (login, name, avatar_url) from `GET https://api.github.com/user` and exposes it as a new FastAPI route. The UI header then displays the user's GitHub avatar and login name instead of the generic "Authenticated" text.

The GitHub token is already embedded (encrypted) in the JWT session cookie. The implementation pattern is: decode JWT on the request, decrypt the `github_token` field, call `GET https://api.github.com/user` with `Authorization: Bearer <token>`, and return the relevant user fields. This is a pure addition — no existing route, model, or JS function needs restructuring. The `username` field already exists on `AuthStatusResponse` as a reserved slot (comment says "Reserved for future multi-user display"), but a dedicated `UserInfoResponse` model with `login`, `name`, and `avatar_url` is cleaner for `/api/me`.

The only integration risk is the GitHub API availability at test time. Tests should mock `httpx.AsyncClient` (the project already uses httpx throughout) rather than making live network calls.

**Primary recommendation:** Add `GET /api/me` behind JWT auth, call `https://api.github.com/user` via httpx, return `{login, name, avatar_url}`. Update the header area in `app.js` to call `/api/me` after `checkAuthStatus()` succeeds and render a small avatar + login span.

## Project Constraints (from CLAUDE.md)

- Tech Stack: Python (LangChain / LangGraph / Copilot SDK). FastAPI + vanilla JS frontend — no React, no npm, no build step.
- Auth: Device Flow only. JWT session cookie for web sessions (`jwt_utils.py`).
- HTTP client: `httpx` (async). Do NOT add `requests`.
- Pydantic v2 patterns: `ConfigDict` / `PrivateAttr`, not class `Config`.
- Do not install the full `langchain` package — `langchain-core` only.
- SDK pinned to exact version 0.2.0 — isolate behind `app/providers/copilot.py`.
- No Redis for personal tool extras — already present for Phase 4 job queue, do not expand usage.
- GSD workflow: use `/gsd:execute-phase` or `/gsd:quick`; do not edit files directly outside a GSD workflow.

## Standard Stack

### Core (already in pyproject.toml — no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `httpx` | >=0.28.0 (installed) | Async HTTP to `api.github.com` | Already in project; async-native, no event-loop blocking |
| `fastapi` | >=0.135.2 (installed) | New `/api/me` route | Existing web layer |
| `PyJWT` | >=2.9.0 (installed) | Decode JWT cookie to extract github_token | Existing auth layer |
| `cryptography` (Fernet) | >=46.0.0 (installed) | Decrypt github_token from JWT payload | Existing: `jwt_utils.decrypt_github_token` |
| `pydantic` v2 | (bundled with FastAPI) | `UserInfoResponse` model | Existing pattern |

No new dependencies required.

**Installation:** none needed.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| httpx | aiohttp | httpx is already present; adding aiohttp is wasteful |
| Dedicated `GET /api/me` | Extend `/api/auth/status` to return user info | Mixing concerns — auth status and user profile are different response shapes/caches |

## Architecture Patterns

### Recommended Project Structure Addition

```
app/
├── api/
│   ├── models.py          # Add UserInfoResponse
│   └── routes/
│       ├── auth.py        # No change
│       └── me.py          # NEW: GET /api/me
├── auth/
│   └── jwt_utils.py       # Use existing decrypt_github_token
static/
├── app.js                 # Update checkAuthStatus → call /api/me
└── style.css              # Add .user-avatar, .user-login CSS
tests/
└── test_api_me.py         # NEW
```

### Pattern 1: JWT-protected route — extract github_token from cookie

The project already has this pattern in `app/api/routes/chat.py` (Plan 02). Replicate it for `/api/me`:

```python
# Source: existing app/api/routes/chat.py pattern
import jwt as pyjwt
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app.auth.jwt_utils import decode_jwt, decrypt_github_token
from app.api.models import UserInfoResponse
import httpx

router = APIRouter(prefix="/api", tags=["me"])

@router.get("/me", response_model=UserInfoResponse)
async def get_me(request: Request):
    session_cookie = request.cookies.get("session")
    if not session_cookie:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
    try:
        payload = decode_jwt(session_cookie)
    except pyjwt.ExpiredSignatureError:
        return JSONResponse(status_code=401, content={"detail": "Session expired"})
    except pyjwt.InvalidTokenError:
        return JSONResponse(status_code=401, content={"detail": "Invalid token"})

    github_token = decrypt_github_token(payload["github_token"])

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )

    if resp.status_code != 200:
        return JSONResponse(status_code=502, content={"detail": "GitHub API error"})

    data = resp.json()
    return UserInfoResponse(
        login=data["login"],
        name=data.get("name"),
        avatar_url=data["avatar_url"],
    )
```

### Pattern 2: Pydantic v2 response model

```python
# Source: existing app/api/models.py pattern
from pydantic import BaseModel

class UserInfoResponse(BaseModel):
    login: str
    name: str | None = None
    avatar_url: str
```

### Pattern 3: GitHub API call — `GET /user`

- **Endpoint:** `https://api.github.com/user`
- **Method:** GET
- **Required headers:** `Authorization: Bearer <ghu_token>`, `Accept: application/vnd.github+json`
- **Response fields used:** `login` (str), `name` (str | null), `avatar_url` (str — HTTPS URL to GitHub CDN avatar)
- **HTTP 200** = success. **HTTP 401** = token invalid/expired. **HTTP 403** = scope issue.
- Confidence: HIGH (verified against GitHub REST API docs 2026-04-01)

### Pattern 4: Frontend — call `/api/me` after auth check

```javascript
// After isAuthenticated = true in checkAuthStatus():
async function loadUserInfo() {
  try {
    const resp = await fetch('/api/me');
    if (!resp.ok) return;
    const data = await resp.json();
    // render avatar + login in header
    const authStatus = document.getElementById('auth-status');
    authStatus.innerHTML =
      `<img class="user-avatar" src="${data.avatar_url}" alt="${data.login}" />` +
      `<span class="user-login">${data.login}</span>`;
    authStatus.className = 'auth-status authenticated';
  } catch (err) {
    console.error('Failed to load user info:', err);
  }
}
```

Security: `avatar_url` is a GitHub CDN URL (`https://avatars.githubusercontent.com/...`) — safe to set as `img src`. `login` is a GitHub username — safe as `textContent` if inserted via DOM text node, but since it goes into a template literal with `innerHTML`, it must be escaped. Use `encodeURIComponent` for src and a text-safe approach for login.

**XSS boundary (existing project rule):** user-supplied strings that go into `innerHTML` must be escaped. GitHub `login` field is alphanumeric + hyphens only (GitHub's own constraint), making XSS impossible in practice, but to stay consistent with project convention (`appendMessage()` uses `textContent` for user content): set `login` text via a separate DOM text node rather than template literal.

### Pattern 5: Register router in main.py

```python
# app/api/main.py
from app.api.routes import auth, chat, jobs, me  # add me

app.include_router(me.router)  # add before static mount
```

### Anti-Patterns to Avoid

- **Making live network calls in tests:** Use `unittest.mock.patch("httpx.AsyncClient")` to mock `GET /user`. The project mocks all external calls in tests.
- **Caching user info in app.state:** Single-user personal tool — no cache needed; a per-request call to GitHub is fine (rare frequency: only on page load).
- **Using `requests` library:** Blocks the event loop. Project constraint: httpx only.
- **Storing avatar_url in JWT:** The JWT already has a 24-hour TTL. User info can change. Fetch fresh on demand.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| GitHub token extraction from JWT | Custom cookie parsing | `decode_jwt` + `decrypt_github_token` from `jwt_utils.py` | Already implemented and tested |
| Async HTTP | `urllib` / `requests` | `httpx.AsyncClient` | Async-native, already in project |
| Request auth guard | Custom decorator | Inline `decode_jwt()` call (same as existing routes) | Project has no DI framework; inline is the pattern |

## Common Pitfalls

### Pitfall 1: `name` field can be `null`
**What goes wrong:** `data["name"]` raises `KeyError` if the user has not set a display name.
**Why it happens:** GitHub `name` is optional on a user profile.
**How to avoid:** Use `data.get("name")` and declare `name: str | None = None` in the Pydantic model.
**Warning signs:** `KeyError: 'name'` in production for users without a display name.

### Pitfall 2: GitHub token scope — `read:user` already requested
**What goes wrong:** Calling `GET /user` might fail if the token lacks `read:user` scope.
**Why it happens:** The Device Flow in `manager.py` already requests `scope": "read:user"` — this is correct. No change needed.
**Verification:** Line 182 of `app/auth/manager.py`: `data={"client_id": CLIENT_ID, "scope": "read:user"}`.

### Pitfall 3: Route registration order in main.py
**What goes wrong:** `me.router` registered after the static file mount gets swallowed by the StaticFiles handler.
**Why it happens:** FastAPI route matching is first-match; `StaticFiles` mounted at `/` catches everything.
**How to avoid:** Register `me.router` before `app.mount("/", StaticFiles(...))` — consistent with existing pattern.
**Warning signs:** `/api/me` returns HTML (index.html content) instead of JSON.

### Pitfall 4: `avatar_url` in `img src` — HTTPS content security
**What goes wrong:** Browsers may block mixed-content if the app serves HTTP and injects an HTTPS avatar URL.
**Why it happens:** Rarely an issue for local dev tools on localhost.
**How to avoid:** No action needed for a local personal tool. If deployed behind HTTPS, this is a non-issue.

### Pitfall 5: XSS via `login` in `innerHTML` template literal
**What goes wrong:** `innerHTML = \`...<span>${data.login}</span>\`` is technically safe for GitHub logins (only `[a-zA-Z0-9-]`), but inconsistent with the project's XSS policy.
**How to avoid:** Set the login span's `textContent` separately after creating the element, or use `document.createTextNode`.

## Code Examples

Verified patterns from official sources and existing codebase:

### GitHub API — GET /user (HIGH confidence, verified against official docs)
```python
# Source: https://docs.github.com/en/rest/users/users?apiVersion=2022-11-28
async with httpx.AsyncClient() as client:
    resp = await client.get(
        "https://api.github.com/user",
        headers={
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
# resp.json() fields: login (str), name (str|null), avatar_url (str), id (int), ...
```

### Test pattern — mock httpx for /api/me
```python
# Source: project convention — mock external calls, use ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

async def test_get_me_success(api_client, jwt_cookie):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "login": "testuser",
        "name": "Test User",
        "avatar_url": "https://avatars.githubusercontent.com/u/1?v=4",
    }
    with patch("app.api.routes.me.httpx.AsyncClient") as mock_client_cls:
        mock_cm = AsyncMock()
        mock_cm.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_cm
        resp = await api_client.get("/api/me", cookies={"session": jwt_cookie})
    assert resp.status_code == 200
    data = resp.json()
    assert data["login"] == "testuser"
    assert data["avatar_url"].startswith("https://avatars.githubusercontent.com")
```

### Frontend — DOM-safe user info rendering
```javascript
// Source: project convention — textContent for user data (XSS boundary)
function renderUserInfo(data) {
  const authStatus = document.getElementById('auth-status');
  authStatus.innerHTML = '';  // clear

  const img = document.createElement('img');
  img.className = 'user-avatar';
  img.src = data.avatar_url;  // GitHub CDN HTTPS URL — safe
  img.alt = '';

  const loginSpan = document.createElement('span');
  loginSpan.className = 'user-login';
  loginSpan.textContent = data.login;  // textContent, not innerHTML

  authStatus.appendChild(img);
  authStatus.appendChild(loginSpan);
  authStatus.className = 'auth-status authenticated';
}
```

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| `username: str | None = None` in `AuthStatusResponse` (commented "Reserved for future") | Dedicated `UserInfoResponse` + `GET /api/me` | Cleaner separation; auth status and user profile have different caching/error semantics |

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `httpx` | `GET https://api.github.com/user` | Yes (pyproject.toml) | >=0.28.0 | — |
| `PyJWT` | JWT decode in `/api/me` | Yes (pyproject.toml) | >=2.9.0 | — |
| `cryptography` | Fernet decrypt github_token | Yes (pyproject.toml) | >=46.0.0 | — |
| GitHub API network | Live user fetch | Dev only (tested via mock) | — | Mock in tests |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None — all required libraries are already installed.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.25 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (asyncio_mode = "auto") |
| Quick run command | `python -m pytest tests/test_api_me.py -x` |
| Full suite command | `python -m pytest tests/ -x` |

### Phase Requirements → Test Map

| ID | Behavior | Test Type | Automated Command | File Exists? |
|----|----------|-----------|-------------------|-------------|
| ME-01 | `GET /api/me` returns `{login, name, avatar_url}` for authenticated user | unit (mocked httpx) | `pytest tests/test_api_me.py::test_get_me_success -x` | Wave 0 |
| ME-02 | `GET /api/me` returns 401 with no cookie | unit | `pytest tests/test_api_me.py::test_get_me_no_cookie -x` | Wave 0 |
| ME-03 | `GET /api/me` returns 401 with expired JWT | unit | `pytest tests/test_api_me.py::test_get_me_expired_cookie -x` | Wave 0 |
| ME-04 | `GET /api/me` returns 502 if GitHub API fails | unit (mocked httpx) | `pytest tests/test_api_me.py::test_get_me_github_error -x` | Wave 0 |
| ME-05 | Header shows avatar + login after auth (visual) | manual | — | manual-only (visual) |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_api_me.py -x`
- **Per wave merge:** `python -m pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_api_me.py` — covers ME-01, ME-02, ME-03, ME-04
- [ ] `app/api/routes/me.py` — new route file
- [ ] `app/api/models.py` — add `UserInfoResponse`

*(Existing test infrastructure: `conftest.py` with `api_client`, `jwt_cookie` fixtures already covers the setup needed.)*

## Open Questions

1. **Should `/api/me` cache the GitHub response?**
   - What we know: Single-user personal tool, `/api/me` is only called on page load after auth.
   - What's unclear: Whether repeated tab opens are a concern.
   - Recommendation: No cache. One httpx call per page load is negligible.

2. **Should `AuthStatusResponse.username` be populated now?**
   - What we know: It exists with comment "Reserved for future multi-user display".
   - What's unclear: Whether the planner wants to populate it from `/api/me` data or keep the two endpoints independent.
   - Recommendation: Keep independent. `AuthStatusResponse` stays as-is. `/api/me` is a separate concern.

3. **Avatar display size in header?**
   - What we know: Header is 48px tall, `#header` has `align-items: center`.
   - Recommendation: 28×28px avatar, `border-radius: 50%`, `margin-right: 8px`.

## Sources

### Primary (HIGH confidence)
- GitHub REST API — Get the authenticated user: https://docs.github.com/en/rest/users/users?apiVersion=2022-11-28 (verified 2026-04-01)
- Existing `app/auth/jwt_utils.py` — `decrypt_github_token`, `decode_jwt` (code read directly)
- Existing `app/api/models.py` — Pydantic v2 model patterns (code read directly)
- Existing `app/api/routes/auth.py` — JWT cookie extraction pattern (code read directly)
- Existing `app/api/main.py` — router registration order (code read directly)
- `pyproject.toml` — confirmed `httpx`, `PyJWT`, `cryptography` all present (code read directly)

### Secondary (MEDIUM confidence)
- GitHub `login` field character constraints (`[a-zA-Z0-9-]` only) — well-known GitHub rule, not re-verified against docs today

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in pyproject.toml, no new deps
- Architecture: HIGH — follows existing route patterns 1:1
- Pitfalls: HIGH — derived from existing codebase conventions and GitHub API docs
- GitHub API response fields: HIGH — verified against official docs 2026-04-01

**Research date:** 2026-04-01
**Valid until:** 2026-05-01 (GitHub API v3 is stable; JWT pattern won't change within project)
