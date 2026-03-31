---
phase: 03-web-chat-ui
plan: 02
subsystem: api
tags: [fastapi, langgraph, sqlite, aiosqlite, asyncio, device-flow, http-testing]

# Dependency graph
requires:
  - phase: 03-web-chat-ui 03-01
    provides: CopilotAuthManager (start_device_flow/check_device_flow), API models, graph/builder.py, ChatCopilot
provides:
  - FastAPI app with lifespan managing graph, checkpointer, auth_manager, llm
  - POST /api/chat — send message, get AI reply with auth expiry detection
  - POST /api/threads — create new UUID4 thread with label
  - GET /api/threads — list threads via direct SQL on checkpoints table
  - GET /api/threads/{id}/messages — retrieve thread message history
  - POST /api/auth/start — initiate GitHub Device Flow
  - GET /api/auth/poll — single poll for Device Flow completion
  - GET /api/auth/status — authenticated/expired state
  - HTTP-level tests for all endpoints (13 new tests, 36 total pass)
affects: [03-web-chat-ui 03-03, frontend-integration, api-consumers]

# Tech tracking
tech-stack:
  added: [aiosqlite (direct SQL on checkpoints table), httpx.AsyncClient+ASGITransport (test client)]
  patterns:
    - FastAPI lifespan for resource management (graph, checkpointer, auth_manager, llm on app.state)
    - API routes registered before StaticFiles mount to prevent route interception
    - app.state.device_flows dict for single-user in-flight Device Flow sessions
    - app.state.auth_expired flag: chat route sets it, auth/status route reads it
    - Direct aiosqlite SQL against checkpoints table (LangGraph alist() has no list-all API)
    - ASGITransport in tests bypasses lifespan — inject mocks directly into app.state

key-files:
  created:
    - app/api/main.py
    - app/api/routes/__init__.py
    - app/api/routes/auth.py
    - app/api/routes/chat.py
    - static/.gitkeep
  modified:
    - tests/conftest.py (added api_client fixture with ASGITransport)
    - tests/test_api_auth.py (full HTTP-level tests, replaced stubs)
    - tests/test_api_chat.py (full HTTP-level tests, replaced stubs)

key-decisions:
  - "device_flows dict uses 'current' key — single-user app, one flow at a time"
  - "check_device_flow() saves token internally (Plan 01 design) — no explicit save_token in poll route"
  - "auth_expired flag set in chat route on SDK auth errors, read by status route — decoupled detection from surfacing"
  - "static/ dir created with .gitkeep — StaticFiles mount fails if directory missing, even in tests"
  - "ASGITransport bypasses lifespan — test fixtures inject mocks directly into app.state"

patterns-established:
  - "Pattern 1: app.state injection for shared resources — all routes access graph/auth_manager/llm via request.app.state"
  - "Pattern 2: auth expiry cross-route signaling — chat route sets flag, auth/status reads it"
  - "Pattern 3: direct SQL on checkpoints table for thread listing — LangGraph has no list-all API"

requirements-completed: [AUTH-03, CHAT-01, CHAT-02, CHAT-03, CHAT-04]

# Metrics
duration: 3min
completed: 2026-04-01
---

# Phase 3 Plan 2: FastAPI Backend Routes Summary

**FastAPI app with lifespan + 7 REST endpoints (auth Device Flow, chat, threads) and 36 passing HTTP-level tests using ASGITransport + mocked app.state**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-01T16:44:36Z
- **Completed:** 2026-04-01T16:47:14Z
- **Tasks:** 3
- **Files modified:** 8

## Accomplishments
- FastAPI lifespan manages all shared resources (graph, checkpointer, auth_manager, llm) on app.state
- 7 REST endpoints covering chat, thread management, and Device Flow auth
- Full HTTP-level test suite (13 new tests) using ASGITransport — all 36 tests pass
- Auth expiry cross-route signaling: chat route detects errors, auth/status route surfaces them

## Task Commits

Each task was committed atomically:

1. **Task 1: FastAPI app entry point with lifespan** - `e0663f4` (feat)
2. **Task 2: Auth API routes (start, poll, status)** - `3ff16ff` (feat)
3. **Task 3: Chat/thread routes + full HTTP tests** - `41bd2eb` (feat)

## Files Created/Modified
- `app/api/main.py` - FastAPI app with lifespan, resource management, route registration
- `app/api/routes/__init__.py` - Empty package init
- `app/api/routes/auth.py` - POST /api/auth/start, GET /api/auth/poll, GET /api/auth/status
- `app/api/routes/chat.py` - POST /api/chat, POST /api/threads, GET /api/threads, GET /api/threads/{id}/messages
- `static/.gitkeep` - Placeholder so StaticFiles mount doesn't fail at startup
- `tests/conftest.py` - Added api_client fixture with ASGITransport + mocked app.state
- `tests/test_api_auth.py` - Full HTTP-level auth tests (6 tests, replaced Plan 01 stubs)
- `tests/test_api_chat.py` - Full HTTP-level chat tests (7 tests, replaced Plan 01 stubs)

## Decisions Made
- `device_flows` uses `"current"` key — single-user app means only one active Device Flow at a time
- `check_device_flow()` already calls `save_token()` internally (Plan 01 design) — poll route needs no explicit persistence
- `app.state.auth_expired` flag decouples detection (chat route) from surfacing (status route) — clean separation
- `static/.gitkeep` required — `StaticFiles(directory="static")` raises at import if directory is missing
- ASGITransport in tests bypasses lifespan — mocks injected directly into `app.state` fields

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Created static/ directory with .gitkeep placeholder**
- **Found during:** Task 1 (FastAPI app entry point)
- **Issue:** `StaticFiles(directory="static", html=True)` raises `RuntimeError` if the directory doesn't exist — plan didn't mention creating it
- **Fix:** Created `static/` directory with `.gitkeep` placeholder before writing `main.py`
- **Files modified:** `static/.gitkeep`
- **Verification:** `uv run python -c "from app.api.main import app; print(app.title)"` succeeds
- **Committed in:** `e0663f4` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Required for main.py import to succeed. No scope creep.

## Issues Encountered
None — all tasks executed cleanly after the static/ directory fix.

## Known Stubs
None — all endpoints are fully implemented and return real data. Thread listing falls back to empty list when DB doesn't exist yet (by design, not a stub).

## Next Phase Readiness
- All 7 API endpoints ready for frontend (Plan 03) to call
- Auth flow (start/poll/status) wired to real CopilotAuthManager
- Chat endpoint wired to real LangGraph graph with SQLite checkpointing
- Thread listing via direct SQL on checkpoints table — will show real threads once messages are sent

---
*Phase: 03-web-chat-ui*
*Completed: 2026-04-01*
