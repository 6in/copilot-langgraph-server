---
phase: 12-hybrid-subagentregistry-tool-quality
plan: 03
subsystem: api
tags: [jsonschema, tool-scripts, input-validation, ci-lint, script-backend]

# Dependency graph
requires:
  - phase: 12-hybrid-subagentregistry-tool-quality
    provides: SubAgentRegistry and orchestrator foundation

provides:
  - ScriptBackend class with jsonschema pre-call validation of tool kwargs
  - INPUT_SCHEMA convention for tool scripts (agents/*/tools/*.py)
  - Example tool lint_file.py demonstrating INPUT_SCHEMA
  - CI lint script scripts/lint_tools.py enforcing INPUT_SCHEMA presence
  - 14 unit + integration tests covering all behaviors

affects: [routing, tool-calling, agent-tools, CI]

# Tech tracking
tech-stack:
  added: [jsonschema>=4.0.0]
  patterns:
    - "Tool scripts define INPUT_SCHEMA JSON Schema constant for pre-call validation"
    - "ScriptBackend loads tool modules via importlib.util, validates kwargs, calls run()"
    - "ScriptBackend is permissive when INPUT_SCHEMA absent (backward-compatible for legacy tools)"
    - "scripts/lint_tools.py discovers agents/*/tools/[!_]*.py via glob, enforces INPUT_SCHEMA"

key-files:
  created:
    - app/orchestrator/script_backend.py
    - agents/code-reviewer/tools/lint_file.py
    - scripts/lint_tools.py
    - tests/test_script_backend.py
    - tests/test_lint_tools.py
  modified:
    - pyproject.toml

key-decisions:
  - "INPUT_SCHEMA is optional (permissive) for legacy tools without the constant — ScriptBackend skips validation rather than failing, enabling gradual adoption"
  - "jsonschema.ValidationError is caught and re-raised as ValueError with 'validation failed' message — consistent error type for callers"
  - "glob pattern [!_]*.py excludes __init__.py and _-prefixed private files from lint scan"
  - "ScriptBackend uses importlib.util.spec_from_file_location — no sys.path manipulation needed for arbitrary file paths"

patterns-established:
  - "INPUT_SCHEMA pattern: tool scripts in agents/<name>/tools/*.py define INPUT_SCHEMA dict (JSON Schema)"
  - "ScriptBackend pattern: load module -> validate -> call run(); permissive when schema absent"
  - "lint_tools.py pattern: CI script discovers all tool scripts, enforces INPUT_SCHEMA, exits non-zero on violation"

requirements-completed: [TOOL-01, TOOL-02, TOOL-03]

# Metrics
duration: 2min
completed: 2026-04-04
---

# Phase 12 Plan 03: INPUT_SCHEMA Standard and ScriptBackend Summary

**jsonschema pre-call validation for tool scripts via ScriptBackend, INPUT_SCHEMA convention established with example tool, CI lint script enforcing schema presence across all agents/*/tools/*.py**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-04T14:37:35Z
- **Completed:** 2026-04-04T14:39:55Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- ScriptBackend class loads tool scripts via importlib.util and validates kwargs against INPUT_SCHEMA using jsonschema before calling run()
- lint_file.py example tool demonstrates the INPUT_SCHEMA convention for future agent tool authors
- scripts/lint_tools.py CI script discovers all agents/*/tools/[!_]*.py and exits non-zero when any tool lacks INPUT_SCHEMA
- 14 tests covering valid/invalid/extra-field/no-schema/missing-run/integration scenarios — all pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Add jsonschema dep, create example tool, build ScriptBackend and lint script** - `fb535de` (feat)
2. **Task 2: Write tests for ScriptBackend and lint_tools** - `9bda265` (test)

**Plan metadata:** (docs commit below)

## Files Created/Modified
- `app/orchestrator/script_backend.py` - ScriptBackend class with importlib + jsonschema validation
- `agents/code-reviewer/tools/lint_file.py` - Example tool demonstrating INPUT_SCHEMA convention
- `scripts/lint_tools.py` - CI lint script: discovers and validates all agent tool scripts
- `tests/test_script_backend.py` - 8 tests for ScriptBackend (valid, invalid type, extra field, no schema, missing run, integration)
- `tests/test_lint_tools.py` - 6 tests for lint_tools (all-good, missing schema, init excluded, nonexistent dir, multi-agent, real agents/ dir)
- `pyproject.toml` - Added jsonschema>=4.0.0 dependency

## Decisions Made
- INPUT_SCHEMA is optional: ScriptBackend skips validation when absent, enabling permissive operation for legacy tools without the constant
- ValueError (not jsonschema.ValidationError) raised on validation failure — consistent error type for callers, message contains "validation failed"
- [!_]*.py glob pattern used in lint_tools.py to exclude __init__.py and _-prefixed helper files from enforcement

## Deviations from Plan

None - plan executed exactly as written.

Note: `uv add jsonschema` failed due to permission issues with the existing .venv symlink. Resolved via `pip install jsonschema` and manual pyproject.toml update. Functionally equivalent result.

## Issues Encountered
- `uv add jsonschema` failed with "Permission denied" on .venv/lib64 — pre-existing environment permission issue. Resolved with `pip install jsonschema` + manual pyproject.toml edit.
- test_graph.py::test_messages_accumulate is a pre-existing failure unrelated to this plan (verified on previous commits).
- test_api_* tests fail with ModuleNotFoundError: arq — pre-existing pip environment missing arq module, unrelated to this plan.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- ScriptBackend foundation ready for integration into SubAgentRegistry (Plan 01/02 work)
- INPUT_SCHEMA pattern established — future agent tool authors can follow lint_file.py as template
- CI lint script ready to add to pre-commit hooks or GitHub Actions workflow

## Self-Check: PASSED

- app/orchestrator/script_backend.py: FOUND
- agents/code-reviewer/tools/lint_file.py: FOUND
- scripts/lint_tools.py: FOUND
- tests/test_script_backend.py: FOUND
- tests/test_lint_tools.py: FOUND
- fb535de: FOUND
- 9bda265: FOUND

---
*Phase: 12-hybrid-subagentregistry-tool-quality*
*Completed: 2026-04-04*
