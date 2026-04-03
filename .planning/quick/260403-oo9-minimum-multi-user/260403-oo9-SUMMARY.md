---
phase: quick
plan: 260403-oo9
subsystem: auth+api
tags: [multi-user, jwt, thread-isolation, postgres]
dependency_graph:
  requires: [260401-lkq-jwt]
  provides: [per-user thread visibility, JWT-protected thread CRUD]
  affects: [app/auth/jwt_utils.py, app/api/routes/auth.py, app/api/routes/chat.py, app/api/main.py]
tech_stack:
  added: []
  patterns: [JWT claims extension, FastAPI Depends per-route auth, INNER JOIN owner filter, COALESCE first-writer-wins upsert]
key_files:
  created: []
  modified:
    - app/auth/jwt_utils.py
    - app/api/routes/auth.py
    - app/api/routes/chat.py
    - app/api/main.py
decisions:
  - "github_login embedded in JWT at auth time: fetched from GET /api/github.com/user after Device Flow, fallback to 'unknown' on error"
  - "GET /api/threads uses INNER JOIN thread_labels + WHERE tl.github_login = %s: orphan threads (no owner) excluded, which is correct post-migration behavior"
  - "POST /api/chat upserts github_login with COALESCE(existing, new): first writer wins, prevents ownership hijack on repeat sends"
  - "DELETE /api/threads verifies ownership before deleting: returns 404 if thread does not belong to JWT user"
  - "github_login column is nullable in thread_labels: backward compat with existing rows that have no owner"
metrics:
  duration: 2min
  completed_date: "2026-04-03"
  tasks_completed: 2
  files_modified: 4
---

# Quick 260403-oo9: Minimum Multi-User Thread Isolation Summary

**One-liner:** JWT now carries github_login (fetched from GitHub API at auth time); all thread routes are JWT-protected; GET /api/threads returns only the authenticated user's threads via INNER JOIN + owner filter.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Embed github_login in JWT and add DB column | cc5c2e8 | jwt_utils.py, auth.py, main.py |
| 2 | JWT-protect thread routes and filter by github_login | 9237aaf | chat.py |

## Changes Made

### app/auth/jwt_utils.py
- `create_jwt()` gains `github_login: str = "unknown"` parameter
- JWT payload now includes `"github_login": github_login` field
- Docstring updated to document the new field

### app/api/routes/auth.py
- Added `import httpx`
- `poll_auth`: after Device Flow success, calls `GET https://api.github.com/user` with Bearer token
- Extracts `login` from response JSON, falls back to `"unknown"` on any error
- Passes `github_login=login` to `create_jwt()`

### app/api/main.py
- `thread_labels` CREATE TABLE now includes `github_login TEXT` (nullable)
- Added `ALTER TABLE thread_labels ADD COLUMN IF NOT EXISTS github_login TEXT` for existing DBs

### app/api/routes/chat.py
- New `get_jwt_payload()` dependency: decodes JWT cookie, returns full payload dict (no github_token decryption needed)
- `POST /api/chat`: second dependency `get_jwt_payload`; after enqueue, upserts `github_login` into `thread_labels` (COALESCE first-writer-wins)
- `GET /api/threads`: JWT-protected; INNER JOIN thread_labels + `WHERE tl.github_login = %s` filter
- `POST /api/threads`: JWT-protected via `get_jwt_payload`
- `DELETE /api/threads/{id}`: JWT-protected + ownership verification (404 if not owner)
- `PATCH /api/threads/{id}`: JWT-protected
- `GET /api/threads/{id}/messages`: JWT-protected
- Module docstring updated to remove stale NOTE about thread routes being unprotected

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

Files exist:
- FOUND: app/auth/jwt_utils.py (github_login param added)
- FOUND: app/api/routes/auth.py (httpx import + login fetch)
- FOUND: app/api/routes/chat.py (get_jwt_payload + all route protection)
- FOUND: app/api/main.py (github_login column)

Commits exist:
- cc5c2e8: feat(quick-260403-oo9): embed github_login in JWT and add github_login column
- 9237aaf: feat(quick-260403-oo9): JWT-protect all thread routes and filter GET /api/threads by github_login
