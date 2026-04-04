---
phase: 10-superchat-thread-labels-mode-get-api-threads-left-join-orchestratorgraph-langgraph-checkpointer-usethreads
plan: "02"
subsystem: database
tags: [postgres, psycopg, migration, applications, threads, audit_log, thread_labels]

requires:
  - phase: 10-01
    provides: Wave 0 test skeletons marking DB-01/DB-02 behavior as executable spec

provides:
  - DROP thread_labels (legacy single-table label store removed)
  - CREATE applications table with chat/superchat seed rows
  - CREATE threads table with app_id FK to applications
  - CREATE audit_log table with indexes (schema only, no write logic)

affects:
  - 10-03 (chat.py routes must be updated to use new threads/applications tables instead of thread_labels)
  - 10-04 (OrchestratorGraph checkpointer, uses thread_id from threads table)
  - 10-05 (frontend useThreads, reads from GET /api/threads which joins threads table)

tech-stack:
  added: []
  patterns:
    - "Inline lifespan migration: all DDL runs inside psycopg.AsyncConnection at startup for zero-config deployment"
    - "Seed data with ON CONFLICT DO NOTHING: idempotent inserts safe on every restart"
    - "audit_log schema-only: table + indexes created but no INSERT logic — write path deferred to future phases"

key-files:
  created: []
  modified:
    - app/api/main.py

key-decisions:
  - "DROP TABLE IF EXISTS thread_labels before creating new tables — clean break, no migration path needed (dev environment)"
  - "applications table uses TEXT PK (not SERIAL) — app_id values are meaningful strings ('chat', 'superchat'), not opaque integers"
  - "threads table has app_id FK NOT NULL — every thread must belong to an application, enforced at DB level"
  - "audit_log gets table + indexes ONLY in this plan — no INSERT logic added (schema preparation for future phases)"

patterns-established:
  - "Normalized schema: applications -> threads (FK) -> audit_log (FK) replaces flat thread_labels table"

requirements-completed: [DB-01, DB-02]

duration: 5min
completed: 2026-04-04
---

# Phase 10 Plan 02: Replace thread_labels with normalized schema (applications/threads/audit_log)

**Lifespan migration in app/api/main.py replaces flat thread_labels table with normalized applications/threads/audit_log schema, seeding chat and superchat rows idempotently**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-04T09:23:37Z
- **Completed:** 2026-04-04T09:28:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Removed legacy `thread_labels` table creation from lifespan migration
- Added normalized schema: `applications`, `threads`, `audit_log` with proper FK constraints
- Seeded `chat` and `superchat` application rows with `ON CONFLICT DO NOTHING` for idempotency
- Created `audit_log_github_login_idx` and `audit_log_created_at_idx` indexes
- Confirmed zero `INSERT INTO audit_log` writes anywhere in the codebase (schema-only preparation)

## Task Commits

Each task was committed atomically:

1. **Task 1: Replace thread_labels migration with new schema in lifespan** - `3b60891` (feat)

**Plan metadata:** (committed with SUMMARY/STATE/ROADMAP update)

## Files Created/Modified

- `app/api/main.py` - Lifespan migration block replaced: DROP thread_labels + CREATE applications/threads/audit_log + seed data + indexes

## Decisions Made

- DROP TABLE IF EXISTS thread_labels first — clean break avoids complex column migration in dev environment
- applications table uses TEXT PK with meaningful names ('chat', 'superchat') rather than SERIAL integer keys
- threads FK app_id NOT NULL — enforces every thread must belong to a known application at DB level
- audit_log schema-only in this plan — write path (INSERT logic) deferred to future phases per plan spec

## Remaining thread_labels References (to be fixed in Wave 2 / plan 10-03)

The following files still reference `thread_labels` and will be updated in plan 10-03:

- `app/api/routes/chat.py:71` — docstring mentions thread_labels
- `app/api/routes/chat.py:94` — comment about upsert
- `app/api/routes/chat.py:101` — INSERT INTO thread_labels SQL
- `app/api/routes/chat.py:104` — DO UPDATE SET ... thread_labels
- `app/api/routes/chat.py:110` — comment about thread_labels upsert failure
- `app/api/routes/chat.py:178` — docstring about INNER JOIN
- `app/api/routes/chat.py:191` — INNER JOIN thread_labels SQL
- `app/api/routes/chat.py:220` — docstring about ownership verification
- `app/api/routes/chat.py:233` — SELECT github_login FROM thread_labels
- `app/api/routes/chat.py:267` — INSERT INTO thread_labels
- `tests/test_api_chat.py:108` — test docstring about thread_labels.mode
- `tests/test_api_chat.py:219` — test for POST /api/chat writes mode to thread_labels
- `tests/test_api_chat.py:248-250` — assertions on thread_labels upsert calls
- `tests/test_api_chat.py:266` — thread_labels upsert assertion
- `tests/test_api_chat.py:275-290` — GET /api/threads test referencing thread_labels

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- pytest not available in worktree environment (`.venv` has broken Python symlink, `uv` fails due to filesystem permissions). Tests verified via grep-based SQL presence checks as specified in the plan's `<automated>` verification block. Tests will run correctly inside Docker where the proper venv exists.

## Next Phase Readiness

- Schema foundation complete: `applications`, `threads`, `audit_log` tables will be created on next app startup
- Plan 10-03 must update `app/api/routes/chat.py` to use `threads` table instead of `thread_labels`
- Existing Wave 0 skipped tests (from plan 10-01) provide executable spec for what 10-03 must implement

---
*Phase: 10-superchat-thread-labels-mode-get-api-threads-left-join-orchestratorgraph-langgraph-checkpointer-usethreads*
*Completed: 2026-04-04*
