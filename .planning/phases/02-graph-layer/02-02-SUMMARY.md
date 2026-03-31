---
phase: 02-graph-layer
plan: 02
subsystem: api
tags: [langgraph, integration-test, e2e, multi-turn, thread-isolation, validate]

# Dependency graph
requires:
  - phase: 02-graph-layer
    plan: 01
    provides: build_graph(llm, checkpointer) factory — used as the graph under test
  - phase: 01-auth-provider-foundation
    provides: ChatCopilot, CopilotAuthManager — used as live LLM + auth for E2E
provides:
  - scripts/validate_graph.py: runnable integration validation script for GRPH-01 + GRPH-02
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "MemorySaver as checkpointer for single-run validation scripts (no persistence needed)"
    - "uuid.uuid4() for unique thread_id generation per test run"

key-files:
  created:
    - scripts/validate_graph.py
  modified: []

key-decisions:
  - "MemorySaver sufficient for single-run validation — no SQLite needed since history need not survive process restart"
  - "Soft assertion on 'Alice' in reply (WARN not FAIL) — LLM responses are non-deterministic; hard assert on message count instead"

# Metrics
duration: 1min
completed: 2026-03-31
---

# Phase 2 Plan 02: Graph Integration Validation Script Summary

**E2E validation script that exercises full graph pipeline (auth -> ChatCopilot -> StateGraph) against live Copilot, testing multi-turn context retention (GRPH-01) and thread isolation (GRPH-02) with MemorySaver checkpointer**

## Performance

- **Duration:** ~1 min
- **Started:** 2026-03-31T13:04:46Z
- **Completed:** 2026-03-31T13:05:47Z
- **Tasks:** 1 completed (Task 2 at checkpoint — awaiting human verification)
- **Files modified:** 1

## Accomplishments

- Created `scripts/validate_graph.py` (99 lines) following Phase 1 `chat_test.py` E2E pattern
- Script validates GRPH-01 (multi-turn: sends "My name is Alice" then "What is my name?" on same thread, asserts 4 messages accumulated)
- Script validates GRPH-02 (thread isolation: sends "What is my name?" on fresh thread, asserts only 2 messages, no Alice context)
- Syntax verified clean (`ast.parse` exits 0)
- All 9 acceptance criteria verified passing

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create graph integration validation script | `69799fb` | scripts/validate_graph.py |

## Files Created/Modified

- `scripts/validate_graph.py` — Integration validation: full graph pipeline E2E against live Copilot

## Decisions Made

- MemorySaver used (not AsyncSqliteSaver) — single-run validation does not need cross-restart persistence
- Soft WARN (not hard FAIL) on "alice" text check — LLM output is non-deterministic; message count assertions are the hard invariants
- Hard assert on message count (`== 4` for thread A, `== 2` for thread B) — these are structural graph properties, not LLM output

## Deviations from Plan

None - plan executed exactly as written.

## Status

**STOPPED AT CHECKPOINT: human-verify (Task 2)**

Task 2 requires human to run `uv run python scripts/validate_graph.py` and confirm live Copilot output shows correct multi-turn context and thread isolation.

## User Setup Required

Run validation script to confirm graph works end-to-end with live Copilot:

```bash
uv run python scripts/validate_graph.py
```

Expected output:
- "PASS: Thread A has 4 messages (multi-turn history works)"
- "PASS: Thread B has 2 messages (isolated from A)"
- "PASS: Thread B does not know 'Alice' (thread isolation works)"
- "=== All graph validations passed ==="

## Self-Check: PASSED

- `scripts/validate_graph.py` exists: FOUND
- Commit `69799fb` exists: FOUND
