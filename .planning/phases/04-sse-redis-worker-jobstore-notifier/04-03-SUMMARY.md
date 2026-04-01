---
phase: 04-sse-redis-worker-jobstore-notifier
plan: 03
subsystem: api-gateway
tags: [fastapi, arq, redis, sse, streaming, async, polling]
dependency_graph:
  requires: ["04-01"]
  provides: ["04-04"]
  affects: ["app/api/routes/chat.py", "app/api/routes/jobs.py", "app/api/main.py"]
tech_stack:
  added: ["arq (ArqRedis.enqueue_job)", "redis.asyncio (Redis)", "StreamingResponse (SSE)"]
  patterns: ["SSE via asyncio.Queue", "arq enqueue pattern", "polling fallback endpoint"]
key_files:
  created: ["app/api/routes/jobs.py", "tests/test_api_jobs.py", "tests/test_sse.py"]
  modified: ["app/api/models.py", "app/api/routes/chat.py", "app/api/main.py", "tests/conftest.py", "tests/test_api_chat.py"]
decisions:
  - "POST /api/chat returns ChatAsyncResponse (job_id + thread_id) instead of ChatResponse (reply) — gateway no longer blocks on LangGraph"
  - "SSE immediate-done path: check job_store.get() before registering queue — handles reload/reconnect case"
  - "arq_redis.enqueue_job() uses keyword-only args: job_id, thread_id, prompt, model, github_token, reply_to"
  - "redis_client and arq_redis torn down in lifespan finally (after yield) with aclose()"
metrics:
  duration: "8min"
  completed: "2026-04-01T07:43:00Z"
  tasks_completed: 2
  files_changed: 8
---

# Phase 4 Plan 03: FastAPI Gateway Async Refactor Summary

**One-liner:** Refactored FastAPI gateway to enqueue chat jobs via arq and return job_id immediately, with SSE stream endpoint and polling fallback for result delivery.

## What Was Built

The gateway became a thin routing layer:
- `POST /api/chat` now enqueues to arq worker via `ArqRedis.enqueue_job("process_chat", ...)` and returns `{job_id, thread_id}` immediately (non-blocking)
- `GET /api/chat/{job_id}/stream` delivers real-time SSE events via `asyncio.Queue` registered in `JobStore`; handles already-done case (immediate done event for reconnects)
- `GET /api/job/{job_id}` polls `JobStore.get()` for result (fallback path)
- FastAPI lifespan now creates `Redis`, `ArqRedis` pool, and `JobStore`; tears them down on shutdown

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add API models + jobs route + SSE endpoint + update main.py lifespan | e03a563 | app/api/models.py, app/api/routes/jobs.py, app/api/routes/chat.py, app/api/main.py, app/jobs/* |
| 2 (TDD) | Update conftest + replace test stubs with real tests | 397e8c0 | tests/conftest.py, tests/test_api_chat.py, tests/test_api_jobs.py, tests/test_sse.py |

## Decisions Made

1. **Gateway enqueue pattern:** `arq_redis.enqueue_job("process_chat", ...)` passes `job_id`, `thread_id`, `prompt`, `model`, `github_token`, `reply_to` as kwargs — worker receives exactly what it needs with no shared state required
2. **SSE immediate-done check:** `await job_store.get(job_id)` before registering queue handles the reload/reconnect scenario (ASYNC-06) without requiring the worker to re-notify
3. **lifespan teardown order:** `redis_client.aclose()` and `arq_redis.aclose()` after the `AsyncSqliteSaver` context exits — ensures DB checkpoints flush before Redis disconnects
4. **ChatResponse kept in models.py:** The old `ChatResponse` model is preserved since it's still imported by other parts; only `send_message` was refactored to use `ChatAsyncResponse`

## Test Coverage

- `test_post_chat_returns_job_id` — POST /api/chat returns job_id immediately
- `test_chat_enqueue_includes_model` — model kwarg propagated to worker
- `test_chat_enqueue_includes_github_token` — github_token kwarg propagated to worker
- `test_get_job_pending` — polling returns pending when not in store
- `test_get_job_done` — polling returns done + result from JobStore
- `test_sse_already_done` — immediate done event for completed jobs
- `test_sse_done_signal` — SSE yields done when queue receives signal; unregister_sse called in finally

**Results:** 54 tests pass (11 new Phase 4 tests + 43 existing)

## Deviations from Plan

### Pre-existing issues (out of scope, deferred)

**1. [Pre-existing] test_api_auth.py::test_auth_poll_pending + test_auth_poll_success_sets_cookie failing**
- **Found during:** Full suite run
- **Issue:** `mock_auth_manager.check_device_flow` returns `None` but `auth.py:66` unpacks it as a 2-tuple `(token, retry_after)`. This mock configuration existed before plan 03 changes.
- **Fix:** Not fixed — pre-existing failure in unrelated file, logged to deferred-items.md
- **Scope:** Out of scope for this plan

### Auto-carried from Plan 01

Plan 01 (worktree `a7d2d6a0`) was not yet merged into main. Cherry-picked relevant artifacts (`app/jobs/`, `docker-compose.yml`, `pyproject.toml` deps) as a prerequisite for plan 03's compilation and test execution. Plan 01's docs/state were NOT carried.

## Known Stubs

None — all plan 03 endpoints are fully implemented and wired.

## Self-Check: PASSED
