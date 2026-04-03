---
phase: 8
slug: orchestratorgraph-subagent-docs-pre-phase1-spec-md
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-03
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `super-agent-sample/pyproject.toml` — Wave 0 installs |
| **Quick run command** | `cd super-agent-sample && PYTHONPATH=src uv run pytest tests/ -x -q` |
| **Full suite command** | `cd super-agent-sample && PYTHONPATH=src uv run pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd super-agent-sample && PYTHONPATH=src uv run pytest tests/ -x -q`
- **After every plan wave:** Run `cd super-agent-sample && PYTHONPATH=src uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | scaffold + pyproject | setup | `git branch --show-current \| grep -q feat/super-agent-sample && uv run python -c "import frontmatter; ..."` | n/a | pending |
| 08-01-02 | 01 | 1 | state.py + AGENT.md + menus | unit | `PYTHONPATH=src uv run python -c "from state import AgentState; ..."` | n/a | pending |
| 08-02-01 | 02 | 2 | test stubs (Wave 0) | setup | `uv run pytest tests/ -x -q` | W0 | pending |
| 08-02-02 | 02 | 2 | agent.py + graph.py + dispatcher.py + full tests | unit | `PYTHONPATH=src uv run python -c "from agent import SubAgent, ..." && uv run pytest tests/ -x -q` | yes (from 08-02-01) | pending |
| 08-03-01 | 03 | 3 | main.py | structure | `PYTHONPATH=src uv run python -c "import ast; ..."` | n/a | pending |
| 08-03-02 | 03 | 3 | smoke test | integration | `PYTHONPATH=src uv run python src/main.py` (manual — requires API key) | n/a | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [x] `super-agent-sample/tests/test_state.py` — real tests for AgentState (state.py exists from Plan 01)
- [x] `super-agent-sample/tests/test_registry.py` — stubs for SubAgent/SubAgentRegistry (skipped until Task 2)
- [x] `super-agent-sample/tests/test_router.py` — stubs for RouterNode (skipped until Task 2)
- [x] `super-agent-sample/tests/test_dispatcher.py` — stubs for MenuDispatcher (skipped until Task 2)
- [x] `super-agent-sample/tests/conftest.py` — shared fixtures (tmp_agents_dir, tmp_menus_dir)
- [x] `uv add pytest` — installed via pyproject.toml dev dependencies in Plan 01

Wave 0 is satisfied by Plan 08-02 Task 1 which creates all test stubs before implementation begins in Task 2.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end LLM call | OrchestratorGraph routes to SubAgent -> LLM -> output | Requires ANTHROPIC_API_KEY and live API | `echo "このコードをレビューして" \| PYTHONPATH=src uv run python src/main.py` |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved
