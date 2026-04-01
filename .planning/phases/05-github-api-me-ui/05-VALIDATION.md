---
phase: 5
slug: github-api-me-ui
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-01
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 5-01-01 | 01 | 1 | /api/me endpoint | unit | `uv run pytest tests/test_me.py -x -q` | ❌ W0 | ⬜ pending |
| 5-01-02 | 01 | 1 | UserInfoResponse model | unit | `uv run pytest tests/test_me.py -x -q` | ❌ W0 | ⬜ pending |
| 5-02-01 | 02 | 2 | Header UI render | manual | see Manual-Only | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_me.py` — stubs for /api/me endpoint tests
- [ ] `tests/conftest.py` — shared fixtures (if not exists)

*Existing pytest infrastructure covers base; new test file needed for /api/me.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Header displays login + avatar | UI display | Browser rendering required | Open app, verify header shows GitHub username and avatar |
| Avatar image loads correctly | UI display | External URL fetch | Check browser devtools for 200 response on avatar_url |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
