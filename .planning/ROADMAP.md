---
gsd_state_version: 1.0
milestone: v6.0
milestone_name: UI/AI Experience
status: active
last_updated: "2026-05-13T00:00:00.000Z"
progress:
  total_phases: 40
  completed_phases: 38
  total_plans: 134
  completed_plans: 134
  percent: 95
---

# Roadmap: Copilot LangGraph Chat

## Milestones

- ✅ **v1.0 MVP** — Phases 1–6 (shipped 2026-04-02) — [Archive](milestones/v1.0-ROADMAP.md)
- ✅ **v2.0 SuperChat** — Phases 7–10 (shipped 2026-04-04)
- ✅ **v3.0 Agent Platform** — Phases 11–17 (shipped 2026-04-07) — [Archive](milestones/v3.0-ROADMAP.md)
- ✅ **v4.0 Canvas API Bridge** — Phases 18–19 (shipped 2026-04-09) — [Archive](milestones/v4.0-ROADMAP.md)
- ✅ **v5.0 Agent Tool Platform** — Phases 20–31 + 31.1 (shipped 2026-04-20) — [Archive](milestones/v5.0-ROADMAP.md)
- 🚧 **v6.0 UI/AI Experience** — Phases 32–39 (in progress)

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

### 🚧 v6.0 UI/AI Experience (Phases 32–39)

**Milestone Goal:** AI からもユーザーからも扱いやすい UI 基盤を整備する — AI 操作可能性と人間 UX の両輪を強化し、ファイル I/O とバグ残債を仕上げる

- [ ] **Phase 32: AI-UI 操作基盤 (data-ai-role + ページ探索 API)** — 主要 UI コンポーネントへ data-ai-role 属性を付与し、現在表示中のページ構造を JSON で返す探索 API を提供する
- [ ] **Phase 33: AI-UI 操作 MCP ツール + trace/人間承認** — ui_click / ui_read / ui_fill / ui_navigate を MCP ツール化し、observability trace 記録と破壊的操作の確認ダイアログ承認をセットで提供する
- [ ] **Phase 34: チャット操作性 + スレッド/アプリ探索性** — メッセージコピー・再送信・キャンセル・ストリーミング、スレッド検索・タイトル自動生成・フィルタなど日常操作の摩擦を低減する
- [x] **Phase 35: ダッシュボード化 + レスポンシブ/デザイン統一** — メニュー画面のダッシュボード再設計とモバイル幅・ダークモード・クロスブラウザ対応の統一 (completed 2026-04-23)
- [x] **Phase 36: ファイル入力 — text/code + image multimodal** — チャット添付からテキスト/コード系ファイル + 画像 (multimodal) を LLM コンテキストへ流し込む基盤 (completed 2026-05-11)
- [x] **Phase 37: ファイル入力 — PDF/Office 抽出 + MCP ツール参照** — PDF / Office ファイルのテキスト抽出と、添付ファイルを execute_python / claude_code 等の MCP ツールから参照可能にする (completed 2026-04-22)
- [x] **Phase 38: ファイル出力 — worker 生成 DL + プレビュー + ユーザー別保持** — execute_python / claude_code 生成物の DL・チャット内プレビュー・ユーザー別ストレージ保持を一括実装 (completed 2026-05-12)
- [x] **Phase 39: UI バグ潰し + Polish 枠** — Mermaid hang・CollapsibleCodeBlock バルーン・test_sse hang/JobStore dead code を整理し、開発中に発覚した小バグをまとめて潰す (completed 2026-05-13)

## Phase Details

### Phase 32: AI-UI 操作基盤 (data-ai-role + ページ探索 API)
**Goal**: AI がチャットから自分の UI を操作するための土台 — 「どこに何があるか」をセマンティックに表現し、機械可読に取得できる
**Depends on**: Phase 31 (Observability 基盤 — trace_id を後続 phase の操作ログに流用)
**Requirements**: AIUI-01, AIUI-03
**Success Criteria** (what must be TRUE):
  1. ユーザーが ThreadSidebar / MessageArea / MenuScreen / GemSelector / Header 等の主要コンポーネントを開発者ツールで `data-ai-role="..."` セマンティック属性で識別できる
  2. AI または開発者が「現在表示中のページにどんな data-ai-role 要素があるか」を JSON で取得できる API（例: `GET /api/ui/inspect` または iframe RPC `ui_inspect`）が動作する
  3. 探索 API が要素の role 名・親子関係・可視性・テキストラベルを構造化して返し、後続 MCP ツールが targeting に使える形式になっている
  4. data-ai-role 付与によるレンダリング負荷増・DOM 肥大が体感できないレベルに抑えられている (200名規模で UX 劣化なし)
**Plans:** 9 plans
Plans:
- [x] 39-01-PLAN.md — Wave 0 baseline + deferred-items scaffold
- [x] 39-02-PLAN.md — UIFIX-01 Mermaid ADR-0053 + 冒頭コメント
- [x] 39-03-PLAN.md — UIFIX-02 CollapsibleCodeBlock CSS override
- [x] 39-04-PLAN.md — UIFIX-03 JobStore dead code + test_sse JWT cookie
- [x] 39-05-PLAN.md — UIFIX-04 D-07/D-08/D-11 (AskMe + TS types + 📎 tooltip)
- [x] 39-06-PLAN.md — UIFIX-04 D-09 + D-10 Pattern E (mcp catalog drift)
- [x] 39-07-PLAN.md — UIFIX-04 D-10 Pattern A 8 件 + Pattern B test_api_chat 3 件
- [x] 39-08-PLAN.md — UIFIX-04 D-10 Pattern C+D 11 件 + Pattern B test_worker 1 件
- [x] 39-09-PLAN.md — Close (verification + ROADMAP/STATE)
**UI hint**: yes

### Phase 33: AI-UI 操作 MCP ツール + trace/人間承認
**Goal**: AI がチャットから自分の UI を実際に操作できる — 観察 (read) → 入力 (click/fill/navigate) のループを MCP ツールセットで完結させ、破壊的操作は人間の確認を経る
**Depends on**: Phase 32 (data-ai-role + ページ探索 API)
**Requirements**: AIUI-02, AIUI-04
**Success Criteria** (what must be TRUE):
  1. AI が `ui_click` / `ui_read` / `ui_fill` / `ui_navigate` MCP ツールを使い data-ai-role を target にして UI 要素を操作できる
  2. 新規 MCP ツールが `config/mcp_tools.yaml` に宣言され、`/add-mcp-tool` フローで追加され、自動生成された helper / JS カタログ / docs と整合している
  3. UI 操作が `RPCContext.correlation_id` を `trace_id` とする stdout JSONL trace に span として記録され、`scripts/trace_query.py` で検索できる
  4. 破壊的操作 (削除・送信・デプロイ等) は実行前に確認ダイアログを表示し、ユーザーが明示的に承認しない限り blocking する
**Plans:** 9 plans
Plans:
- [x] 39-01-PLAN.md — Wave 0 baseline + deferred-items scaffold
- [x] 39-02-PLAN.md — UIFIX-01 Mermaid ADR-0053 + 冒頭コメント
- [x] 39-03-PLAN.md — UIFIX-02 CollapsibleCodeBlock CSS override
- [x] 39-04-PLAN.md — UIFIX-03 JobStore dead code + test_sse JWT cookie
- [x] 39-05-PLAN.md — UIFIX-04 D-07/D-08/D-11 (AskMe + TS types + 📎 tooltip)
- [x] 39-06-PLAN.md — UIFIX-04 D-09 + D-10 Pattern E (mcp catalog drift)
- [x] 39-07-PLAN.md — UIFIX-04 D-10 Pattern A 8 件 + Pattern B test_api_chat 3 件
- [x] 39-08-PLAN.md — UIFIX-04 D-10 Pattern C+D 11 件 + Pattern B test_worker 1 件
- [ ] 39-09-PLAN.md — Close (verification + ROADMAP/STATE)
**UI hint**: yes

### Phase 34: チャット操作性 + スレッド/アプリ探索性
**Goal**: 日常チャット操作とスレッド・アプリ探索の摩擦をまとめて解消し、200名規模の社内利用に耐える人間 UX を確立する
**Depends on**: Phase 33 (AI-UI 操作 MCP ツール — UX 改善で新設するボタン等にも data-ai-role を付与)
**Requirements**: UX-01, UX-02
**Success Criteria** (what must be TRUE):
  1. ユーザーがチャット画面でメッセージのコピー・再送信・実行中ジョブのキャンセル・サイドバーのスムーズな置換などを低摩擦で実行できる
  2. ストリーミング表示があり、AI 応答が逐次更新されているように見える (Copilot SDK 制約下のベスト実装)
  3. ユーザーがスレッド一覧を検索 / フィルタ / 最近アクセス順などで絞り込め、目的のスレッドにすぐ到達できる
  4. 新規スレッドのタイトルが会話内容から自動生成され、無題スレッドが大量に並ばない
**Plans:** 9 plans
Plans:
- [x] 39-01-PLAN.md — Wave 0 baseline + deferred-items scaffold
- [x] 39-02-PLAN.md — UIFIX-01 Mermaid ADR-0053 + 冒頭コメント
- [x] 39-03-PLAN.md — UIFIX-02 CollapsibleCodeBlock CSS override
- [x] 39-04-PLAN.md — UIFIX-03 JobStore dead code + test_sse JWT cookie
- [x] 39-05-PLAN.md — UIFIX-04 D-07/D-08/D-11 (AskMe + TS types + 📎 tooltip)
- [x] 39-06-PLAN.md — UIFIX-04 D-09 + D-10 Pattern E (mcp catalog drift)
- [x] 39-07-PLAN.md — UIFIX-04 D-10 Pattern A 8 件 + Pattern B test_api_chat 3 件
- [x] 39-08-PLAN.md — UIFIX-04 D-10 Pattern C+D 11 件 + Pattern B test_worker 1 件
- [ ] 39-09-PLAN.md — Close (verification + ROADMAP/STATE)
**UI hint**: yes

### Phase 35: ダッシュボード化 + レスポンシブ/デザイン統一
**Goal**: 初見ユーザーが迷わず Gems / Canvas / SuperChat / DebateChat を使い分けられるダッシュボード型メニューと、モバイル幅・ダーク/ライト・クロスブラウザでの破綻ゼロのデザイン統一
**Depends on**: Phase 34 (チャット操作性 — UX 改善基盤の上にデザインシステム的整備を載せる)
**Requirements**: UX-03, UX-04
**Success Criteria** (what must be TRUE):
  1. メニュー画面がダッシュボード化され、Gems / Canvas / SuperChat / DebateChat の用途とエントリポイントが明確になる
  2. 初見ユーザーが説明なしで「最初にどのアプリを使えばいいか」を判断できるような視覚情報設計になっている
  3. UI がモバイル幅 (例: 375-768px) でレイアウト崩れせずに動作する
  4. ダークモード・主要モダンブラウザ (Chrome / Edge / Safari) で chatscope バルーン幅などのデザイン破綻が発生しない
**Plans:** 8/8 plans complete
Plans:
- [x] 35-01-foundation-setup-PLAN.md — CSS 変数基盤 + utils 切り出し + 検証ハーネス (Wave 0)
- [x] 35-02-theme-hex-to-var-PLAN.md — theme.css hex → var() 機械置換 + chatscope override 変数駆動化 (Wave 1)
- [x] 35-03-messagearea-inputbar-split-PLAN.md — MessageArea → InputBar 分離 + var() 移行 + isDark 排除 (Wave 1)
- [x] 35-04-threadsidebar-migration-PLAN.md — ThreadSidebar isDark 排除 + var() 移行 + drawer state (Wave 1)
- [x] 35-05-header-migration-PLAN.md — Header isDark 排除 + var() 移行 + hamburger menu (Wave 1)
- [x] 35-06-dashboard-responsive-PLAN.md — MenuScreen ダッシュボード化 + レスポンシブ @media 集約 (Wave 2)
- [x] 35-07-a11y-crossbrowser-handoff-PLAN.md — :focus-visible + cross-browser + Phase 36 Handoff 検証 + PROJECT.md 更新 (Wave 3) (2026-04-23)
**UI hint**: yes

### Phase 36: ファイル入力 — text/code + image multimodal
**Goal**: チャット入力欄からテキスト/コード系ファイルと画像を添付し、LLM がコンテキストとして参照できる基盤を確立する
**Depends on**: Phase 35 (デザイン統一 — 添付 UI/プレビューがモバイル幅・ダークモードで破綻しないよう Phase 35 完了後に実装)
**Requirements**: FIN-01, FIN-02
**Success Criteria** (what must be TRUE):
  1. ユーザーがチャット入力欄から .txt / .md / .json / .csv / .py / .js などのテキスト/コード系ファイルを添付し、LLM がその内容を参照して応答できる
  2. ユーザーが .png / .jpg / .webp 画像を添付でき、multimodal 対応モデルで画像内容を踏まえた応答を得られる
  3. multimodal 非対応モデルが選択されている場合、エラーで止まらず graceful にテキスト要約や警告にフォールバックする
  4. 添付ファイルがチャット履歴 (PostgreSQL checkpointer) に紐付けされ、スレッドを再オープンしたときも添付情報を確認できる
**Plans:** 7/7 plans complete
Plans:
- [x] 36-01-PLAN.md — Wave 0 A1 risk (additional_kwargs round-trip) + SDK attachments spike 検証 (2026-04-24)
- [x] 36-02-PLAN.md — ChatCopilot provider 配線 (attachments kwarg + list_models + is_vision_model) + GET /api/models route + main.py 登録 (Wave 1) (2026-04-24)
- [x] 36-03-PLAN.md — POST/GET/DELETE /api/threads/{tid}/attachments 実装 + ChatRequest 拡張 + history additional_kwargs 返却 (D-22) (Wave 2) (2026-04-24)
- [x] 36-04-PLAN.md — worker.process_chat + 2 handler (LangGraph / Orchestrator) で HumanMessage.additional_kwargs 注入 + D-18 vision drop (Wave 3) (2026-04-24)
- [x] 36-05-PLAN.md — useAttachments hook + AttachmentButton / AttachmentChips + ChatApp drop zone + paste listener (Wave 4) (2026-04-24)
- [x] 36-06-PLAN.md — useModels + VisionWarningBanner + Header vision 絵文字 + InputBar warningSlot + useChat.sendMessage attachments + bubble AttachmentChipRow (Wave 5) (2026-04-24)
- [x] 36-07-PLAN.md — docker compose E2E integration check + ADR-0050 起票 + patterns.md 追記 + VERIFICATION.md クローズ (Wave 6)
**UI hint**: yes

### Phase 37: ファイル入力 — PDF/Office 抽出 + MCP ツール参照
**Goal**: PDF / Office ファイルをサーバー側で抽出して LLM に渡し、添付ファイルを MCP ツール (execute_python / claude_code 等) からも参照可能にする
**Depends on**: なし（Phase 36 の添付 UI から切り離し — **scope 調整 2026-04-21**）
**Scope 前提 (2026-04-21 調整)**: Phase 36 を待たずに先行着手する。ファイルは「決められたフォルダ」に事前配置される前提で抽出パイプラインと MCP 参照を実装する。基本レイアウトは **チャットセッション (thread_id) 単位のフォルダ** に配置される形式 (例: `/shared/thread-files/<thread_id>/foo.pdf`)。Phase 36 でアップロード UI が完成したら同じフォルダ規約に配置するよう繋ぎ込む。
**Requirements**: FIN-03, FIN-04
**Success Criteria** (what must be TRUE):
  1. 指定フォルダ (例: `/shared/thread-files/<thread_id>/`) に配置された .pdf / .docx / .xlsx / .pptx からサーバー側で抽出されたテキストを LLM が参照して応答できる
  2. 抽出失敗 (パスワード保護・破損・サイズ超過) はエラーで止まらず、ユーザーに理由を返した上でチャットを継続できる
  3. 同じフォルダ規約で配置されたファイルが execute_python sandbox 内にマウントされる、または claude_code workspace から参照可能なパスで渡され、MCP ツール側でファイル内容を直接処理できる
  4. PDF/Office 抽出に必要な依存ライブラリ (例: pypdf / python-docx / openpyxl) が pyproject.toml + Docker image に組み込まれ、再現可能にビルドできる
  5. フォルダ規約 (パス / 命名 / ライフサイクル) が ADR 化され、Phase 36 (アップロード UI) と Phase 38 (出力ファイル保持) が同じ規約で接続できる
**Plans:** 5/5 plans complete
Plans:
- [x] 37-01-spike-mcp-headers-PLAN.md — MultiServerMCPClient headers サポートの検証スパイク (Wave 0)
- [x] 37-02-volume-deps-scaffold-PLAN.md — thread-files volume + MarkItDown 依存 + AgentState.attachments + Wave 0 テストスタブ (Wave 0)
- [x] 37-03-mcp-attachments-tools-PLAN.md — attachments_list / attachments_extract MCP ツール + YAML SSoT + xfail 8 ケース GREEN 化 (Wave 1)
- [x] 37-04-handler-prepend-delete-hook-PLAN.md — LangGraphHandler scan + SystemMessage prepend + delete_thread フォルダ削除 hook (Wave 2)
- [x] 37-05-adr-patterns-integration-PLAN.md — ADR-0048 (フォルダ規約) + patterns.md 追記 + integration check + VALIDATION.md クローズ (Wave 3)

### Phase 38: ファイル出力 — worker 生成 DL + プレビュー + ユーザー別保持
**Goal**: execute_python / claude_code が生成したファイルをユーザーがチャット UI から DL・プレビュー・再取得できる、ユーザー別ストレージを備えた成果物管理基盤
**Depends on**: Phase 37 (ファイル入力 — 入力側の抽出/ストレージ設計を踏まえて出力側を一貫した命名・ライフサイクルで構築)
**Requirements**: FOUT-01, FOUT-02, FOUT-03, FOUT-04
**Success Criteria** (what must be TRUE):
  1. execute_python sandbox で生成された PDF / 画像 / CSV 等をユーザーがチャット UI からダウンロードできる
  2. claude_code 実行 workspace の成果物 (生成された .md / .py / 画像等) もユーザーが同じ UI から取得できる
  3. 画像 / CSV / Markdown 等の生成ファイルは DL せずチャット画面上でプレビューできる
  4. 生成ファイルがユーザー別ストレージに保持され、過去スレッドや一覧画面から再取得できる
  5. ユーザー A のファイルにユーザー B が API 直接叩きでもアクセスできない (multi-user isolation)
**Plans:** 6/6 plans complete
Plans:
**Wave 1**
- [x] 38-01-PLAN.md — types.ts kind enum 化 (D-30 案 A) + AIMessage round-trip risk-gate + テスト scaffold (Wave 0)
- [x] 38-02-PLAN.md — outputs route + MCP attachments_list kind/_generated/ + YAML SSoT 再生成 (Wave 1)
- [x] 38-03-PLAN.md — execute_python cwd 切替 + claude_code cwd 引数削除 + post-process snapshot-diff rename (Wave 1)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 38-04-PLAN.md — attachments_helper 拡張 + langgraph_handler turn-delta bundle + API legacy 正規化 (Wave 2)

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 38-05-PLAN.md — AttachmentModal + 4 renderer + AttachmentChipRow kind 拡張 (Wave 3)

**Wave 4** *(blocked on Wave 3 completion)*
- [x] 38-06-PLAN.md — E2E acceptance + ADR-0052 + patterns.md + VALIDATION close (Wave 4)
**UI hint**: yes

### Phase 39: UI バグ潰し + Polish 枠
**Goal**: v5.0 から繰り越した既知 UI バグと、v6.0 開発中に発覚した小バグをまとめて潰し、milestone を綺麗に閉じる
**Depends on**: Phase 38 (ファイル出力 — v6.0 主要機能完了後の polish phase として配置)
**Requirements**: UIFIX-01, UIFIX-02, UIFIX-03, UIFIX-04
**Success Criteria** (what must be TRUE):
  1. [x] Mermaid View デフォルト表示時の OS レベル hang が再現条件と回避策付きで解消されている (or 恒久修正適用)
  2. [x] CollapsibleCodeBlock のバルーン幅 chatscope fit-content 問題が、chat 内コードブロックが縦長で潰れず横幅が安定する形で解消されている
  3. [x] `tests/test_sse.py::test_sse_done_signal` の hang が修正または削除され、JobStore.register_sse / unregister_sse の dead code が整理されている
  4. [x] v6.0 期間中に発覚した小 UI バグが一覧化され、polish 枠で消化済み or 明示的に v6.1+ defer 判断されている
**Plans:** 9/9 plans complete
Plans:
**Wave 1**
- [x] 39-01-PLAN.md — Wave 0 baseline + deferred-items scaffold
- [x] 39-02-PLAN.md — UIFIX-01 Mermaid ADR-0053 + 冒頭コメント
- [x] 39-03-PLAN.md — UIFIX-02 CollapsibleCodeBlock CSS override
- [x] 39-04-PLAN.md — UIFIX-03 JobStore dead code + test_sse JWT cookie
- [x] 39-05-PLAN.md — UIFIX-04 D-07/D-08/D-11 (AskMe + TS types + 📎 tooltip)
- [x] 39-06-PLAN.md — UIFIX-04 D-09 + D-10 Pattern E (mcp catalog drift)

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 39-07-PLAN.md — UIFIX-04 D-10 Pattern A 8 件 + Pattern B test_api_chat 3 件
- [x] 39-08-PLAN.md — UIFIX-04 D-10 Pattern C+D 11 件 + Pattern B test_worker 1 件

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 39-09-PLAN.md — Close (verification + ROADMAP/STATE)
**Hand-offs from earlier phases (Phase 39 着手時の必読 input):**
  - **Phase 35 起因 — AskMe button regression (5 chat apps)**: `.planning/todos/pending/2026-04-23-fix-askme-button-regression-in-chat-apps-after-phase-35-inpu.md` 参照。`35-03-messagearea-inputbar-split` で InputBar 分離時に 5 アプリ全てで `<MessageArea onAskMe={...} />` 配線が欠落。1 行追加 ×5 ファイルの軽微 fix
  - **Phase 36 起因 — 📎 入口段差** (option): `.planning/phases/36-text-code-image-multimodal/deferred-items.md` 参照。`activeThreadId === null` 時の `AttachmentButton` disabled tooltip 文言改善 (Phase 34 lazy auto-create の方が筋なら Phase 34 で扱う)
**UI hint**: yes

### Phase 40: UI Polish Round 2 (frontend-only)

**Goal**: Phase 39 milestone close 後に蓄積した UI todo 5 件 (#9/#10/#12/#13/#15) を frontend のみで片付け、v6.0 期間中のユーザー報告 polish を完全に消化する
**Depends on**: Phase 39 (UI バグ潰し + Polish 枠) — 同じ milestone v6.0 の延長
**Requirements**: 既存 todo 5 件 (`.planning/todos/pending/2026-05-13-*.md`):
  - `align-back-button-position-in-gems-and-canvas-screens-with-c.md` (#9)
  - `auto-create-new-thread-on-chat-superchat-initial-render.md` (#10)
  - `fix-overlapping-agent-message-balloons-in-debate-chat.md` (#12)
  - `propagate-attachmentbutton-to-superchat-gem-canvas-debate-ch.md` (#13, **Debate 除外**)
  - `simplify-superchat-url-to-omit-redundant-default-app-slug.md` (#15, 後方互換性なし)

**Success Criteria** (what must be TRUE):
  1. [ ] Gems / Canvas Screen の戻るボタンが Chat/SuperChat の Header と同位置・同スタイルに揃っている
  2. [ ] Chat / SuperChat 初回表示時 (URL に threadId なし & activeThreadId null & messages 空) に新しい thread が自動作成され、リロード / 戻る / 既存スレッド開閉時に新規 thread が二重作成されない
  3. [ ] Debate Chat のエージェントメッセージで chatscope デフォルト bubble (薄青) と Phase 35 エージェント別カラー wrapper の 2 層重ねが解消されている
  4. [ ] SuperChat / Gem / Canvas に AttachmentButton が追加され、Phase 36 の既存 attachments パイプラインで動作する (Debate は Phase 41 へ defer 明記)
  5. [ ] SuperChat URL が `/superchat` (default app) と `/superchat/<other-slug>` の 2 パターンで動き、`/superchat/superchat` の二段は新規生成されない (古い URL の互換性は不要)

**Out of Scope**:
  - Backend schema 変更 (Canvas deployed_html / Debate config 永続化 → Phase 41+ で個別検討)
  - Debate Chat 添付対応 (PDF/PPTX content extraction を含む大きめスコープなので独立 Phase 41 Debate Document Review として後追い)
  - 既存 URL `/superchat/superchat/<uuid>` への redirect (ユーザー判断で互換性不要)

**UI hint**: yes (純粋 UI / routing / CSS のみ)

## Progress

**Execution Order:**
Phases execute in numeric order: 32 → 33 → 34 → 35 → 36 → 37 → 38 → 39 → 40

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
| 32. AI-UI 操作基盤 (data-ai-role + ページ探索 API) | v6.0 | 0/TBD | Not started | - |
| 33. AI-UI 操作 MCP ツール + trace/人間承認 | v6.0 | 0/TBD | Not started | - |
| 34. チャット操作性 + スレッド/アプリ探索性 | v6.0 | 0/TBD | Not started | - |
| 35. ダッシュボード化 + レスポンシブ/デザイン統一 | v6.0 | 8/8 | Complete    | 2026-04-23 |
| 36. ファイル入力 — text/code + image multimodal | v6.0 | 7/7 | Complete   | 2026-05-11 |
| 37. ファイル入力 — PDF/Office 抽出 + MCP ツール参照 | v6.0 | 5/5 | Complete    | 2026-04-22 |
| 38. ファイル出力 — worker 生成 DL + プレビュー + ユーザー別保持 | v6.0 | 6/6 | Complete    | 2026-05-12 |
| 39. UI バグ潰し + Polish 枠 | v6.0 | 9/9 | Complete    | 2026-05-13 |
