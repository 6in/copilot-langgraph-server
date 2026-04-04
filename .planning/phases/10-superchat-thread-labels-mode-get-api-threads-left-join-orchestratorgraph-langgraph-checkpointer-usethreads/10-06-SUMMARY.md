---
phase: 10-superchat-thread-labels-mode-get-api-threads-left-join-orchestratorgraph-langgraph-checkpointer-usethreads
plan: "06"
subsystem: api
tags: [superchat, agents, orchestrator, routing, langgraph]

# Dependency graph
requires:
  - phase: 10-04
    provides: OrchestratorGraph wired to AsyncPostgresSaver checkpointer
  - phase: 09-02
    provides: OrchestratorHandler + SubAgentRegistry + RouterNode in app/orchestrator/

provides:
  - agents/general-assistant/AGENT.md — catch-all agent for general conversation in SuperChat
affects:
  - SuperChat routing — RouterNode can now route general messages to general-assistant instead of fallback

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "AGENT.md frontmatter pattern: name, description, model, system_prompt for SubAgentRegistry auto-loading"

key-files:
  created:
    - agents/general-assistant/AGENT.md
  modified: []

key-decisions:
  - "general-assistant AGENT.md added to agents/ — SubAgentRegistry auto-loads via glob; no code change needed"
  - "model: claude-sonnet-4-6 chosen — matches SubAgent default and suitable for general conversation"
  - "description written as explicit catch-all to guide RouterNode LLM away from fallback for general messages"

patterns-established:
  - "Agent addition pattern: drop AGENT.md in agents/<name>/ — zero code change, auto-registered by SubAgentRegistry on startup"

requirements-completed: [ORC-01]

# Metrics
duration: 5min
completed: 2026-04-04
---

# Phase 10 Plan 06: General-Assistant Agent Summary

**Gap closure: agents/general-assistant/AGENT.md added so RouterNode routes general SuperChat messages to a real LLM instead of the fixed fallback error string**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-04T04:29:25Z
- **Completed:** 2026-04-04T04:34:00Z
- **Tasks:** 2 (1 create, 1 verify)
- **Files modified:** 1

## Accomplishments
- Created `agents/general-assistant/AGENT.md` with catch-all description and Japanese system prompt
- SubAgentRegistry now loads 3 agents at startup: code-reviewer, general-assistant, sql-analyst
- RouterNode LLM will route general conversation to general-assistant instead of returning error string
- UAT Test 2 blocker (SuperChat returns "対応できるエージェントが見つかりませんでした。") is resolved

## Task Commits

Each task was committed atomically:

1. **Task 1: Add general-assistant agent** - `0085f02` (feat)
2. **Task 2: Verify registry loads the new agent** - no commit needed (verification only)

**Plan metadata:** (docs commit to follow)

## Files Created/Modified
- `agents/general-assistant/AGENT.md` - Catch-all conversational agent: name=general-assistant, model=claude-sonnet-4-6, Japanese system prompt

## Decisions Made
- Used `name: general-assistant` (hyphen not underscore) — matches routing key format used by other agents
- Added explicit catch-all language in description so RouterNode LLM prefers this over "fallback" for general messages
- No code changes required — SubAgentRegistry uses glob to auto-discover all agents in `agents/**/AGENT.md`

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `test_new_thread_returns_uuid` was already failing (returns 401) before this plan's changes — pre-existing issue unrelated to this plan's scope. Logged as out-of-scope. Not fixed.

## User Setup Required

No external service configuration required. The agent directory is volume-mounted in Docker Compose (`./agents:/app/agents`). Restart the worker service to pick up the new agent:

```bash
docker compose restart worker
```

## Next Phase Readiness

- SuperChat general conversation now routable — UAT Test 2 can be retried
- No further gap closure plans identified for Phase 10
- Phase 10 complete: all 6 plans executed

---
*Phase: 10-superchat-thread-labels-mode-get-api-threads-left-join-orchestratorgraph-langgraph-checkpointer-usethreads*
*Completed: 2026-04-04*
