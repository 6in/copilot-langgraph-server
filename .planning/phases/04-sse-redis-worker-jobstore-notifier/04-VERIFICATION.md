---
phase: 04-sse-redis-worker-jobstore-notifier
verified: 2026-04-01T08:35:58Z
status: gaps_found
score: 6/7 must-haves verified
gaps:
  - truth: "GET /api/chat/{job_id}/stream yields SSE events and done signal"
    status: failed
    reason: "test_sse_done_signal hangs indefinitely because the implementation was migrated to Redis polling (no register_sse call) but the test still mocks asyncio.Queue via register_sse. The test never completes."
    artifacts:
      - path: "tests/test_sse.py"
        issue: "test_sse_done_signal mocks register_sse to return a Queue and puts a done event on it, but stream_job never calls register_sse in the Redis-polling implementation. The polling loop calls job_store.get() which the mock returns None indefinitely — test hangs."
      - path: "app/api/routes/chat.py"
        issue: "stream_job uses Redis polling (job_store.get() in a loop with asyncio.sleep(1)) instead of asyncio.Queue. register_sse and unregister_sse are never called in the in-progress path. The test also asserts unregister_sse.assert_called_once_with('j1') which will also fail since unregister_sse is never called."
    missing:
      - "Update test_sse_done_signal to match Redis-polling implementation: mock job_store.get to return None on first call, then return {'status': 'done', 'result': '...'} on second call (using side_effect=[None, {'status': 'done', 'result': 'hi'}])"
      - "Remove register_sse and unregister_sse assertions from test_sse_done_signal — they are not called by the Redis-polling implementation"
      - "Remove unregister_sse call from mock_job_store fixture or update test to not assert it for the stream endpoint"
human_verification:
  - test: "End-to-end async chat flow in browser"
    expected: "User sends a message, typing indicator appears, AI reply appears after worker processes it. SSE stream in DevTools shows done event."
    why_human: "Requires running Redis, FastAPI, and arq worker process simultaneously. Cannot verify programmatically without live Redis."
---

# Phase 4: Async Job Queue + SSE Verification Report

**Phase Goal:** Migrate synchronous POST /api/chat to async architecture: Gateway enqueues job and returns job_id immediately, Worker process executes LangGraph via arq, SSE delivers real-time completion signal, polling API provides recovery fallback

**Verified:** 2026-04-01T08:35:58Z
**Status:** gaps_found
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | POST /api/chat returns job_id immediately without blocking on LangGraph execution | VERIFIED | `send_message` calls `arq_redis.enqueue_job` and returns `ChatAsyncResponse(job_id, thread_id)`. `test_post_chat_returns_job_id` passes. |
| 2 | GET /api/job/{job_id} returns pending before completion, done with result after | VERIFIED | `get_job` in `jobs.py` calls `job_store.get()` and returns `JobStatusResponse`. `test_get_job_pending` and `test_get_job_done` both pass. |
| 3 | SSE endpoint delivers real-time done signal when worker completes | VERIFIED (implementation) / PARTIAL (test) | `stream_job` Redis-polling implementation exists and delivers done SSE. `test_sse_already_done` passes. `test_sse_done_signal` hangs because the test was written for the asyncio.Queue approach but the implementation uses Redis polling. |
| 4 | SSE endpoint returns immediate done for already-completed jobs (page reload scenario) | VERIFIED | `stream_job` checks `job_store.get()` before entering polling loop. `test_sse_already_done` passes. |
| 5 | Frontend sends message, shows typing indicator, receives AI reply via SSE or polling | VERIFIED (code) / NEEDS HUMAN (UX) | `sendMessage()` in `app.js` uses EventSource, `startPolling()`, and fetch `/api/job/{id}`. No `data.reply` reference remains. Visual verification confirmed by human per Plan 04 checkpoint. |
| 6 | Worker process runs LangGraph in separate process, saves result to Redis before signalling done | VERIFIED | `process_chat` in `worker.py`: save_result called BEFORE notifier.done. `test_process_chat_saves_result` passes (5/5 worker tests green). |
| 7 | Polling fallback activates when SSE connection drops | VERIFIED (code) / NEEDS HUMAN (UX) | `es.onerror` calls `startPolling(job_id)`. `startPolling()` polls every 2 seconds. Cannot test without live browser + SSE disconnect simulation. |

**Score:** 6/7 truths verified (Truth 3 has passing implementation but a hanging test)

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `app/jobs/__init__.py` | Package marker for app.jobs | VERIFIED | Exists, empty package marker. |
| `app/jobs/job_store.py` | JobStore class with Redis persistence + asyncio.Queue | VERIFIED | `class JobStore`, `save_result`, `notify`, `get`, `register_sse`, `unregister_sse` all present. |
| `app/jobs/notifier.py` | BaseNotifier, WebNotifier, build_notifier() | VERIFIED | All three present, wired to JobStore. |
| `app/jobs/worker.py` | arq worker with process_chat + WorkerSettings | VERIFIED | `process_chat`, `WorkerSettings`, `startup`, `shutdown` all present. `job_timeout = 300`. |
| `app/api/routes/chat.py` | POST /api/chat enqueue + GET /api/chat/{id}/stream SSE | VERIFIED | `arq_redis.enqueue_job`, `response_model=ChatAsyncResponse`, `stream_job` with Redis polling. |
| `app/api/routes/jobs.py` | GET /api/job/{job_id} polling endpoint | VERIFIED | `async def get_job`, `response_model=JobStatusResponse`, calls `job_store.get()`. |
| `app/api/models.py` | ChatAsyncResponse + JobStatusResponse models | VERIFIED | Both models present with correct fields. |
| `app/api/main.py` | Redis + arq + JobStore in lifespan | VERIFIED | `redis_client`, `arq_redis`, `job_store` all set on `app.state`. Teardown with `aclose()`. |
| `docker-compose.yml` | Redis 7-alpine service | VERIFIED | `redis:7-alpine` image. Full compose file includes `api` and `worker` services. Note: host port 6379 is NOT published (avoids conflict) — local dev requires `docker compose up` with compose networking. |
| `static/app.js` | Frontend with SSE + polling async flow | VERIFIED | `EventSource`, `startPolling`, `es.onerror`, `es.close`, `clearInterval`, `job_id` from POST response. No `data.reply` reference (old sync field). |
| `tests/test_job_store.py` | 5 unit tests for JobStore | VERIFIED | All 5 tests pass. |
| `tests/test_sse.py` | SSE endpoint tests | PARTIAL | `test_sse_already_done` passes. `test_sse_done_signal` hangs (test-implementation mismatch). |
| `tests/test_api_jobs.py` | Polling endpoint tests | VERIFIED | Both tests pass, no `pytest.mark.skip`. |
| `tests/test_worker.py` | arq worker tests | VERIFIED | All 5 tests pass, no `pytest.mark.skip`. |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `app/api/routes/chat.py` | `app/jobs/job_store.py` | `request.app.state.job_store` for SSE | WIRED | `job_store.get(job_id)` called in `stream_job`. |
| `app/api/routes/chat.py` | `app/api/main.py` | `request.app.state.arq_redis` for enqueue | WIRED | `arq_redis.enqueue_job(...)` called in `send_message`. |
| `app/api/routes/jobs.py` | `app/jobs/job_store.py` | `request.app.state.job_store.get()` | WIRED | `job_store.get(job_id)` called in `get_job`. |
| `app/jobs/worker.py` | `app/jobs/job_store.py` | `JobStore` instantiated in `startup`, used in `process_chat` | WIRED | `job_store.save_result(job_id, final_text)` called before `notifier.done()`. |
| `app/jobs/worker.py` | `app/jobs/notifier.py` | `build_notifier` called in `process_chat` | WIRED | `build_notifier(reply_to, job_store)` called with `reply_to={"type": "web", ...}`. |
| `app/jobs/worker.py` | `app/graph/builder.py` | `build_graph` called with llm and checkpointer | WIRED | `graph = build_graph(llm, checkpointer)` inside `AsyncSqliteSaver` context. |
| `static/app.js` | `/api/chat` | POST fetch for job_id | WIRED | `fetch('/api/chat', { method: 'POST', ... })` in `sendMessage()`. |
| `static/app.js` | `/api/chat/{job_id}/stream` | EventSource SSE connection | WIRED | `new EventSource('/api/chat/${job_id}/stream')`. |
| `static/app.js` | `/api/job/{job_id}` | fetch for result after done signal + polling fallback | WIRED | Both `es.onmessage` done handler and `startPolling()` call `fetch('/api/job/${job_id}')`. |

---

## Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `app/api/routes/chat.py` `send_message` | `job_id` | `uuid.uuid4()` | Yes — generates unique UUID | FLOWING |
| `app/api/routes/chat.py` `stream_job` | `result` | `job_store.get(job_id)` → Redis key `job:{id}` | Yes — reads from Redis after worker saves | FLOWING |
| `app/api/routes/jobs.py` `get_job` | `job` | `job_store.get(job_id)` → Redis | Yes — reads from Redis | FLOWING |
| `app/jobs/worker.py` `process_chat` | `final_text` | `graph.ainvoke(...) result["messages"][-1].content` | Yes — LangGraph AI response | FLOWING |
| `static/app.js` `sendMessage` | AI reply | `GET /api/job/{job_id}` after SSE done signal | Yes — fetches from polling API | FLOWING |

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| JobStore imports | `python -c "from app.jobs.job_store import JobStore; print('OK')"` | OK | PASS |
| Notifier imports | `python -c "from app.jobs.notifier import WebNotifier, build_notifier; print('OK')"` | OK | PASS |
| Worker imports + WorkerSettings | `python -c "from app.jobs.worker import WorkerSettings; print(WorkerSettings.functions)"` | `[<function process_chat at ...>]` | PASS |
| 5 JobStore tests | `pytest tests/test_job_store.py -v` | 5 passed | PASS |
| 5 Worker tests | `pytest tests/test_worker.py -v` | 5 passed | PASS |
| 2 Jobs API tests | `pytest tests/test_api_jobs.py -v` | 2 passed | PASS |
| SSE already-done test | `pytest tests/test_sse.py::test_sse_already_done -v` | 1 passed | PASS |
| SSE done signal test | `pytest tests/test_sse.py::test_sse_done_signal -v` | HANGS (timeout) | FAIL |
| Chat API tests | `pytest tests/test_api_chat.py -v` | 6 passed | PASS |

---

## Requirements Coverage

The ASYNC-* requirement IDs referenced in PLANs are not defined in `.planning/REQUIREMENTS.md` (which only covers v1 AUTH/PROV/GRPH/CHAT IDs). They are defined inline in the ROADMAP.md Phase 4 Success Criteria and VALIDATION.md. Cross-referencing against those definitions:

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| ASYNC-01 | 04-01, 04-03 | POST /api/chat enqueues job and returns job_id immediately | SATISFIED | `send_message` calls `arq_redis.enqueue_job`. `test_post_chat_returns_job_id` passes. |
| ASYNC-02 | 04-01, 04-03 | GET /api/job/{job_id} returns pending/done | SATISFIED | `get_job` in `jobs.py` verified. `test_get_job_pending` + `test_get_job_done` pass. |
| ASYNC-03 | 04-01 | JobStore saves result to Redis and retrieves it | SATISFIED | `save_result` writes JSON with TTL, `get` reads JSON. `test_save_and_get` passes. |
| ASYNC-04 | 04-01, 04-03 | SSE endpoint delivers real-time done signal | SATISFIED (implementation) / PARTIAL (test) | `stream_job` Redis-polling sends `{"status":"done"}`. `test_sse_done_signal` hangs due to test-implementation mismatch. |
| ASYNC-05 | 04-01 | JobStore.notify() with no registered queue does not raise | SATISFIED | `notify` guards with `if job_id in self.queues`. `test_notify_no_queue` passes. |
| ASYNC-06 | 04-01, 04-03 | SSE returns immediate done for already-complete jobs | SATISFIED | `stream_job` checks `job_store.get()` before polling loop. `test_sse_already_done` passes. |
| ASYNC-07 | 04-02 | Worker calls save_result before notifier.done, handles errors, closes LLM | SATISFIED | `process_chat` ordering enforced. All 5 worker tests pass. |

**Note:** ASYNC-* IDs are NOT defined in `.planning/REQUIREMENTS.md` — the file was last updated 2026-03-31 before Phase 4 was planned. The traceability table in REQUIREMENTS.md does not include Phase 4 rows. This is an ORPHANED requirements coverage gap in the planning docs, but the actual behavior requirements are defined in ROADMAP.md and VALIDATION.md.

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `tests/test_sse.py` | 35-70 | `test_sse_done_signal` mocks `register_sse` but implementation uses Redis polling — test hangs infinitely | Blocker | CI will hang on this test |
| `tests/test_sse.py` | 69-70 | Asserts `mock_job_store.unregister_sse.assert_called_once_with("j1")` — `unregister_sse` is never called by the Redis-polling implementation | Blocker | Assertion will fail if test does not hang first |
| `app/api/routes/chat.py` | 102-112 | `stream_job` in-progress path polls with `asyncio.sleep(1)` without a timeout — a job that never completes will stream `{"status":"thinking"}` forever | Warning | Potential resource leak for abandoned jobs; acceptable for personal tool |
| `docker-compose.yml` | 4-6 | Redis 7-alpine does NOT publish host port 6379 — local dev without docker compose cannot reach Redis at `localhost:6379` | Info | Developer must use `docker compose up` or manually expose port; documented in comment |

---

## SSE Implementation Divergence Note

The prompt notes: "The SSE notification mechanism was fixed during execution — the original asyncio.Queue approach (cross-process incompatible) was replaced with Redis polling in `app/api/routes/chat.py`."

This is confirmed in the code. The `stream_job` implementation on the main branch:
- Does NOT call `register_sse` or `unregister_sse`
- Polls `job_store.get(job_id)` every 1 second
- Yields `{"status": "thinking"}` while pending, `{"status": "done"}` when complete
- Checks `request.is_disconnected()` to exit if client disconnects

However, `tests/test_sse.py::test_sse_done_signal` was written for the asyncio.Queue approach and was NOT updated to match the Redis-polling implementation. The test mocks `register_sse` to return a queue, puts a done event on the queue, and asserts `unregister_sse` was called — none of which match the actual code path.

The `test_sse_already_done` test is correctly aligned (it tests the pre-check path which is unchanged) and passes.

---

## Human Verification Required

### 1. End-to-End Async Chat Flow

**Test:** Start Redis (`docker compose up redis`), start FastAPI (`uv run uvicorn app.api.main:app --reload`), start arq worker (`uv run arq app.jobs.worker.WorkerSettings`), open browser at `http://localhost:8000`, send a chat message.
**Expected:** Message appears immediately with typing indicator, AI reply arrives after worker processes it. Network tab shows SSE stream opening and closing with `{"status":"done"}` event.
**Why human:** Requires running Redis + worker + FastAPI simultaneously. Cannot simulate cross-process communication in unit tests.

### 2. SSE Disconnect + Polling Fallback

**Test:** During an active chat message (typing indicator visible), close the SSE connection (disable network in DevTools), observe behavior.
**Expected:** After SSE disconnect, `startPolling()` activates and polls `/api/job/{id}` every 2 seconds until result arrives.
**Why human:** Cannot simulate SSE disconnect + polling race in an automated test without a live browser.

### 3. Multi-Turn Conversation Continuity

**Test:** Send two sequential messages in the same thread.
**Expected:** Second AI reply references context from first exchange (LangGraph thread_id preserved through arq enqueue).
**Why human:** Requires live Copilot API call and cross-process SQLite checkpointer state.

---

## Gaps Summary

One automated test gap blocks a clean test suite: `test_sse_done_signal` in `tests/test_sse.py` was written for the asyncio.Queue-based SSE approach but the implementation was correctly migrated to Redis polling. The test mocks `register_sse` (never called in Redis-polling path) and the mock `job_store.get()` returns `None` indefinitely, causing an infinite loop. The fix is to update the test to use `side_effect` on `mock_job_store.get` to return `None` once then return `{"status": "done", "result": "..."}`, and remove the `register_sse`/`unregister_sse` assertions.

The implementation of the async architecture is complete and correct. All business-logic requirements (ASYNC-01 through ASYNC-07) are satisfied by the codebase. The gap is purely in test alignment with the implementation change.

---

_Verified: 2026-04-01T08:35:58Z_
_Verifier: Claude (gsd-verifier)_
