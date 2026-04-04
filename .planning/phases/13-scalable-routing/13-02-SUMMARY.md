---
phase: 13-scalable-routing
plan: 02
subsystem: api
tags: [langgraph, routing, agents, keyword-routing, 2-stage, structured-logging]

# Dependency graph
requires:
  - phase: 13-scalable-routing
    plan: 01
    provides: SubAgent.keywords attribute from AGENT.md frontmatter
provides:
  - RouterNode with 2-stage routing (keyword pre-filter + LLM fallback)
  - stage field in all routing log entries ('keyword' or 'llm')
  - 6 new tests covering keyword routing behavior and stage logging
affects: [13-scalable-routing, agent-routing, orchestrator-graph]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "2-stage RouterNode: keyword pre-filter (Stage 1) then LLM fallback (Stage 2)"
    - "getattr(a, 'keywords', []) safe access pattern for mixed code/folder agent compatibility"
    - "Case-insensitive keyword matching via .lower() on both input and keywords"
    - "stage field in structured JSON routing log — enables routing analysis (D-04, ROUTING-03)"

key-files:
  created:
    - tests/test_routing_keyword.py
  modified:
    - app/orchestrator/graph.py
    - tests/test_orchestrator_graph.py

key-decisions:
  - "getattr(a, 'keywords', []) instead of a.keywords — safe for code-type agents that may lack keywords attribute"
  - "context = state.get('context') moved to top of __call__ — both stages need it, avoids duplication"
  - "Stage 1 only routes on exactly 1 keyword match — 0 or multiple falls through to LLM for unambiguous routing"
  - "Case-insensitive matching via .lower() on both input and keywords — handles English/mixed-case keywords"

patterns-established:
  - "Pattern: 2-stage routing — keyword pre-filter provides O(n*k) cheap routing, LLM handles ambiguous cases"
  - "Pattern: stage field in all routing log entries enables post-hoc analysis of keyword vs LLM routing ratio"

requirements-completed: [ROUTING-02, ROUTING-03]

# Metrics
duration: 3min
completed: 2026-04-05
---

# Phase 13 Plan 02: 2-Stage RouterNode Summary

**RouterNode upgraded to 2-stage routing: keyword pre-filter skips LLM for unambiguous single-keyword matches, with stage field in all routing log entries for analysis**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-05T16:38:44Z
- **Completed:** 2026-04-05T16:42:xx Z
- **Tasks:** 2 (TDD RED + GREEN implementation)
- **Files modified:** 3

## Accomplishments

- RouterNode gains Stage 1 keyword pre-filter: scans all agent keywords for a unique match, routes immediately without LLM invocation if exactly 1 agent matches
- Stage 2 (existing LLM routing) unchanged — triggers when 0 or multiple keyword matches exist
- All routing log entries now contain `"stage"` field with value `"keyword"` (Stage 1) or `"llm"` (Stage 2)
- Case-insensitive keyword matching (`"Python"` keyword matches `"python code review"` input)
- Safe `getattr(a, "keywords", [])` access ensures code-type agents without keywords attribute don't crash
- 6 new tests in `test_routing_keyword.py` covering all keyword routing scenarios
- 2 existing tests in `test_orchestrator_graph.py` updated with stage field assertions

## Task Commits

Each task was committed atomically:

1. **Task 1: Create test_routing_keyword.py + update test_orchestrator_graph.py (TDD RED)** - `c41a4e1` (test)
2. **Task 2: Implement 2-stage RouterNode with keyword pre-filter and stage log field (GREEN)** - `f553e23` (feat)

## Files Created/Modified

- `app/orchestrator/graph.py` - RouterNode.__call__ gains Stage 1 keyword pre-filter; both stages log `"stage"` field; `context = state.get("context")` moved to top
- `tests/test_routing_keyword.py` - 6 new tests covering: single keyword match skips LLM, no match uses LLM, multi-match uses LLM, case-insensitive matching, stage='keyword' in log, stage='llm' in log
- `tests/test_orchestrator_graph.py` - Added `routing_log["stage"] == "llm"` assertion to both existing routing tests

## Decisions Made

- `getattr(a, "keywords", [])` not `a.keywords` — defensive access for code-type agents that may not expose keywords attribute (Risk 1 from RESEARCH.md)
- `context = state.get("context")` moved from Stage 2 to top of method — both stages need it for log fields; avoids code duplication
- Stage 1 requires exactly 1 keyword match — 0 matches (no agent covers this) or 2+ matches (ambiguous) both fall through to LLM for proper disambiguation

## Deviations from Plan

**[Rule 3 - Blocking] Updated github-copilot-sdk from 0.1.19 to 0.2.0**
- **Found during:** Task 1 (TDD RED) — tests/test_orchestrator_graph.py failed to collect due to `ImportError: cannot import name 'SubprocessConfig'` from copilot module
- **Issue:** Dev environment had SDK 0.1.19 which doesn't export `SubprocessConfig`; `app/providers/copilot.py` imports it at module level
- **Fix:** `pip install github-copilot-sdk==0.2.0` — the version already pinned in pyproject.toml
- **Files modified:** None (package install only)
- **Impact:** Allowed test collection and execution; pre-existing environment issue

**[Rule - Environment] Worktree rebased onto phase-13 branch**
- **Found during:** Plan start — worktree was on an older branch without Plan 13-01's SubAgent.keywords changes
- **Fix:** `git rebase gsd/phase-13-scalable-routing` to get Plan 13-01 commits
- **Impact:** Enabled correct test behavior with keywords attribute available

## Test Results

All 8 routing tests pass:
- `tests/test_routing_keyword.py` — 6 tests
- `tests/test_orchestrator_graph.py` — 2 tests

Pre-existing environment failures (not caused by this plan):
- `test_rpc_integration.py::test_orchestrator_handler_injects_context` — langgraph.checkpoint.postgres not installed in dev env
- `test_graph.py::test_messages_accumulate` — pre-existing assertion failure
- JWT auth test errors — ModuleNotFoundError: arq not installed in dev env

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 2-stage routing is complete: keyword pre-filter + LLM fallback with stage logging
- `stage` field in logs enables routing analysis (e.g., what % of requests route via keyword vs LLM)
- Phase 13 is now complete (plans 13-01 and 13-02 both done)

## Self-Check: PASSED

- `app/orchestrator/graph.py` exists: FOUND
- `tests/test_routing_keyword.py` exists: FOUND  
- `tests/test_orchestrator_graph.py` updated: FOUND
- Task commits: c41a4e1 and f553e23 — FOUND
- All 8 tests pass: VERIFIED

---
*Phase: 13-scalable-routing*
*Completed: 2026-04-05*
