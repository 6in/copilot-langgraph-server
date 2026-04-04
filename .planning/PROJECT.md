# Copilot LangGraph Chat

## What This Is

GitHub Copilot を LangGraph の AI プロバイダーとして使う、個人用の非同期チャット Web アプリ。
`ChatCopilot`（`BaseChatModel` のカスタム実装）を通じて Copilot の推論能力を活用しながら、LangGraph の StateGraph により将来のエージェント化・ツール呼び出し拡張に対応できる設計。
Device Flow 認証で JWT セッション管理を行い、arq + Redis による非同期ジョブキューと SSE でリアルタイム応答を実現し、PostgreSQL で会話履歴を永続化する。

## Core Value

Copilot の JSON-RPC ベース SDK を LangChain 互換プロバイダーとして動かし、スレッド維持付きのチャット UI から使えること。

## Requirements

### Validated

- ✓ `ChatCopilot` — `BaseChatModel` を継承した LangChain 互換ラッパーを実装する — v1.0
- ✓ Device Flow 認証 — GitHub OAuth でトークンを取得し、Fernet 暗号化でローカルに保存・再利用する — v1.0
- ✓ JWT セッション管理 — Device Flow 後に HS256 JWT を発行、cookie 経由でチャット API を保護する — v1.0
- ✓ 会話スレッド維持 — 複数ターンの会話履歴を LangGraph の MessagesState として管理する — v1.0
- ✓ LangGraph グラフ設計 — 将来のツール呼び出し・マルチエージェント拡張を見越した素直な StateGraph 構造 — v1.0
- ✓ Web チャット UI — ブラウザで動作するダークテーマ chat 画面（送信・受信・履歴・Markdown レンダリング） — v1.0
- ✓ モデル選択 — UI のドロップダウンで Copilot 提供モデルを切り替えられる — v1.0
- ✓ 非同期ジョブキュー + SSE — arq + Redis で AI 実行を非同期化、SSE でリアルタイム完了通知、ポーリングでフォールバック — v1.0
- ✓ GitHub ユーザー情報表示 — GET /api/me でプロフィールを取得し、ヘッダーにアバターとログイン名を表示 — v1.0
- ✓ PostgreSQL チェックポインター — AsyncPostgresSaver で会話履歴を永続化、Docker Compose で postgres サービスを提供 — v1.0
- ✓ スレッド削除 — `adelete_thread()` でスレッドと全チェックポイントを原子的に削除 — v1.0

### Validated (v2.0)

- ✓ OrchestratorGraph + SubAgent マルチエージェントルーティング — `app/orchestrator/` モジュール、`github_token` threading でマルチユーザー対応 — Validated in Phase 9
- ✓ Simple / Super モード切替 — React UI トグル + `POST /api/chat` の `mode` フィールドで OrchestratorHandler へルーティング — Validated in Phase 9
- ✓ applications/threads/audit_log スキーマ刷新 — thread_labels 廃止、applications + threads テーブルで Chat/SuperChat スレッドを分離管理 — Validated in Phase 10
- ✓ GET /api/threads LEFT JOIN + app_id フィルタ — チェックポイントなしスレッドも返却、app_id でアプリ別フィルタ可能 — Validated in Phase 10
- ✓ OrchestratorGraph checkpointer 接続 — AsyncPostgresSaver で SuperChat の会話継続性を実現 — Validated in Phase 10
- ✓ フロント useThreads appId 対応 — ChatApp/SuperChatApp が各自の app_id でスレッドを分離取得 — Validated in Phase 10

- ✓ general-assistant エージェント追加 — `agents/general-assistant/AGENT.md` で SubAgentRegistry に汎用会話エージェントを追加、RouterNode が一般メッセージを正しくルーティング可能に — Validated in Phase 10 (10-06)

### Validated (v3.0)

- ✓ RPCContext 統合 — `app/orchestrator/context.py` に `RPCContext` frozen dataclass + `_keep_first` reducer、`AgentState` に `context: Annotated[RPCContext, _keep_first]` + `error: str | None`、OrchestratorHandler で構築して注入、RouterNode が correlation_id を構造化 JSON ログに出力 — Validated in Phase 11

### Validated (v3.0) — Phase 12

- ✓ ハイブリッド SubAgentRegistry — フォルダ定義型（AGENT.md のみ）とコード実装型（agent.py あり）を自動判別してロード、HEALTHY/DEGRADED/FAILED ステータス管理、GET /health/agents エンドポイント（JWT 不要） — Validated in Phase 12
- ✓ INPUT_SCHEMA 標準化 — ツールスクリプトに INPUT_SCHEMA 定数、ScriptBackend が jsonschema で事前バリデーション、CI lint スクリプト（scripts/lint_tools.py）で全ツールスクリプトの INPUT_SCHEMA 有無を強制 — Validated in Phase 12

### Active (v3.0)

- [ ] アプリケーションパッケージ — アプリ定義ファイルでエージェントサブセットを宣言、メニュー画面からアプリ選択 → 対応エージェント群のみ RouterNode に渡す
- [ ] スケーラブルルーティング — AGENT.md description 規約（対象外 必須）、2段ルーター（キーワード前段 → LLM）、構造化ルーティングログ

### Out of Scope

- マルチユーザー対応 — 個人ツールのため不要
- ストリーミング応答 — Copilot SDK Technical Preview では未対応（v2 候補）
- ツール呼び出し（bind_tools） — 設計考慮済み（ToolNode extension point 文書化）、実装は v2 以降
- モバイル対応 — PC ブラウザのみ対象

## Current Milestone: v3.0 Agent Platform

**Goal:** 50エージェント・複数アプリケーションに耐えるマルチエージェントプラットフォーム基盤を構築し、エージェント追加・組み合わせをユーザー体験の核心にする。

**Target features:**
- ハイブリッド SubAgentRegistry（フォルダ型 + コード型、HEALTHY/DEGRADED/FAILED）
- アプリケーションパッケージ（エージェントサブセットをアプリ定義で管理、メニューから選択）
- スケーラブルルーティング（description 規約 + 2段ルーター + 構造化ログ）
- RPCContext 統合（app_id / user_id / correlation_id を AgentState に）
- INPUT_SCHEMA 標準化（AST 抽出 + jsonschema + CI lint）

## Context

**v1.0 shipped 2026-04-02** — 6 phases, 17 plans, 163 commits, 2 days
**v2.0 Phase 10 complete 2026-04-04** — thread_labels replaced with applications/threads/audit_log; app-isolated thread listing; OrchestratorGraph checkpointer; frontend useThreads appId support
**v3.0 Phase 12 complete 2026-04-04** — Hybrid SubAgentRegistry with HEALTHY/DEGRADED/FAILED health tracking; GET /health/agents endpoint; INPUT_SCHEMA tool standard with ScriptBackend validation and CI lint enforcement
**Codebase:** ~4,935 Python LOC · 640 JS · 719 CSS · 144 files changed
**Stack:** Python 3.12 · FastAPI · LangGraph · arq · Redis · PostgreSQL (pgvector/pgvector:pg17) · Vanilla JS · React 19

- Copilot SDK (`github-copilot-sdk==0.2.0`) は JSON-RPC で Copilot CLI と通信。`BaseChatModel` カスタム実装が必須。
- SDK は **Technical Preview** — `app/providers/copilot.py` の薄いラッパーで変更を隔離
- JWT 認証: Device Flow → JWT cookie (`~/.copilot_sdk/.jwt_secret`) → chat API 保護
- arq worker が LangGraph を別プロセスで実行、job結果を Redis に保存してから SSE/ポーリングで通知
- Docker Compose: `postgres` (pgvector:pg17)、`redis` (7-alpine)、`api`、`worker` サービス

**Known tech debt:**
- `tests/test_sse.py::test_sse_done_signal` hangs — test implements asyncio.Queue approach, production uses Redis polling; fix = update test mock
- marked.js CDN (@9.1.6) vs app.js comment (v17) — reconcile version or comment
- JobStore.register_sse/unregister_sse dead code — queue pattern replaced by Redis polling
- ASYNC-*, ME-*, CKPT-* IDs not in archived REQUIREMENTS.md traceability

## Constraints

- **Tech Stack**: Python（LangChain / LangGraph / Copilot SDK） — ドキュメントのサンプルコードが Python ベース
- **Auth**: Device Flow のみ — PAT 直接指定は対象外
- **SDK 安定性**: Copilot SDK は Technical Preview — 外部インターフェースを薄いラッパーで隔離しておく

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| `BaseChatModel` ラッパー実装 | Copilot SDK は JSON-RPC 通信のため OpenAI 互換 URL では代替不可 | ✓ `app/providers/copilot.py` — `ChatCopilot(BaseChatModel)` |
| Device Flow 認証 | ブラウザ経由で簡単に認証でき、トークン再利用でインタラクション最小化 | ✓ `app/auth/manager.py` — Fernet暗号化 + Device Flow |
| JWT セッション管理 | web API を保護しながら Device Flow 後の状態を stateless に管理 | ✓ HS256 JWT cookie、JTI blocklist で logout 対応 |
| LangGraph をグラフ基盤に採用 | 今後のエージェント化（ツール呼び出し・マルチノード）への拡張性 | ✓ `app/graph/builder.py` — ToolNode 拡張ポイント文書化 |
| `send_and_wait(prompt)` — str を渡す | SDK 0.2.0 で API シグネチャ変更、dict 渡しは JS バイナリで TypeError | ✓ `app/providers/copilot.py:95` 修正済み |
| arq + Redis 非同期アーキテクチャ | HTTP リクエストを LangGraph 実行からデカップリング、タイムアウト回避 | ✓ POST /api/chat → job_id; SSE + polling でリアルタイム通知 |
| redis[asyncio]>=4.2.0 に緩和 | arq 0.27.0 が redis[hiredis]<6 に依存、>=7.0 ではインストール不可 | ✓ redis 5.3.1 で解決 |
| SSE は Redis ポーリングで実装 | asyncio.Queue は別プロセス間通信に使えない（arq worker は別プロセス） | ✓ stream_job が job_store.get() をポーリング |
| save_result BEFORE notifier.done | SSE クライアントが done 受信時に結果を取得できることを保証 | ✓ worker.py process_chat 順序を強制 |
| AsyncPostgresSaver (PostgreSQL) | MemorySaver はプロセス再起動で消失、SQLite は本番ツールとして不十分 | ✓ docker-compose postgres + langgraph-checkpoint-postgres |
| pgvector/pgvector:pg17 イメージ | 将来の RAG・埋め込み拡張のため pgvector を有効化しておく | ✓ `docker/initdb/01-enable-pgvector.sql` |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-05 — Phase 13 complete: 2-stage RouterNode (keyword pre-filter + LLM fallback), SubAgent.keywords loaded from AGENT.md frontmatter, ROUTING-01 startup warning for missing 対象外 sections*
