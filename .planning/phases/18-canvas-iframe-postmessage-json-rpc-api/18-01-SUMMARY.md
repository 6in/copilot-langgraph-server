---
phase: 18-canvas-iframe-postmessage-json-rpc-api
plan: "01"
subsystem: backend
tags: [iframe-rpc, canvas, arq, worker, psycopg, security]
dependency_graph:
  requires:
    - app/jobs/handlers/base.py
    - app/jobs/notifier.py
    - app/jobs/job_store.py
    - app/providers/copilot.py
    - app/api/routes/chat.py (get_jwt_payload, get_github_token)
    - app/api/main.py
  provides:
    - IframeRpcHandler (app/jobs/handlers/iframe_rpc_handler.py)
    - is_select_only (app/jobs/handlers/iframe_rpc_handler.py)
    - POST /api/iframe-rpc (app/api/routes/iframe_rpc.py)
  affects:
    - app/api/main.py (router registration)
    - app/jobs/worker.py (Plan 02 will add iframe_app_api to TASK_HANDLERS)
tech_stack:
  added: []
  patterns:
    - TaskHandler subclass pattern (same as LangGraphHandler)
    - arq enqueue_job → job_id → SSE poll pattern
    - psycopg dict_row for DB query results
    - SQL comment stripping + prefix token validation for SELECT-only guard
key_files:
  created:
    - app/jobs/handlers/iframe_rpc_handler.py
    - app/api/routes/iframe_rpc.py
    - tests/test_iframe_rpc_handler.py
    - tests/test_iframe_rpc_route.py
  modified:
    - app/api/main.py
decisions:
  - is_select_only uses regex comment stripping + semicolon-split detection — no external sqlparse dependency needed
  - pool_name validated against ctx["db_pools"] dict keys — unknown pools return error without DB access
  - _handle_ai uses direct ChatCopilot instantiation (no LangGraph graph) — one-shot per D-14
  - llm.close() in finally block — guarantees subprocess cleanup on success and exception
  - thread_id and prompt passed as empty strings in enqueue — IframeRpcHandler ignores them
metrics:
  duration: 15min
  completed: 2026-04-08
  tasks_completed: 2
  files_created: 4
  files_modified: 1
---

# Phase 18 Plan 01: IframeRpcHandler + POST /api/iframe-rpc Summary

**One-liner:** SELECT-only DB query + ChatCopilot one-shot handler with JWT-protected arq enqueue endpoint for Canvas iframe JSON-RPC bridge.

## What Was Built

### Task 1: IframeRpcHandler + is_select_only (TDD)

`app/jobs/handlers/iframe_rpc_handler.py` implements:

- **`is_select_only(sql)`** — strips SQL block/line comments via regex, rejects multi-statement input (`;` after stripping trailing semicolon), verifies first token is `SELECT` or `WITH`. Covers T-18-01 SQL injection defense.
- **`IframeRpcHandler.handle()`** — dispatches on `rpc_method`: `QUERY` → `_handle_query`, `AI` → `_handle_ai`, unknown → error result. Saves JSON result to `job_store` and calls `notifier.done()` in both success and exception paths.
- **`_handle_query()`** — validates `pool_name` against `ctx["db_pools"]` (T-18-02), calls `is_select_only` guard, executes via `psycopg dict_row` cursor. Returns `{"result": true, "rows": [...]}`.
- **`_handle_ai()`** — instantiates `ChatCopilot` with `github_token` from job payload, invokes `[HumanMessage(prompt)]`, returns `{"result": true, "responseText": "..."}`. `llm.close()` called in `finally`.

19 pytest tests cover all behavior cases.

### Task 2: POST /api/iframe-rpc + router registration

`app/api/routes/iframe_rpc.py` implements:

- `IframeRpcRequest` — `{id: str, method: str, params: dict | None}`
- `IframeRpcResponse` — `{job_id: str}`
- `POST /api/iframe-rpc` — JWT-authenticated via `Depends(get_github_token)`. Enqueues `process_chat` arq job with `task_type="iframe_app_api"`, `rpc_method`, `rpc_params`. Returns `job_id` for SSE/polling.

`app/api/main.py` updated: `iframe_rpc` added to imports and `app.include_router(iframe_rpc.router)` added after `canvas.router`.

6 route tests cover: 200 + job_id, enqueue args verification, 401 without JWT, null params → empty dict, unique job_id per call.

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None. `IframeRpcHandler` is fully wired but requires Plan 02 to register `iframe_app_api` in `TASK_HANDLERS` dict in `app/jobs/worker.py` before it can be dispatched by the arq worker.

## Threat Surface Scan

No new threat surfaces beyond what the plan's threat model already documents (T-18-01 through T-18-05).

- `POST /api/iframe-rpc` is protected by existing JWT auth chain — same as all other authenticated endpoints.
- `is_select_only` provides SQL injection defense at the handler layer.
- `pool_name` is whitelist-validated against known pools.

## Self-Check: PASSED

| Item | Result |
|------|--------|
| app/jobs/handlers/iframe_rpc_handler.py | FOUND |
| app/api/routes/iframe_rpc.py | FOUND |
| tests/test_iframe_rpc_handler.py | FOUND |
| tests/test_iframe_rpc_route.py | FOUND |
| commit faa5b1a (IframeRpcHandler impl) | FOUND |
| commit b573ff4 (iframe-rpc route) | FOUND |
| 25 tests pass | PASSED |
