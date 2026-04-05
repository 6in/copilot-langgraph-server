---
phase: 14
slug: application-packages-menu
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-05
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) + vitest (frontend) |
| **Config file** | `pytest.ini` / `frontend/vite.config.ts` |
| **Quick run command** | `docker compose exec backend pytest tests/ -x -q` |
| **Full suite command** | `docker compose exec backend pytest tests/ && docker compose exec frontend bun run test` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `docker compose exec backend pytest tests/ -x -q`
- **After every plan wave:** Run `docker compose exec backend pytest tests/ && docker compose exec frontend bun run test`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 14-01-01 | 01 | 1 | APP-01 | — | N/A | unit | `docker compose exec backend pytest tests/test_app_registry.py -x -q` | ❌ W0 | ⬜ pending |
| 14-01-02 | 01 | 1 | APP-01 | — | N/A | unit | `docker compose exec backend pytest tests/test_app_registry.py -x -q` | ❌ W0 | ⬜ pending |
| 14-02-01 | 02 | 1 | APP-02 | — | N/A | integration | `docker compose exec backend pytest tests/test_apps_route.py -x -q` | ❌ W0 | ⬜ pending |
| 14-02-02 | 02 | 1 | APP-03 | — | N/A | integration | `docker compose exec backend pytest tests/test_apps_route.py -x -q` | ❌ W0 | ⬜ pending |
| 14-03-01 | 03 | 2 | APP-02 | — | N/A | e2e | manual | — | ⬜ pending |
| 14-03-02 | 03 | 2 | APP-04 | — | N/A | integration | `docker compose exec backend pytest tests/test_agent_scoping.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_app_registry.py` — stubs for APP-01 (AppRegistry scan, frontmatter parse, dedup)
- [ ] `tests/test_apps_route.py` — stubs for APP-02, APP-03 (GET /api/apps, FK upsert)
- [ ] `tests/test_agent_scoping.py` — stubs for APP-04 (agent filtering by app slug in job payload)

*Existing test infrastructure (pytest, docker compose exec) covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Menu screen renders cards with name/description/icon | APP-02 | React component visual check | Navigate to `/app`, verify menu grid shows all APP.md packages with correct titles |
| Chat header shows active app name | APP-03 | Visual regression | Select app from menu, verify header/title reflects app name |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
