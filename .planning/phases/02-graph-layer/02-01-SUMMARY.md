---
phase: 02-graph-layer
plan: 01
subsystem: api
tags: [langgraph, langgraph-checkpoint-sqlite, aiosqlite, messagesstate, stategraph, tdd]

# Dependency graph
requires:
  - phase: 01-auth-provider-foundation
    provides: ChatCopilot (BaseChatModel), CopilotAuthManager — used as llm parameter type in build_graph
provides:
  - build_graph() factory: compiles StateGraph(MessagesState) with chatbot node
  - app/graph/builder.py: thread-safe conversation graph with documented tools extension point
  - app/graph/__init__.py: clean package re-export of build_graph
affects: [03-web-ui, future-tool-calling-phase]

# Tech tracking
tech-stack:
  added:
    - langgraph==1.1.4
    - langgraph-checkpoint-sqlite==3.0.3
    - aiosqlite==0.22.1
  patterns:
    - "StateGraph(MessagesState) with add_messages reducer for automatic history accumulation"
    - "compile(checkpointer=checkpointer) for thread-scoped conversation isolation"
    - "TDD RED-GREEN cycle: stub raises NotImplementedError, tests fail, then implementation makes green"

key-files:
  created:
    - app/graph/__init__.py
    - app/graph/builder.py
    - tests/test_graph.py
  modified:
    - pyproject.toml
    - uv.lock

key-decisions:
  - "MemorySaver used in tests, AsyncSqliteSaver reserved for production — checkpointer ownership stays with caller"
  - "chatbot_node defined as inner async function to close over llm parameter cleanly"
  - "Extension point documented in docstring (ToolNode + tools_condition) instead of dead code"

patterns-established:
  - "Pattern 1: build_graph(llm, checkpointer) factory — compile once at startup, reuse across requests"
  - "Pattern 2: config={'configurable': {'thread_id': '<id>'}} for per-thread message history scoping"
  - "Pattern 3: async chatbot_node(state: MessagesState) -> dict returns {messages: [response]} for add_messages reducer"

requirements-completed: [GRPH-01, GRPH-02, GRPH-03]

# Metrics
duration: 7min
completed: 2026-03-31
---

# Phase 2 Plan 01: Graph Layer — build_graph() Summary

**StateGraph(MessagesState) conversation graph with chatbot node, thread-based history isolation via MemorySaver/AsyncSqliteSaver checkpointer, and ToolNode extension point documented for v2 tool-calling**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-31T12:58:54Z
- **Completed:** 2026-03-31T13:00:43Z
- **Tasks:** 2 (RED stub + GREEN implementation)
- **Files modified:** 5

## Accomplishments

- LangGraph 1.1.4 installed with SQLite checkpoint support (langgraph-checkpoint-sqlite 3.0.3)
- `build_graph(llm, checkpointer)` factory compiles `StateGraph(MessagesState)` with `START->chatbot->END` topology
- Multi-turn message accumulation via `add_messages` reducer (GRPH-01), thread isolation via `thread_id` config (GRPH-02)
- ToolNode/tools_condition extension point documented in docstring for future v2 tool-calling (GRPH-03)
- 4 new tests, 22/22 total test suite passes (no regressions on Phase 1 auth+provider tests)

## Task Commits

Each task was committed atomically:

1. **Task 1: Install LangGraph dependencies and create graph module skeleton** - `c0f6c1c` (test)
2. **Task 2: Implement build_graph() to make all tests GREEN** - `f6076b3` (feat)

_Note: TDD tasks have two commits (test RED stub → feat GREEN implementation)_

## Files Created/Modified

- `app/graph/__init__.py` — Package init re-exporting `build_graph`
- `app/graph/builder.py` — `build_graph()` factory with `StateGraph(MessagesState)` + chatbot node + extension point docs
- `tests/test_graph.py` — 4 tests: `test_messages_accumulate`, `test_thread_isolation`, `test_extension_point`, `test_single_message_response`
- `pyproject.toml` — Added langgraph, langgraph-checkpoint-sqlite, aiosqlite dependencies
- `uv.lock` — Updated lockfile

## Decisions Made

- MemorySaver used in tests, AsyncSqliteSaver reserved for production — the checkpointer lifecycle is owned by the caller (FastAPI startup/shutdown), not by `build_graph()` itself
- `chatbot_node` is an inner async function so it closes over `llm` parameter — avoids global state
- Extension point documented in docstring (not as dead code or commented-out stubs)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `build_graph()` is ready to be wired into FastAPI routes with `AsyncSqliteSaver` as the production checkpointer
- The compiled graph accepts `await graph.ainvoke({"messages": [...]}, config={"configurable": {"thread_id": "<id>"}})` — exact contract FastAPI endpoint will use
- No blockers; Phase 3 (Web UI) can proceed

---
*Phase: 02-graph-layer*
*Completed: 2026-03-31*
