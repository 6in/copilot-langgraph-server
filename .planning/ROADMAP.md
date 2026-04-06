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
- [x] **Phase 13: Scalable Routing** — 2-stage router (keyword pre-filter + LLM), AGENT.md description convention enforced, structured routing logs with correlation_id (completed 2026-04-04)
- [x] **Phase 14: Application Packages + Menu** — App definition files declare agent subsets, menu screen launches app-specific chat, agents shared across apps

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
| 13. Scalable Routing | v3.0 | 2/2 | Complete    | 2026-04-04 |
| 14. Application Packages + Menu | v3.0 | 2/2 | Complete | 2026-04-06 |
| 15. Gem + Canvas | — | 4/4 | Complete   | 2026-04-05 |
| 15.1. Gem UX 強化 | — | 3/3 | Complete | 2026-04-06 |
| 16. SuperChat × Gem 招待 | — | 1/3 | In Progress|  |

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
**Plans:** 2/2 plans complete

Plans:
- [x] 13-01-PLAN.md -- SubAgent keywords + ROUTING-01 warning (ROUTING-01, ROUTING-02)
- [x] 13-02-PLAN.md -- 2-stage RouterNode + stage log field (ROUTING-02, ROUTING-03)

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
- [ ] 14-01-PLAN.md — Backend: AppRegistry + GET /api/apps + chat.py app_id + OrchestratorHandler update (APP-01, APP-03, APP-04)
- [ ] 14-02-PLAN.md — Frontend: Dynamic MenuScreen + App.tsx activeApp + SuperChatApp props + Header app name (APP-02, APP-03, APP-04)

### Phase 15: Gem + Canvas 機能実装
**Goal:** Gem（AI ペルソナ）と Canvas（シングルファイル HTML 生成・デプロイ）機能を実装する。gems / canvas_apps テーブルを追加し、Gem CRUD API / Canvas Apps API / Worker HTML 抽出を実装し、React UI に GemSelector チップストリップと CanvasPane エディタ/プレビュー/デプロイ UI を追加する
**Depends on:** Phase 14
**Requirements:** GEM-01, GEM-02, GEM-03, CANVAS-01, CANVAS-02, CANVAS-03, CANVAS-04, FE-01, FE-02, FE-03, FE-04
**Success Criteria** (what must be TRUE):
  1. ユーザーが Gem（AI ペルソナ）を作成・一覧・更新・削除でき、他ユーザーの Gem にはアクセスできない
  2. Canvas Gem を選択してチャットを開始すると、AI がシングルファイル HTML を生成し、canvas_apps テーブルに自動保存される
  3. Canvas ペインでエディタ/プレビューを切り替えて HTML を編集・保存でき、Deploy ボタンで /apps/{app_id}/ に公開できる
  4. HTML アップロードで外部作成のアプリを canvas_apps に登録できる
**UI hint**: yes
**Plans:** 4/4 plans complete

Plans:
- [x] 15-01-PLAN.md — Backend DB + Pydantic models + Gem CRUD API (GEM-01, GEM-02, GEM-03, CANVAS-01)
- [x] 15-02-PLAN.md — Backend Canvas API + Worker extension + Deploy (CANVAS-02, CANVAS-03, CANVAS-04)
- [x] 15-03-PLAN.md — Frontend types + hooks + GemSelector (FE-01, FE-02)
- [x] 15-04-PLAN.md — Frontend CanvasPane + ChatApp integration + human verification (FE-03, FE-04)

### Phase 15.1: Gem UX 強化 — GemsScreen ハブ・GemChatApp・ナビゲーション改善・description/knowledge フィールド追加

**Goal:** Gem 機能を「アプリ」として再設計する。MenuScreen に「Gems」アプリカードを固定追加し、GemsScreen（Gem CRUD 管理ハブ）と GemChatApp（Gem 専用チャット）を新規作成する。既存 ChatApp / SuperChatApp から GemSelector を撤去する。さらに Gem モデルに description（カード表示用説明文）と knowledge（チャット時にシステムプロンプトへ結合するナレッジ）フィールドを追加する。

**Requirements:** D-01, D-02, D-03, D-04, D-05, D-06, D-07, D-08, D-09, D-10, D-11, D-12, D-13, D-14, D-15, D-16, D-17, D-18, D-19, D-20, D-21, Todo-6, Todo-7, Todo-8

**Depends on:** Phase 15

**Note:** D-01〜D-21（オリジナル Phase 15.1 スコープ）はコードベース上すでに実装済み。このフェーズのプランは Todo 6〜8（description/knowledge フィールド）の追加実装にフォーカスする。

**Plans:** 3 plans

Plans:
- [ ] 15.1-01-PLAN.md — バックエンド: description/knowledge カラム追加（DB ALTER TABLE + API models + routes + LangGraph handler）(Todo-6, Todo-7)
- [ ] 15.1-02-PLAN.md — フロントエンド: types.ts 更新 + GemsScreen description/knowledge フォーム対応・カード表示切り替え (Todo-6, Todo-7)
- [ ] 15.1-03-PLAN.md — E2E 確認チェックポイント: 全画面フロー・description/knowledge チャット動作確認 (D-01〜D-21, Todo-6, Todo-7, Todo-8)

### Phase 16: SuperChat × Gem 招待 — Gem をプロンプトエージェントとして OrchestratorGraph に統合

**Goal:** SuperChat のオーケストレーターが、`./agents/`（ツールエージェント）と Gem（プロンプトエージェント）の両方をルーティング候補として扱えるようにする。ユーザーは SuperChat チャット開始時に招待する Gem を選択でき、OrchestratorGraph が動的に GemSubAgent ラッパーを生成して通常の SubAgent と同じインターフェースで処理する。

**Depends on:** Phase 15.1, Phase 14

**背景・設計方針:**
- `./agents/` SubAgent: Python コード + ツール呼び出し可能（検索・計算・外部 API 連携）
- Gem: `system_prompt` + `knowledge` のみ（ノーコードで作成、ペルソナ・専門知識の切り替えに特化）
- 両者を同一ルーターで扱うため、Gem を「動的生成される軽量 SubAgent」としてラップする

**Requirements:**
- GEM-SUB-01: `GemSubAgent` クラス — Gem の `system_prompt`/`knowledge` を受け取り、BaseChatModel を直接呼び出す SubAgent 互換ラッパー
- GEM-SUB-02: OrchestratorHandler 拡張 — `gem_ids`（招待 Gem リスト）をジョブパラメータで受け取り、GemSubAgent を既存 SubAgent と混在させてルーターに渡す
- GEM-SUB-03: API 拡張 — `POST /api/chat` に `gem_ids` 独立フィールドを追加（型安全、後方互換）
- GEM-SUB-04: フロントエンド — SuperChat に GemSelector コンポーネント + useGems フックを追加

**Success Criteria** (what must be TRUE):
1. ユーザーが SuperChat で「コードレビュー Bot」Gem と `code-reviewer` SubAgent を同時に招待し、それぞれが独自の回答を返してオーケストレーターが統合する
2. Gem のみ招待した場合（`./agents/` エージェントなし）でも SuperChat が正常に動作し、Gem の `system_prompt` + `knowledge` でペルソナが切り替わる
3. 招待なしの通常 SuperChat は既存動作のまま変わらない（後方互換）
4. 公開 Gem（`is_public = true`）は全ユーザーの SuperChat 招待候補に自動的に表示される

**Plans:** 1/3 plans executed

Plans:
- [x] 16-01-PLAN.md — バックエンド: GemSubAgent クラス実装 + OrchestratorHandler gem_ids 統合 (GEM-SUB-01, GEM-SUB-02)
- [ ] 16-02-PLAN.md — API + フロントエンド: ChatRequest gem_ids + useGems + GemSelector + SuperChatApp + useChat (GEM-SUB-03, GEM-SUB-04)
- [ ] 16-03-PLAN.md — テスト: GemSubAgent ユニットテスト + OrchestratorHandler gem_ids 統合テスト (GEM-SUB-01〜04)
