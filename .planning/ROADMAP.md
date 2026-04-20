---
gsd_state_version: 1.0
milestone: v5.0
milestone_name: Agent Tool Platform
status: shipped
last_updated: "2026-04-21T00:00:00.000Z"
progress:
  total_phases: 32
  completed_phases: 32
  total_plans: 91
  completed_plans: 91
  percent: 100
---

# Roadmap: Copilot LangGraph Chat

## Milestones

- ✅ **v1.0 MVP** — Phases 1–6 (shipped 2026-04-02) — [Archive](milestones/v1.0-ROADMAP.md)
- ✅ **v2.0 SuperChat** — Phases 7–10 (shipped 2026-04-04)
- ✅ **v3.0 Agent Platform** — Phases 11–17 (shipped 2026-04-07) — [Archive](milestones/v3.0-ROADMAP.md)
- ✅ **v4.0 Canvas API Bridge** — Phases 18–19 (shipped 2026-04-09) — [Archive](milestones/v4.0-ROADMAP.md)
- ✅ **v5.0 Agent Tool Platform** — Phases 20–31 + 31.1 (shipped 2026-04-20) — [Archive](milestones/v5.0-ROADMAP.md)
- 📋 **v6.0** — (planning — run `/gsd-new-milestone`)

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

<details>
<summary>✅ v4.0 Canvas API Bridge (Phases 18–19) — SHIPPED 2026-04-09</summary>

- [x] **Phase 18: Canvas iframe postMessage JSON-RPC API ブリッジ実装** — iframe 内 JS から DB クエリ・AI 呼び出しを postMessage 経由で実行できる JSON-RPC ブリッジ（IframeRpcHandler、arq worker 拡張、psycopg3 DB プール）(completed 2026-04-08)
- [x] **Phase 19: Canvas アプリのデプロイ＆ホスティング機能** — GET /apps/{app_id} 動的ホスティングシェル、parent-bridge.js 共通化、JWT Cookie 認証 (completed 2026-04-09)

See [v4.0-ROADMAP.md](milestones/v4.0-ROADMAP.md) for full phase details.

</details>

<details>
<summary>✅ v5.0 Agent Tool Platform (Phases 20–31 + 31.1) — SHIPPED 2026-04-20</summary>

- [x] **Phase 20: FastMCP Docker サービス基盤** — mcp-server healthy 起動、worker から streamable-http 接続、LangChain BaseTool 取得 (completed 2026-04-13)
- [x] **Phase 21: LangGraph bind_tools + ToolNode 統合** — ChatCopilot.bind_tools() プロンプト方式、ToolEnabledSubAgent mini ReAct グラフ、10 ステップ自動停止 (completed 2026-04-10)
- [x] **Phase 22: Web 検索ツール（Tavily）** — web_search MCP ツール、レスポンスサイズ制限 (completed 2026-04-13)
- [x] **Phase 23: DB クエリ + Claude Code 実行ツール** — db_query (SELECT-only) + claude_code (env sanitization + 60s timeout) (completed 2026-04-13)
- [x] **Phase 24: config.yaml ツールルーティング** — mcp_tools.yaml + ToolRegistry 双方向検証 (completed 2026-04-13)
- [x] **Phase 25: React Router v7 URL ルーティング** — BrowserRouter + アプリ種別/thread_id URL 化 (completed 2026-04-14)
- [x] **Phase 26: ADR 整理 + patterns.md + GSD 統合** — docs/adr/INDEX.md 自動生成 + patterns.md + canonical_refs 運用 (completed 2026-04-07)
- [x] **Phase 27: AskUserQuestion AI-UI 対話** — 構造化質問 + QuestionPanel + 全 5 アプリ伝播 (completed 2026-04-17)
- [x] **Phase 28: CodeAct パターン** — execute_python MCP ツール (AST allowlist + sandbox) + CodeAct SubAgent (completed 2026-04-17)
- [x] **Phase 29: ユーザー選択モデル伝播** — SuperChat 選択モデルを AGENT.md デフォルトより優先、4 種 SubAgent model_override (completed 2026-04-18)
- [x] **Phase 30: MCP ツールカタログ single-source-of-truth** — 自動生成スクリプト + pre-commit drift 検知 (completed 2026-04-18)
- [x] **Phase 31: Observability 基盤** — stdout JSONL 1 行 1 span、3 経路統合、scripts/trace_query.py CLI (completed 2026-04-20)
- [x] **Phase 31.1: v5.0 milestone cleanup** — 9 phase VALIDATION.md backfill + Phase 30 VALIDATION.md 遡及作成 (completed 2026-04-20)

See [v5.0-ROADMAP.md](milestones/v5.0-ROADMAP.md) for full phase details.

</details>

### 📋 v6.0 (Planning)

次期 milestone は `/gsd-new-milestone` で計画。現時点の候補 (PROJECT.md Active v6.0 セクション):

- エージェント別 ツール allowlist (Phase 24 D-02 で defer)
- MCP サーバーゲートウェイ機能 (別 MCP サーバーのツール中継)
- チャット入力ファイルアップロード + worker 生成ファイルダウンロード
- claude_code MCP ツール認証バインド (spirit-room 方式)
- Mermaid View ハング調査
- AI 操作しやすい UI (data-ai-role 属性)
- インストール済み code review skill の運用フロー組込み

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
| 18. Canvas iframe postMessage JSON-RPC API ブリッジ実装 | v4.0 | 3/3 | Complete | 2026-04-08 |
| 19. Canvas アプリのデプロイ＆ホスティング機能 | v4.0 | 2/2 | Complete | 2026-04-09 |
| 20. FastMCP Docker サービス基盤 | v5.0 | 2/2 | Complete | 2026-04-13 |
| 21. LangGraph bind_tools + ToolNode 統合 | v5.0 | 3/3 | Complete | 2026-04-10 |
| 22. Web 検索ツール（Tavily） | v5.0 | 2/2 | Complete | 2026-04-13 |
| 23. DB クエリ + Claude Code 実行ツール | v5.0 | 2/2 | Complete | 2026-04-13 |
| 24. config.yaml ツールルーティング | v5.0 | 1/1 | Complete | 2026-04-13 |
| 25. React Router v7 URL ルーティング | v5.0 | 1/1 | Complete | 2026-04-14 |
| 26. ADR 整理 + patterns.md + GSD 統合 | v5.0 | 3/3 | Complete | 2026-04-07 |
| 27. AskUserQuestion AI-UI 対話 | v5.0 | 2/2 | Complete | 2026-04-17 |
| 28. CodeAct パターン | v5.0 | 2/2 | Complete | 2026-04-17 |
| 29. ユーザー選択モデル伝播 | v5.0 | 1/1 | Complete | 2026-04-18 |
| 30. MCP ツールカタログ single-source-of-truth | v5.0 | 6/6 | Complete | 2026-04-18 |
| 31. Observability 基盤 | v5.0 | 8/8 | Complete | 2026-04-20 |
| 31.1. v5.0 milestone cleanup | v5.0 | 2/2 | Complete | 2026-04-20 |
