---
phase: 06-sqlite-postgresql-checkpointer
plan: 01
subsystem: database
tags: [postgres, psycopg, langgraph-checkpoint-postgres, docker-compose, checkpointer]

# Dependency graph
requires:
  - phase: 04-sse-redis-worker-jobstore-notifier
    provides: arq worker (worker.py) and FastAPI lifespan (main.py) that both use checkpointer
  - phase: 03-web-chat-ui
    provides: chat.py thread routes (list_threads, delete_thread) using db connection

provides:
  - AsyncPostgresSaver replaces AsyncSqliteSaver in FastAPI lifespan and arq worker
  - PostgreSQL Docker service with healthcheck in docker-compose.yml
  - psycopg-based thread listing and adelete_thread-based deletion in chat.py
  - Worker startup() hook calls checkpointer.setup() for race condition safety

affects:
  - phase-06-plan-02 (thread route tests that depend on db_uri state field)

# Tech tracking
tech-stack:
  added:
    - langgraph-checkpoint-postgres>=3.0.5 (AsyncPostgresSaver)
    - psycopg[binary]>=3.2.0 (async PostgreSQL driver v3)
    - psycopg-pool>=3.2.0 (connection pool support)
  patterns:
    - AsyncPostgresSaver.from_conn_string(DB_URI) as async context manager in lifespan
    - await checkpointer.setup() called once at startup (idempotent table migration)
    - Worker startup() hook calls setup() for race condition safety
    - DATABASE_URL env var as single source of truth for PostgreSQL DSN
    - adelete_thread() replaces raw SQL DELETE for thread deletion

key-files:
  created: []
  modified:
    - pyproject.toml
    - docker-compose.yml
    - app/api/main.py
    - app/jobs/worker.py
    - app/graph/builder.py
    - app/api/routes/chat.py
    - tests/conftest.py
    - tests/test_worker.py

key-decisions:
  - "AsyncPostgresSaver.from_conn_string(DB_URI) used in both api lifespan and worker process_chat — matches prior SQLite pattern"
  - "Worker startup() calls checkpointer.setup() idempotently — eliminates race condition if worker starts before api lifespan completes"
  - "DATABASE_URL env var with postgresql://postgres:postgres@localhost:5432/postgres?sslmode=disable default — conventional name, Docker-friendly"
  - "adelete_thread() replaces raw SQL DELETE in chat.py — avoids schema-name coupling, atomic across all checkpoint tables"
  - "psycopg[binary] over psycopg (pure Python) — works in slim bookworm Docker image without libpq-dev apt install"
  - "postgres:17-alpine with pg_isready healthcheck and condition:service_healthy — prevents api/worker starting before PG ready"

patterns-established:
  - "Pattern: FastAPI lifespan owns PostgreSQL connection via async with AsyncPostgresSaver.from_conn_string; calls setup() immediately"
  - "Pattern: Worker opens fresh AsyncPostgresSaver.from_conn_string per job (same as former SQLite pattern)"
  - "Pattern: Worker startup hook opens temporary checkpointer context solely to call setup() — closed after setup completes"

requirements-completed: [CKPT-01, CKPT-02, CKPT-05]

# Metrics
duration: 4min
completed: 2026-04-01
---

# Phase 06 Plan 01: SQLite to PostgreSQL Checkpointer Migration Summary

**AsyncPostgresSaver replaces AsyncSqliteSaver in FastAPI lifespan and arq worker; PostgreSQL added to Docker Compose with healthcheck; psycopg replaces aiosqlite in thread routes**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-04-01T11:06:34Z
- **Completed:** 2026-04-01T11:10:13Z
- **Tasks:** 3 planned + 1 deviation auto-fix
- **Files modified:** 8

## Accomplishments

- Replaced `AsyncSqliteSaver` with `AsyncPostgresSaver` in FastAPI lifespan (`main.py`) with `await checkpointer.setup()` call
- Replaced `AsyncSqliteSaver` with `AsyncPostgresSaver` in arq worker (`worker.py`); added `checkpointer.setup()` in `startup()` hook for race condition safety
- Added `postgres:17-alpine` service to `docker-compose.yml` with `pg_isready` healthcheck and `condition: service_healthy` for api/worker dependencies
- Migrated `app/api/routes/chat.py` thread routes from `aiosqlite` to `psycopg`; replaced raw DELETE SQL with `checkpointer.adelete_thread()`
- Removed `langgraph-checkpoint-sqlite` and `aiosqlite` from `pyproject.toml`; added `langgraph-checkpoint-postgres`, `psycopg[binary]`, `psycopg-pool`

## Task Commits

1. **Task 1: Update dependencies and Docker Compose** - `83d187f` (feat)
2. **Task 2: Migrate main.py and worker.py to AsyncPostgresSaver** - `2fbb6db` (feat)
3. **Task 3: Update tests — conftest.py and test_worker.py patches** - `32b0812` (test)
4. **Deviation: Migrate chat.py thread routes from aiosqlite to psycopg** - `7d28330` (fix)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `pyproject.toml` - Replaced SQLite deps with PostgreSQL deps
- `docker-compose.yml` - Added postgres service, DATABASE_URL env vars, healthy depends_on
- `app/api/main.py` - AsyncPostgresSaver, checkpointer.setup(), DB_URI, app.state.db_uri
- `app/jobs/worker.py` - AsyncPostgresSaver, DB_URI, setup() in startup() hook
- `app/graph/builder.py` - Updated docstring: AsyncSqliteSaver -> AsyncPostgresSaver
- `app/api/routes/chat.py` - Replaced aiosqlite with psycopg; list_threads uses dict_row; delete_thread uses adelete_thread()
- `tests/conftest.py` - app.state.db_path -> app.state.db_uri
- `tests/test_worker.py` - All patches updated to AsyncPostgresSaver; startup test verifies setup() called

## Decisions Made

- Used `adelete_thread()` for thread deletion instead of raw SQL — atomic, schema-independent, recommended in research
- Worker `startup()` calls `checkpointer.setup()` in a temporary context manager — idempotent, eliminates race condition with api lifespan
- `DATABASE_URL` env var with `localhost` default for local dev, `postgres` hostname in Docker Compose for container networking

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Migrated chat.py thread routes from aiosqlite to psycopg**
- **Found during:** Post-Task 3 verification (overall test run)
- **Issue:** Removing `aiosqlite` from `pyproject.toml` in Task 1 caused `ModuleNotFoundError: No module named 'aiosqlite'` when `chat.py` was imported. This broke 68 tests that import the FastAPI app (which imports `chat.py`). The plan listed `chat.py` as out of scope for Plan 01, but the dependency removal made it blocking.
- **Fix:** Rewrote `list_threads()` using `psycopg.AsyncConnection.connect` with `dict_row`; replaced raw SQL DELETE in `delete_thread()` with `checkpointer.adelete_thread()`; renamed `db_path` -> `db_uri` state access; updated docstring
- **Files modified:** `app/api/routes/chat.py`
- **Verification:** 68 tests pass (2 pre-existing auth test failures unrelated to this migration)
- **Committed in:** `7d28330` (separate deviation commit)

---

**Total deviations:** 1 auto-fixed (blocking import error)
**Impact on plan:** Necessary to complete the migration. The aiosqlite removal required the chat.py migration to happen in the same plan. This effectively merged the chat.py work from a hypothetical Plan 02 into Plan 01.

## Issues Encountered

- Pre-existing test failures in `test_api_auth.py::test_auth_poll_pending` and `test_auth_poll_success_sets_cookie` (2 failures) — unrelated to this migration, existed before phase 06 work. Not fixed (out of scope).

## User Setup Required

None - no external service configuration required for development. For production, set `DATABASE_URL` environment variable. Docker Compose handles PostgreSQL automatically.

## Next Phase Readiness

- PostgreSQL checkpointer migration complete — all production code uses `AsyncPostgresSaver`
- `docker-compose.yml` ready to run with `docker compose up`
- Test suite passes (68/70, 2 pre-existing auth failures)
- Plan 02 scope may be reduced since `chat.py` migration was completed here

---
*Phase: 06-sqlite-postgresql-checkpointer*
*Completed: 2026-04-01*
