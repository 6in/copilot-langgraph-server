# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

---

## Milestone: v1.0 — Copilot LangGraph Chat MVP

**Shipped:** 2026-04-02
**Phases:** 6 | **Plans:** 17 | **Commits:** 163 | **Duration:** 2 days (2026-03-31 → 2026-04-02)

### What Was Built

- `ChatCopilot(BaseChatModel)` — LangChain-compatible wrapper around Copilot SDK JSON-RPC transport
- Device Flow OAuth + Fernet-encrypted token storage → JWT session management for web API
- LangGraph StateGraph with MessagesState, thread isolation, and documented ToolNode extension point
- FastAPI async backend: 7 REST endpoints, 71 passing tests, arq job queue + Redis
- SSE real-time completion delivery + polling fallback; separate arq worker process
- GET /api/me with GitHub profile API → avatar + login display in header
- AsyncPostgresSaver checkpointer migration: Docker Compose with postgres (pgvector:pg17) + healthcheck
- Dark-themed Vanilla JS frontend: auth panel, thread sidebar, Markdown rendering, XSS-safe message display

### What Worked

- **TDD-first approach** for Python layers (auth, provider, graph) — having 18+ tests green before integration saved debugging time when wiring layers together
- **Phase layering discipline** — auth → graph → API → async → user → persistence is the correct dependency order; no phase had to back-fill a dependency
- **Human checkpoint phases** (03-04, 04-04) — auto-approved in yolo mode but having the gate meant verifier ran full artifact checks before marking complete
- **`gsd:quick` for cross-cutting fixes** — 7 quick tasks (JWT auth, re-auth fix, pgvector, sidebar refresh etc.) handled outside phase structure cleanly without polluting phase plans
- **arq + Redis pattern** — decoupling the LangGraph execution from HTTP with job_id + SSE is a strong pattern for any AI workload; straightforward to implement and test

### What Was Inefficient

- **Several SUMMARY one-liners missing** (Phases 4-5, 06-02) — some plans had placeholder "One-liner:" values instead of real summaries; this surfaced as noise in MILESTONES.md. Plans should enforce non-empty one-liners before marking complete.
- **test_sse_done_signal never updated** — the asyncio.Queue → Redis polling migration happened during execution but the test was not updated atomically. This left a CI-blocking hanging test as tech debt. Rule: when migrating an implementation approach, always update tests in the same commit.
- **marked.js version mismatch comment** — developer noted "v17 UMD" in a comment but loaded v9 in HTML. This created a confusing integration warning (false alarm, v9 exports `Marked` too). Version comments in CDN links should match the actual pinned version.
- **REQUIREMENTS.md not updated for Phases 4-6** — ASYNC-*, ME-*, CKPT-* IDs defined in ROADMAP.md but never registered in REQUIREMENTS.md traceability. For multi-milestone projects, update REQUIREMENTS.md when new requirement IDs are introduced in plans.

### Patterns Established

- **`job_store.get()` polling for cross-process SSE** — asyncio.Queue is incompatible with separate worker processes; Redis poll-on-read is the correct pattern for arq-based architectures
- **`save_result()` BEFORE `notifier.done()`** — ordering guarantee that the job result is retrievable when the SSE done signal arrives
- **`AsyncMock()` for checkpointer in conftest** — MagicMock doesn't support `await`; `AsyncMock` auto-creates awaitable children without manual reassignment
- **`except Exception: pass` for DB operations that should fail silently** (list_threads, delete_thread) — defensive pattern for the startup race where DB may not be ready; returns empty gracefully
- **JWT cookie with file-fallback for secret** — `~/.copilot_sdk/.jwt_secret` file means zero-config for local development while docker-compose services share the volume mount

### Key Lessons

1. **Ship the implementation change and the test change together.** The SSE Redis-polling migration was correct but `test_sse_done_signal` was not updated, leaving a hanging test as the only real artifact gap in the milestone.
2. **Phased architecture (auth → core → web → async → auth-ext → persistence) works well for AI chat apps.** Each phase was independently runnable. No backtracking needed.
3. **arq is ergonomic for LangGraph worker processes.** `WorkerSettings`, `process_chat`, `startup/shutdown` hooks integrate cleanly with FastAPI lifespan. The `job_timeout=300` guard matches SDK timeouts.
4. **pgvector from the start costs nothing extra.** Switching from `postgres:17-alpine` to `pgvector/pgvector:pg17` + initdb script adds zero operational overhead while enabling future RAG features without a migration.
5. **Personal tool architecture tradeoffs are valid.** Single-user means: no Redis token store, unprotected thread CRUD routes, in-memory JTI blocklist, plaintext token in arq payload. Document these explicitly rather than over-engineering.

### Cost Observations

- Model mix: balanced profile (Sonnet 4.6 as primary)
- Sessions: ~10 sessions across 2 days
- Notable: yolo mode + coarse granularity made full phases executable in single sessions; planning artifacts (PLAN.md → SUMMARY.md → VERIFICATION.md) provided good forward context for each session

---

## Cross-Milestone Trends

| Milestone | Phases | Plans | Duration | Tests at Ship | Tech Debt Items |
|-----------|--------|-------|----------|---------------|-----------------|
| v1.0 | 6 | 17 | 2 days | 71 | ~10 (1 CI blocker, rest minor) |

*More data needed for trends. Update after v2.0.*
