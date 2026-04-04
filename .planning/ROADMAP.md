# Roadmap: Copilot LangGraph Chat

## Milestones

- ✅ **v1.0 MVP** — Phases 1–6 (shipped 2026-04-02) — [Archive](milestones/v1.0-ROADMAP.md)
- ✅ **v2.0** — Phases 7–10 (shipped 2026-04-04)
- 📋 **v3.0 Agent Platform** — Phases 11–14 (in progress)

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

<details>
<summary>✅ v2.0 (Phases 7–10) — SHIPPED 2026-04-04</summary>

- [x] **Phase 7: React Chat UI** — chatscope + Vite + Bun served at /app, full feature parity with Vanilla JS (completed 2026-04-02)
- [x] **Phase 8: Super Agent Sample** — OrchestratorGraph + SubAgent architecture in super-agent-sample/, live smoke test verified (completed 2026-04-03)
- [x] **Phase 9: SuperChat App Integration** — OrchestratorGraph integrated into app/, simple/super mode toggle in React UI (completed 2026-04-04)
- [x] **Phase 10: SuperChat Thread Persistence** — applications/threads schema, app-isolated thread listing, OrchestratorGraph checkpointer, general-assistant agent (completed 2026-04-04)

</details>

## v3.0 Agent Platform Phases

- [x] **Phase 11: RPCContext Integration** — RPCContext unified into AgentState, all nodes access context via state["context"], correlation_id flows through routing and audit logs (completed 2026-04-04)
- [x] **Phase 12: Hybrid SubAgentRegistry + Tool Quality** — Folder-type and code-type agent auto-loading, HEALTHY/DEGRADED/FAILED status management, INPUT_SCHEMA standard + CI lint (completed 2026-04-04)
- [ ] **Phase 13: Scalable Routing** — 2-stage router (keyword pre-filter + LLM), AGENT.md description convention enforced, structured routing logs with correlation_id
- [ ] **Phase 14: Application Packages + Menu** — App definition files declare agent subsets, menu screen launches app-specific chat, agents shared across apps

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
| 9. SuperChat メインアプリ統合 | v2.0 | 3/4 | Complete |  2026-04-04 |
| 10. SuperChat 履歴保存とモード別スレッド分離 | v2.0 | 6/6 | Complete    | 2026-04-04 |
| 11. RPCContext Integration | v3.0 | 4/4 | Complete    | 2026-04-04 |
| 12. Hybrid SubAgentRegistry + Tool Quality | v3.0 | 3/3 | Complete    | 2026-04-04 |
| 13. Scalable Routing | v3.0 | 0/2 | In progress | - |
| 14. Application Packages + Menu | v3.0 | 0/? | Not started | - |

## Shipped Phase Details

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

### Phase 9: SuperChat メインアプリ統合 — OrchestratorGraph を app/ に組み込み、既存 Chat と共存

**Goal:** Integrate the OrchestratorGraph + SubAgent + MenuDispatcher prototype from `super-agent-sample/` into the main `app/` as a selectable mode (`simple` vs `super`), with `github_token` threading for multi-user auth, a new `OrchestratorHandler` in the arq worker, and a React UI toggle to switch between modes.

**Requirements:** D-01 (app/orchestrator module), D-02 (remove standalone copies, import from app/), D-03 (keep super-agent-sample/), D-04 (mode field on POST /api/chat), D-06 (same job/SSE/polling), D-07 (AGENT_DIR/MENU_DIR env vars), D-08 (React mode toggle)

**Depends on:** Phase 8

**Plans:** 3/4 plans executed

Plans:
- [x] 09-01-PLAN.md — Create app/orchestrator/ module + repo-root agents/menus directories
- [x] 09-02-PLAN.md — OrchestratorHandler + API mode routing + Docker env vars
- [x] 09-03-PLAN.md — Frontend mode toggle in React UI
- [x] 09-04-PLAN.md — Integration smoke test and UAT verification

### Phase 10: SuperChat 履歴保存とモード別スレッド分離 — thread_labels に mode カラム追加、GET /api/threads を LEFT JOIN 化、OrchestratorGraph を LangGraph checkpointer 対応にして会話継続性を修正、フロント useThreads をモード別リスト対応に

**Goal:** Chat と SuperChat をアプリケーション（モード）として捉え、アプリケーション＋ユーザーという単位でスレッドを分離・管理できるようにする。thread_labels に mode カラムを追加し、GET /api/threads を LEFT JOIN + mode フィルタ対応にし、OrchestratorGraph に checkpointer を接続して SuperChat の会話継続性を実現し、フロント useThreads をモード別対応にする。

**Requirements:** DB-01 (mode column), DB-02 (default chat for existing), API-01 (LEFT JOIN + mode filter), API-02 (backward compat no-mode), API-03 (mode upsert in POST /api/chat), ORC-01 (checkpointer + thread_id), FE-01 (useThreads mode param), FE-02 (ChatApp/SuperChatApp pass mode)

**Depends on:** Phase 9

**Plans:** 6/6 plans complete

Plans:
- [ ] 10-01-PLAN.md — Wave 0: Test scaffolding (failing tests for all new behaviors)
- [ ] 10-02-PLAN.md — Wave 1: DB migration (thread_labels mode column)
- [ ] 10-03-PLAN.md — Wave 2: API changes (LEFT JOIN + mode filter + mode upsert)
- [ ] 10-04-PLAN.md — Wave 3: OrchestratorGraph checkpointer integration
- [ ] 10-05-PLAN.md — Wave 4: Frontend useThreads mode support

## Phase Details

### Phase 11: RPCContext Integration
**Goal:** RPCContext (user_id / app_id / thread_id / correlation_id) is unified into AgentState and flows immutably through every node and log entry, enabling end-to-end request tracing
**Depends on:** Phase 10
**Requirements:** CONTEXT-01, CONTEXT-02, CONTEXT-03, CONTEXT-04
**Success Criteria** (what must be TRUE):
  1. Developer can access state["context"].correlation_id from any node in the graph without passing extra arguments
  2. A node that attempts to overwrite state["context"] is silently ignored — the original context from request intake survives the full graph execution
  3. Developer can construct an RPCContext from an HTTP request via RPCContext.from_http() with app_id, user_id, and auto-generated correlation_id
  4. A routing log entry and an audit log entry for the same request share the same correlation_id, making the full processing chain traceable
**Plans:** 4/4 plans complete

Plans:
- [x] 11-01-PLAN.md -- RPCContext dataclass + _keep_first reducer + unit tests
- [x] 11-02-PLAN.md -- AgentState context + error fields with reducer integration tests
- [x] 11-03-PLAN.md -- RouterNode structured logging with correlation_id
- [x] 11-04-PLAN.md -- Wire HTTP -> arq job -> OrchestratorHandler RPCContext injection

### Phase 12: Hybrid SubAgentRegistry + Tool Quality
**Goal:** Agents are auto-discovered from the agents/ directory — both folder-type (AGENT.md only) and code-type (agent.py present) — with HEALTHY/DEGRADED/FAILED health status, and all tool scripts expose INPUT_SCHEMA for validation and CI enforcement
**Depends on:** Phase 11
**Requirements:** REGISTRY-01, REGISTRY-02, REGISTRY-03, REGISTRY-04, TOOL-01, TOOL-02, TOOL-03
**Success Criteria** (what must be TRUE):
  1. Developer drops a new folder into agents/ with only an AGENT.md and tools/ scripts; on next startup the agent appears in GET /health/agents as HEALTHY with no code change
  2. Developer adds an agent.py to an existing folder-type agent; GET /health/agents shows the agent is using the code implementation (agent.py takes precedence)
  3. One agent fails initialization due to a missing dependency; GET /health/agents shows it as FAILED with the error reason while all other agents remain HEALTHY and the app starts normally
  4. Developer views GET /health/agents and sees HEALTHY/DEGRADED/FAILED status and failure reason for every registered agent
  5. CI fails a pull request when a new tool script is added without an INPUT_SCHEMA constant (scripts/lint_tools.py exits non-zero)
**Plans:** 3/3 plans complete

Plans:
- [x] 12-01-PLAN.md -- Hybrid SubAgentRegistry with health tracking (REGISTRY-01, 02, 03)
- [x] 12-02-PLAN.md -- GET /health/agents endpoint + startup metadata registry (REGISTRY-04)
- [x] 12-03-PLAN.md -- ScriptBackend + INPUT_SCHEMA + lint_tools.py (TOOL-01, 02, 03)

### Phase 13: Scalable Routing
**Goal:** RouterNode operates as a 2-stage pipeline (keyword pre-filter then LLM) so routing stays accurate and prompt size stays bounded as the agent count grows, with every routing decision logged for analysis
**Depends on:** Phase 12
**Requirements:** ROUTING-01, ROUTING-02, ROUTING-03
**Success Criteria** (what must be TRUE):
  1. An AGENT.md file without an exclusion section ("対象外") triggers a warning log entry when SubAgentRegistry loads it, telling the developer what is missing
  2. A request that clearly matches a keyword-stage agent is routed without invoking the LLM, reducing latency and token usage for unambiguous cases
  3. After a routing decision is made, a structured log entry records input message, chosen agent, candidate list, and correlation_id — visible in application logs without additional instrumentation
**Plans:** 2 plans

Plans:
- [ ] 13-01-PLAN.md -- SubAgent keywords + ROUTING-01 warning (ROUTING-01, ROUTING-02)
- [ ] 13-02-PLAN.md -- 2-stage RouterNode + stage log field (ROUTING-02, ROUTING-03)

### Phase 14: Application Packages + Menu
**Goal:** Developers define application packages that declare an agent subset, and users select an application from a menu screen that launches a chat scoped to only that application's agents
**Depends on:** Phase 13
**Requirements:** APP-01, APP-02, APP-03, APP-04
**Success Criteria** (what must be TRUE):
  1. Developer creates an app definition file listing 3 of 10 installed agents; the app appears on the menu screen after restart with no code change
  2. User selects an application from the menu screen and the chat UI opens with a title or indicator showing which application is active
  3. A message sent in App A is routed only among App A's declared agents — an agent registered only to App B is never a candidate, even if it would otherwise match
  4. The same agent folder (e.g. agents/code-reviewer/) is listed in two app definition files; both apps route to it correctly without duplicating the agent definition
**UI hint**: yes
**Plans:** 2 plans

Plans:
- [ ] 13-01-PLAN.md -- SubAgent keywords + ROUTING-01 warning (ROUTING-01, ROUTING-02)
- [ ] 13-02-PLAN.md -- 2-stage RouterNode + stage log field (ROUTING-02, ROUTING-03)
