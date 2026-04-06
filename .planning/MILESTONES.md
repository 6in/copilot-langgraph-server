# Milestones

## v3.0 Agent Platform (Shipped: 2026-04-06)

**Phases completed:** Phases 11–16 (6 core phases + 15.1 insert), 38 plans, 41 tasks
**Timeline:** 2026-04-04 → 2026-04-06 (3 days)
**Stats:** 161 files changed · ~23,000 insertions · ~10,148 Python LOC · ~4,344 TS LOC

**Delivered:** マルチエージェントプラットフォーム基盤 — RPCContext 統合・ハイブリッド SubAgentRegistry・2段ルーティング・アプリケーションパッケージ・Gem/Canvas 機能・SuperChat × Gem 招待

**Key accomplishments:**

- **RPCContext 統合 (Phase 11)** — `RPCContext` frozen dataclass + `_keep_first` reducer を `AgentState` に統合。全ノードが `state["context"].correlation_id` でリクエスト横断追跡可能、HTTP → arq job → OrchestratorHandler の correlation_id フロー確立
- **ハイブリッド SubAgentRegistry (Phase 12)** — フォルダ型（AGENT.md のみ）とコード型（agent.py）エージェントを自動発見・ロード、HEALTHY/DEGRADED/FAILED ヘルス管理、`GET /health/agents` エンドポイント（JWT 不要）
- **INPUT_SCHEMA 標準化 (Phase 12)** — ツールスクリプトに `INPUT_SCHEMA` 定数、ScriptBackend が jsonschema で事前バリデーション、`scripts/lint_tools.py` CI lint で品質ゲート強制
- **スケーラブル2段ルーティング (Phase 13)** — `SubAgent.keywords` 属性 + キーワード前段フィルタで LLM 呼び出し不要な明確なルーティングを高速処理、全決定を構造化ログ（`stage: keyword|llm`）に記録
- **アプリケーションパッケージ + メニュー (Phase 14)** — `APP.md` 定義ファイルでエージェントサブセットをパッケージ化、`AppRegistry` + `GET /api/apps`、動的 MenuScreen、SuperChatApp が `appId` でスレッドとエージェントを分離
- **Gem（AI ペルソナ）+ Canvas 機能 (Phase 15)** — `gems` / `canvas_apps` テーブル追加、Gem CRUD API（所有権チェック付き）、Canvas Worker HTML 抽出・静的デプロイ、GemSelector チップ UI、CanvasPane エディタ/プレビュー/デプロイ
- **Gem UX 強化 (Phase 15.1)** — `description`/`knowledge` フィールド追加、GemsScreen ハブ（Gem CRUD 管理）、GemChatApp 専用チャット、MenuScreen への「Gems」カード固定追加
- **SuperChat × Gem 招待 (Phase 16)** — `GemSubAgent` クラス（Gem を SubAgent 互換ラッパーに動的変換）、OrchestratorHandler `gem_ids` 統合、全テスト PASS、人手 UAT PASSED（じゃんけん Gem 動作確認済み）

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
