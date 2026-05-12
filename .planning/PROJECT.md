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

### Validated (v5.0)

- ✓ FastMCP Docker サービス基盤 — mcp-server コンテナ healthy 起動、worker から streamable-http 接続、LangChain BaseTool 取得 — v5.0
- ✓ LangGraph bind_tools + ToolNode 統合 — ChatCopilot.bind_tools() プロンプト方式で JSON 解析、ToolEnabledSubAgent の mini ReAct グラフ、10 ステップ自動停止 — v5.0
- ✓ Web 検索ツール (Tavily) — web_search MCP ツール + レスポンスサイズ制限 — v5.0
- ✓ DB クエリ + Claude Code 実行ツール — db_query (SELECT-only) + claude_code (env sanitization + 60s timeout) — v5.0
- ✓ config.yaml ツールルーティング — config/mcp_tools.yaml で 6 ツール宣言、ToolRegistry が YAML/MCP 双方向検証 — v5.0
- ✓ URL ルーティング (React Router v7) — BrowserRouter でアプリ種別 + thread_id を URL 化、スレッド共有リンク対応 — v5.0
- ✓ ADR カタログ化 + patterns.md + GSD 統合 — docs/adr/INDEX.md (pre-commit 自動生成) + .planning/patterns.md で GSD plan-phase から canonical_refs 経由で自動参照 — v5.0
- ✓ AskUserQuestion 対話パターン — `<ask_user_question>` タグで構造化質問、QuestionPanel UI、全 5 アプリ伝播 — v5.0
- ✓ CodeAct パターン (Python サンドボックス) — execute_python MCP ツール (AST allowlist + メモリ制限 + timeout)、CodeAct 専用 SubAgent — v5.0
- ✓ ユーザー選択モデル伝播 — SuperChat 選択モデルを AGENT.md デフォルトより優先、4 種 SubAgent 全てで model_override — v5.0
- ✓ MCP ツールカタログ single-source-of-truth — config/mcp_tools.yaml を唯一のソースとし、scripts/generate_mcp_artifacts.py が helper/js/docs を自動生成、pre-commit drift 検知 — v5.0
- ✓ Observability 基盤 — stdout JSONL 1 行 1 span (OTEL span-like)、trace_id = RPCContext.correlation_id、3 経路統合、scripts/trace_query.py CLI — v5.0
- ✓ v5.0 milestone cleanup — 9 phase VALIDATION.md を status: validated に backfill + Phase 30 VALIDATION.md 遡及作成 — v5.0 (Phase 31.1)

### Validated (v6.0)

- ✓ Phase 37: ファイル入力 PDF/Office 抽出 + MCP ツール参照 — `attachments_list` / `attachments_extract` を MCP ツールとして実装、`/shared/thread-files/<login>/<thread_id>/` フォルダ規約 (ADR-0048)、SuperChat / Chat 両経路で per-job MCP client + RPCContext 伝播 (Phase 37.1 in-place fix)、thread 削除時の folder 同期 + path traversal 防御 — v6.0
- ✓ Phase 38: ファイル出力 — worker 生成 DL + プレビュー + ユーザー別保持 — `_generated/` サブフォルダ + post-process `{ts}_{name}` rename (Phase 38 D-08/D-10)、`GET /threads/{tid}/outputs/{name}` route (D-05)、`AttachmentMeta.kind` enum 化 (D-30)、4 種 preview renderer (image/markdown/csv/text + PDF unsupported fallback) を Chat 経路 (langgraph_handler) で integration — ADR-0052 — v6.0

### Active (v6.0 candidates)

- [ ] エージェント別 ツール allowlist — Phase 24 D-02 で defer、エージェントごとに呼び出し可能なツールを制限
- [ ] MCP サーバーゲートウェイ機能 — 別の MCP サーバーのツールを中継し単一 worker から集約アクセス
- [ ] claude_code MCP ツール認証バインド — spirit-room 方式でユーザー別トークン注入
- [ ] Mermaid View ハング調査 — OS レベル hang の再現手順と回避策
- [ ] AI が操作しやすい UI — data-ai-role 属性導入、AI 向け操作性向上
- [ ] code review skill 活用運用フロー — インストール済みスキル群のルーチン組み込み

### Deferred (v6.1+ 以降)

- [ ] RAG / ナレッジ検索 — pgvector を活用した Gem knowledge の埋め込み検索
- [ ] エージェント管理 UI — エージェントの追加・編集・削除を GUI で操作
- [ ] RETRY / 回復メカニズム — DEGRADED エージェントを再起動なしに HEALTHY に回復（retry_ready()）
- [ ] 本番モード Docker Compose 整備 — Vite dev server なしで React ビルド済み静的ファイルを FastAPI から配信
- [ ] Canvas アプリから MCP ツール呼び出し — FastAPI ブリッジ経由
- [ ] 汎用 HTTP ツール（GitHub API, Slack API 等）

### Out of Scope

- Slack ボット実装 — from_slack ファクトリを用意するが、Slack 連携は v4.0 以降
- 生成アプリからの社内 DB アクセス API — Canvas App 拡張フェーズ
- Canvas バージョン管理・ロールバック — v1 では最新 HTML のみ保持
- エージェント間の非同期並列実行 — 現状は逐次ルーティング、並列化は v4.1 以降
- **ネイティブモバイルアプリ** — タブレット幅（768-1024px）までは PC ブラウザでプライマリ scope、スマホ幅（375-767px）もレイアウト破綻ゼロは保証（Phase 35 で実施）。iOS/Android ネイティブアプリは非対象。
- ストリーミング応答（逐次トークン） — Copilot SDK Technical Preview では未対応

## Current Milestone: v6.0 UI/AI Experience

**Goal:** AI からもユーザーからも扱いやすい UI 基盤を整備する — AI 操作可能性と人間 UX の両輪を強化し、ファイル I/O とバグ残債を仕上げる。

**Target features:**

- AI が UI を操作できる基盤（data-ai-role 属性方式 vs AI-API ファースト方式を research フェーズで調査、要件フェーズで決定）
- 人間向け UX 改善（チャット操作性・視認性・メニュー導線など、v5.0 で顕在化した痛点を要件化して解消）
- ファイル I/O UX（チャット入力ファイルアップロード + worker 生成ファイルダウンロード、双方 v6.0 スコープ）
- 既存 UI バグ潰し（Mermaid View ハング、CollapsibleCodeBlock バルーン幅、その他 v5.0 で defer された UI 不具合）

**規模感:** 中規模（6-8 phase 想定）

**Key context:**

- AI 操作のターゲット層（Canvas 内 / チャット UI 全体 / 両方）は要件定義フェーズで確定
- AI 操作基盤の具体アーキテクチャは research フェーズで両アプローチを調査してから要件化
- v5.0 の observability（stdout JSONL trace）を UI 操作の監査ログとしても継続利用
- 200 名規模・社内利用 — AI 操作基盤が人間 UX を阻害しない（DOM 肥大 / レンダリング負荷の最小化）こと

## Previous State: v5.0 COMPLETE

**v5.0 shipped 2026-04-20** — 13 フェーズ（20–31 + 31.1）、35 プラン、118 コミット、10 日間

### What Shipped in v5.0

- **MCP ツールエコシステム (Phase 20/23/24/30)**: FastMCP Docker 基盤 + 6 ツール (ping/web_search/db_query/claude_code/execute_python/get_current_datetime) + config/mcp_tools.yaml single source of truth + 自動生成スクリプト + pre-commit drift 検知
- **LangGraph bind_tools + ReAct 統合 (Phase 21/22)**: Copilot SDK が native tool-calling 未対応のため「プロンプト方式 + JSON 解析」で bind_tools() 実装、ToolEnabledSubAgent の mini ReAct グラフ、Tavily Web 検索
- **高度対話パターン (Phase 27/28)**: AskUserQuestion で AI が構造化選択肢を提示、CodeAct で Python コード生成 + sandbox 実行ループ
- **observability 基盤 (Phase 31)**: stdout JSONL 1 行 1 span、3 経路 (ToolEnabled/CodeAct/iframe RPC) 統合、scripts/trace_query.py CLI、audit_log テーブル退役
- **UX 底上げ (Phase 25/29)**: React Router v7 URL ルーティング、ユーザーモデル伝播
- **設計知識の再利用可能化 (Phase 26)**: 30+ ADR を INDEX.md + patterns.md に分離、GSD plan-phase が canonical_refs 経由で自動参照。v5.0 期間中に ADR-0020〜0047 の 27 本追加
- **milestone cleanup (Phase 31.1)**: 9 phase VALIDATION.md backfill + Phase 30 VALIDATION.md 遡及作成、帳簿 100% 整合で archive

### Next

`/gsd-new-milestone` で v6.0 計画へ

## Context

**v1.0 shipped 2026-04-02** — 6 phases, 17 plans, 163 commits, 2 days
**v2.0 shipped 2026-04-04** — 4 phases (7–10), React UI + OrchestratorGraph + SuperChat
**v3.0 shipped 2026-04-07** — 8 phases (11–17+15.1), Agent Platform, Gem, Canvas, DebateChat
**v4.0 shipped 2026-04-09** — 2 phases (18–19), Canvas API Bridge, iframe JSON-RPC, Hosting Shell
**v5.0 shipped 2026-04-20** — 13 phases (20–31+31.1), Agent Tool Platform, MCP 6 tools, CodeAct, observability
**Codebase:** Python 7,040 LOC + TypeScript 8,460 LOC · 47 ADRs · 6 MCP tools
**Stack:** Python 3.12 · FastAPI · LangGraph · LangChain + MCP · arq · Redis · PostgreSQL (pgvector) · React 19 + TypeScript + Vite · FastMCP (Docker サービス)

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
| bind_tools はプロンプトエンジニアリング方式 (v5.0) | Copilot SDK 0.2.0 は native tool-calling 未対応 — system prompt にスキーマ注入 + JSON 解析で妥協 | ✓ `app/providers/copilot.py::BoundChatCopilot`、ADR-0021 |
| MCP transport = streamable-http 固定 (v5.0) | stdio は Docker 間不可、sse はセッションアフィニティ問題あり | ✓ `mcp-server` service、ADR-0020 |
| CodeAct = 直接実行 (v5.0) | ReAct ループを経由せず、コード生成 → sandbox 実行 → 結果観察を `execute_python` ツール 1 本で完結 | ✓ ADR-0041 |
| observability = stdout JSONL、外部集約基盤なし (v5.0) | 社内 200 名規模には OTEL Collector / Loki / Tempo 等は過剰、docker logs + CLI で十分 | ✓ `app/observability/trace.py`、ADR-0045 |
| MCP single-source-of-truth (v5.0) | YAML 宣言 → 自動生成スクリプトで Python helper / JS カタログ / docs を全生成、手書きファイルと物理分離 + pre-commit drift 検知 | ✓ `scripts/generate_mcp_artifacts.py`、ADR-0044 |
| Integration check gate を phase 必須化 (v5.0) | Phase 31 Wave 6 で unit test 60/60 green の後に 3 件 silent failure を捕捉した経験則。Python logging root level / LangGraph state 復元 / route→worker シグネチャ不整合 | ✓ ADR-0046、CLAUDE.md |
| Decimal phase for milestone cleanup (v5.0) | Milestone archive 直前の帳簿整合作業を独立 decimal phase (例: 31.1) に集約。主 phase 番号を汚さず GSD 規律を保つ | ✓ ADR-0047 |
| Mobile responsive policy 反転 (Phase 35) | タブレット幅（768-1024px）まで primary scope、スマホ幅（375-767px）は破綻ゼロ保証、iOS/Android ネイティブは非対象 | D-07 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-12 — Phase 38 完了 (worker 生成ファイル DL/プレビュー/ユーザー別保持 — `_generated/` + outputs route + AttachmentMeta.kind enum + 4 種 preview renderer / ADR-0052)*
