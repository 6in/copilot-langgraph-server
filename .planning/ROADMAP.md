---
gsd_state_version: 1.0
milestone: v5.0
milestone_name: milestone
status: unknown
last_updated: "2026-04-17T14:28:39.965Z"
progress:
  total_phases: 30
  completed_phases: 29
  total_plans: 81
  completed_plans: 85
  percent: 100
---

# Roadmap: Copilot LangGraph Chat

## Milestones

- ✅ **v1.0 MVP** — Phases 1–6 (shipped 2026-04-02) — [Archive](milestones/v1.0-ROADMAP.md)
- ✅ **v2.0 SuperChat** — Phases 7–10 (shipped 2026-04-04)
- ✅ **v3.0 Agent Platform** — Phases 11–17 (shipped 2026-04-07) — [Archive](milestones/v3.0-ROADMAP.md)
- ✅ **v4.0 Canvas API Bridge** — Phases 18–19 (shipped 2026-04-09) — [Archive](milestones/v4.0-ROADMAP.md)
- 📋 **v5.0 Agent Tool Platform** — Phases 20–24 (active)

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

### v5.0 Agent Tool Platform (Phases 20–24)

- [x] **Phase 20: FastMCP Docker サービス基盤** — mcp-server Docker サービスが起動し、worker コンテナから streamable-http で接続でき、スタブツールが LangChain BaseTool として取得できる (completed 2026-04-13)
- [x] **Phase 21: LangGraph bind_tools + ToolNode 統合** — ChatCopilot.bind_tools() 実装、SubAgent ReAct ループ、ToolMessage 履歴記録、最大 10 ステップ自動停止 (completed 2026-04-10)
- [x] **Phase 22: Web 検索ツール（Tavily）** — web_search MCP ツール本番動作、Tavily API 連携、レスポンスサイズ制限 (completed 2026-04-13)
- [x] **Phase 23: DB クエリ + Claude Code 実行ツール** — db_query MCP ツール（SELECT-only ガード）、claude_code MCP ツール（env sanitization + タイムアウト） (completed 2026-04-13)
- [x] **Phase 24: config.yaml ツールルーティング** — mcp_tools.yaml に MCP ツールカタログを宣言、ToolRegistry クラスが worker 起動時に YAML と MCP 実ツールの完全一致を検証 (completed 2026-04-13)
- [ ] **Phase 29: ユーザー選択モデルのエージェントデフォルト優先** — フロントエンド選択モデルを AGENT.md デフォルトより優先し、SubAgent / ToolEnabledSubAgent / CodeActSubAgent / GemSubAgent 全種別で model_override を伝搬

## Phase Details

### Phase 20: FastMCP Docker サービス基盤

**Goal**: エージェントがツールを呼び出すための MCP サービス基盤が稼働し、worker コンテナから接続確認できる
**Depends on**: Phase 19 (v4.0 complete)
**Requirements**: MCP-01, MCP-02
**Success Criteria** (what must be TRUE):

  1. `docker compose up` で mcp-server コンテナが healthy 状態で起動する
  2. worker コンテナから `MultiServerMCPClient.get_tools()` を呼ぶと LangChain BaseTool リストが返る
  3. スタブ `ping` ツールを呼び出すと正常なレスポンスが返り、通信ログに記録される
  4. `/health` エンドポイントが 200 OK を返す（ヘルスチェック用）

**Plans**: 2 plans

- [x] 20-01-PLAN.md — mcp_server/ 独立 uv プロジェクト + FastMCP サーバー + 4 スタブツール + /health + pytest
- [x] 20-02-PLAN.md — docker-compose.yml に mcp-server 追加 + worker 依存配線 + langchain-mcp-adapters + 実機スモーク

### Phase 21: LangGraph bind_tools + ToolNode 統合

**Goal**: SubAgent が bind_tools + ToolNode の ReAct ループでツールを呼び出し、結果が会話履歴に残る
**Depends on**: Phase 20
**Requirements**: TOOL-01, TOOL-02, TOOL-03
**Success Criteria** (what must be TRUE):

  1. `llm.bind_tools([...])` を呼んでも NotImplementedError が発生しない（ChatCopilot.bind_tools() 実装済み）
  2. tool-enabled SubAgent が Web 検索プロンプトに対してツール呼び出しを発火させ、end-to-end で結果を返す
  3. ToolMessage が PostgreSQL チェックポイントに会話履歴として記録され、スレッド再開後も参照できる
  4. tool_calls ループが 10 ステップを超えると自動停止し、部分結果を返す

**Plans**: 3 plans
Plans:

- [x] 21-01-PLAN.md — bind_tools スパイク + BoundChatCopilot 実装
- [x] 21-02-PLAN.md — ToolEnabledSubAgent + SubAgentRegistry 拡張
- [x] 21-03-PLAN.md — Worker MCP Singleton + e2e テスト

### Phase 22: Web 検索ツール（Tavily）

**Goal**: エージェントが Tavily API 経由でリアルタイム情報を取得して回答に反映できる
**Depends on**: Phase 21
**Requirements**: SEARCH-01, SEARCH-02
**Success Criteria** (what must be TRUE):

  1. エージェントに「最新の〇〇を教えて」と聞くと web_search ツールが呼ばれ、Tavily から取得した情報が回答に含まれる
  2. 検索結果のサイズが制限（max_results=3, max_tokens=3000 相当）に収まり、コンテキスト超過エラーが発生しない

**Plans**: 2 plans
Plans:

- [x] 22-01-PLAN.md — web_search ツール実装 + stubs 差し替え + テスト
- [x] 22-02-PLAN.md — UAT ギャップクローズ: ツールプロンプト強化 + general-assistant ガイダンス追記

### Phase 23: DB クエリ + Claude Code 実行ツール

**Goal**: エージェントが PostgreSQL データを安全に参照でき、Claude Code CLI をサブプロセスとして実行できる
**Depends on**: Phase 22
**Requirements**: DB-01, DB-02, CODE-01, CODE-02, CODE-03
**Success Criteria** (what must be TRUE):

  1. エージェントが SELECT クエリを呼び出すと PostgreSQL のデータが返る（is_select_only ガード通過）
  2. INSERT/UPDATE/DELETE クエリはブロックされ、エラーメッセージが返る（セキュリティガード動作確認）
  3. エージェントが claude_code ツールを呼び出すと Claude Code CLI が実行され、出力が返る
  4. CLAUDECODE=1 等の危険な環境変数が子プロセスに継承されない（env sanitization 確認）
  5. 60 秒タイムアウトが機能し、zombie プロセスが残らない

**Plans**: TBD

### Phase 24: config.yaml ツールルーティング

**Goal**: MCP ツールカタログを YAML で宣言し、worker 起動時に MCP サーバーの実ツールリストとの完全一致を検証することで、デプロイ後の無言不整合を防止する
**Depends on**: Phase 23
**Requirements**: MCP-03
**Success Criteria** (what must be TRUE):

  1. `config/mcp_tools.yaml` に 4 ツール（ping/web_search/db_query/claude_code）が宣言されており、ToolRegistry が yaml.safe_load() で読み込み frozenset で管理する
  2. ToolRegistry.validate() が YAML と MCP 実ツールリストの双方向不一致を検出し RuntimeError を raise する
  3. worker startup() が MCP 接続成功後（try/except の外）で validate() を呼び、不一致時に RuntimeError を伝播させて worker 起動を失敗させる
  4. YAML 変更後にコンテナを再起動すると新しいカタログ設定が反映される（ホットリロード不要）
  *(注: エージェント別 allowlist は CONTEXT.md D-02 / Deferred セクションで明示的に defer済み — 将来フェーズで対応)*
**Plans**: 1 plan

- [x] 24-01-PLAN.md — ToolRegistry クラス + mcp_tools.yaml + worker startup バリデーション統合

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
| 20. FastMCP Docker サービス基盤 | v5.0 | 2/2 | Complete   | 2026-04-13 |
| 21. LangGraph bind_tools + ToolNode 統合 | v5.0 | 3/3 | Complete   | 2026-04-10 |
| 22. Web 検索ツール（Tavily） | v5.0 | 2/2 | Complete   | 2026-04-13 |
| 23. DB クエリ + Claude Code 実行ツール | v5.0 | 2/2 | Complete   | 2026-04-13 |
| 24. config.yaml ツールルーティング | v5.0 | 1/1 | Complete   | 2026-04-13 |
| 25. React Router v7 URL ルーティング | v5.0 | 1/1 | Complete   | 2026-04-14 |
| 29. ユーザー選択モデルのエージェントデフォルト優先 | v5.0 | 0/0 | Planned | — |

### Phase 25: React Router v7 による URL ベースルーティング導入

**Goal:** BrowserRouter + Routes でアプリ種別・thread_id を URL に反映し、スレッド共有リンクとブラウザ履歴ナビゲーションを実現する
**Requirements**: URL-01
**Depends on:** Phase 24
**Plans:** 1 plan

Plans:

- [x] 25-01-PLAN.md — BrowserRouter 導入 + Routes 置換 + 各 ChatApp URL 同期 + nginx SPA fallback

### Phase 26: ADR 整理 + patterns.md 作成 + GSD プランニング統合

**Goal:** 30 件の ADR から再利用可能パターンを `.planning/patterns.md` として抽出・カタログ化し、`docs/adr/INDEX.md`（pre-commit hook 自動生成）と合わせて CLAUDE.md 経由で GSD の discuss/plan フェーズが canonical_refs 経由で自動参照できる状態を作る。ADR 本文の変更・Status 付与・欠番補完は対象外（D-03/D-04/D-05）。
**Requirements**: none (整備フェーズのため REQ-ID なし)
**Depends on:** Phase 25
**Plans:** 3/3 plans complete

Plans:

- [x] 26-01-PLAN.md — adr-categories.yaml + generate_adr_index.py + pre-commit hook + pytest
- [x] 26-02-PLAN.md — docs/adr/INDEX.md 生成 + .planning/patterns.md 新規作成
- [x] 26-03-PLAN.md — CLAUDE.md 運用ルール追記 + /create-adr リマインダ + ROADMAP 更新

### Phase 27: AskUserQuestion の実装 — AI エージェントがユーザーに選択肢・確認を提示する対話的インタラクションパターンをチャット UI + バックエンドに組み込む

**Goal:** AI エージェントが `<ask_user_question>` タグで構造化質問（single/multi/text）をユーザーに提示し、QuestionPanel UI で回答を受け取り、テキスト化して既存チャットフローに送信する対話パターンを全アプリで動作させる
**Requirements**: AUQ-01, AUQ-02, AUQ-03, AUQ-04, AUQ-05
**Depends on:** Phase 26
**Plans:** 2/2 plans complete

Plans:

- [x] 27-01-PLAN.md — AUQ_PROTOCOL system prompt 注入（両経路）+ AUQ 型定義 + QuestionPanel.tsx 作成
- [x] 27-02-PLAN.md — useChat AUQ 検出 + MessageArea 入力置換 + 全 5 アプリ伝播 + ブラウザ確認

### Phase 28: CodeAct パターンの実装 — LLM がコードを生成・サンドボックス実行し結果を観察する推論ループ

**Goal:** execute_python MCP ツール（AST インポートホワイトリスト + メモリ制限 + タイムアウト付きサンドボックス）と CodeAct 専用エージェント（recursion_limit: 12）を実装し、LLM が Python コードを生成・実行・結果観察する推論ループを既存 ReAct 基盤上で動作させる
**Requirements**: EXEC-01, EXEC-02, EXEC-03, EXEC-04, EXEC-05, EXEC-06, EXEC-07
**Depends on:** Phase 27
**Plans:** 2 plans

Plans:

- [ ] 28-01-PLAN.md — execute_python MCP ツール実装 + sandbox_allowlist.yaml + サーバー登録 + テスト
- [ ] 28-02-PLAN.md — CodeAct エージェント定義 + ToolEnabledSubAgent recursion_limit 拡張 + テスト

### Phase 29: ユーザー選択モデルのエージェントデフォルト優先

**Goal:** フロントエンドで選択したモデルが SuperChat モードのエージェントデフォルト（AGENT.md `model` フィールド）より優先され、ユーザーの意図通りのモデルで推論が実行される
**Requirements**: none (UX 改善フェーズのため REQ-ID なし)
**Depends on:** Phase 28
**Success Criteria** (what must be TRUE):

  1. SuperChat で gpt-4.1 を選択した状態でメッセージを送ると、AGENT.md に claude-sonnet-4-6 と書かれたエージェントでも gpt-4.1 で推論される
  2. モデル未選択（デフォルト）の場合は従来通り AGENT.md の `model` フィールドが使われる
  3. SubAgent / ToolEnabledSubAgent / CodeActSubAgent / GemSubAgent の全エージェント種別で model_override が機能する
  4. 通常 Chat モードの動作に影響がない（既存の model パラメータがそのまま使われる）

**Plans**: TBD
