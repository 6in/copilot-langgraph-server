# Copilot LangGraph Chat

## What This Is

GitHub Copilot を LangGraph の AI プロバイダーとして使う、社内向けマルチエージェントチャット Web アプリ。
`ChatCopilot`（`BaseChatModel` のカスタム実装）を通じて Copilot の推論能力を活用しながら、LangGraph の StateGraph により複数のエージェント・Gem（AI ペルソナ）・Canvas（HTML 生成）を組み合わせたチャット体験を提供する。
Device Flow 認証で JWT セッション管理を行い、arq + Redis による非同期ジョブキューと SSE でリアルタイム応答を実現し、PostgreSQL で会話履歴を永続化する。

> **利用コンテキスト:** 200名規模の社内プロジェクト向けシステム。マルチユーザー・マルチアプリケーションの運用に対応（ユーザー分離、アプリケーション管理、監査ログ）。

## Core Value

Copilot の JSON-RPC ベース SDK を LangChain 互換プロバイダーとして動かし、アプリケーション（Chat / SuperChat / Gems）＋ユーザーという単位でスレッドを管理できるチャット UI から使えること。

## Requirements

### Validated (v1.0)

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

- ✓ OrchestratorGraph + SubAgent マルチエージェントルーティング — `app/orchestrator/` モジュール、`github_token` threading でマルチユーザー対応 — v2.0
- ✓ Simple / Super モード切替 — React UI トグル + `POST /api/chat` の `mode` フィールドで OrchestratorHandler へルーティング — v2.0
- ✓ applications/threads/audit_log スキーマ刷新 — thread_labels 廃止、applications + threads テーブルで Chat/SuperChat スレッドを分離管理 — v2.0
- ✓ GET /api/threads LEFT JOIN + app_id フィルタ — チェックポイントなしスレッドも返却、app_id でアプリ別フィルタ可能 — v2.0
- ✓ OrchestratorGraph checkpointer 接続 — AsyncPostgresSaver で SuperChat の会話継続性を実現 — v2.0
- ✓ フロント useThreads appId 対応 — ChatApp/SuperChatApp が各自の app_id でスレッドを分離取得 — v2.0
- ✓ general-assistant エージェント追加 — SubAgentRegistry に汎用会話エージェントを追加、RouterNode が一般メッセージを正しくルーティング可能に — v2.0

### Validated (v3.0)

- ✓ RPCContext 統合 — `RPCContext` frozen dataclass + `_keep_first` reducer、`AgentState` に `context` + `error` フィールド、OrchestratorHandler で構築して注入、RouterNode が correlation_id を構造化 JSON ログに出力 — v3.0
- ✓ ハイブリッド SubAgentRegistry — フォルダ定義型（AGENT.md のみ）とコード実装型（agent.py あり）を自動判別してロード、HEALTHY/DEGRADED/FAILED ステータス管理、GET /health/agents エンドポイント（JWT 不要） — v3.0
- ✓ INPUT_SCHEMA 標準化 — ツールスクリプトに INPUT_SCHEMA 定数、ScriptBackend が jsonschema で事前バリデーション、CI lint スクリプト（scripts/lint_tools.py）で全ツールスクリプトの INPUT_SCHEMA 有無を強制 — v3.0
- ✓ スケーラブル2段ルーティング — SubAgent.keywords 属性 + キーワード前段フィルタ + LLM fallback、全ルーティング決定をステージ（stage: keyword|llm）付き構造化ログに記録 — v3.0
- ✓ アプリケーションパッケージ + メニュー — APP.md 定義ファイルでエージェントサブセット宣言、AppRegistry + GET /api/apps、動的 MenuScreen、SuperChatApp が appId でスレッドとエージェントを分離 — v3.0
- ✓ Gem（AI ペルソナ）機能 — gems テーブル、Gem CRUD API（所有権チェック付き）、スレッド作成時の gem_id 指定、description/knowledge フィールド — v3.0
- ✓ Canvas（HTML 生成・デプロイ）機能 — canvas_apps テーブル、Worker HTML 抽出・保存・静的デプロイ（/apps/{app_id}/）、CanvasPane エディタ/プレビュー/デプロイ UI — v3.0
- ✓ Gem UX 強化 — GemsScreen ハブ（Gem CRUD 管理）、GemChatApp（Gem 専用チャット）、MenuScreen への「Gems」カード固定追加 — v3.0
- ✓ SuperChat × Gem 招待 — GemSubAgent（SubAgent 互換ラッパー）、OrchestratorHandler gem_ids 統合、POST /api/chat gem_ids フィールド、GemSelector UI — v3.0

### Active (v4.0)

- [ ] ターン制マルチエージェント討論チャット — 複数 Gem/SubAgent をターン制で会話させる DebateChatApp（討論・パネル・チェーンパターン、ターン数制御、人間延長承認）

### Out of Scope

- ストリーミング応答 — Copilot SDK Technical Preview では未対応（v4.0 候補）
- ツール呼び出し（LLM function calling） — INPUT_SCHEMA 構造は準備済み、bind_tools 実装は v4.0 以降
- エージェント管理 UI — CLI / ファイル操作で管理、GUI は対象外
- Canvas バージョン管理・ロールバック — v1 では最新 HTML のみ保持
- 生成アプリからの社内 DB アクセス API — 拡張フェーズ
- モバイル対応 — PC ブラウザのみ対象

## Current Milestone: v4.0

**Goal:** ターン制マルチエージェント討論チャットプラットフォームの実装

**Target features:**
- DebateChatApp — 討論・パネル・チェーンの 3 パターン
- DebateHandler — arq worker に登録する新ハンドラー
- ターン数制御 + 人間延長承認
- Gem / SubAgent / 混在のいずれでも動作

## Context

**v1.0 shipped 2026-04-02** — 6 phases, 17 plans, ~4,935 Python LOC
**v2.0 shipped 2026-04-04** — 4 phases (7–10), React UI + SuperChat + マルチエージェント基盤
**v3.0 shipped 2026-04-06** — 6 phases (11–16+15.1), 38 plans, 161 files changed, ~10,148 Python LOC · ~4,344 TS LOC

**Stack:** Python 3.12 · FastAPI · LangGraph · arq · Redis · PostgreSQL (pgvector/pgvector:pg17) · Vanilla JS · React 19 + TypeScript + Vite · @chatscope/chat-ui-kit-react

- Copilot SDK (`github-copilot-sdk==0.2.0`) は JSON-RPC で Copilot CLI と通信。`BaseChatModel` カスタム実装が必須。
- SDK は **Technical Preview** — `app/providers/copilot.py` の薄いラッパーで変更を隔離
- JWT 認証: Device Flow → JWT cookie → chat/threads API 保護
- arq worker が LangGraph / OrchestratorGraph / DebateGraph を別プロセスで実行
- Docker Compose: `postgres` (pgvector:pg17)、`redis` (7-alpine)、`api`、`worker`、`frontend` サービス

**Known tech debt:**
- `tests/test_sse.py::test_sse_done_signal` hangs — test written for asyncio.Queue approach, production uses Redis polling
- marked.js CDN pins @9.1.6 while app.js comment references v17 API
- JobStore queue methods (`register_sse`, `unregister_sse`, `notify`) are dead code
- `OrchestratorHandler` の `from app.providers.copilot import ChatCopilot` がインライン import（機能問題なし）

## Constraints

- **Tech Stack**: Python（LangChain / LangGraph / Copilot SDK） — ドキュメントのサンプルコードが Python ベース
- **Auth**: Device Flow のみ — PAT 直接指定は対象外
- **SDK 安定性**: Copilot SDK は Technical Preview — 外部インターフェースを薄いラッパーで隔離しておく
- **スケール感**: 200名規模・社内利用 — 高トラフィック対策より運用性（監査ログ・アプリ管理）を優先する

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| `BaseChatModel` ラッパー実装 | Copilot SDK は JSON-RPC 通信のため OpenAI 互換 URL では代替不可 | ✓ `app/providers/copilot.py` — `ChatCopilot(BaseChatModel)` |
| Device Flow 認証 | ブラウザ経由で簡単に認証でき、トークン再利用でインタラクション最小化 | ✓ `app/auth/manager.py` — Fernet暗号化 + Device Flow |
| JWT セッション管理 | web API を保護しながら Device Flow 後の状態を stateless に管理 | ✓ HS256 JWT cookie、JTI blocklist で logout 対応 |
| LangGraph をグラフ基盤に採用 | 今後のエージェント化（ツール呼び出し・マルチノード）への拡張性 | ✓ `app/graph/builder.py` — ToolNode 拡張ポイント文書化 |
| arq + Redis 非同期アーキテクチャ | HTTP リクエストを LangGraph 実行からデカップリング、タイムアウト回避 | ✓ POST /api/chat → job_id; SSE + polling でリアルタイム通知 |
| AsyncPostgresSaver (PostgreSQL) | MemorySaver はプロセス再起動で消失、SQLite は本番ツールとして不十分 | ✓ docker-compose postgres + langgraph-checkpoint-postgres |
| pgvector/pgvector:pg17 イメージ | 将来の RAG・埋め込み拡張のため pgvector を有効化しておく | ✓ `docker/initdb/01-enable-pgvector.sql` |
| RPCContext frozen dataclass + _keep_first reducer | ノードが context を上書きできない不変性を型安全に保証 | ✓ `app/orchestrator/context.py` — AgentState に Annotated[RPCContext, _keep_first] |
| HEALTHY/DEGRADED/FAILED 3段階ヘルス | 1エージェント障害がシステム全体を止めない耐障害設計 | ✓ `app/orchestrator/agent.py` — AgentStatusEnum |
| 2段ルーティング（キーワード → LLM） | 50エージェント規模でもプロンプトサイズと精度を両立 | ✓ `app/orchestrator/graph.py` — RouterNode stage field |
| APP.md アプリ定義ファイル | エージェントサブセット管理をコード変更なしで実現 | ✓ `apps/*/APP.md` — AppRegistry auto-load |
| GemSubAgent 独立クラス（SubAgent 非継承） | Gem は system_prompt+knowledge のみ、code/tools 不要。継承より合成で十分 | ✓ `app/orchestrator/gem_agent.py` |
| gem_ids を ChatRequest の独立フィールドに | gem_id（単数スレッド指定）と gem_ids（SuperChat招待）は別概念 | ✓ `app/api/models.py` — gem_ids: list[str] | None |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-06 after v3.0 milestone — Agent Platform shipped: RPCContext統合・ハイブリッドSubAgentRegistry・2段ルーティング・アプリパッケージ・Gem/Canvas・SuperChat×Gem招待*
