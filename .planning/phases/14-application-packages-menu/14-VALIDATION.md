---
phase: 14
slug: application-packages-menu
status: draft
nyquist_compliant: true
wave_0_complete: true
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
| 14-01-01 | 01 | 1 | APP-01, APP-04 | T-14-05 | Malformed APP.md logged and skipped | unit | `uv run pytest tests/test_app_registry.py -x -q` | TDD (created in task) | ⬜ pending |
| 14-01-02 | 01 | 1 | APP-01, APP-02, APP-03 | T-14-01, T-14-02 | JWT required on GET /api/apps; FK validates app_id | integration | `uv run pytest tests/test_apps_route.py -x -q` | TDD (created in task) | ⬜ pending |
| 14-02-01 | 02 | 2 | APP-02 | — | N/A | type-check | `cd frontend && npx tsc --noEmit` | existing | ⬜ pending |
| 14-02-02 | 02 | 2 | APP-02, APP-03, APP-04 | T-14-08 | Icon rendered as text, no innerHTML | type-check + vitest | `cd frontend && npx tsc --noEmit && npx vitest run --reporter=verbose` | existing | ⬜ pending |
| 14-02-03 | 02 | 2 | APP-02 | — | N/A | e2e | manual (checkpoint:human-verify) | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

All test files are created alongside implementation (TDD tasks in Plan 01). No separate Wave 0 plan needed.

- `tests/test_app_registry.py` — created in Plan 01 Task 1 (TDD: tests written before AppRegistry implementation)
- `tests/test_apps_route.py` — created in Plan 01 Task 2 (TDD: tests written before route implementation)

*Existing test infrastructure (pytest, docker compose exec, vitest) covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Menu screen renders cards with name/description/icon | APP-02 | React component visual check | Navigate to `/app`, verify menu grid shows all APP.md packages with correct titles |
| Chat header shows active app name | APP-02 | Visual regression | Select app from menu, verify header/title reflects app name |
| Agent chips filtered to app's declared agents | APP-03 | Visual + functional check | Select SuperChat, verify only superchat agents shown in chips |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (tests created in TDD tasks)
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
