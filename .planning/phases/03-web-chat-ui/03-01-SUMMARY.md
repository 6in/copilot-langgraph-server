---
phase: 03-web-chat-ui
plan: 01
subsystem: api
tags: [fastapi, uvicorn, pydantic, device-flow, auth, testing]

requires:
  - phase: 02-graph-layer
    provides: build_graph(llm, checkpointer) factory and CopilotAuthManager with device_login
  - phase: 01-auth-provider
    provides: CopilotAuthManager base class, Fernet token encryption, Device Flow OAuth

provides:
  - FastAPI + uvicorn[standard] + python-multipart installed in project deps
  - Pydantic v2 models: ChatRequest, ChatResponse, ThreadInfo, AuthStartResponse, AuthPollResponse, AuthStatusResponse
  - CopilotAuthManager.start_device_flow() — non-blocking Device Flow initiation
  - CopilotAuthManager.check_device_flow() — single-poll Device Flow check for web routes
  - Test fixtures: mock_graph (AsyncMock), mock_auth_manager (MagicMock)
  - Test stubs: test_api_auth.py, test_api_chat.py defining contract for Plan 02

affects:
  - 03-02 (auth routes: start_device_flow, check_device_flow called from web endpoints)
  - 03-02 (chat routes: ChatRequest/ChatResponse consumed in route handlers)
  - 03-03 (frontend: ThreadInfo and ChatResponse shape defines JSON contract)

tech-stack:
  added:
    - fastapi>=0.135.2
    - uvicorn[standard]>=0.42.0
    - python-multipart>=0.0.22
    - httpx>=0.28.1 (dev)
  patterns:
    - "Pydantic v2 models: use `from pydantic import BaseModel` with `str | None = None` union types"
    - "Non-blocking Device Flow: start returns codes immediately; check_device_flow polls once per HTTP request"
    - "Test fixtures use AsyncMock for coroutine methods (start_device_flow, check_device_flow)"

key-files:
  created:
    - app/api/__init__.py
    - app/api/models.py
    - tests/test_api_auth.py
    - tests/test_api_chat.py
  modified:
    - pyproject.toml (added fastapi, uvicorn, python-multipart, httpx dev dep)
    - uv.lock (dependency lockfile updated)
    - app/auth/manager.py (added start_device_flow, check_device_flow)
    - tests/conftest.py (added mock_graph, mock_auth_manager fixtures)

key-decisions:
  - "start_device_flow / check_device_flow split: web routes cannot use blocking device_login() poll loop — split into initiate + single-poll methods"
  - "device_login() and get_token() preserved unchanged for CLI backward compatibility"
  - "check_device_flow() calls save_token() on success to persist token before returning to caller"
  - "httpx added to dev deps (ASGITransport needed for async test client in Plan 02)"
  - "Test stubs use mock contracts only — full HTTP assertions deferred to Plan 02 when app/api/main.py exists"

patterns-established:
  - "API models live in app/api/models.py, imported by route handlers via `from app.api.models import`"
  - "Mock fixtures in conftest.py use AsyncMock for async methods, MagicMock for sync methods"

requirements-completed: [AUTH-03, CHAT-01, CHAT-02, CHAT-04]

duration: 2min
completed: 2026-04-01
---

# Phase 03 Plan 01: FastAPI Foundation + Auth Manager Web Split Summary

**FastAPI/uvicorn deps added, Pydantic v2 API models defined, and CopilotAuthManager split into non-blocking start/check Device Flow methods with async test fixtures**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-03-31T16:39:25Z
- **Completed:** 2026-03-31T16:41:20Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments

- FastAPI, uvicorn[standard], and python-multipart added to production dependencies; httpx added to dev deps
- 6 Pydantic v2 models defined in app/api/models.py covering all chat and auth endpoint contracts
- CopilotAuthManager extended with start_device_flow() and check_device_flow() methods enabling non-blocking web Device Flow; existing device_login() / get_token() untouched
- Test infrastructure added: mock_graph and mock_auth_manager fixtures in conftest.py, plus auth and chat test stub files defining Plan 02 contract

## Task Commits

Each task was committed atomically:

1. **Task 1: Add FastAPI dependencies and create API data models** - `5eaf32e` (feat)
2. **Task 2: Refactor CopilotAuthManager for web-compatible Device Flow** - `02ad234` (feat)
3. **Task 3: Create test infrastructure for API endpoints** - `5dfd6f4` (test)

## Files Created/Modified

- `app/api/__init__.py` - Package init for API module
- `app/api/models.py` - Pydantic v2 models: ChatRequest, ChatResponse, ThreadInfo, AuthStartResponse, AuthPollResponse, AuthStatusResponse
- `app/auth/manager.py` - Added start_device_flow() and check_device_flow() methods for web-compatible Device Flow
- `pyproject.toml` - Added fastapi, uvicorn[standard], python-multipart; httpx in dev group
- `uv.lock` - Updated lockfile
- `tests/conftest.py` - Added mock_graph and mock_auth_manager fixtures
- `tests/test_api_auth.py` - Auth endpoint test stubs (AUTH-03 contract)
- `tests/test_api_chat.py` - Chat/thread endpoint test stubs (CHAT-01, CHAT-02, CHAT-04 contract)

## Decisions Made

- Web routes cannot use the blocking `device_login()` poll loop. Split into `start_device_flow()` (returns codes immediately) and `check_device_flow()` (single HTTP poll, called once per web request). CLI code remains unchanged.
- `check_device_flow()` calls `save_token()` internally on success so the token is persisted before the web route responds.
- Test stubs define the mock contract now; full HTTP-level assertions (using `AsyncClient` with `ASGITransport`) deferred to Plan 02 when `app/api/main.py` exists.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 02 (auth + chat routes) can now import `from app.api.models import ...` and call `auth_manager.start_device_flow()` / `auth_manager.check_device_flow()`
- `api_client` fixture to be added in Plan 02 conftest when `app/api/main.py` is created
- All 29 tests pass (9 existing + 6 new stubs + 14 prior)

---
*Phase: 03-web-chat-ui*
*Completed: 2026-04-01*
