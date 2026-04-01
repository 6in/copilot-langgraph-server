---
phase: 6
slug: sqlite-postgresql-checkpointer-langgraph-checkpoint-postgres-docker-compose
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-01
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
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
| 6-01-01 | 01 | 0 | CKPT-01 | unit stub | `uv run pytest tests/test_checkpointer.py -x -q` | ❌ W0 | ⬜ pending |
| 6-01-02 | 01 | 1 | CKPT-01 | unit | `uv run pytest tests/test_checkpointer.py -x -q` | ✅ W0 | ⬜ pending |
| 6-01-03 | 01 | 1 | CKPT-02 | integration | `uv run pytest tests/test_checkpointer.py -k test_setup -x -q` | ✅ W0 | ⬜ pending |
| 6-02-01 | 02 | 1 | CKPT-03 | unit | `uv run pytest tests/ -x -q` | ✅ W0 | ⬜ pending |
| 6-02-02 | 02 | 1 | CKPT-04 | unit | `uv run pytest tests/ -x -q` | ✅ W0 | ⬜ pending |
| 6-02-03 | 02 | 2 | CKPT-05 | manual | Docker Compose up + smoke test | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_checkpointer.py` — stubs for PostgreSQL checkpointer (CKPT-01, CKPT-02)
- [ ] `tests/conftest.py` — add `postgres_dsn` fixture (skipped without `TEST_POSTGRES_URL`)

*Existing test infrastructure in `tests/` covers most patterns; only checkpointer-specific stubs needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Docker Compose `postgres` service healthy before `api`/`worker` start | CKPT-05 | Requires Docker runtime | Run `docker compose up`, verify no "connection refused" errors in `api` logs |
| Existing chat threads continue working after migration | CKPT-01 | Requires live PostgreSQL + Copilot auth | Start app, send message, verify response persisted in `pg_threads` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
