---
phase: 10-superchat-thread-labels-mode-get-api-threads-left-join-orchestratorgraph-langgraph-checkpointer-usethreads
plan: "03"
subsystem: api
tags: [threads, app_id, left-join, postgresql, fastapi]
dependency_graph:
  requires: ["10-02"]
  provides: ["threads-api-with-app-id", "left-join-listing"]
  affects: ["frontend/useThreads", "10-04"]
tech_stack:
  added: []
  patterns: ["LEFT JOIN for nullable-safe thread listing", "app_id derived from mode at write time"]
key_files:
  created: []
  modified:
    - app/api/routes/chat.py
    - app/api/models.py
decisions:
  - "list_threads uses t.updated_at DESC not checkpoint_id: checkpoint_id is NULL for new threads under LEFT JOIN, breaking sort"
  - "send_message derives app_id from mode at write time: super->superchat, simple->chat"
  - "app_id NOT overwritten on conflict in threads upsert: first message determines application identity"
  - "rename_thread uses plain UPDATE threads (not upsert): rename only called on existing threads from UI"
metrics:
  duration: 2min
  completed: "2026-04-04"
  tasks: 2
  files: 2
---

# Phase 10 Plan 03: API Routes Migration to threads Table Summary

Migrated all `/api/threads` routes from the old `thread_labels` table to the new `threads` table with LEFT JOIN for listing and app_id-based application segregation.

## What Was Built

- `GET /api/threads`: Rewrote from `INNER JOIN thread_labels` to `LEFT JOIN checkpoints` FROM the `threads` table, so threads without checkpoints now appear in listings. Added optional `app_id` query parameter for per-application filtering. Sorting uses `t.updated_at DESC` (not checkpoint_id which is NULL under LEFT JOIN).
- `POST /api/chat`: Replaced `INSERT INTO thread_labels` with `INSERT INTO threads` including `app_id` field. app_id is derived from mode: `super` -> `superchat`, `simple` -> `chat`. app_id is never overwritten on conflict.
- `DELETE /api/threads/{id}`: Ownership check now queries `threads` table.
- `PATCH /api/threads/{id}`: Replaced upsert into `thread_labels` with plain `UPDATE threads SET label = %s`.
- `ThreadInfo` model: Added optional `app_id: str | None = None` field.

## Deviations from Plan

### Pre-existing Test Failures (Out of Scope)

3 tests in `tests/test_api_chat.py` were already failing before this plan's execution:
- `test_new_thread_returns_uuid` — calls `POST /api/threads` without JWT cookie; route requires auth
- `test_list_threads_empty` — calls `GET /api/threads` without JWT cookie; route requires auth
- `test_delete_thread_calls_adelete` — calls `DELETE /api/threads/{id}` without JWT cookie

These pre-existed in the codebase (verified by running tests after git stash). Not introduced by this plan. Same 5 tests that were passing before remain passing.

None — plan executed exactly as written for Task 1 and Task 2. Pre-existing test failures are documented above and deferred.

## Success Criteria Verification

- [x] list_threads uses LEFT JOIN from threads to checkpoints
- [x] list_threads accepts optional app_id query parameter via FastAPI
- [x] No app_id = all threads returned (backward compat)
- [x] send_message upserts into threads with app_id; app_id NOT overwritten on conflict
- [x] delete_thread references threads table
- [x] rename_thread references threads table
- [x] ThreadInfo model includes optional app_id field
- [x] Zero references to thread_labels in app/api/routes/chat.py

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 43513df | feat(10-03): update ThreadInfo model + list_threads with LEFT JOIN and app_id filter |
| 2 | ebeb8d6 | feat(10-03): migrate all routes from thread_labels to threads table |

## Self-Check: PASSED
