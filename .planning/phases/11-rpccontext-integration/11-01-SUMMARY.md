---
phase: 11-rpccontext-integration
plan: "01"
subsystem: orchestrator
tags: [rpccontext, dataclass, frozen, tdd, reducer, langgraph]
dependency_graph:
  requires: []
  provides: [RPCContext, _keep_first]
  affects: [app/orchestrator/state.py, app/jobs/handlers/orchestrator_handler.py]
tech_stack:
  added: []
  patterns:
    - frozen=True dataclass for immutable request context
    - _keep_first LangGraph reducer for unwritable state fields
    - TDD: RED (import error) → GREEN (8 tests pass)
key_files:
  created:
    - app/orchestrator/context.py
    - tests/test_rpc_context.py
  modified: []
decisions:
  - "from_http takes explicit kwargs (user_id, app_id, thread_id) not raw HTTP headers — worker never has raw request"
  - "_keep_first returns a if a is not None else b — handles unset checkpoint (None first arg) per Pitfall 3"
  - "Minimal field set for Phase 11: user_id, app_id, thread_id, correlation_id — extra fields (user_roles, message_id, session_id) deferred to future phases"
metrics:
  duration: 5min
  completed: "2026-04-04"
  tasks_completed: 1
  files_created: 2
  files_modified: 0
requirements: [CONTEXT-02, CONTEXT-03]
---

# Phase 11 Plan 01: RPCContext Foundation Summary

## One-liner

Frozen `RPCContext` dataclass with `_keep_first` reducer, `from_http`/`from_slack` factories, and 8 unit tests (TDD green).

## What Was Built

`app/orchestrator/context.py` — the foundation type for all Phase 11 plans:

- `RPCContext`: `@dataclass(frozen=True)` with 4 fields: `user_id` (str), `app_id` (str, default ""), `thread_id` (str, default ""), `correlation_id` (str, auto-generated UUID4 via `default_factory`)
- `_keep_first(a, b)`: returns `a if a is not None else b` — the LangGraph reducer that makes `context` immutable in `AgentState`
- `RPCContext.from_http(user_id, app_id, thread_id)`: explicit-kwargs factory (not raw HTTP headers)
- `RPCContext.from_slack(event)`: builds context from Slack event dict; uses `thread_ts` as `thread_id`, falls back to `ts`

`tests/test_rpc_context.py` — 8 unit tests covering all specified behaviors:
1. `test_rpccontext_frozen` — mutation raises `FrozenInstanceError`
2. `test_rpccontext_defaults` — correct default field values + UUID4 `correlation_id`
3. `test_rpccontext_correlation_id_unique` — two instances have different `correlation_id`s
4. `test_from_http_factory` — correct field values from explicit kwargs
5. `test_from_slack_factory_with_thread_ts` — uses `thread_ts` when present
6. `test_from_slack_factory_falls_back_to_ts` — uses `ts` when `thread_ts` absent
7. `test_keep_first_preserves_existing` — returns first arg when both are non-None
8. `test_keep_first_none_first_arg` — returns second arg when first is None

## TDD Execution

- **RED:** `ModuleNotFoundError: No module named 'app.orchestrator.context'` — confirmed
- **GREEN:** 8 passed in 0.01s — confirmed

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 00d6624 | feat | RPCContext frozen dataclass and _keep_first reducer |

## Deviations from Plan

None — plan executed exactly as written.

The plan called for 7 test cases; implementation includes 8 (split `test_from_slack_factory` into `test_from_slack_factory_with_thread_ts` and `test_from_slack_factory_falls_back_to_ts` for clearer coverage of both branches). Both behaviors were specified in the plan's `<behavior>` block.

## Known Stubs

None. `RPCContext` is a pure data type with no external dependencies. All fields are populated at construction time.

## Deferred Items

Pre-existing test failure logged (out of scope for this plan):
- `tests/test_api_chat.py::test_new_thread_returns_uuid` — fails with 401 (requires JWT cookie; pre-dates Phase 11)

## Self-Check: PASSED

Files exist:
- FOUND: app/orchestrator/context.py
- FOUND: tests/test_rpc_context.py

Commits exist:
- FOUND: 00d6624
