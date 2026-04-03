---
phase: "09"
plan: "02"
subsystem: orchestrator-handler
tags: [orchestrator, worker, task-handler, mode-routing, docker]
dependency_graph:
  requires: [app.orchestrator, agents/, menus/]
  provides: [app.jobs.handlers.orchestrator_handler, mode-routing]
  affects: [app/jobs/worker.py, app/api/models.py, app/api/routes/chat.py, docker-compose.yml]
tech_stack:
  added: []
  patterns: [task_type routing via TASK_HANDLERS dict, mode-to-task_type translation, per-job registry construction]
key_files:
  created:
    - app/jobs/handlers/orchestrator_handler.py
  modified:
    - app/jobs/handlers/__init__.py
    - app/jobs/worker.py
    - app/api/models.py
    - app/api/routes/chat.py
    - docker-compose.yml
decisions:
  - "OrchestratorHandler builds SubAgentRegistry per job for multi-user token isolation — no app.state sharing"
  - "mode='super' overrides task_type to 'orchestrator' — mode takes priority over task_type field"
  - "AGENT_DIR and MENU_DIR added to both api and worker services in docker-compose.yml"
metrics:
  duration: "3min"
  completed: "2026-04-03"
  tasks: 4
  files: 6
---

# Phase 09 Plan 02: OrchestratorHandler + API mode routing + Docker env Summary

Created `OrchestratorHandler(TaskHandler)` for `task_type="orchestrator"` with per-job registry construction, added `mode: Literal["simple","super"]` to `ChatRequest` with `"super"` translating to `"orchestrator"` task_type in the chat route, and added `AGENT_DIR`/`MENU_DIR` env vars to both Docker services.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Create OrchestratorHandler task handler | 0d95dd6 | app/jobs/handlers/orchestrator_handler.py |
| 2 | Register OrchestratorHandler in worker and update exports | e2f0caf | app/jobs/handlers/__init__.py, app/jobs/worker.py |
| 3 | Add mode field to ChatRequest and wire routing in chat route | dd31006 | app/api/models.py, app/api/routes/chat.py |
| 4 | Add AGENT_DIR and MENU_DIR env vars to docker-compose.yml | d88dfcf | docker-compose.yml |

## Decisions Made

- **Per-job OrchestratorGraph construction:** `OrchestratorHandler.handle()` creates a new `SubAgentRegistry` and graph per job. This avoids the `app.state` sharing problem (arq worker is a separate process) and ensures each user gets their own `github_token`-scoped `ChatCopilot` instances.
- **mode priority over task_type:** When `mode='super'`, `task_type` is overridden to `'orchestrator'` regardless of what was set. When `mode='simple'`, `task_type` is used as-is. This maintains backward compatibility with clients that set `task_type` directly.
- **AGENT_DIR and MENU_DIR in Docker:** Both `api` and `worker` services get the env vars pointing to `/app/agents` and `/app/menus`, which are covered by the existing `.:/app` volume mount.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. All implementations are fully wired.

## Verification

All completion criteria verified:
- `OrchestratorHandler` exists in `app/jobs/handlers/orchestrator_handler.py` and imports cleanly (Docker verified)
- `OrchestratorHandler.handle()` calls `await registry.close()` in a `finally` block
- `TASK_HANDLERS` in `worker.py` includes `"orchestrator": OrchestratorHandler()` (Docker verified)
- `ChatRequest` has `mode: Literal["simple", "super"] = "simple"` field (Docker verified)
- `send_message` route translates `mode='super'` to `task_type='orchestrator'` before enqueuing
- `docker-compose.yml` has `AGENT_DIR` and `MENU_DIR` in both `api` and `worker` services (grep verified)
- Existing `mode='simple'` (default) behavior is completely unchanged

## Self-Check: PASSED

Files verified present:
- app/jobs/handlers/orchestrator_handler.py: FOUND
- app/jobs/handlers/__init__.py: FOUND (modified)
- app/jobs/worker.py: FOUND (modified)
- app/api/models.py: FOUND (modified)
- app/api/routes/chat.py: FOUND (modified)
- docker-compose.yml: FOUND (modified)

Commits verified:
- 0d95dd6: Task 1 — OrchestratorHandler created
- e2f0caf: Task 2 — worker registration and exports
- dd31006: Task 3 — mode field and routing
- d88dfcf: Task 4 — docker-compose env vars
