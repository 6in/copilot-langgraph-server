---
phase: 13-scalable-routing
plan: 01
subsystem: api
tags: [langgraph, routing, agents, subagent, registry, frontmatter]

# Dependency graph
requires:
  - phase: 12-hybrid-subagentregistry-tool-quality
    provides: SubAgentRegistry with HEALTHY/DEGRADED/FAILED status tracking and folder-type agent loading
provides:
  - SubAgent.keywords attribute loaded from AGENT.md frontmatter (prerequisite for Plan 13-02 keyword-stage routing)
  - ROUTING-01 warning in SubAgentRegistry for agents missing 対象外 exclusion section
  - Updated AGENT.md files for all three production agents with keywords frontmatter
  - general-assistant AGENT.md with 対象外 exclusion line
affects: [13-scalable-routing, agent-routing]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "AGENT.md keywords: list[str] frontmatter — agents declare their keyword triggers for two-stage routing"
    - "ROUTING-01 warning pattern — SubAgentRegistry validates description quality at load time, warns on missing 対象外"

key-files:
  created: []
  modified:
    - app/orchestrator/agent.py
    - agents/general-assistant/AGENT.md
    - agents/code-reviewer/AGENT.md
    - agents/sql-analyst/AGENT.md
    - tests/test_hybrid_registry.py

key-decisions:
  - "keywords: list[str] defaults to [] (not None) — backward compatible with code-type agents that don't pass it"
  - "general-assistant uses keywords: [] (empty) — catch-all agent should never be matched by keyword stage"
  - "ROUTING-01 warning fires at registry load time (not per-request) — one-time quality gate, not runtime overhead"

patterns-established:
  - "Pattern: AGENT.md description must include 対象外: line — enforced by ROUTING-01 warning at startup"
  - "Pattern: AGENT.md keywords list declares keyword triggers for two-stage routing pre-filter"

requirements-completed: [ROUTING-01, ROUTING-02]

# Metrics
duration: 8min
completed: 2026-04-05
---

# Phase 13 Plan 01: Scalable Routing Foundation Summary

**SubAgent.keywords attribute loaded from AGENT.md frontmatter and ROUTING-01 warning for missing 対象外 exclusion, enabling two-stage keyword routing in Plan 13-02**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-05T16:27:00Z
- **Completed:** 2026-04-05T16:36:16Z
- **Tasks:** 2 (TDD: RED + GREEN)
- **Files modified:** 5

## Accomplishments

- SubAgent gains `keywords: list[str]` attribute populated from AGENT.md `keywords:` frontmatter field, defaulting to `[]`
- SubAgentRegistry emits WARNING at load time when any successfully loaded agent's description lacks `対象外` exclusion section (ROUTING-01)
- All three production AGENT.md files updated: code-reviewer and sql-analyst get keywords lists; general-assistant gets both keywords and 対象外 line
- Test suite extended from 7 to 11 tests with 4 new tests covering ROUTING-01 warning and keywords loading

## Task Commits

Each task was committed atomically:

1. **Task 1: Add ROUTING-01 warning tests and keywords loading tests (RED)** - `d290d60` (test)
2. **Task 2: Implement SubAgent.keywords + ROUTING-01 warning + update AGENT.md files (GREEN)** - `b10f81b` (feat)

**Plan metadata:** (docs commit follows)

_Note: Task 1 is TDD RED (failing tests), Task 2 is TDD GREEN (implementation making tests pass)_

## Files Created/Modified

- `app/orchestrator/agent.py` - SubAgent.__init__ gains `keywords` param; from_dir reads frontmatter keywords; SubAgentRegistry emits ROUTING-01 WARNING
- `agents/general-assistant/AGENT.md` - Added `keywords: []` frontmatter and `対象外:` exclusion line to description
- `agents/code-reviewer/AGENT.md` - Added `keywords:` frontmatter list (コードレビュー, リント, フォーマット, 静的解析, Python, JavaScript, TypeScript)
- `agents/sql-analyst/AGENT.md` - Added `keywords:` frontmatter list (SQL, クエリ, パフォーマンス, インデックス, 実行計画, テーブル定義)
- `tests/test_hybrid_registry.py` - Updated `_write_agent_md` helper; added 4 new test functions

## Decisions Made

- `keywords` defaults to `None` in `__init__` signature but stores as `[]` — backward compatible with code-type agents that don't pass it
- `general-assistant` uses `keywords: []` (empty list) — it is a catch-all agent, should never match in keyword pre-filter stage
- ROUTING-01 warning fires at registry load time rather than per-request — quality gate at startup, not runtime overhead

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Pre-existing: `arq` module not installed in dev test environment, causing `tests/test_api_*` collection errors. This is an environment limitation pre-existing before this plan. Tests relevant to changes (`test_hybrid_registry.py`, `test_rpc_context.py`, `test_agent_state.py`, `test_orchestrator_graph.py`) all pass.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `SubAgent.keywords` is the prerequisite for Plan 13-02's keyword-stage routing (fast pre-filter before LLM routing)
- ROUTING-01 warning will fire at runtime for any agent added without `対象外` in description
- Plan 13-02 can now implement `KeywordRouter` using `agent.keywords` to route messages before LLM call

---
*Phase: 13-scalable-routing*
*Completed: 2026-04-05*
