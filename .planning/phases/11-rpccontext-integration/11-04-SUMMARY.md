---
phase: 11-rpccontext-integration
plan: "04"
subsystem: orchestrator-pipeline
tags: [rpccontext, correlation-id, github-login, arq-worker, integration-test]
dependency_graph:
  requires: ["11-02", "11-03"]
  provides: ["CONTEXT-01", "CONTEXT-04"]
  affects: [app/api/routes/chat.py, app/jobs/worker.py, app/jobs/handlers/orchestrator_handler.py]
tech_stack:
  added: []
  patterns: [RPCContext.from_http, initial-state-injection, correlation-id-tracing]
key_files:
  created: [tests/test_rpc_integration.py]
  modified:
    - app/api/routes/chat.py
    - app/jobs/worker.py
    - app/jobs/handlers/orchestrator_handler.py
decisions:
  - "github_login extracted before enqueue_job in chat.py — ensures user_id is always included in arq job payload at request intake time"
  - "OrchestratorHandler constructs RPCContext after agent registry validation — RPCContext only created for valid jobs with at least one agent"
  - "error: None always included in initial AgentState — AgentState has no NotRequired annotation, all fields required"
metrics:
  duration: 8min
  completed_date: "2026-04-04"
  tasks_completed: 2
  files_changed: 4
---

# Phase 11 Plan 04: github_login-to-RPCContext Pipeline Wiring Summary

RPCContext injection into initial AgentState with github_login flowing from POST /api/chat through arq job payload to OrchestratorHandler, where correlation_id is generated and threads through RouterNode log entries.

## What Was Built

### Task 1: github_login pipeline wiring (3 files)

**app/api/routes/chat.py** — Moved `github_login = payload.get("github_login", "unknown")` and `app_id` extraction to BEFORE `arq_redis.enqueue_job()`. Added `github_login=github_login` to the enqueue kwargs. Previously, github_login was extracted after enqueue (cosmetic only) and was not passed to the worker.

**app/jobs/worker.py** — Added `github_login: str = "unknown"` parameter to `process_chat()` function signature. Added `"github_login": github_login` to the `job` dict forwarded to handler.handle(). Default value preserves backward compatibility with any legacy callers.

**app/jobs/handlers/orchestrator_handler.py** — Three changes:
- Added `from app.orchestrator.context import RPCContext` import
- Added `github_login: str = job.get("github_login", "unknown")` extraction
- Constructed `RPCContext.from_http(user_id=github_login, app_id="superchat", thread_id=thread_id)`
- Updated initial AgentState to include `"context": context` and `"error": None`

### Task 2: Integration tests (tests/test_rpc_integration.py)

**test_orchestrator_handler_injects_context** — Mocks SubAgentRegistry, AsyncPostgresSaver, and build_orchestrator_graph. Calls OrchestratorHandler.handle() with a job dict containing `github_login="test-user"`. Captures the initial dict passed to graph.ainvoke and asserts it contains an RPCContext with correct user_id, app_id, thread_id, and error=None.

**test_correlation_id_in_routing_log** — Constructs a known RPCContext with fixed correlation_id. Creates a RouterNode with mocked LLM. Calls node(state) with the context-bearing state. Captures log output and asserts the routing JSON log entry contains the same correlation_id.

## Key Links Completed

```
POST /api/chat
  → github_login extracted from JWT payload
  → passed as github_login= to arq.enqueue_job()
  → process_chat(github_login=...) receives it
  → job dict includes "github_login": github_login
  → OrchestratorHandler.handle(ctx, job) extracts job.get("github_login")
  → RPCContext.from_http(user_id=github_login, app_id="superchat", thread_id=...)
  → initial: AgentState = {..., "context": context, "error": None}
  → graph.ainvoke(initial, config=...)
  → RouterNode logs: {"event": "routing", "correlation_id": context.correlation_id, ...}
```

## Decisions Made

- github_login extraction moved before enqueue_job — ensures user_id is in the arq job payload at request intake for complete correlation chain
- RPCContext constructed after agent registry validation in OrchestratorHandler — only create context for jobs that will actually run
- error: None always in initial state — AgentState has no NotRequired annotation, all fields required at every turn
- app_id hardcoded to "superchat" in OrchestratorHandler — OrchestratorHandler is only used for SuperChat mode; chat mode uses LangGraphHandler

## Test Results

All 14 Phase 11 tests pass:
- tests/test_rpc_context.py: 8 passed
- tests/test_agent_state.py: 2 passed
- tests/test_orchestrator_graph.py: 2 passed
- tests/test_rpc_integration.py: 2 passed

Pre-existing failures (out of scope, not caused by this plan):
- tests/test_api_chat.py::test_new_thread_returns_uuid — 401 (JWT auth expectation mismatch in test)
- tests/test_worker.py (3 tests) — patch target app.jobs.worker.ChatCopilot doesn't exist (stale test from old architecture)
- tests/test_graph.py::test_messages_accumulate — pre-existing

## Deviations from Plan

None — plan executed exactly as written.

The plan noted that github_login was "currently on line 99" after enqueue_job. In the actual file it was already on the correct line but was not passed to enqueue_job. The fix was straightforward: move extraction before the call and add it as a kwarg.

## Known Stubs

None.

## Self-Check: PASSED
