---
phase: 08-orchestratorgraph-subagent-docs-pre-phase1-spec-md
plan: "03"
subsystem: agent
tags: [langgraph, orchestrator, sub-agent, dispatcher, routing, smoke-test]

# Dependency graph
requires:
  - phase: 08-02
    provides: agent.py (SubAgentRegistry), graph.py (build_orchestrator_graph, build_simple_graph), dispatcher.py (MenuDispatcher, MenuRegistry)
provides:
  - CLI entry point (super-agent-sample/src/main.py) with 4 demo cases
  - End-to-end smoke test confirming routing, sub-agent execution, fallback, and simple-chat modes
affects: [future-phase1, docs]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "main() as top-level CLI runner: create registry, compile graphs, dispatch 4 cases sequentially"
    - "PYTHONPATH=src uv run python src/main.py: run from project root with src on path"

key-files:
  created:
    - super-agent-sample/src/main.py
  modified: []

key-decisions:
  - "main.py written verbatim from spec section 9 — no modifications needed"
  - "Smoke test verified manually by human across all 4 routing paths"

patterns-established:
  - "Run command: cd super-agent-sample && PYTHONPATH=src uv run python src/main.py (relative paths require this cwd)"

requirements-completed: [SAMPLE-08, SAMPLE-09]

# Metrics
duration: 18min
completed: 2026-04-03
---

# Phase 08 Plan 03: main.py CLI entry point + end-to-end smoke test verified

**Working main.py entry point added verbatim from spec section 9; human-verified smoke test confirms OrchestratorGraph routes code-reviewer, sql-analyst, and fallback correctly while simple-chat bypasses the router**

## Performance

- **Duration:** ~18 min (including human verification)
- **Started:** 2026-04-03T13:45:00Z
- **Completed:** 2026-04-03T15:03:38Z
- **Tasks:** 2 (1 auto + 1 human-verify checkpoint)
- **Files modified:** 1

## Accomplishments
- Implemented `super-agent-sample/src/main.py` exactly as written in `docs/pre/phase1_spec.md` section 9
- Human verified all 4 demo cases with live Copilot SDK calls:
  - **simple-chat**: LLM responded directly, no `[router]` log line
  - **super-chat → code-reviewer**: `[router]` log appeared, code review output with severity levels
  - **super-chat → sql-analyst**: `[router]` log appeared, SQL optimization output
  - **super-chat → fallback**: `[router]` log appeared, `対応できるエージェントが見つかりませんでした。` returned
- End-to-end orchestrator pipeline (SubAgentRegistry → OrchestratorGraph → MenuDispatcher) confirmed working

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement main.py entry point from spec** - `8ab6edc` (feat)
2. **Task 2: Live smoke test — verify all 4 cases** - Human verified (no code changes)

**Plan metadata:** (this commit) (docs: complete plan)

## Files Created/Modified
- `super-agent-sample/src/main.py` — CLI entry point: creates SubAgentRegistry, compiles orchestrator + simple graphs, dispatches 4 demo cases via MenuDispatcher

## Decisions Made
- main.py written verbatim from spec — no modifications necessary; spec was already implementation-ready
- Smoke test verified by human rather than automated CI: live Copilot SDK calls require auth credentials, unsuitable for headless automation

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required beyond the Copilot auth already set up in prior phases.

## Next Phase Readiness
- super-agent-sample is complete: all 3 plans (08-01, 08-02, 08-03) shipped
- The full OrchestratorGraph + SubAgent + MenuDispatcher pipeline is verified end-to-end
- Ready for Phase 1 implementation (docs/pre/phase1_spec.md is now validated against a working sample)

---
*Phase: 08-orchestratorgraph-subagent-docs-pre-phase1-spec-md*
*Completed: 2026-04-03*
