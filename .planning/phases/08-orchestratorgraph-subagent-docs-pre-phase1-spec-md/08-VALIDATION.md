---
phase: 8
slug: orchestratorgraph-subagent-docs-pre-phase1-spec-md
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| 08-01-01 | 01 | 0 | state.py | unit | `PYTHONPATH=src uv run pytest tests/test_state.py -x -q` | ❌ W0 | ⬜ pending |
| 08-01-02 | 01 | 1 | agent.py | unit | `PYTHONPATH=src uv run pytest tests/test_agent.py -x -q` | ❌ W0 | ⬜ pending |
| 08-01-03 | 01 | 1 | graph.py | unit | `PYTHONPATH=src uv run pytest tests/test_graph.py -x -q` | ❌ W0 | ⬜ pending |
| 08-01-04 | 01 | 2 | dispatcher.py | unit | `PYTHONPATH=src uv run pytest tests/test_dispatcher.py -x -q` | ❌ W0 | ⬜ pending |
| 08-01-05 | 01 | 3 | smoke test | integration | `PYTHONPATH=src uv run python src/main.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `super-agent-sample/tests/test_state.py` — stubs for AgentState
- [ ] `super-agent-sample/tests/test_agent.py` — stubs for SubAgent/SubAgentRegistry
- [ ] `super-agent-sample/tests/test_graph.py` — stubs for OrchestratorGraph/RouterNode
- [ ] `super-agent-sample/tests/test_dispatcher.py` — stubs for MenuDispatcher
- [ ] `super-agent-sample/tests/conftest.py` — shared fixtures
- [ ] `uv add pytest` — install test framework

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end LLM call | OrchestratorGraph routes to SubAgent → LLM → output | Requires ANTHROPIC_API_KEY and live API | `echo "このコードをレビューして" \| PYTHONPATH=src uv run python src/main.py` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
