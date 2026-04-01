---
phase: 6
slug: sqlite-postgresql-checkpointer-langgraph-checkpoint-postgres-docker-compose
status: draft
nyquist_compliant: true
wave_0_complete: true
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
| 6-01-01 | 01 | 1 | CKPT-01 | unit | `grep -q "langgraph-checkpoint-postgres" pyproject.toml && grep -q "postgres:17-alpine" docker-compose.yml && grep -q "postgres-data" docker-compose.yml` | N/A (config) | pending |
| 6-01-02 | 01 | 1 | CKPT-01, CKPT-02 | unit | `grep -q "AsyncPostgresSaver" app/api/main.py && grep -q "checkpointer.setup" app/api/main.py && grep -q "AsyncPostgresSaver" app/jobs/worker.py` | N/A (grep) | pending |
| 6-01-03 | 01 | 1 | CKPT-02 | unit | `uv run pytest tests/test_worker.py -x -q` | tests/test_worker.py | pending |
| 6-02-01 | 02 | 2 | CKPT-03 | unit | `uv run pytest tests/test_api_chat.py -x -q` | tests/test_api_chat.py | pending |
| 6-02-02 | 02 | 2 | CKPT-04, CKPT-05 | unit | `uv run pytest tests/ -x -q` | tests/test_api_chat.py | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

No Wave 0 tasks needed. Existing test infrastructure (`tests/test_worker.py`, `tests/test_api_chat.py`, `tests/conftest.py`) covers all phase requirements. Tests need patch target updates and state field renames, but no new test files are required.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Docker Compose `postgres` service healthy before `api`/`worker` start | CKPT-05 | Requires Docker runtime | Run `docker compose up`, verify no "connection refused" errors in `api` logs |
| Existing chat threads continue working after migration | CKPT-01 | Requires live PostgreSQL + Copilot auth | Start app, send message, verify response persisted in `pg_threads` |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or existing test file dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] No Wave 0 gaps — existing test files cover all requirements
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
