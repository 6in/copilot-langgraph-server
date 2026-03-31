---
phase: 2
slug: graph-layer
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-31
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml (pytest section — Wave 0 installs if missing) |
| **Quick run command** | `uv run pytest tests/test_graph.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -x -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_graph.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 0 | GRPH-01 | unit stub | `uv run pytest tests/test_graph.py -x -q` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | GRPH-01 | unit | `uv run pytest tests/test_graph.py::test_messages_accumulate -x -q` | ✅ | ⬜ pending |
| 02-01-03 | 01 | 1 | GRPH-02 | unit | `uv run pytest tests/test_graph.py::test_thread_isolation -x -q` | ✅ | ⬜ pending |
| 02-01-04 | 01 | 1 | GRPH-03 | unit | `uv run pytest tests/test_graph.py::test_extension_point -x -q` | ✅ | ⬜ pending |
| 02-02-01 | 02 | 2 | GRPH-01 | integration | `uv run python scripts/validate_graph.py` | ✅ | ⬜ pending |
| 02-02-02 | 02 | 2 | GRPH-02 | integration | `uv run python scripts/validate_graph.py` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_graph.py` — stubs for GRPH-01, GRPH-02, GRPH-03
- [ ] `tests/conftest.py` — shared fixtures (mock ChatCopilot)
- [ ] `uv add langgraph langgraph-checkpoint-sqlite aiosqlite` — install missing packages

*Wave 0 creates test stubs before implementation begins.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Second message references prior context (live Copilot) | GRPH-01 | Requires real Copilot token; cannot mock LLM response coherence | Run `uv run python scripts/validate_graph.py` with valid token, verify AI response references first message |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
