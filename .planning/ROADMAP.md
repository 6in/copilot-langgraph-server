# Roadmap: Copilot LangGraph Chat

## Milestones

- ✅ **v1.0 MVP** — Phases 1–6 (shipped 2026-04-02) — [Archive](milestones/v1.0-ROADMAP.md)
- ✅ **v2.0 SuperChat** — Phases 7–10 (shipped 2026-04-04)
- ✅ **v3.0 Agent Platform** — Phases 11–17 (shipped 2026-04-07) — [Archive](milestones/v3.0-ROADMAP.md)
- 🚧 **v4.0 Canvas API Bridge** — Phases 18+

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
<summary>✅ v2.0 SuperChat (Phases 7–10) — SHIPPED 2026-04-04</summary>

- [x] **Phase 7: React Chat UI** — chatscope + Vite + Bun served at /app, full feature parity with Vanilla JS (completed 2026-04-02)
- [x] **Phase 8: Super Agent Sample** — OrchestratorGraph + SubAgent architecture in super-agent-sample/, live smoke test verified (completed 2026-04-03)
- [x] **Phase 9: SuperChat App Integration** — OrchestratorGraph integrated into app/, simple/super mode toggle in React UI (completed 2026-04-04)
- [x] **Phase 10: SuperChat Thread Persistence** — applications/threads schema, app-isolated thread listing, OrchestratorGraph checkpointer, general-assistant agent (completed 2026-04-04)

</details>

<details>
<summary>✅ v3.0 Agent Platform (Phases 11–17) — SHIPPED 2026-04-07</summary>

- [x] **Phase 11: RPCContext Integration** — RPCContext unified into AgentState, all nodes access context via state["context"], correlation_id flows through routing and audit logs (completed 2026-04-04)
- [x] **Phase 12: Hybrid SubAgentRegistry + Tool Quality** — Folder-type and code-type agent auto-loading, HEALTHY/DEGRADED/FAILED status management, INPUT_SCHEMA standard + CI lint (completed 2026-04-04)
- [x] **Phase 13: Scalable Routing** — 2-stage router (keyword pre-filter + LLM), AGENT.md description convention enforced, structured routing logs with correlation_id (completed 2026-04-04)
- [x] **Phase 14: Application Packages + Menu** — App definition files declare agent subsets, menu screen launches app-specific chat, agents shared across apps (completed 2026-04-05)
- [x] **Phase 15: Gem + Canvas** — Gem（AI ペルソナ）・Canvas（HTML 生成・デプロイ）完全実装（gems/canvas_apps テーブル、CRUD API、CanvasPane UI）(completed 2026-04-05)
- [x] **Phase 15.1: Gem UX 強化** — GemsScreen ハブ・GemChatApp・description/knowledge フィールド追加 (completed 2026-04-06)
- [x] **Phase 16: Canvas App** — CanvasChatApp（分割レイアウト）・CanvasScreen（一覧）・Canvas 専用グラフ (completed 2026-04-07)
- [x] **Phase 17: DebateChatApp** — マルチエージェント討論チャット、ターン制リアルタイムストリーミング (completed 2026-04-07)

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
| 14. Application Packages + Menu | v3.0 | 2/2 | Complete | 2026-04-05 |
| 15. Gem + Canvas | v3.0 | 4/4 | Complete | 2026-04-05 |
| 15.1. Gem UX 強化 | v3.0 | 3/3 | Complete | 2026-04-06 |
| 16. Canvas App | v3.0 | 4/4 | Complete | 2026-04-07 |
| 17. DebateChatApp | v3.0 | 3/3 | Complete | 2026-04-07 |
| 18. Canvas iframe postMessage JSON-RPC API ブリッジ実装 | v4.0 | 3/3 | Complete   | 2026-04-08 |

### Phase 18: Canvas iframe postMessage JSON-RPC API ブリッジ実装

**Goal:** iframe 内 Canvas アプリの JS から postMessage 経由で DB クエリ（SELECT）と AI（Copilot ワンショット）を呼び出せる JSON-RPC ブリッジを実装する
**Requirements**: [D-01, D-02, D-03, D-04, D-05, D-06, D-07, D-08, D-09, D-10, D-11, D-12, D-13, D-14, D-15, D-16, D-17, D-18, D-19, D-20]
**Depends on:** Phase 17
**Plans:** 3/3 plans complete

Plans:
- [x] 18-01-PLAN.md — IframeRpcHandler + POST /api/iframe-rpc エンドポイント + テスト
- [x] 18-02-PLAN.md — arq ワーカー拡張 + DB プール管理 + config 設定
- [x] 18-03-PLAN.md — CanvasPane postMessage リスナー + iframe JSON-RPC ブリッジ

### Phase 19: Canvas アプリのデプロイ＆ホスティング機能（/apps/{app-id}/ ルーティング、iframe ホスティングシェル、Phase 18 RPC ブリッジ流用）

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 18
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd-plan-phase 19 to break down)
