# Copilot LangGraph Chat

## What This Is

GitHub Copilot を LangGraph の AI プロバイダーとして使う、社内向け汎用チャット Web アプリ。
`ChatCopilot`（`BaseChatModel` のカスタム実装）を通じて Copilot の推論能力を活用しながら、LangGraph のグラフ構造により将来のエージェント化・ツール呼び出し拡張に対応できる設計。
Device Flow 認証で JWT セッション管理を行い、arq + Redis による非同期ジョブキューと SSE でリアルタイム応答を実現し、PostgreSQL で会話履歴を永続化する。
複数アプリケーション（Chat / SuperChat / Gem / Canvas / DebateChat）＋ユーザーという単位でスレッドを管理し、マルチエージェントプラットフォーム基盤を提供する。

## Core Value

Copilot の JSON-RPC ベース SDK を LangChain 互換プロバイダーとして動かし、アプリケーション（Chat / SuperChat / Gems / Canvas / DebateChat）＋ユーザーという単位でスレッドを管理できるチャット UI から使えること。

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
- ✓ general-assistant エージェント追加 — `agents/general-assistant/AGENT.md` で SubAgentRegistry に汎用会話エージェントを追加 — v2.0

### Validated (v3.0)

- ✓ RPCContext 統合 — `app/orchestrator/context.py` に `RPCContext` frozen dataclass + `_keep_first` reducer、全ノードから correlation_id 横断トレース可能 — v3.0
- ✓ ハイブリッド SubAgentRegistry — フォルダ定義型（AGENT.md のみ）とコード実装型（agent.py あり）を自動判別してロード、HEALTHY/DEGRADED/FAILED ステータス管理、GET /health/agents — v3.0
- ✓ INPUT_SCHEMA 標準化 — ツールスクリプトに INPUT_SCHEMA 定数、ScriptBackend が jsonschema で事前バリデーション、CI lint スクリプト — v3.0
- ✓ 2段ルーター（キーワード前段 → LLM） — SubAgent.keywords + ROUTING-01 startup 警告、50エージェント規模対応、構造化ルーティングログ — v3.0
- ✓ Application Packages + Menu — アプリ定義ファイルでエージェントサブセットを宣言、メニュー画面からアプリ選択、GET /api/apps — v3.0
- ✓ Gem（AI ペルソナ）管理 — gems テーブル、CRUD API、GemsScreen ハブ、GemChatApp、description/knowledge フィールド — v3.0
- ✓ Canvas App — CanvasChatApp（分割レイアウト）、CanvasScreen（一覧）、Canvas 専用グラフ（HTML トリミング）、デプロイ — v3.0
- ✓ DebateChatApp — マルチエージェント討論チャット、ターン制リアルタイム SSE ストリーミング、履歴復元 — v3.0

### Validated (v4.0)

- ✓ Canvas iframe postMessage JSON-RPC ブリッジ — iframe 内 JS から POST /api/iframe-rpc 経由で DB クエリ（SELECT）と AI（Copilot ワンショット）を呼び出せる仕組み — v4.0
- ✓ Canvas アプリ独立ホスティング — GET /apps/{app_id} で Canvas アプリをスタンドアロン URL で公開、parent-bridge.js 共通リレー — v4.0

### Active (v5.0)

- [ ] LangGraph ツール呼び出し（bind_tools） — INPUT_SCHEMA を Anthropic tools フォーマットに自動変換、LLM がツールを直接呼び出し
- [ ] RAG / ナレッジ検索 — pgvector を活用した Gem knowledge の埋め込み検索
- [ ] 監査ログ DB 永続化 — correlation_id を PostgreSQL に記録してクエリで追跡
- [ ] エージェント管理 UI — エージェントの追加・編集・削除を GUI で操作
- [ ] RETRY / 回復メカニズム — DEGRADED エージェントを再起動なしに HEALTHY に回復（retry_ready()）
- [ ] 本番モード Docker Compose 整備 — Vite dev server なしで React ビルド済み静的ファイルを FastAPI から配信

### Out of Scope

- Slack ボット実装 — from_slack ファクトリを用意するが、Slack 連携は v4.0 以降
- 生成アプリからの社内 DB アクセス API — Canvas App 拡張フェーズ
- Canvas バージョン管理・ロールバック — v1 では最新 HTML のみ保持
- エージェント間の非同期並列実行 — 現状は逐次ルーティング、並列化は v4.1 以降
- モバイル対応 — PC ブラウザのみ対象
- ストリーミング応答（逐次トークン） — Copilot SDK Technical Preview では未対応

## Current State: v4.0 COMPLETE

**v4.0 shipped 2026-04-09** — 2 フェーズ（18–19）、5 プラン、118 コミット、2 日間

### What Shipped in v4.0

- **Canvas iframe JSON-RPC ブリッジ**: iframe 内 JS から postMessage 経由で DB クエリ・AI 呼び出しを安全に実行
- **arq worker 拡張**: frame_app_api ジョブタイプ追加、psycopg3 DB プール（psycopg_pool）、config 設定
- **Canvas アプリ独立ホスティング**: GET /apps/{app_id} 動的シェル、srcdoc エスケープ、sandbox 制限
- **parent-bridge.js 共通化**: Shell HTML と CanvasPane.tsx が同一リレーロジックを共有
- **JWT Cookie 認証**: /api/iframe-rpc を JWT Cookie で保護（サーバー共有トークン方式を廃止）

### Next

`/gsd-new-milestone` で v5.0 計画へ

## Context

**v1.0 shipped 2026-04-02** — 6 phases, 17 plans, 163 commits, 2 days
**v2.0 shipped 2026-04-04** — 4 phases (7–10), React UI + OrchestratorGraph + SuperChat
**v3.0 shipped 2026-04-07** — 8 phases (11–17+15.1), Agent Platform, Gem, Canvas, DebateChat
**v4.0 shipped 2026-04-09** — 2 phases (18–19), Canvas API Bridge, iframe JSON-RPC, Hosting Shell
**Codebase:** ~12,000+ Python + TypeScript LOC · 173+ ファイル変更
**Stack:** Python 3.12 · FastAPI · LangGraph · arq · Redis · PostgreSQL (pgvector) · React 19 + TypeScript + Vite

- Copilot SDK (`github-copilot-sdk==0.2.0`) は JSON-RPC で Copilot CLI と通信。`BaseChatModel` カスタム実装が必須。
- SDK は **Technical Preview** — `app/providers/copilot.py` の薄いラッパーで変更を隔離
- JWT 認証: Device Flow → JWT cookie (`~/.copilot_sdk/.jwt_secret`) → chat API 保護
- arq worker が LangGraph を別プロセスで実行、job 結果を Redis に保存してから SSE/ポーリングで通知
- Docker Compose: `postgres` (pgvector:pg17)、`redis` (7-alpine)、`api`、`worker`、`frontend` サービス
- nginx `/orochi` プレフィックス対応: VITE_APP_BASE + FastAPI root_path

**Known tech debt:**
- `tests/test_sse.py::test_sse_done_signal` hangs — test implements asyncio.Queue approach, production uses Redis polling
- JobStore.register_sse/unregister_sse dead code — queue pattern replaced by Redis polling
- CollapsibleCodeBlock のバルーン幅（chatscope の fit-content 問題）— 保留中

## Constraints

- **Tech Stack**: Python（LangChain / LangGraph / Copilot SDK） — ドキュメントのサンプルコードが Python ベース
- **Auth**: Device Flow のみ — PAT 直接指定は対象外
- **SDK 安定性**: Copilot SDK は Technical Preview — 外部インターフェースを薄いラッパーで隔離しておく
- **スケール感**: 200名規模・社内利用 — 高トラフィック対策より運用性（監査ログ・アプリ管理）を優先

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| `BaseChatModel` ラッパー実装 | Copilot SDK は JSON-RPC 通信のため OpenAI 互換 URL では代替不可 | ✓ `app/providers/copilot.py` |
| Device Flow 認証 | ブラウザ経由で簡単に認証でき、トークン再利用でインタラクション最小化 | ✓ `app/auth/manager.py` |
| JWT セッション管理 | web API を保護しながら Device Flow 後の状態を stateless に管理 | ✓ HS256 JWT cookie、JTI blocklist |
| LangGraph をグラフ基盤に採用 | 今後のエージェント化（ツール呼び出し・マルチノード）への拡張性 | ✓ `app/graph/builder.py` |
| arq + Redis 非同期アーキテクチャ | HTTP リクエストを LangGraph 実行からデカップリング、タイムアウト回避 | ✓ POST /api/chat → job_id |
| AsyncPostgresSaver (PostgreSQL) | MemorySaver はプロセス再起動で消失、SQLite は本番ツールとして不十分 | ✓ docker-compose postgres |
| pgvector/pgvector:pg17 イメージ | 将来の RAG・埋め込み拡張のため pgvector を有効化しておく | ✓ `docker/initdb/01-enable-pgvector.sql` |
| RPCContext frozen dataclass + _keep_first reducer | ノードが context を上書きできない不変性の保証 | ✓ `app/orchestrator/context.py` |
| Hybrid SubAgentRegistry | フォルダ型とコード型を同一 API で扱い、起動時健全性チェック | ✓ HEALTHY/DEGRADED/FAILED |
| 2段ルーター（keyword → LLM） | 50エージェント規模でプロンプトサイズと精度を両立 | ✓ `app/orchestrator/graph.py` |
| Application Packages | エージェントサブセットをファイル宣言でパッケージ化、コード変更不要 | ✓ `apps/*.yaml` + AppRegistry |
| Canvas 専用グラフ（build_canvas_graph） | 古い HTML を LLM コンテキストに含めない — Canvas 品質と速度の改善 | ✓ `app/graph/canvas_builder.py` |
| DebateHandler は astream で turns 蓄積 | aget_state での PostgreSQL 逆シリアライズで AIMessage 型が失われる問題を回避 | ✓ `app/jobs/handlers/debate_handler.py` |
| VITE_APP_BASE を docker-compose 環境変数で渡す | APP_PREFIX 未設定で root_path が空。ビルド時定数として確実 | ✓ `docker-compose.yml` |
| parent-bridge.js を新規作成して共通化 | Shell HTML と CanvasPane.tsx の両方が同じリレーロジックを使う — iframe RPC 実装の重複を排除 | ✓ `static/js/parent-bridge.js` |
| /api/iframe-rpc JWT Cookie 認証を維持 | auth_manager.load_token()（サーバー共有トークン）は不適切。呼び出し元ユーザーの JWT Cookie から github_token を取得 | ✓ `app/api/routes/iframe_rpc.py` |
| hosted_apps.router を StaticFiles より前に登録 | FastAPI のルート優先順位: 動的ルートが StaticFiles より先にマッチする必要がある | ✓ `app/api/main.py` |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-09 after v4.0 Canvas API Bridge milestone*
