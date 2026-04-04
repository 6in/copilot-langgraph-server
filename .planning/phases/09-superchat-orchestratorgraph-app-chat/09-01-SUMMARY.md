---
phase: "09"
plan: "01"
subsystem: orchestrator
tags: [orchestrator, subagent, langgraph, multi-agent, github_token]
dependency_graph:
  requires: []
  provides: [app.orchestrator, agents/, menus/]
  affects: [app/jobs/worker.py]
tech_stack:
  added: [python-frontmatter>=1.1.0, pyyaml>=6.0.3]
  patterns: [github_token threading, SubAgent lifecycle management, close() pattern]
key_files:
  created:
    - app/orchestrator/__init__.py
    - app/orchestrator/state.py
    - app/orchestrator/agent.py
    - app/orchestrator/graph.py
    - app/orchestrator/dispatcher.py
    - agents/code-reviewer/AGENT.md
    - agents/code-reviewer/rules.md
    - agents/sql-analyst/AGENT.md
    - menus/super-chat.yaml
    - menus/simple-chat.yaml
  modified:
    - pyproject.toml
    - uv.lock
decisions:
  - "github_token threaded through all orchestrator classes — required for multi-user auth isolation"
  - "build_simple_graph() dropped from graph.py — main app uses app/graph/builder.py"
  - "SubAgent.close() + SubAgentRegistry.close() added for SDK subprocess cleanup"
  - "Empty-registry warning logs but does not raise — caller (OrchestratorHandler) decides error handling"
metrics:
  duration: "2min"
  completed: "2026-04-03"
  tasks: 3
  files: 12
---

# Phase 09 Plan 01: Create app/orchestrator/ Module and Repo-Root agents/menus Summary

Migrated OrchestratorGraph prototype into `app/orchestrator/` with `github_token` threading for multi-user auth isolation, and copied `agents/` and `menus/` sample directories to repo root.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Add python-frontmatter and pyyaml dependencies | afee71f | pyproject.toml, uv.lock |
| 2 | Create app/orchestrator/ module with github_token threading | 6a53ffe | 5 new files |
| 3 | Copy agents/ and menus/ to repo root | 6ba9570 | 5 new files |

## Decisions Made

- **github_token threading:** `SubAgent.__init__`, `SubAgent.from_dir`, `SubAgentRegistry.__init__`, `RouterNode.__init__`, and `build_orchestrator_graph` all accept `github_token: str`. This ensures each request uses the authenticated user's token, not a shared on-disk token from `CopilotAuthManager`.
- **build_simple_graph() dropped:** The prototype's `build_simple_graph()` function was not migrated — the main app uses `app/graph/builder.py:build_graph()` for simple chat mode.
- **SubAgent.close() + SubAgentRegistry.close():** Added async cleanup methods so `OrchestratorHandler` (Plan 02) can call `await registry.close()` in a `finally` block, preventing Copilot SDK subprocess leaks.
- **Empty-registry warning:** `SubAgentRegistry.__init__` prints a warning when no agents are found, but does not raise — the calling handler decides whether to error.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All orchestrator classes are fully implemented with proper github_token threading.

## Verification

All completion criteria verified:
- `python-frontmatter` and `pyyaml` are in `pyproject.toml` and importable
- `app/orchestrator/` module exists with all 5 files
- All orchestrator imports resolve without errors
- `SubAgent`, `SubAgentRegistry`, `RouterNode`, `build_orchestrator_graph` all accept `github_token`
- `SubAgent.close()` calls `await self._llm.close()`
- `SubAgentRegistry.close()` closes all agents
- `build_simple_graph` is NOT present in `app/orchestrator/graph.py`
- `agents/` and `menus/` directories exist at repo root with sample content
- `super-agent-sample/` directory is preserved (not deleted)

## Self-Check: PASSED

Files verified present:
- app/orchestrator/__init__.py: FOUND
- app/orchestrator/state.py: FOUND
- app/orchestrator/agent.py: FOUND
- app/orchestrator/graph.py: FOUND
- app/orchestrator/dispatcher.py: FOUND
- agents/code-reviewer/AGENT.md: FOUND
- agents/sql-analyst/AGENT.md: FOUND
- menus/super-chat.yaml: FOUND
- menus/simple-chat.yaml: FOUND

Commits verified:
- afee71f: FOUND
- 6a53ffe: FOUND
- 6ba9570: FOUND
