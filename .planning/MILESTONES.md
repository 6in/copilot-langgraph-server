# Milestones

## v5.0 Agent Tool Platform (Shipped: 2026-04-20)

**Phases completed:** 13 phases (20–31 + 31.1), 35 plans
**Timeline:** 2026-04-10 → 2026-04-20 (10 days)
**Commits:** 118 / Files changed: 408 (+182,470 / -9,629 incl. lockfiles)
**LOC (cumulative):** 7,040 Python / 8,460 TypeScript
**ADRs added:** 27 (ADR-0020 through ADR-0047)

**Delivered:** MCP ツールエコシステム (6 tools) + LangGraph bind_tools 統合 + CodeAct/AskUserQuestion の高度対話パターン + stdout JSONL observability 基盤を備えたエージェントプラットフォームを完成。`config/mcp_tools.yaml` single source of truth から Python helper / JS カタログ / docs を決定論的に自動生成し、pre-commit hook で drift 検知まで統合。

**Key accomplishments:**

- **MCP ツールエコシステム確立** — FastMCP Docker 基盤 + 6 ツール (ping / web_search / db_query / claude_code / execute_python / get_current_datetime)、`config/mcp_tools.yaml` single source of truth + `scripts/generate_mcp_artifacts.py` 決定論的自動生成 + pre-commit drift 検知 (Phase 20/23/24/30、ADR-0020/0023/0044)
- **LangGraph ↔ Copilot を bind_tools + ReAct で統合** — Copilot SDK native tool-calling 未対応のためプロンプト方式 + JSON 解析で `ChatCopilot.bind_tools()` 実装、ToolEnabledSubAgent mini ReAct グラフ、Tavily Web 検索で e2e 動作 (Phase 21/22、ADR-0021/0022)
- **CodeAct + AskUserQuestion の高度対話パターン** — LLM が Python コードを生成 → AST allowlist + sandbox 実行 → 結果観察する CodeAct ループ、AI が構造化選択肢を提示する AUQ プロトコルを 5 アプリ全てに展開 (Phase 27/28、ADR-0039/0041)
- **observability 基盤 — 新規 infra ゼロで実行可視化** — stdout JSONL 1 行 1 span (OTEL span-like、10 フィールド)、`trace_id = RPCContext.correlation_id`、3 経路 (ToolEnabled/CodeAct/iframe RPC) 統合、`scripts/trace_query.py` CLI + jq レシピで運用完結。既存 `audit_log` テーブル退役 (Phase 31、ADR-0045/0046)
- **UX 底上げ + 設計知識の再利用可能化** — React Router v7 URL ルーティング、ユーザー選択モデル伝播 (4 種 SubAgent 全て)、30+ ADR を `docs/adr/INDEX.md` (pre-commit 自動生成) と `.planning/patterns.md` に分離して GSD plan-phase が canonical_refs で自動参照 (Phase 25/26/29、ADR-0042)
- **milestone close 帳簿整合** — Phase 31.1 で 9 phase の VALIDATION.md backfill + Phase 30 VALIDATION.md 遡及作成、帳簿 100% 整合で archive。Decimal phase を milestone cleanup に流用する運用パターンを確立 (Phase 31.1、ADR-0047)

**Known deferred items at close:** 64 (historical drift across v1.0–v5.0、STATE.md `## Deferred Items` 参照) — machine-generated audit artifacts と次期 milestone 候補の混在、functional には影響なし

---

## v4.0 Canvas API Bridge (Shipped: 2026-04-09)

**Phases completed:** 2 phases, 5 plans, 7 tasks
**Timeline:** 2026-04-08 → 2026-04-09 (2 days)

**Delivered:** Canvas iframe から DB クエリ・AI 呼び出しを postMessage JSON-RPC で安全に実行できるブリッジと、Canvas アプリを `/apps/{app_id}` URL でスタンドアロンホスティングする仕組みを実装。

**Key accomplishments:**

- SELECT-only SQL ガード（コメント除去 + トークン検証）+ ChatCopilot ワンショット AI 呼び出しを処理する `IframeRpcHandler`、JWT 保護の `POST /api/iframe-rpc` エンドポイント実装
- arq worker に `iframe_app_api` タスクタイプを登録、`psycopg_pool.AsyncConnectionPool` による DB プールのライフサイクル管理、`config/db_pools.yaml` 設定ファイル整備
- `CanvasPane.tsx` に postMessage リスナーを実装し、`POST /api/iframe-rpc` → SSE ポーリング → iframe 返信のフロントエンドブリッジを完成
- `parent-bridge.js` 共通スクリプトを新設し、Shell HTML と CanvasPane.tsx の両方が同一リレーロジックを共有する設計に統一
- `GET /apps/{app_id}` 動的ホスティングシェル実装（srcdoc エスケープ、sandbox 制限、FastAPI ルート優先順位対応）、SSE URL バグ修正・JWT Cookie 認証復活を含む動作確認チェックポイント通過

---

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
