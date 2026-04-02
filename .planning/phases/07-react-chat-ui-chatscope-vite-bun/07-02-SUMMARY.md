---
phase: 07-react-chat-ui-chatscope-vite-bun
plan: 02
subsystem: ui
tags: [react, typescript, vite, device-flow, auth, chatscope]

# Dependency graph
requires:
  - phase: 07-react-chat-ui-chatscope-vite-bun
    provides: Vite React-TS scaffold with chatscope packages, /api proxy, CORSMiddleware on FastAPI

provides:
  - frontend/src/types.ts — TypeScript types aligned with backend app/api/models.py
  - frontend/src/api/client.ts — typed fetch wrappers for all 12 backend endpoints
  - frontend/src/hooks/useAuth.ts — Device Flow auth state machine with 5s polling
  - frontend/src/components/AuthPanel.tsx — Device Flow UI (code display, verification link, polling)
  - frontend/src/components/Header.tsx — model selector (gpt-4.1 default) + avatar + logout
  - frontend/src/App.tsx — AuthContext.Provider wrapping auth gate (AuthPanel or ChatApp stub)
  - frontend/src/main.tsx — chatscope CSS import before React rendering
  - npm run build passes with no TypeScript errors

affects: [07-03, 07-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "AuthContext pattern: useAuthProvider() owns state, AuthContext.Provider wraps tree, useAuth() consumes — no prop drilling"
    - "apiFetch<T>() generic wrapper: single credentials: include fetch helper, all endpoints typed"
    - "Device Flow polling: setInterval every 5s in useRef, retry_after support, cleared on done or error"
    - "chatscope CSS imported in main.tsx before React renders — not in component files"

key-files:
  created:
    - frontend/src/types.ts
    - frontend/src/api/client.ts
    - frontend/src/hooks/useAuth.ts
    - frontend/src/components/AuthPanel.tsx
    - frontend/src/components/Header.tsx
  modified:
    - frontend/src/App.tsx
    - frontend/src/main.tsx

key-decisions:
  - "AuthContext.Provider in App.tsx, not in a separate AuthProvider component: avoids extra indirection for a single-user app"
  - "useAuthProvider() returns the value object, App.tsx passes it to Provider: clean separation between state logic and tree injection"
  - "doPoll() catches all network errors silently: keeps polling alive through transient failures (device flow can take minutes)"
  - "deleteThread uses raw fetch not apiFetch: 204 No Content has no body; apiFetch calls resp.json() which would throw"

patterns-established:
  - "All API calls use apiFetch<T>() with credentials: include — session cookie auth"
  - "SSE uses native EventSource (not apiFetch) — EventSource is GET-only, cannot set headers"
  - "deleteThread: raw fetch + status check for 204 (no body to parse)"

requirements-completed: [D-01, D-02, D-07]

# Metrics
duration: 3min
completed: 2026-04-02
---

# Phase 7 Plan 02: Auth Shell and Shared Infrastructure Summary

**React auth shell with Device Flow state machine, typed API client for all 12 backend endpoints, and Header with model selector defaulting to gpt-4.1**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-02T00:11:57Z
- **Completed:** 2026-04-02T00:14:30Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Created `frontend/src/types.ts` with all TypeScript types aligned with `app/api/models.py`
- Created `frontend/src/api/client.ts` with typed fetch wrappers for all 12 backend endpoints (auth, me, chat, job, threads, SSE)
- Built Device Flow auth state machine in `useAuth.ts` with 5-second polling and `retry_after` support
- Built `AuthPanel.tsx` for Device Flow UI (code display, copy button, polling indicator)
- Built `Header.tsx` with model selector (gpt-4.1 default per D-07), GitHub avatar, and logout
- Replaced scaffold `App.tsx` with AuthContext-gated layout (AuthPanel or ChatApp stub)
- Replaced scaffold `main.tsx` with chatscope CSS import before React rendering
- `npm run build` exits 0, no TypeScript errors, `frontend/dist/index.html` produced

## Task Commits

Each task was committed atomically:

1. **Task 1: Create types.ts and api/client.ts** - `ce5a45c` (feat)
2. **Task 2: Create useAuth hook, AuthPanel, Header, App, and main.tsx** - `746d899` (feat)

## Files Created/Modified

- `frontend/src/types.ts` - All TypeScript types: AuthStartResponse, AuthPollResponse, AuthStatusResponse, AuthLogoutResponse, ChatAsyncResponse, JobStatusResponse, ThreadInfo, UserInfoResponse, ChatMessage, ThreadMessagesResponse, ChatRequest
- `frontend/src/api/client.ts` - Typed fetch wrappers: checkAuthStatus, startAuthFlow, pollAuthFlow, logout, getMe, postChat, getJob, streamJob, listThreads, createThread, deleteThread, getThreadMessages, loadThreadMessages
- `frontend/src/hooks/useAuth.ts` - Device Flow state machine: AuthState type, AuthContext, useAuth(), useAuthProvider()
- `frontend/src/components/AuthPanel.tsx` - Device Flow UI with copy button and polling spinner
- `frontend/src/components/Header.tsx` - Model selector (gpt-4.1 default) + avatar + logout button
- `frontend/src/App.tsx` - AuthContext.Provider wrapping auth gate (replaces scaffold default)
- `frontend/src/main.tsx` - chatscope CSS import + React root mount (replaces scaffold default)

## Decisions Made

- **AuthContext.Provider in App.tsx directly** — useAuthProvider() owns the state, App.tsx passes the value object to the Provider; avoids a separate AuthProvider wrapper component for a single-user app
- **doPoll() swallows network errors** — Device Flow can take several minutes while user completes browser auth; transient failures should not abort the flow
- **deleteThread uses raw fetch not apiFetch** — 204 No Content has no body; calling resp.json() on a 204 response throws a parse error; raw fetch + status check handles this correctly
- **SSE via native EventSource** — EventSource is GET-only and cannot set custom headers; all other endpoints use the apiFetch<T>() wrapper

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — TypeScript build passed on first attempt, no dependency issues.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All TypeScript types, API client, auth hook, and auth UI components are in place
- `npm run build` is clean — ready for Plan 07-03 to replace `ChatAppStub` with the actual chatscope chat UI
- Device Flow auth can be completed end-to-end in a browser when FastAPI backend is running
- Header model selector is wired and functional with gpt-4.1 as default

---
*Phase: 07-react-chat-ui-chatscope-vite-bun*
*Completed: 2026-04-02*

## Self-Check: PASSED

- FOUND: frontend/src/types.ts
- FOUND: frontend/src/api/client.ts
- FOUND: frontend/src/hooks/useAuth.ts
- FOUND: frontend/src/components/AuthPanel.tsx
- FOUND: frontend/src/components/Header.tsx
- FOUND: frontend/dist/index.html
- FOUND commit: ce5a45c (Task 1)
- FOUND commit: 746d899 (Task 2)
