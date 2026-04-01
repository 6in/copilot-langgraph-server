---
phase: quick
plan: 260401-lkq
subsystem: auth
tags: [jwt, authentication, multi-user, cookies, security]
dependency_graph:
  requires: []
  provides:
    - JWT-based per-user authentication
    - httpOnly session cookie management
    - in-memory logout blocklist
  affects:
    - app/auth/jwt_utils.py (new)
    - app/api/routes/auth.py
    - app/api/routes/chat.py
    - app/api/models.py
    - app/api/main.py
    - static/app.js
tech_stack:
  added:
    - PyJWT 2.12.1 (HS256 JWT signing/verification)
  patterns:
    - FastAPI Depends for JWT cookie extraction
    - Fernet encryption for GitHub tokens in JWT payloads
    - In-memory JTI blocklist for logout revocation
    - Per-request token injection into shared LLM instance
key_files:
  created:
    - app/auth/jwt_utils.py
    - tests/test_jwt_auth.py
  modified:
    - app/api/models.py
    - app/api/routes/auth.py
    - app/api/routes/chat.py
    - app/api/main.py
    - static/app.js
    - tests/test_api_auth.py
    - tests/test_api_chat.py
    - tests/conftest.py
    - pyproject.toml
    - uv.lock
decisions:
  - "JWT HS256 with secret from env var or ~/.copilot_sdk/.jwt_secret file — zero-config for local use"
  - "Fernet encryption reuses same key strategy as CopilotAuthManager — single key file for token encryption"
  - "In-memory JTI blocklist: clears on restart, no Redis dependency — acceptable for personal tool"
  - "device_flows keyed by uuid4().hex flow_id: multi-user capable, replaces single current key"
  - "Per-request github_token injection: llm.close() on token change forces SDK re-init — safe for sequential personal tool"
  - "Thread CRUD routes intentionally unprotected: local SQLite, no sensitive data, personal tool"
  - "FastAPI Depends get_github_token: 401 responses with auth_required/auth_expired/auth_invalid detail strings"
metrics:
  duration: "~15 min"
  completed_date: "2026-04-01"
  tasks_completed: 5
  files_modified: 11
---

# Quick Task 260401-lkq: JWT Multi-User Auth Summary

**One-liner:** Per-user JWT authentication via httpOnly cookies — Device Flow issues JWT with Fernet-encrypted GitHub token, blocklist-based logout, 401 middleware on chat endpoint.

## What Was Built

Migrated from single-user global auth state (`app.state.auth_expired`, `device_flows["current"]`) to per-user JWT cookie authentication.

### Core components

**`app/auth/jwt_utils.py`** (new)
- `create_jwt(github_token)`: HS256-signed JWT with Fernet-encrypted GitHub token in payload, UUID4 JTI, 24h default expiry
- `decode_jwt(token)`: verify signature + expiry + blocklist check
- `encrypt_github_token` / `decrypt_github_token`: Fernet roundtrip using shared `~/.copilot_sdk/.enc_key`
- `add_to_blocklist` / `is_blocked`: module-level `set[str]` for JTI revocation
- `_get_jwt_secret()`: env var `JWT_SECRET` or auto-created `~/.copilot_sdk/.jwt_secret`

**Auth routes (`app/api/routes/auth.py`)**
- `POST /api/auth/start`: generates `flow_id = uuid4().hex`, stores `device_flows[flow_id]`
- `GET /api/auth/poll?flow_id=...`: on success creates JWT + sets httpOnly session cookie
- `POST /api/auth/logout`: adds JTI to blocklist, deletes session cookie via Set-Cookie
- `GET /api/auth/status`: reads JWT from cookie, returns authenticated/expired/false

**Chat route (`app/api/routes/chat.py`)**
- `get_github_token(request)` FastAPI Depends: extracts JWT cookie, decrypts GitHub token
- Returns 401 with `auth_required`/`auth_expired`/`auth_invalid` detail strings
- Per-request token injection: `llm.github_token = token; await llm.close()` on token change

**Frontend (`static/app.js`)**
- `startAuthFlow`: stores `flow_id` from `/api/auth/start`
- `pollAuth(flowId)`: passes `?flow_id=` to poll endpoint; JWT cookie set by browser from `Set-Cookie` header; calls `checkAuthStatus()` instead of `location.reload()`
- `sendMessage`: handles `resp.status === 401` before `resp.ok`; calls `checkAuthStatus()` + shows appropriate error

## Tests

53 tests pass — 14 new JWT tests + existing suite with no regressions:

| Test file | Tests | Coverage |
|-----------|-------|----------|
| `test_jwt_auth.py` | 14 | JWT roundtrip, expiry, blocklist, Fernet encryption, auth endpoint integration |
| `test_api_auth.py` | 8 | Auth routes with JWT cookies; flow_id; poll sets cookie |
| `test_api_chat.py` | 8 | JWT-protected chat; 401 without cookie; model override |
| existing | 23 | No regressions |

## Commits

| Task | Hash | Description |
|------|------|-------------|
| Task 1 | 529e99d | JWT utilities module + PyJWT dependency |
| Task 2 | ab9a999 | Auth routes for per-user JWT cookie flow |
| Task 3 | 3d91eb6 | JWT-protect chat route with per-request token injection |
| Task 4 | 95cfe5b | Frontend for JWT cookie auth + flow_id polling |
| Task 5 | 13c5b86 | Integration smoke tests — 53 pass, no regressions |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_api_auth.py tests relied on deprecated load_token() pattern**
- **Found during:** Task 2 verification
- **Issue:** Old auth tests called `mock_auth_manager.load_token.return_value` and directly set `app.state.auth_expired` — patterns that no longer exist in the new JWT auth flow
- **Fix:** Rewrote `test_api_auth.py` to use JWT cookies for all auth state assertions
- **Files modified:** tests/test_api_auth.py
- **Commit:** ab9a999

**2. [Rule 1 - Bug] test_api_chat.py tests sent chat requests without JWT cookie**
- **Found during:** Task 3 verification
- **Issue:** Chat tests hit the now-JWT-protected `/api/chat` endpoint without a session cookie — all returned 401
- **Fix:** Added `jwt_cookie` fixture to conftest, updated all protected chat tests to pass `cookies={"session": jwt_cookie}`; also added `test_chat_requires_auth` to explicitly test the 401 path
- **Files modified:** tests/test_api_chat.py, tests/conftest.py
- **Commit:** 3d91eb6

**3. [Rule 1 - Bug] conftest mock_llm used MagicMock for close() which can't be awaited**
- **Found during:** Task 3 test run
- **Issue:** `await llm.close()` in chat route raised `TypeError: object MagicMock can't be used in 'await' expression`
- **Fix:** Changed `app.state.llm` mock in conftest to use `AsyncMock()` for `.close`; also added `.github_token = None` to allow inequality check
- **Files modified:** tests/conftest.py
- **Commit:** 3d91eb6

## Known Stubs

None — all JWT utility functions are fully implemented with real Fernet and PyJWT operations. No hardcoded placeholder values.

## Self-Check: PASSED

All created files exist and all commits are present in git history.
