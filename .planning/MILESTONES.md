# Milestones

## v1.0 Copilot LangGraph Chat MVP (Shipped: 2026-04-02)

**Phases completed:** 6 phases, 17 plans, 26 tasks
**Timeline:** 2026-03-31 → 2026-04-02 (2 days)
**Stats:** 144 files changed · ~23,749 insertions · 163 commits · ~4,935 Python LOC

**Delivered:** Full async chat app — GitHub Copilot via LangChain-compatible provider, LangGraph StateGraph with thread isolation, FastAPI + arq/Redis async job queue, SSE real-time delivery, PostgreSQL persistence, JWT auth, GitHub profile display.

**Key accomplishments:**

- `ChatCopilot(BaseChatModel)` — LangChain-compatible wrapper around Copilot SDK JSON-RPC transport with full async lifecycle
- GitHub Device Flow OAuth with Fernet-encrypted token persistence + JWT session management (cookie-based, HS256)
- LangGraph `StateGraph(MessagesState)` — multi-turn conversation graph with `thread_id` isolation and documented ToolNode extension point
- FastAPI async backend with lifespan, 7+ REST endpoints (auth, chat, threads, /api/me), 71 passing tests
- arq + Redis async job queue — POST /api/chat returns `job_id` immediately; separate worker executes LangGraph; SSE delivers completion; polling fallback on disconnect
- GET /api/me with GitHub profile API → avatar + login display in header (XSS-safe via `textContent`)
- AsyncPostgresSaver checkpointer migration — Docker Compose with `pgvector/pgvector:pg17` + `pg_isready` healthcheck; psycopg for thread queries; `adelete_thread` for atomic deletion
- Dark-themed Vanilla JS frontend — Device Flow auth panel, thread sidebar, Markdown rendering (marked.js + highlight.js), SSE EventSource + polling fallback

**Known gaps accepted as tech debt:**
- `tests/test_sse.py::test_sse_done_signal` hangs — test written for asyncio.Queue approach, production uses Redis polling; fix = update test mock (no production change needed)
- marked.js CDN pins @9.1.6 while app.js comment references v17 API — reconcile version or comment
- JobStore queue methods (`register_sse`, `unregister_sse`, `notify`) are dead code — Redis polling replaced in-process queue design
- ASYNC-*, ME-*, CKPT-* requirement IDs not in archived REQUIREMENTS.md traceability

---
