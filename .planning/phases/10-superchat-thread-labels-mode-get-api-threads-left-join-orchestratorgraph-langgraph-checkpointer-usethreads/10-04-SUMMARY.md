---
phase: 10-superchat-thread-labels-mode-get-api-threads-left-join-orchestratorgraph-langgraph-checkpointer-usethreads
plan: "04"
subsystem: orchestrator
tags: [checkpointer, langgraph, superchat, persistence, postgres]
dependency_graph:
  requires: ["10-02"]
  provides: ["OrchestratorGraph with checkpointer", "SuperChat conversation persistence"]
  affects: ["app/orchestrator/graph.py", "app/jobs/handlers/orchestrator_handler.py"]
tech_stack:
  added: []
  patterns: ["AsyncPostgresSaver context manager", "thread_id config for LangGraph checkpointer"]
key_files:
  created: []
  modified:
    - app/orchestrator/graph.py
    - app/jobs/handlers/orchestrator_handler.py
decisions:
  - "checkpointer=None default keeps build_orchestrator_graph backward-compatible"
  - "Omit messages from initial AgentState each turn — checkpointer accumulates via operator.add reducer"
  - "await checkpointer.setup() called each job to ensure schema exists (idempotent)"
metrics:
  duration: "54s"
  completed_date: "2026-04-04"
  tasks_completed: 2
  files_modified: 2
---

# Phase 10 Plan 04: OrchestratorGraph LangGraph Checkpointer Summary

**One-liner:** Wired AsyncPostgresSaver into OrchestratorGraph so SuperChat conversations persist across turns via thread_id-scoped checkpointer, mirroring the proven LangGraphHandler pattern.

## What Was Built

Connected `build_orchestrator_graph` and `OrchestratorHandler` to the LangGraph PostgreSQL checkpointer so SuperChat messages accumulate conversation history across turns, instead of starting fresh each time.

**Before:** `graph.compile()` — no checkpointer, stateless.
**After:** `graph.compile(checkpointer=checkpointer)` with `AsyncPostgresSaver` opened per job and `thread_id` passed in `config`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add checkpointer param to build_orchestrator_graph | 10e4615 | app/orchestrator/graph.py |
| 2 | Wire AsyncPostgresSaver into OrchestratorHandler | 42bf237 | app/jobs/handlers/orchestrator_handler.py |

## Decisions Made

- **checkpointer=None default:** Backward-compatible — existing callers not passing checkpointer get `None` (same as before; `graph.compile(checkpointer=None)` is equivalent to no checkpointer).
- **Omit `"messages": []` from initial state:** AgentState uses `Annotated[list[BaseMessage], operator.add]` reducer. The checkpointer is the single source of truth for accumulated messages across turns; passing an empty list is unnecessary and confusing.
- **`await checkpointer.setup()` per job:** Idempotent call ensures PostgreSQL schema (`checkpoints`, `checkpoint_writes` tables) exists before first use. Safe to call on every job.
- **Pattern mirrors LangGraphHandler exactly:** Same `AsyncPostgresSaver.from_conn_string(DB_URI)` context manager, same `config = {"configurable": {"thread_id": thread_id}}` pattern.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all wiring complete. SuperChat conversations will persist across turns once PostgreSQL is running.

## Self-Check: PASSED

- [x] app/orchestrator/graph.py modified — `checkpointer` in signature and compile call
- [x] app/jobs/handlers/orchestrator_handler.py modified — AsyncPostgresSaver import, DB_URI, thread_id extraction, context manager
- [x] Commits exist: 10e4615 (Task 1), 42bf237 (Task 2)
