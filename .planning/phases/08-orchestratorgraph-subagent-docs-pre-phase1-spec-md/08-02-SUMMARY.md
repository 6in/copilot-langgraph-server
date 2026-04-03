---
phase: 08-orchestratorgraph-subagent-docs-pre-phase1-spec-md
plan: "02"
subsystem: sample
tags: [langgraph, langchain-anthropic, python-frontmatter, pytest, unittest.mock, super-agent]

# Dependency graph
requires:
  - 08-01 (AgentState, AGENT.md files, menu YAMLs, pyproject.toml, uv sync)
provides:
  - SubAgent and SubAgentRegistry (src/agent.py)
  - RouterNode, build_orchestrator_graph, build_simple_graph, fallback_node (src/graph.py)
  - MenuRegistry and MenuDispatcher (src/dispatcher.py)
  - Full unit test suite (14 tests, mocked LLM, no live API calls)
affects: [08-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - MagicMock name attribute pitfall: use agent.name = n, not MagicMock(name=n)
    - patch("module.ClassName") for unit-test isolation of LLM calls
    - Wave 0 stub pattern: @pytest.mark.skip stubs before production code, then flesh out

key-files:
  created:
    - super-agent-sample/src/agent.py
    - super-agent-sample/src/graph.py
    - super-agent-sample/src/dispatcher.py
    - super-agent-sample/tests/conftest.py
    - super-agent-sample/tests/test_state.py
    - super-agent-sample/tests/test_registry.py
    - super-agent-sample/tests/test_router.py
    - super-agent-sample/tests/test_dispatcher.py
  modified: []

key-decisions:
  - "-> Any (from typing) not -> any: spec has Python typing error; corrected in graph.py"
  - "MagicMock name pitfall: MagicMock(name=x) sets mock repr, not .name attribute; use agent = MagicMock(); agent.name = x"
  - "patch('agent.ChatAnthropic') for registry tests, patch('graph.ChatAnthropic') for router tests — module-level patching"

patterns-established:
  - "Pattern: Wave 0 stubs with @pytest.mark.skip allow TDD red-green cycle without blocking state tests"
  - "Pattern: make_mock_agent() helper assigns attributes directly to avoid MagicMock(name=...) confusion"

requirements-completed: [SAMPLE-03, SAMPLE-04, SAMPLE-05, SAMPLE-10]

# Metrics
duration: 2min
completed: 2026-04-03
---

# Phase 08 Plan 02: Core Modules + Unit Tests Summary

**SubAgent/SubAgentRegistry (agent.py), RouterNode/OrchestratorGraph (graph.py), and MenuDispatcher (dispatcher.py) implemented verbatim from spec with -> Any fix; 14 unit tests pass using mocked LLM, no live API calls**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-03T13:40:10Z
- **Completed:** 2026-04-03T13:42:35Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments

- Wave 0 test stubs created (conftest.py + 4 test files) — state tests green, 12 stubs skipped
- agent.py: SubAgent.from_dir() using python-frontmatter, SubAgentRegistry glob-scans agents/ directory
- graph.py: RouterNode with LLM-based routing, build_orchestrator_graph with conditional edges, build_simple_graph
- dispatcher.py: MenuRegistry YAML loader, MenuDispatcher.dispatch() routes by mode name
- All test stubs fleshed out: 5 registry tests, 3 router tests, 4 dispatcher tests, 2 state tests
- 14/14 tests pass; no test touches ChatAnthropic without mocking

## Task Commits

Each task was committed atomically:

1. **Task 1: Wave 0 test stubs + state tests** - `c797419` (test)
2. **Task 2: agent.py, graph.py, dispatcher.py + full tests** - `fd40f09` (feat)

## Files Created/Modified

- `super-agent-sample/src/agent.py` - SubAgent (from_dir, run) + SubAgentRegistry (glob scan, get, all)
- `super-agent-sample/src/graph.py` - RouterNode, fallback_node, build_orchestrator_graph, build_simple_graph; uses `-> Any` (typing) not `-> any`
- `super-agent-sample/src/dispatcher.py` - MenuRegistry (YAML glob load, get_graph) + MenuDispatcher (dispatch by mode)
- `super-agent-sample/tests/conftest.py` - tmp_agents_dir + tmp_menus_dir fixtures
- `super-agent-sample/tests/test_state.py` - 2 real tests for AgentState TypedDict
- `super-agent-sample/tests/test_registry.py` - 5 full tests (SubAgent.from_dir, default model, system prompt, registry scan, get by name)
- `super-agent-sample/tests/test_router.py` - 3 full tests (selects agent, fallback on unknown, strips whitespace)
- `super-agent-sample/tests/test_dispatcher.py` - 4 full tests (menu load, get_graph, correct dispatch, routing by mode)

## Decisions Made

- `-> Any` (from `typing`) used instead of `-> any` (spec typo): Python `any` is a builtin, not a type hint
- `patch("agent.ChatAnthropic")` and `patch("graph.ChatAnthropic")` used at the module level for proper mock isolation
- `make_mock_agent(name)` helper created: `MagicMock(name=x)` in Python's unittest.mock sets the mock's repr/name, not a `.name` attribute

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed MagicMock name attribute pitfall in test_router.py**
- **Found during:** Task 2 — test_router_selects_code_reviewer failed: result["next"] was "fallback" instead of "code-reviewer"
- **Issue:** `MagicMock(name="code-reviewer")` sets the mock's internal `_mock_name` (used for repr), not the `.name` attribute. `a.name` returned a child MagicMock, so `valid = {a.name for a in agents}` was a set of mock objects, not strings. "code-reviewer" (a string) was not in the set, so router fell back.
- **Fix:** Extracted `make_mock_agent(name)` helper that creates `agent = MagicMock(); agent.name = name` — assigns name as a real string attribute
- **Files modified:** `super-agent-sample/tests/test_router.py`
- **Commit:** `fd40f09`

## Known Stubs

None — all tests are fully implemented. No placeholder data.

## Self-Check: PASSED

All created files verified to exist on disk. All task commits (c797419, fd40f09) verified in git log.
