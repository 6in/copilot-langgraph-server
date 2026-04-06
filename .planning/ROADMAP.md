# Roadmap: Copilot LangGraph Chat

## Milestones

- ✅ **v1.0 MVP** — Phases 1–6 (shipped 2026-04-02) — [Archive](milestones/v1.0-ROADMAP.md)
- ✅ **v2.0** — Phases 7–10 (shipped 2026-04-04)
- ✅ **v3.0 Agent Platform** — Phases 11–16 (shipped 2026-04-06) — [Archive](milestones/v3.0-ROADMAP.md)
- 📋 **v4.0** — Phase 17+ (planned)

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

<details>
<summary>✅ v3.0 Agent Platform (Phases 11–16) — SHIPPED 2026-04-06</summary>

- [x] **Phase 11: RPCContext Integration** — RPCContext unified into AgentState, correlation_id flows through routing and audit logs (completed 2026-04-04)
- [x] **Phase 12: Hybrid SubAgentRegistry + Tool Quality** — Folder-type and code-type agent auto-loading, HEALTHY/DEGRADED/FAILED status, INPUT_SCHEMA + CI lint (completed 2026-04-04)
- [x] **Phase 13: Scalable Routing** — 2-stage router (keyword pre-filter + LLM), structured routing logs with correlation_id (completed 2026-04-04)
- [x] **Phase 14: Application Packages + Menu** — APP.md defines agent subsets, AppRegistry + GET /api/apps, dynamic MenuScreen, thread scoped to appId (completed 2026-04-06)
- [x] **Phase 15: Gem + Canvas** — gems/canvas_apps tables, Gem CRUD API, Canvas Worker HTML extraction + deploy, GemSelector + CanvasPane UI (completed 2026-04-05)
- [x] **Phase 15.1: Gem UX 強化** — description/knowledge fields, GemsScreen hub, GemChatApp, Gems menu card (completed 2026-04-06)
- [x] **Phase 16: SuperChat × Gem 招待** — GemSubAgent wraps Gem as SubAgent-compatible, OrchestratorHandler gem_ids integration, UAT PASSED (completed 2026-04-06)

See [v3.0-ROADMAP.md](milestones/v3.0-ROADMAP.md) for full phase details.

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
| 8. Super Agent Sample | v2.0 | 3/3 | Complete | 2026-04-03 |
| 9. SuperChat メインアプリ統合 | v2.0 | 4/4 | Complete | 2026-04-04 |
| 10. SuperChat 履歴保存とモード別スレッド分離 | v2.0 | 6/6 | Complete | 2026-04-04 |
| 11. RPCContext Integration | v3.0 | 4/4 | Complete | 2026-04-04 |
| 12. Hybrid SubAgentRegistry + Tool Quality | v3.0 | 3/3 | Complete | 2026-04-04 |
| 13. Scalable Routing | v3.0 | 2/2 | Complete | 2026-04-04 |
| 14. Application Packages + Menu | v3.0 | 2/2 | Complete | 2026-04-06 |
| 15. Gem + Canvas | v3.0 | 4/4 | Complete | 2026-04-05 |
| 15.1. Gem UX 強化 | v3.0 | 3/3 | Complete | 2026-04-06 |
| 16. SuperChat × Gem 招待 | v3.0 | 3/3 | Complete | 2026-04-06 |
| 17. マルチエージェント討論チャット | v4.0 | 0/3 | In progress | — |

## Phase Details

### Phase 17: マルチエージェント討論チャット — ターン制マルチエージェント会話プラットフォーム

**Goal:** 複数の Gem / SubAgent をターン制で会話させる新アプリ「討論チャット」を実装する。ユーザーが会話パターン（討論・パネル・チェーン）と参加エージェントを選択し、お題を投稿すると、指定ターン数でエージェント同士が順番に発言する。討論終了後にユーザーが延長を承認できる。

**Depends on:** Phase 16

**Requirements:**
- DEBATE-01: ターン制マルチエージェントグラフ — 参加エージェントリスト × ターン数で構成される LangGraph グラフ。各ノードが前のメッセージ全体を見て発言する
- DEBATE-02: 会話パターン選択 — 討論（A→B→A→B→...→統合）、パネル（並列→統合）、チェーン（A→B→C）の 3 パターン
- DEBATE-03: ターン数制御 — 指定ターン数で自動終了。終了後に人間が延長承認できる
- DEBATE-04: DebateChatApp フロントエンド — パターン選択 + 参加エージェント選択 + チャット UI。各エージェントの発言が順に表示される
- DEBATE-05: 新 task_type "debate" + DebateHandler — arq worker に登録する新ハンドラー

**Success Criteria** (what must be TRUE):
1. ユーザーが討論パターンを選択し、2 つ以上の Gem/SubAgent を選んでお題を投げると、指定ターン数分エージェントが順番に発言する
2. ターン終了後に「延長しますか？」という確認が表示され、ユーザーが承認すると追加ターンが実行される
3. 各エージェントの発言がチャット UI に「エージェント名: 発言内容」として順次表示される
4. Gem のみ、SubAgent のみ、混在のいずれの組み合わせでも動作する

**UI hint**: yes

**Plans:** 3 plans

Plans:
- [ ] 17-01-PLAN.md — DebateGraph コア TDD (DebateState + build_debate_graph + 3 パターン + 再エンキュー)
- [ ] 17-02-PLAN.md — DebateHandler + API 拡張 (ChatRequest/process_chat/enqueue_job)
- [ ] 17-03-PLAN.md — DebateChatApp フロントエンド (設定パネル + チャット + 延長 + MenuScreen 統合)
