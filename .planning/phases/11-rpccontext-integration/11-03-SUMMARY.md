---
phase: 11-rpccontext-integration
plan: "03"
subsystem: orchestrator
tags: [logging, json, correlation-id, rpccontext, tdd, structured-logging]

dependency_graph:
  requires:
    - phase: 11-01
      provides: RPCContext dataclass with correlation_id field
  provides:
    - RouterNode structured JSON logging with correlation_id
    - logger.info() routing log entry (event, input, chosen, candidates, thread_id, correlation_id)
    - Graceful handling of legacy threads without context
  affects:
    - app/orchestrator/graph.py
    - tests/test_orchestrator_graph.py

tech-stack:
  added: []
  patterns:
    - "json.dumps() inside logger.info() for structured log emission"
    - "state.get('context') with fallback empty strings for legacy thread safety"
    - "TDD: RED (caplog assertion fails on print) -> GREEN (logger.info passes)"

key-files:
  created:
    - tests/test_orchestrator_graph.py
  modified:
    - app/orchestrator/graph.py

key-decisions:
  - "logger.warning() for routing_fallback (unknown LLM response) separate from logger.info() routing event"
  - "state.get('context') not state['context'] — dict.get returns None for missing key, no KeyError for legacy threads"
  - "json.dumps() payload inside logger.info() not as extra kwarg — keeps log format portable and parseable by structured log aggregators"

patterns-established:
  - "Structured logging pattern: logger.info(json.dumps({event: ..., correlation_id: ...})) in all orchestrator nodes"

requirements-completed: [CONTEXT-04]

duration: 1min
completed: "2026-04-04"
---

# Phase 11 Plan 03: RouterNode Structured Correlation-ID Logging Summary

**RouterNode print() replaced with logger.info(json.dumps({...})) including correlation_id, enabling end-to-end request tracing via RPCContext**

## Performance

- **Duration:** 1 min
- **Started:** 2026-04-04T05:59:23Z
- **Completed:** 2026-04-04T06:01:00Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 2

## Accomplishments

- Replaced two `print()` calls in `RouterNode.__call__` with structured JSON logging via `logger.info()` and `logger.warning()`
- Log entry includes: `event`, `input` (truncated to 80 chars), `chosen`, `candidates`, `thread_id`, `correlation_id`
- Legacy threads (no `context` in state dict) handled gracefully — empty strings used for `thread_id` and `correlation_id`
- Two unit tests added covering both the happy path (context present) and legacy path (context absent)

## Task Commits

1. **RED: test_orchestrator_graph.py** - `3741710` (test)
2. **GREEN: graph.py structured logging** - `d05a029` (feat)

## Files Created/Modified

- `tests/test_orchestrator_graph.py` — Two async tests: `test_router_log_contains_correlation_id` and `test_router_log_handles_missing_context`
- `app/orchestrator/graph.py` — Added `import json, logging`, `logger = logging.getLogger(__name__)`, replaced `print()` with structured `logger.info()`/`logger.warning()` calls

## Decisions Made

- `logger.warning()` for routing_fallback (unknown LLM response) separate from `logger.info()` routing event — warning signals unexpected LLM output
- `state.get("context")` not `state["context"]` — gracefully returns None for legacy threads, no KeyError
- `json.dumps()` payload inside `logger.info()` keeps format portable and parseable by log aggregators without requiring special log handler configuration

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - the TDD cycle was clean: RED immediately showed print() output in stdout (not caplog), GREEN succeeded after logger conversion.

## Known Stubs

None. RouterNode now emits structured JSON log entries unconditionally on every routing decision.

## Next Phase Readiness

- CONTEXT-04 complete: RouterNode emits structured log with correlation_id
- Plan 11-04 (RPCContext injection in arq worker / OrchestratorHandler) can proceed independently

## Self-Check: PASSED

Files exist:
- FOUND: tests/test_orchestrator_graph.py
- FOUND: app/orchestrator/graph.py

Commits exist:
- FOUND: 3741710
- FOUND: d05a029

---
*Phase: 11-rpccontext-integration*
*Completed: 2026-04-04*
