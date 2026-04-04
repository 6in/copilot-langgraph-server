---
phase: 10-superchat-thread-labels-mode
plan: "01"
subsystem: tests
tags: [tdd, wave-0, red-phase, mode-filter, left-join, orchestrator, checkpointer]
dependency_graph:
  requires: []
  provides: [test-scaffolding-phase10]
  affects: [tests/test_api_chat.py, tests/test_worker.py]
tech_stack:
  added: []
  patterns: [pytest.mark.skip, unittest.mock.patch, Wave-0-RED-phase]
key_files:
  created: []
  modified:
    - tests/test_api_chat.py
    - tests/test_worker.py
decisions:
  - Wave 0 tests marked skip so existing CI stays green while serving as executable spec for Waves 1-3
  - Mocked psycopg.AsyncConnection.connect at patch level for DB-touching route tests
  - Captured SQL text via side_effect on conn.execute to assert mode column and LEFT JOIN are used
  - test_orchestrator_handler_uses_checkpointer captures build_orchestrator_graph call args to assert checkpointer != None
metrics:
  duration: 2min
  completed_date: "2026-04-04"
  tasks_completed: 2
  files_modified: 2
---

# Phase 10 Plan 01: Wave 0 RED Phase — Failing Tests Summary

Wave 0 RED phase: 5 failing (skipped) tests establish the executable spec for all Phase 10 backend behaviors before any production code is changed.

## What Was Done

Added 4 new skip-marked test functions to `tests/test_api_chat.py` and 1 to `tests/test_worker.py` that describe the desired Phase 10 behaviors.

### tests/test_api_chat.py — 4 new tests

| Test | Requirement | Validates |
|------|-------------|-----------|
| `test_list_threads_mode_filter` | API-02 | GET /api/threads?mode=superchat returns only superchat threads |
| `test_list_threads_no_mode_returns_all` | API-02 | No ?mode param returns all threads (backward compat) |
| `test_chat_upsert_mode` | DB-01, API-01 | POST /api/chat upserts mode='superchat' or mode='chat' to thread_labels |
| `test_list_threads_left_join` | API-03 | GET /api/threads includes threads with no checkpoints (LEFT JOIN) |

### tests/test_worker.py — 1 new test

| Test | Requirement | Validates |
|------|-------------|-----------|
| `test_orchestrator_handler_uses_checkpointer` | ORC-01 | OrchestratorHandler wires AsyncPostgresSaver as checkpointer, passes thread_id in config |

## Test Patterns Used

- `@pytest.mark.skip(reason="Phase 10 Wave 0: will pass after Wave 1-2/3")` — keeps CI green
- `patch("psycopg.AsyncConnection.connect", return_value=mock_conn)` — intercepts DB calls in routes
- SQL capture via `side_effect` on `conn.execute` — asserts mode column appears in upsert SQL
- `captured_build_args` dict via `side_effect` on `build_orchestrator_graph` — verifies checkpointer kwarg

## Deviations from Plan

None — plan executed exactly as written.

Pre-existing test failures noted (out of scope, not introduced by this plan):
- `test_new_thread_returns_uuid`, `test_list_threads_empty`, `test_delete_thread_calls_adelete` — routes gained JWT protection after tests were written; tests don't pass cookies
- `test_graph.py::test_messages_accumulate` — pre-existing failure
- `test_worker.py::test_process_chat_*` (3 tests) — `ChatCopilot` import patched at wrong path

These failures all pre-dated this plan (confirmed via git stash test).

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | f821455 | test(10-01): add Phase 10 Wave 0 failing tests for mode filter, LEFT JOIN, mode upsert |
| Task 2 | 4bb0fec | test(10-01): add Phase 10 Wave 0 failing test for orchestrator checkpointer |

## Self-Check: PASSED
