---
phase: 04-sse-redis-worker-jobstore-notifier
plan: "02"
subsystem: jobs-worker
tags: [arq, worker, async, redis, langgraph]
dependency_graph:
  requires: ["04-01"]
  provides: ["app/jobs/worker.py", "arq WorkerSettings", "process_chat"]
  affects: ["app/jobs/job_store.py", "app/jobs/notifier.py"]
tech_stack:
  added: ["arq>=0.26", "redis[asyncio]>=4.2.0"]
  patterns: ["arq worker startup/shutdown hooks", "save_result before notifier.done ordering"]
key_files:
  created:
    - app/jobs/worker.py
    - app/jobs/job_store.py
    - app/jobs/notifier.py
    - app/jobs/__init__.py
    - tests/test_worker.py
  modified:
    - pyproject.toml
    - uv.lock
decisions:
  - "process_chat saves result BEFORE calling notifier.done — guarantees SSE client can fetch result immediately on done signal"
  - "llm.close() in finally block — unconditional cleanup regardless of success or error"
  - "job_store.py and notifier.py created in this worktree as Plan 01 is running in parallel — interfaces match Plan 01 exactly"
  - "WorkerSettings.job_timeout = 300 — 5 minutes matches send_and_wait timeout"
metrics:
  duration: "2min"
  completed: "2026-04-01"
  tasks_completed: 1
  files_created: 5
  files_modified: 2
---

# Phase 04 Plan 02: arq Worker Module Summary

**One-liner:** arq worker with process_chat function that runs LangGraph ainvoke, saves result to Redis via JobStore, then signals SSE completion via Notifier — with guaranteed LLM cleanup in finally block.

## Tasks Completed

| # | Task | Status | Commit |
|---|------|--------|--------|
| 1 | Implement arq worker module + update test_worker.py to pass | Done | 61fe98b |

## What Was Built

### app/jobs/worker.py

The arq worker module that runs as a separate process from FastAPI. Key components:

- `startup(ctx)`: Initialises Redis client and JobStore on worker process start
- `shutdown(ctx)`: Closes Redis connection on worker process stop
- `process_chat(ctx, *, job_id, thread_id, prompt, model, github_token, reply_to)`: Main job function that:
  1. Builds notifier from `reply_to` channel spec
  2. Creates `ChatCopilot` with per-job github_token
  3. Opens `AsyncSqliteSaver` context for LangGraph checkpointing
  4. Calls `build_graph(llm, checkpointer).ainvoke(...)` with thread config
  5. Saves result via `job_store.save_result(job_id, final_text)` **first**
  6. Then calls `notifier.done()` to unblock the SSE stream
  7. On exception: saves error message, still calls `notifier.done()`
  8. In finally: always calls `llm.close()`
- `WorkerSettings`: arq configuration class listing `process_chat`, startup/shutdown hooks, and `job_timeout = 300`

### tests/test_worker.py

5 tests covering all critical behaviors:
- `test_process_chat_saves_result` — verifies save_result called with correct args, notifier called
- `test_process_chat_error_handling` — verifies error string saved, notifier.done still called
- `test_process_chat_closes_llm` — verifies llm.close() in finally block
- `test_startup_creates_redis_and_jobstore` — verifies ctx keys populated
- `test_shutdown_closes_redis` — verifies redis_client.aclose() called

## Decisions Made

1. **save_result BEFORE notifier.done**: Critical ordering — the SSE client's done handler fetches the result immediately, so result must be persisted first. Documented in code comment.

2. **llm.close() in finally**: Unconditional — guarantees the CopilotClient subprocess terminates even if LangGraph throws. Matches existing pattern in `_agenerate()`.

3. **job_store.py and notifier.py duplicated in this worktree**: Plan 01 (which creates these files) is running as a parallel agent. Interfaces were copied exactly from Plan 01's worktree output. The orchestrator merge will deduplicate.

4. **arq + redis added to pyproject.toml**: Required for worker functionality. Versions match RESEARCH.md recommendations (arq>=0.26, redis[asyncio]>=4.2.0).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Created app/jobs/job_store.py and notifier.py in this worktree**
- **Found during:** Task 1 setup — these files don't exist in this worktree (Plan 01 is a parallel agent)
- **Issue:** worker.py imports from app.jobs.job_store and app.jobs.notifier; without them the module fails to import
- **Fix:** Created both files with interfaces identical to Plan 01's output (verified from agent-a7d2d6a0 worktree)
- **Files modified:** app/jobs/job_store.py, app/jobs/notifier.py (created)
- **Commit:** 61fe98b

### Pre-existing Failures (Out of Scope)

Two tests in `test_api_auth.py` were failing before this plan:
- `test_auth_poll_pending` — TypeError in check_device_flow mock
- `test_auth_poll_success_sets_cookie` — ValueError in check_device_flow mock

These are pre-existing failures unrelated to worker implementation. Documented in `deferred-items.md` for follow-up.

## Known Stubs

None — all code paths are fully implemented and tested.

## Self-Check: PASSED

- [x] app/jobs/worker.py exists and contains all required symbols
- [x] tests/test_worker.py exists with 5 tests, no pytest.mark.skip
- [x] commit 61fe98b exists
- [x] `uv run pytest tests/test_worker.py -x -q` exits 0 (5 passed)
- [x] WorkerSettings.functions returns [process_chat]
