---
phase: 12-hybrid-subagentregistry-tool-quality
plan: "01"
subsystem: orchestrator
tags: [agent-registry, health-tracking, hybrid-loading, importlib, tdd]
dependency_graph:
  requires: []
  provides:
    - AgentStatusEnum (HEALTHY/DEGRADED/FAILED)
    - AgentHealth dataclass
    - _load_code_agent() code-type agent loader
    - SubAgentRegistry.health dict
    - SubAgentRegistry.list_health() method
  affects:
    - app/orchestrator/agent.py
    - tests/test_hybrid_registry.py
tech_stack:
  added: []
  patterns:
    - importlib.util.spec_from_file_location for dynamic module loading
    - Per-agent try/except isolation (FAILED vs DEGRADED exception classification)
    - TDD: RED tests committed before implementation
key_files:
  created:
    - tests/test_hybrid_registry.py
  modified:
    - app/orchestrator/agent.py
decisions:
  - "FAILED = ImportError/ModuleNotFoundError/SyntaxError/AttributeError (agent code is broken)"
  - "DEGRADED = ConnectionError/OSError/any other exception (external dependency unavailable)"
  - "Glob changed from **/AGENT.md to */AGENT.md (flat structure, avoid deep recursion)"
  - "list_health() added to SubAgentRegistry for future /health/agents endpoint"
  - "Copilot SDK stub via sys.modules in test file to avoid needing SDK installed in test env"
metrics:
  duration: "3min"
  completed: "2026-04-04"
  tasks_completed: 2
  files_changed: 2
---

# Phase 12 Plan 01: Hybrid SubAgentRegistry with Health Tracking Summary

Hybrid SubAgentRegistry with HEALTHY/DEGRADED/FAILED per-agent health tracking, supporting both folder-type (AGENT.md only) and code-type (agent.py + AGENT.md) agents via importlib dynamic loading.

## What Was Built

Extended `app/orchestrator/agent.py` with:

1. `AgentStatusEnum` — `str, Enum` with HEALTHY / DEGRADED / FAILED values
2. `AgentHealth` — dataclass tracking name, agent_type, status, and optional error message
3. `_load_code_agent()` — loads code-type agents via `importlib.util.spec_from_file_location`, using unique module name `f"agent_{dir_name}"` to avoid import cache collisions
4. `SubAgentRegistry.health` dict — populated with one entry per discovered agent directory
5. `SubAgentRegistry.list_health()` — returns all health entries regardless of status (for future `/health/agents` endpoint)
6. Per-agent try/except in `__init__` — FAILED for code-level errors (`_INIT_FAILURE_TYPES`), DEGRADED for external dependency errors (any other exception)

The glob was changed from `**/AGENT.md` (recursive) to `*/AGENT.md` (flat, one level) to match the documented flat agent directory structure.

## Tests Created

`tests/test_hybrid_registry.py` — 7 unit tests:

| Test | Verifies |
|------|---------|
| `test_folder_type_agent_loads` | AGENT.md-only agents load as HEALTHY with correct name/description |
| `test_code_type_takes_precedence` | agent.py takes precedence, health shows agent_type="code" |
| `test_failed_agent_isolated` | ImportError in agent.py → FAILED; other agents remain HEALTHY |
| `test_degraded_agent_isolated` | ConnectionError in agent.py → DEGRADED; excluded from registry.all() |
| `test_health_dict_populated` | 3 agents (healthy/failed/degraded) produce 3 health entries |
| `test_all_returns_only_healthy` | registry.all() excludes FAILED and DEGRADED; get() raises KeyError |
| `test_empty_dir_no_crash` | Empty directory → empty dicts, no exception |

All tests run in under 0.1s with no Docker required (pure unit tests with mocks).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Copilot SDK stub for test isolation**

- **Found during:** Task 1 (RED phase)
- **Issue:** `app.orchestrator.agent` imports `ChatCopilot` from `app.providers.copilot`, which imports from the `copilot` SDK. The SDK package is not installed in the test environment (it requires platform-specific binaries).
- **Fix:** Added `sys.modules.setdefault("copilot", _copilot_stub)` at the top of `test_hybrid_registry.py` before the import chain executes. This creates a minimal stub with the three names the SDK module exposes (`CopilotClient`, `SubprocessConfig`, `PermissionHandler`).
- **Files modified:** `tests/test_hybrid_registry.py`

**2. [Rule 3 - Blocking] python-frontmatter not installed in test environment**

- **Found during:** Task 1 (RED phase test collection)
- **Issue:** `python-frontmatter` is listed in `pyproject.toml` but was not installed in the current pyenv environment used by pytest.
- **Fix:** Ran `pip install python-frontmatter` to install it.

### Pre-existing Issues (Out of Scope, Documented)

The following test failures pre-existed and are not caused by this plan's changes (verified by running tests before changes):

- `test_graph.py::test_messages_accumulate` — assertion `len == 3` fails (4 messages accumulated); pre-existing
- `test_api_*.py`, `test_jwt_auth.py` — `ModuleNotFoundError: No module named 'arq'` — missing arq in test env
- `test_worker.py`, `test_sse.py`, `test_rpc_integration.py` (orchestrator handler) — `ModuleNotFoundError: No module named 'langgraph.checkpoint.postgres'` — missing postgres checkpoint in test env

These are tracked in deferred-items.

## Known Stubs

None — all plan goals achieved. The `list_health()` method is wired to the real health dict and returns live data. No placeholder data in the implementation.

## Self-Check: PASSED

- `app/orchestrator/agent.py` exists with `AgentStatusEnum`, `AgentHealth`, `_load_code_agent`, `self.health`, `list_health` ✓
- `tests/test_hybrid_registry.py` exists with 7 test functions ✓
- Commits verified:
  - `7e734b1` — test(12-01): add failing tests for hybrid registry with health tracking
  - `09efe7a` — feat(12-01): implement hybrid SubAgentRegistry with health tracking
