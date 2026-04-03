# Roadmap: Copilot LangGraph Chat

## Milestones

- ✅ **v1.0 MVP** — Phases 1–6 (shipped 2026-04-02) — [Archive](milestones/v1.0-ROADMAP.md)
- 📋 **v2.0** — Phases 7+ (in progress)

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1–6) — SHIPPED 2026-04-02</summary>

- [x] **Phase 1: Auth + Provider Foundation** — Copilot SDK isolated, Device Flow auth working, ChatCopilot gets a response end-to-end from a Python script (completed 2026-03-31)
- [x] **Phase 2: Graph Layer** — LangGraph StateGraph wired to ChatCopilot, multi-turn conversation history accumulates correctly, thread_id session isolation works (completed 2026-03-31)
- [x] **Phase 3: Web + Chat UI** — FastAPI serves the API, vanilla JS chat UI runs in the browser with full send/receive/history/auth flows (completed 2026-04-01)
- [x] **Phase 4: Async Job Queue + SSE** — Redis worker decouples AI execution from HTTP, SSE delivers real-time completion, polling provides fallback (completed 2026-04-01)
- [x] **Phase 5: GitHub User Info + Header UI** — GET /api/me fetches GitHub profile, header displays avatar + login name (completed 2026-04-01)
- [x] **Phase 6: SQLite to PostgreSQL Checkpointer Migration** — AsyncPostgresSaver replaces AsyncSqliteSaver, postgres Docker service added, all tests pass (completed 2026-04-02)

See [v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md) for full phase details.

</details>

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Auth + Provider Foundation | v1.0 | 3/3 | Complete | 2026-03-31 |
| 2. Graph Layer | v1.0 | 2/2 | Complete | 2026-03-31 |
| 3. Web + Chat UI | v1.0 | 4/4 | Complete | 2026-04-01 |
| 4. Async Job Queue + SSE | v1.0 | 4/4 | Complete | 2026-04-01 |
| 5. GitHub User Info + Header UI | v1.0 | 2/2 | Complete | 2026-04-01 |
| 6. SQLite → PostgreSQL Checkpointer | v1.0 | 2/2 | Complete | 2026-04-02 |
| 7. React Chat UI (chatscope + Vite + Bun) | v2.0 | 4/4 | Complete | 2026-04-02 |
| 8. Super Agent Sample | v2.0 | 3/3 | Complete   | 2026-04-03 |

## v2.0 Phases

### Phase 7: React Chat UI — chatscope + Vite served at /react, full feature parity with Vanilla JS

**Goal:** Build a full-featured React chat UI in `frontend/` using @chatscope/chat-ui-kit-react + Vite, served by FastAPI at `/react`, with full feature parity to the existing Vanilla JS version: Device Flow auth, multi-turn Markdown chat, thread sidebar, model selector (gpt-4.1 default), GitHub user info, SSE + polling fallback, logout.

**Requirements:** D-01 (feature parity), D-02 (self-contained auth), D-03 (chatscope default CSS), D-04 (bun build → FastAPI /react), D-05 (message alignment), D-06 (thread sidebar), D-07 (gpt-4.1 default), D-08 (TypingIndicator)

**Depends on:** Phase 6

**Plans:** 4/4 complete (human verification approved 2026-04-02)

Plans:
- [x] 07-01-PLAN.md — Vite scaffold + npm install + FastAPI CORSMiddleware + /react StaticFiles mount
- [x] 07-02-PLAN.md — Core shell: types.ts, api/client.ts, useAuth, AuthPanel, Header, App, main.tsx
- [x] 07-03-PLAN.md — Chat features: useThreads, useChat, ThreadSidebar, MarkdownMessage, MessageArea, ChatApp
- [x] 07-04-PLAN.md — Visual verification: HUMAN-UAT.md + browser walkthrough of all 10 success criteria

### Phase 8: スーパーエージェントサンプル実装 — OrchestratorGraph + SubAgent + メニュー追加（docs/pre/phase1_spec.md 仕様準拠、別ブランチ作業）

**Goal:** Implement a standalone sample in `super-agent-sample/` demonstrating the OrchestratorGraph + SubAgent architecture: RouterNode routes user input to specialized agents (code-reviewer, sql-analyst) or fallback, MenuDispatcher selects between orchestrator and simple graph modes, all verified with a live Anthropic API smoke test.

**Requirements:** SAMPLE-01 (scaffold), SAMPLE-02 (AgentState), SAMPLE-03 (SubAgent/Registry), SAMPLE-04 (RouterNode/OrchestratorGraph), SAMPLE-05 (MenuDispatcher), SAMPLE-06 (AGENT.md files), SAMPLE-07 (menu YAMLs), SAMPLE-08 (main.py entry point), SAMPLE-09 (smoke test), SAMPLE-10 (unit tests)

**Depends on:** Phase 7

**Plans:** 3/3 plans complete

Plans:
- [x] 08-01-PLAN.md — Feature branch + scaffold: pyproject.toml, uv sync, state.py, AGENT.md files, menu YAMLs
- [x] 08-02-PLAN.md — Core modules: agent.py, graph.py, dispatcher.py + full unit test suite
- [x] 08-03-PLAN.md — Entry point main.py + live smoke test (human verification)
