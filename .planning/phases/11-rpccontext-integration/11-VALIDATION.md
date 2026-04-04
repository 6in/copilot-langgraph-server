---
phase: 11
slug: rpccontext-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-04
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml (existing) |
| **Quick run command** | `docker compose exec backend pytest tests/ -x -q` |
| **Full suite command** | `docker compose exec backend pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `docker compose exec backend pytest tests/ -x -q`
- **After every plan wave:** Run `docker compose exec backend pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 0 | CONTEXT-01 | unit | `pytest tests/test_rpc_context.py -x -q` | ❌ W0 | ⬜ pending |
| 11-01-02 | 01 | 1 | CONTEXT-01 | unit | `pytest tests/test_rpc_context.py -x -q` | ❌ W0 | ⬜ pending |
| 11-01-03 | 01 | 1 | CONTEXT-02 | unit | `pytest tests/test_rpc_context.py::test_immutability -x -q` | ❌ W0 | ⬜ pending |
| 11-01-04 | 01 | 1 | CONTEXT-03 | unit | `pytest tests/test_rpc_context.py::test_factory -x -q` | ❌ W0 | ⬜ pending |
| 11-02-01 | 02 | 1 | CONTEXT-01 | unit | `pytest tests/test_agent_state.py -x -q` | ❌ W0 | ⬜ pending |
| 11-02-02 | 02 | 1 | CONTEXT-02 | unit | `pytest tests/test_agent_state.py::test_context_immutable -x -q` | ❌ W0 | ⬜ pending |
| 11-03-01 | 03 | 1 | CONTEXT-04 | unit | `pytest tests/test_orchestrator_graph.py::test_correlation_id_in_logs -x -q` | ❌ W0 | ⬜ pending |
| 11-04-01 | 04 | 2 | CONTEXT-01,04 | integration | `pytest tests/test_rpc_integration.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_rpc_context.py` — unit stubs for CONTEXT-01, CONTEXT-02, CONTEXT-03
- [ ] `tests/test_agent_state.py` — unit stubs for CONTEXT-01, CONTEXT-02
- [ ] `tests/test_orchestrator_graph.py` — stubs for CONTEXT-04 correlation_id logging
- [ ] `tests/test_rpc_integration.py` — integration stub for end-to-end context flow

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| correlation_id appears in Docker log output | CONTEXT-04 | Requires live log inspection | `docker compose up` → send chat request → `docker compose logs backend \| grep correlation_id` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
