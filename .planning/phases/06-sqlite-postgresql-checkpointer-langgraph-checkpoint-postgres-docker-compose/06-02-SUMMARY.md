---
phase: 06-sqlite-postgresql-checkpointer
plan: 02
subsystem: tests
tags: [postgresql, psycopg, testing, asyncmock, chat-routes]
dependency_graph:
  requires: ["06-01"]
  provides: ["CKPT-03", "CKPT-04", "CKPT-05"]
  affects: ["tests/test_api_chat.py", "tests/conftest.py"]
tech_stack:
  added: []
  patterns:
    - "AsyncMock for async checkpointer in test fixtures"
    - "adelete_thread delegation pattern for thread deletion"
key_files:
  created: []
  modified:
    - tests/conftest.py
    - tests/test_api_chat.py
decisions:
  - "AsyncMock() used for checkpointer in conftest — MagicMock() does not support await, causing TypeError on adelete_thread calls"
  - "test_delete_thread_calls_adelete does NOT manually reassign adelete_thread = AsyncMock() — AsyncMock auto-creates awaitable children; manual reassignment would mask regression if conftest reverted"
metrics:
  duration: 2min
  completed: 2026-04-01
  tasks_completed: 2
  files_changed: 2
---

# Phase 06 Plan 02: Chat Test Suite — AsyncMock Upgrade + adelete_thread Verification

One-liner: Test fixtures upgraded from MagicMock to AsyncMock for checkpointer, with new test asserting DELETE /api/threads delegates to adelete_thread (CKPT-04).

## What Was Done

Plan 06-01 had already fully migrated `app/api/routes/chat.py` to psycopg + adelete_thread as a deviation. Plan 06-02 completed the remaining work: upgrading the test infrastructure to match the new async checkpointer usage.

### Task 1: Rewrite chat.py thread routes (already done by 06-01 executor)

`app/api/routes/chat.py` was already fully migrated by the 06-01 executor as a documented deviation. Verified all acceptance criteria pass:
- No `aiosqlite` references
- Uses `psycopg.AsyncConnection.connect` for thread listing
- Uses `checkpointer.adelete_thread(thread_id)` for deletion
- Uses `request.app.state.db_uri` for the connection string

No commit was needed — Task 1 was already complete.

### Task 2: Update test_api_chat.py and conftest.py

**Commit:** `6c3307d`

Changes made:
- `tests/conftest.py`: Changed `app.state.checkpointer = MagicMock()` to `app.state.checkpointer = AsyncMock()`. Required because `delete_thread` now awaits `checkpointer.adelete_thread()` — MagicMock raises TypeError in that context.
- `tests/test_api_chat.py`: Added `test_delete_thread_calls_adelete` test that verifies DELETE /api/threads/{id} returns 204 and calls `checkpointer.adelete_thread("test-thread-123")` exactly once.
- `tests/test_api_chat.py`: Updated module docstring to say "local PostgreSQL data only" (not SQLite).

## Verification Results

```
8 passed (test_api_chat.py) — all chat tests green
63 passed total (excluding pre-existing test_auth_poll_pending failure)
No aiosqlite/AsyncSqliteSaver/langgraph.checkpoint.sqlite/db_path refs in app/ or tests/
```

## Deviations from Plan

### Pre-existing out-of-scope failure

**Found during:** Task 2 verification
**Issue:** `tests/test_api_auth.py::test_auth_poll_pending` fails with `TypeError: cannot unpack non-iterable NoneType` — pre-dates this plan (confirmed by checking git stash before my changes). This is in `app/api/routes/auth.py:66` and unrelated to the checkpointer migration.
**Action:** Logged to deferred-items. Not fixed — out of scope per deviation rule (pre-existing, different subsystem).

### Task 1 already completed by 06-01 executor

**Type:** Not a deviation — the 06-01 executor proactively migrated chat.py as a documented deviation in 06-01-SUMMARY.md. Task 1 of this plan was already done.

## Known Stubs

None — all routes wire to real state fields (db_uri, checkpointer).

## Self-Check: PASSED

- `tests/conftest.py` — modified, verified `AsyncMock()` present
- `tests/test_api_chat.py` — modified, verified `test_delete_thread_calls_adelete` present
- Commit `6c3307d` — exists (`git log --oneline | grep 6c3307d`)
- Zero sqlite refs in app/ and tests/
- 8/8 chat tests pass
