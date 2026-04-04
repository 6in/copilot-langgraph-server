---
phase: 12
slug: hybrid-subagentregistry-tool-quality
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-04
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml (existing) |
| **Quick run command** | `docker compose exec backend pytest tests/ -x -q --tb=short` |
| **Full suite command** | `docker compose exec backend pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `docker compose exec backend pytest tests/ -x -q --tb=short`
- **After every plan wave:** Run `docker compose exec backend pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 12-01-01 | 01 | 0 | REGISTRY-01/02/03 | unit | `pytest tests/test_hybrid_registry.py --collect-only -q` | tests/test_hybrid_registry.py (W0) | pending |
| 12-01-02 | 01 | 1 | REGISTRY-01/02/03 | unit | `pytest tests/test_hybrid_registry.py -x -q` | tests/test_hybrid_registry.py | pending |
| 12-02-01 | 02 | 1 | REGISTRY-04 | unit+integration | `pytest tests/test_health_route.py -x -q` | tests/test_health_route.py (W0) | pending |
| 12-02-02 | 02 | 2 | REGISTRY-04 | integration | `pytest tests/test_health_route.py tests/test_hybrid_registry.py -x -q` | tests/test_health_route.py | pending |
| 12-03-01 | 03 | 1 | TOOL-01/02/03 | unit | `python3 scripts/lint_tools.py && echo OK` | scripts/lint_tools.py | pending |
| 12-03-02 | 03 | 1 | TOOL-01/02 | unit | `pytest tests/test_script_backend.py tests/test_lint_tools.py -x -q` | tests/test_script_backend.py, tests/test_lint_tools.py (W0) | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

Wave 0 test files are created as part of their respective plan tasks (TDD RED phase):

- [x] `tests/test_hybrid_registry.py` -- Plan 12-01, Task 1 creates this (REGISTRY-01, REGISTRY-02, REGISTRY-03 including DEGRADED)
- [x] `tests/test_health_route.py` -- Plan 12-02, Task 1 creates this (REGISTRY-04, health endpoint tests)
- [x] `tests/test_script_backend.py` -- Plan 12-03, Task 2 creates this (TOOL-01, TOOL-02 ScriptBackend validation)
- [x] `tests/test_lint_tools.py` -- Plan 12-03, Task 2 creates this (TOOL-03 lint script behavior)
- [x] `scripts/lint_tools.py` -- Plan 12-03, Task 1 creates this (TOOL-03 CI enforcement)

All Wave 0 test file creation is accounted for within plan tasks. No separate Wave 0 stubs needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| App starts normally with 1 FAILED agent | REGISTRY-03 | Requires running the full Docker stack | `docker compose up`, drop a broken agent folder, verify startup logs show FAILED agent but app is healthy |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** complete
