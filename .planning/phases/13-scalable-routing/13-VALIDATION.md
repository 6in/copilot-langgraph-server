---
phase: 13
slug: scalable-routing
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-05
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `python -m pytest tests/test_hybrid_registry.py tests/test_orchestrator_graph.py tests/test_routing_keyword.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_hybrid_registry.py tests/test_orchestrator_graph.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 13-01-W0 | 01 | 0 | ROUTING-01 | unit | `pytest tests/test_hybrid_registry.py -k "test_missing_exclusion or test_with_exclusion" -x` | ❌ W0 | ⬜ pending |
| 13-01-W0b | 01 | 0 | ROUTING-02 | unit | `pytest tests/test_hybrid_registry.py -k "test_keywords_loaded" -x` | ❌ W0 | ⬜ pending |
| 13-01-W1 | 01 | 1 | ROUTING-01 | unit | `pytest tests/test_hybrid_registry.py -k "test_missing_exclusion" -x -q` | ❌ W0 | ⬜ pending |
| 13-01-W2 | 01 | 2 | ROUTING-02 | unit | `pytest tests/test_hybrid_registry.py -k "test_keywords_loaded" -x -q` | ❌ W0 | ⬜ pending |
| 13-02-W0 | 02 | 0 | ROUTING-02 | unit | `pytest tests/test_routing_keyword.py -x` | ❌ W0 | ⬜ pending |
| 13-02-W0b | 02 | 0 | ROUTING-03 | unit | `pytest tests/test_orchestrator_graph.py -k "test_stage" -x` | ❌ W0 | ⬜ pending |
| 13-02-W1 | 02 | 1 | ROUTING-02 | unit | `pytest tests/test_routing_keyword.py -k "test_single_keyword_match or test_no_keyword_match or test_multi_keyword_match" -x -q` | ❌ W0 | ⬜ pending |
| 13-02-W1b | 02 | 1 | ROUTING-03 | unit | `pytest tests/test_routing_keyword.py -k "test_stage_keyword_log" -x -q` | ❌ W0 | ⬜ pending |
| 13-02-W2 | 02 | 2 | ROUTING-03 | unit | `pytest tests/test_orchestrator_graph.py -x -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_hybrid_registry.py` — Add ROUTING-01 warning tests (`test_missing_exclusion_warns`, `test_with_exclusion_no_warn`) and keywords loading tests (`test_keywords_loaded`, `test_keywords_default_empty`)
- [ ] `tests/test_routing_keyword.py` — New file: ROUTING-02 single/no/multi keyword match tests + ROUTING-03 stage field tests for keyword path
- [ ] `tests/test_orchestrator_graph.py` — Add `stage: "llm"` assertion to existing routing log test

*All test files for Wave 0 are new stubs or additions to existing files — no framework installation required.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| None | — | — | — |

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
