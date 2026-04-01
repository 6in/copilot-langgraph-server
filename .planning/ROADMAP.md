# Roadmap: Copilot LangGraph Chat

## Overview

Three phases follow the strict dependency order the architecture demands: the Copilot SDK (highest risk, Technical Preview) is isolated and validated first, the LangGraph graph layer is built on top of a proven provider, and the FastAPI web layer plus vanilla JS frontend deliver the browser chat experience last. Each phase produces something independently runnable before the next layer is added.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Auth + Provider Foundation** - Copilot SDK isolated, Device Flow auth working, ChatCopilot gets a response end-to-end from a Python script (completed 2026-03-31)
- [x] **Phase 2: Graph Layer** - LangGraph StateGraph wired to ChatCopilot, multi-turn conversation history accumulates correctly, thread_id session isolation works (completed 2026-03-31)
- [x] **Phase 3: Web + Chat UI** - FastAPI serves the API, vanilla JS chat UI runs in the browser with full send/receive/history/auth flows (completed 2026-04-01)
- [x] **Phase 4: Async Job Queue + SSE** - Redis worker decouples AI execution from HTTP, SSE delivers real-time completion, polling provides fallback (completed 2026-04-01)
- [ ] **Phase 5: GitHub User Info + Header UI** - GET /api/me fetches GitHub profile, header displays avatar + login name

## Phase Details

### Phase 1: Auth + Provider Foundation
**Goal**: Developer can invoke ChatCopilot from a Python script and receive a Copilot response, with auth token persisted across restarts
**Depends on**: Nothing (first phase)
**Requirements**: AUTH-01, AUTH-02, PROV-01, PROV-02, PROV-03
**Success Criteria** (what must be TRUE):
  1. Running the auth script triggers Device Flow, opens a browser URL, and saves an encrypted token to ~/.copilot_sdk/token.enc
  2. Re-running the auth script reuses the saved token without re-prompting
  3. A Python script that creates ChatCopilot and calls ainvoke([HumanMessage("hello")]) receives a non-empty AIMessage response
  4. Changing the model parameter (e.g., gpt-4.1 vs claude-sonnet-4-5) produces a response without error
  5. CopilotClient start/stop lifecycle completes without subprocess leaks or warnings
**Plans:** 3/3 plans complete

Plans:
- [x] 01-01-PLAN.md — Project setup + CopilotAuthManager (Device Flow + Fernet encryption)
- [x] 01-02-PLAN.md — ChatCopilot BaseChatModel provider (SDK 0.2.0 wrapper)
- [x] 01-03-PLAN.md — End-to-end validation script + live Copilot verification

### Phase 2: Graph Layer
**Goal**: Multi-turn conversation flows through a LangGraph StateGraph backed by ChatCopilot, with correct history accumulation and thread isolation
**Depends on**: Phase 1
**Requirements**: GRPH-01, GRPH-02, GRPH-03
**Success Criteria** (what must be TRUE):
  1. A second message in a conversation receives a reply that references context from the first message
  2. Two separate thread_ids maintain completely independent conversation histories
  3. Calling build_graph() once at startup and invoking it multiple times per thread does not recompile or recreate the graph
  4. The StateGraph structure has a clear extension point where tool-calling nodes could be added without rewiring the core graph
**Plans:** 2/2 plans complete

Plans:
- [x] 02-01-PLAN.md — TDD: build_graph() with MessagesState, multi-turn history, thread isolation, extension point
- [x] 02-02-PLAN.md — Integration validation script + live Copilot verification

### Phase 3: Web + Chat UI
**Goal**: User can open a browser, authenticate via Device Flow, and hold a multi-turn chat conversation with Copilot
**Depends on**: Phase 2
**Requirements**: AUTH-03, CHAT-01, CHAT-02, CHAT-03, CHAT-04
**Success Criteria** (what must be TRUE):
  1. Opening the app in a browser and clicking "Login" triggers Device Flow and the page shows authenticated status after completion
  2. Sending a message shows a loading indicator, then displays the assistant reply in a message bubble
  3. Sending a follow-up message receives a reply that references the prior conversation context
  4. Assistant replies containing Markdown headers, bold text, or fenced code blocks render formatted — not as raw markup
  5. Clicking "New Chat" clears the message list and the next message starts a fresh conversation with no prior context
  6. When the Copilot token is expired, the UI shows a Re-authenticate button instead of a generic error
**Plans:** 4/4 plans complete
**UI hint**: yes

Plans:
- [x] 03-01-PLAN.md — Dependencies, API models, auth manager refactor, test infrastructure
- [x] 03-02-PLAN.md — FastAPI app with lifespan + all API routes (auth, chat, threads)
- [x] 03-03-PLAN.md — Frontend: HTML/CSS/JS chat UI with markdown rendering
- [x] 03-04-PLAN.md — Visual verification checkpoint (human verify)

### Phase 4: 非同期ジョブキュー + SSE ストリーミング移行（Redis Worker / JobStore / Notifier パターン）

**Goal:** Migrate synchronous POST /api/chat to async architecture: Gateway enqueues job and returns job_id immediately, Worker process executes LangGraph via arq, SSE delivers real-time completion signal, polling API provides recovery fallback
**Requirements**: ASYNC-01, ASYNC-02, ASYNC-03, ASYNC-04, ASYNC-05, ASYNC-06, ASYNC-07
**Depends on:** Phase 3
**Success Criteria** (what must be TRUE):
  1. POST /api/chat returns job_id immediately without blocking on LangGraph execution
  2. GET /api/job/{job_id} returns pending before completion, done with result after completion
  3. SSE endpoint delivers real-time done signal when worker completes
  4. SSE endpoint returns immediate done for already-completed jobs (page reload scenario)
  5. Frontend sends message, shows typing indicator, receives AI reply via SSE or polling
  6. Worker process runs LangGraph in separate process, saves result to Redis before signalling done
  7. Polling fallback activates when SSE connection drops
**Plans:** 4/4 plans complete

Plans:
- [x] 04-01-PLAN.md — Dependencies, docker-compose, JobStore, Notifier, Wave 0 test stubs
- [x] 04-02-PLAN.md — arq Worker (process_chat, WorkerSettings, startup/shutdown)
- [x] 04-03-PLAN.md — Gateway refactor (POST enqueue, SSE stream, polling endpoint, lifespan)
- [x] 04-04-PLAN.md — Frontend JS async flow (SSE + polling) + visual verification

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Auth + Provider Foundation | 3/3 | Complete   | 2026-03-31 |
| 2. Graph Layer | 2/2 | Complete   | 2026-03-31 |
| 3. Web + Chat UI | 4/4 | Complete   | 2026-04-01 |
| 4. Async Job Queue + SSE | 4/4 | Complete   | 2026-04-01 |
| 5. GitHub User Info + Header UI | 0/2 | Planning   | — |

### Phase 5: GitHubユーザー情報取得＆ヘッダー表示（/api/me エンドポイント追加 + UI）

**Goal:** Authenticated user's GitHub profile (avatar, login) is fetched via GET /api/me and displayed in the header, replacing generic "Authenticated" text
**Requirements**: ME-01, ME-02, ME-03, ME-04, ME-05
**Depends on:** Phase 4
**Success Criteria** (what must be TRUE):
  1. GET /api/me with valid JWT returns 200 with {login, name, avatar_url}
  2. GET /api/me without session cookie returns 401
  3. GET /api/me with expired JWT returns 401
  4. GET /api/me returns 502 when GitHub API fails
  5. Header displays GitHub avatar (circle) and login name when authenticated
**Plans:** 2 plans

Plans:
- [ ] 05-01-PLAN.md — Backend: UserInfoResponse model + GET /api/me route + tests
- [ ] 05-02-PLAN.md — Frontend: header avatar + login display + visual verification

### Phase 6: SQLiteからPostgreSQLへのCheckpointer移行（langgraph-checkpoint-postgres + Docker Compose）

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 5
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd:plan-phase 6 to break down)
