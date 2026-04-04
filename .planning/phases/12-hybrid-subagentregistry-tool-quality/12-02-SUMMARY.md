---
phase: 12-hybrid-subagentregistry-tool-quality
plan: "02"
subsystem: api
tags: [health-endpoint, agent-registry, fastapi, tdd, no-auth]
dependency_graph:
  requires:
    - AgentStatusEnum (from 12-01)
    - AgentHealth dataclass (from 12-01)
    - list_health() method on SubAgentRegistry (from 12-01)
  provides:
    - GET /health/agents endpoint (no JWT required)
    - AgentHealthEntry Pydantic model
    - _check_agent_importable() metadata-only import check
    - app.state.agent_health populated at startup
  affects:
    - app/api/models.py
    - app/api/routes/health.py (new)
    - app/api/main.py
    - app/orchestrator/agent.py
    - tests/test_health_route.py (new)
tech_stack:
  added: []
  patterns:
    - Health endpoint uses Request.app.state (not Depends) for state access
    - No JWT auth on /health/* routes (operational endpoints)
    - Startup metadata scan via glob("*/AGENT.md") -- no ChatCopilot instantiation
    - _check_agent_importable uses f"agent_{name}" module naming (avoids import cache collisions)
    - TDD: RED commit before GREEN implementation
key_files:
  created:
    - app/api/routes/health.py
    - tests/test_health_route.py
  modified:
    - app/api/models.py
    - app/api/main.py
    - app/orchestrator/agent.py
decisions:
  - "health router uses prefix=/health not /api -- operational endpoints are not application API"
  - "_check_agent_importable uses same f'agent_{name}' module naming as _load_code_agent to prevent import cache collisions"
  - "app.state.agent_health populated before yield -- available before first request"
  - "glob '*/AGENT.md' (flat, one level) consistent with Plan 01 decision"
  - "FAILED/_INIT_FAILURE_TYPES / DEGRADED classification consistent with SubAgentRegistry"
metrics:
  duration: "2min"
  completed: "2026-04-04"
  tasks_completed: 2
  files_changed: 5
---

# Phase 12 Plan 02: Health Endpoint and Startup Metadata Registry Summary

GET /health/agents endpoint returning HEALTHY/DEGRADED/FAILED status for all discovered agents, served without JWT auth, backed by a metadata-only startup scan using shared _check_agent_importable helper.

## What Was Built

1. `AgentHealthEntry` Pydantic model in `app/api/models.py` — serializes AgentHealth dataclass to JSON with name, agent_type, status (str), error (str | None)

2. `app/api/routes/health.py` — new router with `prefix="/health"`, no JWT Depends, reads `request.app.state.agent_health` set at startup

3. `_check_agent_importable(agent_dir)` in `app/orchestrator/agent.py` — module-level helper that imports agent.py and verifies SubAgent class exists, without calling from_dir() or creating ChatCopilot instances. Uses `f"agent_{agent_dir.name}"` naming (same as `_load_code_agent`) to reuse import cache entries

4. Startup metadata scan in `app/api/main.py` lifespan — globs `*/AGENT.md`, classifies each agent as HEALTHY/FAILED/DEGRADED using `_check_agent_importable` and `_INIT_FAILURE_TYPES`, stores result in `app.state.agent_health`

5. Health router registered after `agents.router` in main.py

## Tests Created

`tests/test_health_route.py` — 4 integration tests using ASGITransport (no Docker required):

| Test | Verifies |
|------|---------|
| `test_health_agents_returns_list` | 200 with JSON list of agent health entries |
| `test_health_entry_has_required_fields` | name/agent_type/status present; error=null for HEALTHY |
| `test_health_no_auth_required` | No cookie/header → still 200 |
| `test_health_failed_agent_shows_error` | FAILED agent has non-null error string |

All 4 tests pass in 0.18s with no Docker required.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Copilot SDK stub for test isolation**

- **Found during:** Task 1 (GREEN phase)
- **Issue:** `app.api.routes.health` imports from `app.orchestrator.agent`, which imports `ChatCopilot`, which imports from the `copilot` SDK. SDK not installed in test environment.
- **Fix:** Added the same `sys.modules.setdefault("copilot", _copilot_stub)` pattern from `test_hybrid_registry.py` at the top of `test_health_route.py`.
- **Files modified:** `tests/test_health_route.py`
- **Commit:** c647a32

**2. [Rule 3 - Blocking] Missing `from pathlib import Path` in main.py**

- **Found during:** Task 2 implementation
- **Issue:** Startup scan uses `Path(agent_dir_path).glob(...)` but `Path` was not imported in `app/api/main.py`.
- **Fix:** Added `from pathlib import Path` to main.py imports.
- **Files modified:** `app/api/main.py`
- **Commit:** ee7cce9

### Pre-existing Issues (Out of Scope)

Same pre-existing failures as documented in 12-01-SUMMARY.md:
- `test_graph.py::test_messages_accumulate` — assertion `len == 3` fails (4 messages)
- `test_api_*.py`, `test_jwt_auth.py` — `ModuleNotFoundError: No module named 'arq'`
- `test_worker.py`, `test_sse.py`, `test_rpc_integration.py` — `ModuleNotFoundError: No module named 'langgraph.checkpoint.postgres'`

## Known Stubs

None — all plan goals achieved. `app.state.agent_health` is wired to real startup scan. The endpoint returns live data on each request.

## Self-Check: PASSED

- `app/api/models.py` contains `class AgentHealthEntry(BaseModel)` ✓
- `app/api/routes/health.py` exists with `router = APIRouter(prefix="/health"` ✓
- `app/api/routes/health.py` contains `async def list_agent_health` ✓
- `app/api/routes/health.py` does NOT contain `Depends(get_jwt_payload)` ✓
- `app/api/routes/health.py` contains `request.app.state.agent_health` ✓
- `app/orchestrator/agent.py` contains `def _check_agent_importable` ✓
- `app/orchestrator/agent.py` `_check_agent_importable` uses `f"agent_{agent_dir.name}"` ✓
- `app/api/main.py` contains `from app.api.routes import agents, auth, chat, health, jobs, me` ✓
- `app/api/main.py` contains `app.include_router(health.router)` ✓
- `app/api/main.py` contains `app.state.agent_health = agent_health` ✓
- `app/api/main.py` contains `_check_agent_importable` call ✓
- `app/api/main.py` does NOT contain `spec_from_file_location` ✓
- `tests/test_health_route.py` has 4 tests, all passing ✓
- Commits verified:
  - `a00bdbe` — test(12-02): add failing tests for GET /health/agents endpoint
  - `c647a32` — feat(12-02): implement AgentHealthEntry model and GET /health/agents route
  - `ee7cce9` — feat(12-02): wire health route and startup metadata registry into main.py
