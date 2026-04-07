# Milestones

## v3.0 Agent Platform (Shipped: 2026-04-07)

**Phases completed:** 12 phases, 41 plans, 45 tasks

**Key accomplishments:**

- Vite React-TS project with @chatscope/chat-ui-kit-react scaffolded in frontend/, FastAPI updated with CORSMiddleware and /react StaticFiles mount
- React auth shell with Device Flow state machine, typed API client for all 12 backend endpoints, and Header with model selector defaulting to gpt-4.1
- Complete chatscope chat UI with SSE-driven AI responses, Markdown rendering, thread sidebar, and TypingIndicator — replacing ChatAppStub with the full ChatApp
- HUMAN-UAT.md created and all 10 phase success criteria (SC-01 through SC-10) verified in a real browser session by the human tester
- Standalone super-agent-sample/ project scaffolded on feat/super-agent-sample branch: AgentState TypedDict, code-reviewer and sql-analyst AGENT.md definitions, and orchestrator/simple menu YAML files, all verified parseable with python-frontmatter and yaml.safe_load
- SubAgent/SubAgentRegistry (agent.py), RouterNode/OrchestratorGraph (graph.py), and MenuDispatcher (dispatcher.py) implemented verbatim from spec with -> Any fix; 14 unit tests pass using mocked LLM, no live API calls
- Working main.py entry point added verbatim from spec section 9; human-verified smoke test confirms OrchestratorGraph routes code-reviewer, sql-analyst, and fallback correctly while simple-chat bypasses the router
- 1. [Rule 2 - Convention] Omitted emoji labels from toggle buttons
- Automated smoke tests confirm all Python/Docker integration is wired correctly; 5 of 6 checks pass (TypeScript check blocked by environment permissions); manual UAT checklist deferred to human with live stack.
- Lifespan migration in app/api/main.py replaces flat thread_labels table with normalized applications/threads/audit_log schema, seeding chat and superchat rows idempotently
- One-liner:
- One-liner:
- Gap closure: agents/general-assistant/AGENT.md added so RouterNode routes general SuperChat messages to a real LLM instead of the fixed fallback error string
- RouterNode print() replaced with logger.info(json.dumps({...})) including correlation_id, enabling end-to-end request tracing via RPCContext
- app/api/routes/chat.py
- 1. [Rule 3 - Blocking] Copilot SDK stub for test isolation
- 1. [Rule 3 - Blocking] Copilot SDK stub for test isolation
- SubAgent.keywords attribute loaded from AGENT.md frontmatter and ROUTING-01 warning for missing 対象外 exclusion, enabling two-stage keyword routing in Plan 13-02
- RouterNode upgraded to 2-stage routing: keyword pre-filter skips LLM for unambiguous single-keyword matches, with stage field in all routing log entries for analysis
- Dynamic MenuScreen fetching apps from GET /api/apps with skeleton/error/empty states; App.tsx activeApp routing; SuperChatApp thread-scoped by appId with client-side agent filtering; Header showing active app name
- One-liner:
- One-liner:
- TypeScript 型・Gem/Canvas API クライアント関数・useGems/useCanvas hooks・GemSelector チップ UI を追加し、createThread/createNewThread が gem_id を POST /api/threads ボディで送信できるようにした
- One-liner:
- One-liner:
- One-liner:
- Status:
- One-liner:
- One-liner:
- One-liner:
- Canvas 専用 Gem 自動登録（SELECT→INSERT 冪等）+ GET /api/canvas/gem エンドポイント + deployed フィルタ付き GET /api/canvas/apps
- 1. [Rule 3 - Blocking] soft-reset で staging に残っていた削除差分が混入
- 1. [Rule 3 - Blocking] Plan 02 の成果物をこのworktreeで先行実装
- マージで失われた Canvas Gem API 実装（`GET /api/canvas/gem` + `deployed` フィルタ + lifespan 自動登録）を復元し、Phase 16 の全 E2E 検証項目を完了した。
- One-liner:
- DebateHandler(TaskHandler) を実装し TASK_HANDLERS['debate'] に登録 — ChatRequest/process_chat/enqueue_job に討論用フィールド 4 つを追加してバックエンド統合完了
- 討論チャット設定パネル (パターン選択・参加者選択・ターン数入力) + チャット画面 (ExtensionBanner 付き) + MenuScreen ナビゲーション統合を React + TypeScript で実装

---

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
