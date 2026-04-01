---
phase: 4
slug: sse-redis-worker-jobstore-notifier
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-01
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (`asyncio_mode = "auto"`) |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green (all 53 existing + new Phase 4 tests)
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 4-W0-01 | 01 | 0 | ASYNC-03, ASYNC-05 | unit | `uv run pytest tests/test_job_store.py -x -q` | ❌ W0 | ⬜ pending |
| 4-W0-02 | 01 | 0 | ASYNC-04, ASYNC-06 | integration | `uv run pytest tests/test_sse.py -x -q` | ❌ W0 | ⬜ pending |
| 4-W0-03 | 01 | 0 | ASYNC-01, ASYNC-02 | unit | `uv run pytest tests/test_api_chat.py tests/test_api_jobs.py -x -q` | ❌ W0 | ⬜ pending |
| 4-W0-04 | 01 | 0 | ASYNC-07 | unit (mock) | `uv run pytest tests/test_worker.py -x -q` | ❌ W0 | ⬜ pending |
| 4-01-01 | 01 | 1 | ASYNC-01 | unit | `uv run pytest tests/test_api_chat.py -k "test_post_chat_returns_job_id" -x -q` | ❌ W0 | ⬜ pending |
| 4-01-02 | 01 | 1 | ASYNC-03 | unit | `uv run pytest tests/test_job_store.py -k "test_save_and_get" -x -q` | ❌ W0 | ⬜ pending |
| 4-01-03 | 01 | 1 | ASYNC-05 | unit | `uv run pytest tests/test_job_store.py -k "test_notify_no_queue" -x -q` | ❌ W0 | ⬜ pending |
| 4-02-01 | 02 | 1 | ASYNC-07 | unit | `uv run pytest tests/test_worker.py -k "test_process_chat_saves_result" -x -q` | ❌ W0 | ⬜ pending |
| 4-03-01 | 03 | 1 | ASYNC-04 | integration | `uv run pytest tests/test_sse.py -k "test_sse_done_signal" -x -q` | ❌ W0 | ⬜ pending |
| 4-03-02 | 03 | 1 | ASYNC-06 | unit | `uv run pytest tests/test_sse.py -k "test_sse_already_done" -x -q` | ❌ W0 | ⬜ pending |
| 4-03-03 | 03 | 1 | ASYNC-02 | unit | `uv run pytest tests/test_api_jobs.py -k "test_get_job_pending" -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_job_store.py` — stubs for ASYNC-03, ASYNC-05 (mock Redis client with `AsyncMock`)
- [ ] `tests/test_sse.py` — stubs for ASYNC-04, ASYNC-06 (mock JobStore + ASGITransport)
- [ ] `tests/test_api_chat.py` — extend existing file for ASYNC-01
- [ ] `tests/test_api_jobs.py` — new file for ASYNC-02 polling endpoint
- [ ] `tests/test_worker.py` — stubs for ASYNC-07 (mock graph, mock job_store)

**Mock strategy:** `redis.asyncio.Redis` mocked with `AsyncMock`. `JobStore` tested with real `asyncio.Queue` + mock Redis. SSE tests use `httpx.AsyncClient` with `ASGITransport` + manually injected mock `job_store` in `app.state`.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Redis daemon is running and accepting connections | ASYNC-01..07 | Infrastructure dependency | `docker run -d -p 6379:6379 redis:7-alpine` then `redis-cli ping` → PONG |
| Worker process handles Redis reconnect after restart | Resilience | Non-deterministic timing | Kill and restart Redis while worker is idle; verify worker resumes processing jobs |
| SSE stream displays "Thinking..." indicator in browser before response | UX | Browser rendering | Open UI, send message, observe loading indicator appears before reply |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
