---
phase: 05-github-api-me-ui
plan: "01"
subsystem: api
tags: [api, github, auth, jwt, fastapi]
dependency_graph:
  requires:
    - "app/auth/jwt_utils.py (decode_jwt, decrypt_github_token)"
    - "app/api/models.py (Pydantic BaseModel)"
  provides:
    - "GET /api/me — GitHub user profile endpoint"
    - "UserInfoResponse Pydantic model"
  affects:
    - "app/api/main.py (router registration)"
tech_stack:
  added: []
  patterns:
    - "JWT cookie extraction via request.cookies.get('session') + decode_jwt"
    - "httpx.AsyncClient for async GitHub API calls"
    - "JSONResponse for explicit 401/502 error returns (not HTTPException)"
key_files:
  created:
    - app/api/routes/me.py
    - tests/test_api_me.py
  modified:
    - app/api/models.py
    - app/api/main.py
decisions:
  - "GET /api/me uses JSONResponse for 401/502 errors (not HTTPException) — consistent with plan spec"
  - "me.router registered before static mount in main.py — preserves route priority"
metrics:
  duration: "2min"
  completed: "2026-04-01"
  tasks_completed: 2
  files_modified: 4
---

# Phase 05 Plan 01: GET /api/me Backend Endpoint Summary

**One-liner:** JWT-protected GET /api/me route that decrypts embedded GitHub token and fetches user profile from GitHub REST API with full error handling.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Add UserInfoResponse model + GET /api/me route + register router | 9dfe4a6 | app/api/models.py, app/api/routes/me.py, app/api/main.py |
| 2 | Tests for GET /api/me (4 cases: success, no cookie, expired, GitHub error) | 2189e7b | tests/test_api_me.py |

## What Was Built

- `UserInfoResponse` Pydantic model added to `app/api/models.py` with `login: str`, `name: str | None`, `avatar_url: str`
- `app/api/routes/me.py` created with `GET /api/me` endpoint that:
  - Reads session cookie and returns 401 if missing
  - Calls `decode_jwt()` and returns 401 on expired/invalid token
  - Decrypts GitHub token via `decrypt_github_token()`
  - Calls `https://api.github.com/user` with Bearer auth + GitHub API version header
  - Returns 502 if GitHub API returns non-200
  - Returns `UserInfoResponse` on success
- `app/api/main.py` updated to import and register `me.router` before static mount

## Verification Results

- `uv run pytest tests/test_api_me.py -x -v` — 4/4 passed
- `python -c "from app.api.routes.me import router; print([r.path for r in router.routes])"` — `['/api/me']`
- 62 other tests continue to pass (1 pre-existing failure in test_api_auth.py documented in deferred-items.md)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all fields (login, name, avatar_url) are wired to live GitHub API response data.

## Pre-existing Issues (Out of Scope)

- `tests/test_api_auth.py::test_auth_poll_pending` — pre-existing failure before Phase 05; `mock_auth_manager.check_device_flow` returns `None` but route expects tuple. Documented in `deferred-items.md`.

## Self-Check: PASSED

Files exist:
- app/api/routes/me.py: FOUND
- tests/test_api_me.py: FOUND
- app/api/models.py (contains UserInfoResponse): FOUND
- app/api/main.py (contains me.router): FOUND

Commits exist:
- 9dfe4a6: FOUND
- 2189e7b: FOUND
