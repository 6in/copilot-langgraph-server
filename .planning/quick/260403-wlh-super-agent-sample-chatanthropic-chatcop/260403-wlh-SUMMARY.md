---
phase: quick
plan: 260403-wlh
subsystem: super-agent-sample
tags: [provider-swap, async-migration, chatcopilot]
dependency_graph:
  requires: []
  provides: [super-agent-sample ChatCopilot provider]
  affects: [super-agent-sample/src, super-agent-sample/tests]
tech_stack:
  added: [github-copilot-sdk==0.2.0, pydantic>=2.0, cryptography>=41.0, pytest-asyncio>=0.23]
  patterns: [async/await throughout call chain, ChatCopilot mock at class level in tests]
key_files:
  created:
    - super-agent-sample/src/copilot.py
  modified:
    - super-agent-sample/src/agent.py
    - super-agent-sample/src/graph.py
    - super-agent-sample/src/dispatcher.py
    - super-agent-sample/src/main.py
    - super-agent-sample/pyproject.toml
    - super-agent-sample/tests/test_registry.py
    - super-agent-sample/tests/test_router.py
    - super-agent-sample/tests/test_dispatcher.py
decisions:
  - ChatCopilot SDK imports deferred to _ensure_client() to avoid circular import: copilot.py IS the copilot module when src/ is on sys.path
  - asyncio_mode=auto in pytest config eliminates need for @pytest.mark.asyncio decorator
  - RouterNode.__call__ made async; graph nodes wrapped in async def for ainvoke compatibility
  - test_registry: ANY used for github_token assertion since it reads env var at runtime
metrics:
  duration: 4min
  completed_date: "2026-04-03"
  tasks_completed: 2
  files_changed: 8
---

# Quick 260403-wlh: Replace ChatAnthropic with ChatCopilot in super-agent-sample

**One-liner:** Replaced ChatAnthropic with standalone ChatCopilot wrapper and migrated entire call chain (agent → graph → dispatcher → main) to async/await using ainvoke().

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Copy ChatCopilot provider and update dependencies | 96854cd | copilot.py (new), pyproject.toml |
| 2 | Convert sync to async and replace ChatAnthropic with ChatCopilot | 9e7933b | agent.py, graph.py, dispatcher.py, main.py, 3 test files, pyproject.toml |

## Outcome

- `super-agent-sample/src/copilot.py` created as standalone ChatCopilot provider copy
- All `ChatAnthropic` / `langchain_anthropic` references removed from src/ and tests/
- Entire call chain is async: `asyncio.run(main())` → `dispatcher.dispatch()` → `graph.ainvoke()` → node async functions → `ChatCopilot.ainvoke()`
- `pyproject.toml`: `github-copilot-sdk==0.2.0` replaces `langchain-anthropic`; `pytest-asyncio>=0.23` added
- All 14 tests pass (4 dispatcher, 5 registry, 3 router, 2 state)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Deferred SDK imports in copilot.py to avoid circular import**
- **Found during:** Task 1
- **Issue:** `src/copilot.py` is itself the `copilot` module when `src/` is on `sys.path` (per `pythonpath = ["src"]` in pyproject.toml). Top-level `from copilot import CopilotClient, ...` would cause a circular import — Python finds `src/copilot.py` as the `copilot` module, tries to import from partially initialized self.
- **Fix:** Moved `CopilotClient`, `SubprocessConfig`, `PermissionHandler` imports inside `_ensure_client()` using `importlib.import_module("copilot")`. Module-level pydantic/langchain-core imports remain at top-level (no conflict).
- **Files modified:** super-agent-sample/src/copilot.py
- **Commit:** 96854cd

**2. [Rule 2 - Missing functionality] Added asyncio_mode=auto to pytest config**
- **Found during:** Task 2
- **Issue:** `@pytest.mark.asyncio` requires `asyncio_mode = "auto"` or explicit decorator recognition; without it, async test functions would silently pass without being awaited in some pytest-asyncio versions.
- **Fix:** Added `asyncio_mode = "auto"` to `[tool.pytest.ini_options]` in pyproject.toml. This also allowed removing explicit `@pytest.mark.asyncio` decorators (though they were kept for clarity).
- **Files modified:** super-agent-sample/pyproject.toml
- **Commit:** 9e7933b

## Known Stubs

None — all ChatCopilot wiring is complete. Tests mock at class level (patch `agent.ChatCopilot`, `graph.ChatCopilot`) so no real SDK calls are made during testing.

## Self-Check: PASSED
