---
phase: 04-sse-redis-worker-jobstore-notifier
plan: 04
subsystem: frontend
tags: [vanilla-js, sse, polling, async, frontend, eventsource]
dependency_graph:
  requires: ["04-02", "04-03"]
  provides: []
  affects: ["static/app.js"]
tech_stack:
  added: ["EventSource (browser SSE API)"]
  patterns: ["SSE + polling fallback", "immediate-done check on reconnect", "async job flow: POST → job_id → SSE → fetch result"]
key_files:
  created: []
  modified: ["static/app.js"]
decisions:
  - "sendMessage() no longer blocks on POST — returns job_id immediately, SSE delivers done signal, result fetched from GET /api/job/{id}"
  - "finally block removed: input re-enable moved to each completion path (SSE onmessage, startPolling, error handlers)"
  - "startPolling() uses 2-second interval, clears on done, re-enables input itself"
  - "immediate-done check after POST handles page-reload/reconnect scenario (ASYNC-06)"
metrics:
  duration: "1min"
  completed: "2026-04-01T07:50:28Z"
  tasks_completed: 1
  files_changed: 1
---

# Phase 4 Plan 04: Frontend Async Chat Flow Summary

**One-liner:** Replaced synchronous sendMessage() with EventSource SSE + polling fallback flow — POST /api/chat gets job_id immediately, browser subscribes to SSE stream, result fetched from /api/job/{id} on done signal.

## What Was Built

Updated `static/app.js` `sendMessage()` function to use the full async job pattern:

1. POST `/api/chat` returns `{job_id, thread_id}` immediately (non-blocking)
2. Immediate-done check via `GET /api/job/{job_id}` — handles reload/reconnect case (ASYNC-06)
3. `EventSource` opened on `/api/chat/{job_id}/stream` for real-time done signal
4. On `status === "done"` SSE event: fetch result from `GET /api/job/{job_id}`, render AI reply
5. `es.onerror` handler: close EventSource, start `startPolling()` as fallback
6. New `startPolling(jobId)` function: polls every 2 seconds, clears interval on done, re-enables input

Input enable/disable logic restructured:
- Disabled in try block (before POST) — unchanged
- No blanket `finally` re-enable — removed
- Re-enabled in: 401 path, non-OK path, immediate-done path, SSE onmessage done path, `startPolling` done path, catch error path

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Refactor sendMessage() to use async job flow with SSE + polling | 0b3e06c | static/app.js |

## Decisions Made

1. **No finally re-enable:** The old `finally` block guaranteed unlock on any path, but with async SSE/polling the UI must stay locked until the worker responds. Each terminal path (success, error, fallback) manages its own re-enable.
2. **thread_id from POST response:** The new `ChatAsyncResponse` returns `{job_id, thread_id}`. Destructure both — update `activeThreadId` if server assigned one (preserves existing thread-creation behaviour).
3. **startPolling() gets DOM refs inline:** `document.getElementById('user-input')` called inside the function rather than closed over outer scope — safe for single-message-at-a-time personal tool.
4. **401 and non-OK error paths re-enable input:** Previously handled by `finally`; moved explicitly into each branch so they are correct after `finally` removal.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — `sendMessage()` fully wired to async job API. All SSE and polling paths are implemented.

## Self-Check: PASSED
