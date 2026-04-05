---
phase: 15
slug: gem-canvas
status: draft
nyquist_compliant: false
wave_0_complete: true
created: 2026-04-05
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + vitest |
| **Config file** | `pytest.ini` / `frontend/vite.config.ts` |
| **Quick run command** | `cd /workspace && pytest tests/ -x -q 2>&1 | tail -20` |
| **Full suite command** | `cd /workspace && pytest tests/ -q && cd frontend && bun run test 2>&1 | tail -30` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q 2>&1 | tail -20`
- **After every plan wave:** Run full suite (pytest + vitest)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 15-01-01 | 01 | 1 | gem-data-model | — | Gem data isolated per user | unit | `pytest tests/test_gems.py -q` | ❌ W0 | ⬜ pending |
| 15-01-02 | 01 | 1 | gem-api | — | CRUD endpoints return correct shape | integration | `pytest tests/test_gem_api.py -q` | ❌ W0 | ⬜ pending |
| 15-02-01 | 02 | 1 | canvas-backend | — | Canvas state persisted per thread | unit | `pytest tests/test_canvas.py -q` | ❌ W0 | ⬜ pending |
| 15-03-01 | 03 | 2 | gem-ui | — | GemPanel renders list correctly | unit | `cd frontend && bun run test -- gems` | ❌ W0 | ⬜ pending |
| 15-04-01 | 04 | 2 | canvas-ui | — | CanvasPanel renders and saves | unit | `cd frontend && bun run test -- canvas` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_gems.py` — stubs for gem CRUD
- [ ] `tests/test_gem_api.py` — integration stubs for gem API
- [ ] `tests/test_canvas.py` — stubs for canvas persistence
- [ ] `frontend/src/components/__tests__/GemPanel.test.tsx` — UI stubs
- [ ] `frontend/src/components/__tests__/CanvasPanel.test.tsx` — UI stubs

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Gem system prompt applied to LLM | gem-apply | LLM output non-deterministic | Create gem, start chat, verify system prompt prepended in request |
| Canvas autosave on tab switch | canvas-autosave | Browser timing dependent | Open canvas, type content, switch tabs, return — verify content persisted |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
