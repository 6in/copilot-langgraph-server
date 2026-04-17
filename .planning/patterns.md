# Patterns Catalog

**Purpose:** 過去の設計判断（ADR）から抽出した再利用可能パターンのカタログ。
**Source of Truth:** `docs/adr/` — ADR にないパターンはここに載せない（D-08）。
**Integration:** 各フェーズの CONTEXT.md の `canonical_refs` に本ファイル（`.planning/patterns.md`）と `docs/adr/INDEX.md` を必ず追加する（CLAUDE.md 運用ルール参照）。
**Maintenance:** 手動更新。新規 ADR 追加時は `/create-adr` の手順に従って本ファイルにも追記する。

---

## Auth

### JWT ブロックリストの Redis 移行
httpOnly cookie に格納した JWT の logout 無効化は Redis ブロックリストで実現する。
インメモリ実装は再起動で無効化できないため Redis へ移行した。
関連 ADR: [0014](../docs/adr/0014-phase17-security-hardening-jwt-blocklist-redis-and-endpoint-auth.md)

---

## LangGraph・Graph

### OrchestratorGraph Per-Job Construction
OrchestratorGraph はリクエストごとに生成・廃棄する（アプリ起動時に 1 インスタンス共有しない）。
github_token のマルチユーザー分離を実現するためのパターン。
関連 ADR: [0005](../docs/adr/0005-orchestratorgraph-integration-per-job-construction.md)

### APP.md 定義によるアプリケーションパッケージ
`agents/menus/APP.md` でエージェントサブセットを宣言する。
コード変更ゼロでアプリ別エージェント構成が可能。
関連 ADR: [0007](../docs/adr/0007-application-packages-app-md-pattern.md)

### bind_tools プロンプトエンジニアリング方式
Copilot SDK は OpenAI tool_calls 形式非対応のため、ツールスキーマをシステムプロンプトに JSON として注入し、
テキスト応答を解析して tool_calls に変換する BoundChatCopilot パターン。
関連 ADR: [0021](../docs/adr/0021-langgraph-bind-tools-toolnode-via-prompt-engineering.md)

### エージェントプロンプトへの日時・ユーザー自動注入
ToolEnabledSubAgent の system prompt 先頭に現在日時・ログインユーザーを毎回注入する。
エージェント AGENT.md には記載不要。
関連 ADR: [0025](../docs/adr/0025-datetime-and-user-context-injection-into-agent-prompts.md)

### DebateChat ターン制マルチエージェントグラフ
複数 SubAgent が交互に発言するターン制を LangGraph ループで実現する。
DebateGraph ノードは state.turn_index で話者を決定する。
関連 ADR: [0011](../docs/adr/0011-debate-chat-multi-agent-turn-based-platform.md)

### AIMessage.name 強制付与ラッパー (_wrap_agent_run)
LangGraph checkpoint のシリアライズで `AIMessage.name` が失われる問題への対策。
エージェントノードをラッパーで包み、戻り値の `AIMessage` に `name` が未設定なら強制付与する。
DebateGraph の `dispatch_node` が先行実装。OrchestratorGraph にも同パターンを適用。
関連 ADR: [0038](../docs/adr/0038-superchat-context-messages-and-agent-name-persistence.md)

### context_messages によるシステム的コンテキスト注入
過去の会話をメッセージテキストに埋め込むのではなく、API の `context_messages` フィールドで
バックエンドに渡し、SubAgent の LLM メッセージリストに HumanMessage/AIMessage として注入する。
プレゼンテーション層とデータ層の責務分離。
関連 ADR: [0038](../docs/adr/0038-superchat-context-messages-and-agent-name-persistence.md)

### Token Streaming 3 層配管
Copilot SDK ストリームを worker → SSE → frontend の 3 層で中継する。
notifier.py でチャンクをキューイングし SSE エンドポイントが消費する。
関連 ADR: [0031](../docs/adr/0031-copilot-sdk-token-streaming-three-layer-plumbing.md)

---

## MCP・Tools

### FastMCP Docker 独立サービス基盤
ツール実装を API サーバーに組み込まず FastMCP 独立コンテナとして分離する。
worker から streamable-http で接続。stdio は Docker 間通信不可、SSE はセッションアフィニティ問題あり。
関連 ADR: [0020](../docs/adr/0020-fastmcp-docker-service-infrastructure.md)

### MCP ツールカタログ YAML 検証 (ToolRegistry)
`config/mcp_tools.yaml` に宣言ツールセットを定義し、worker 起動時に MCP 実ツールリストと双方向一致を検証する。
不一致で RuntimeError → デプロイ後の無言不整合を防止する。
関連 ADR: [0024](../docs/adr/0024-mcp-tool-catalog-validation.md)

### db_query SELECT-only ガード
`is_select_only()` ユーティリティで SELECT 以外をブロックする。
`app/utils/sql_safety.py` に配置し iframe-rpc と MCP ツールの両方から再利用。
関連 ADR: [0023](../docs/adr/0023-mcp-db-query-and-claude-code-tools.md)

### claude_code env sanitization
Claude Code CLI サブプロセス起動前に `CLAUDECODE=1` 等の危険な環境変数を除去する。
タイムアウト 60 秒 + zombie プロセス対策を含む。
関連 ADR: [0023](../docs/adr/0023-mcp-db-query-and-claude-code-tools.md)

### iframe-rpc.js ツールカタログ埋め込み + 同期スクリプト
`config/mcp_tools.yaml` のツール情報を `static/js/iframe-rpc.js` に `AVAILABLE_TOOLS` 定数として埋め込む。
マーカーコメント (`BEGIN/END TOOL_CATALOG`) で囲み、`scripts/sync-tool-list-to-js.py` で自動更新可能。
関連 ADR: [0040](../docs/adr/0040-ui-improvements-batch-mermaid-copy-thread-grouping-authflow.md)

### Tavily JSON モード互換性
Copilot モデルは関数呼び出し非対応のため、Tavily 検索結果を JSON スキーマとして prompt に注入し
text 応答から parse する。
関連 ADR: [0022](../docs/adr/0022-tavily-web-search-json-tool-calling-model-compatibility.md)

---

## Worker・Jobs

### Worker Pluggable Task Routing Facade
`dispatcher.py` がタスクタイプ（chat/orchestrator/canvas 等）を TaskHandler サブクラスへルーティングする。
handler 追加はコードのみで完結（コンフィグ変更不要）。
関連 ADR: [0003](../docs/adr/0003-worker-pluggable-task-routing-facade.md)

---

## Frontend・UI

### nginx prefix-strip URL ルーティング
リバースプロキシで `/orochi` プレフィックスを strip して転送する。
FastAPI は `APP_PREFIX` で root_path 設定、Vite は `VITE_APP_BASE` でアセット URL を制御。
関連 ADR: [0001](../docs/adr/0001-nginx-prefix-strip-for-url-routing.md), [0002](../docs/adr/0002-api-path-prefix-management-in-react-spa.md)

### Canvas iframe postMessage JSON-RPC ブリッジ
iframe 内 JS から `window.parent.postMessage` 経由で DB/AI ツールを呼び出す。
JSON-RPC over postMessage パターン。`static/js/iframe-rpc.js` ライブラリとして配布。
関連 ADR: [0018](../docs/adr/0018-canvas-iframe-postmessage-json-rpc-bridge.md)

### Canvas スタンドアロンホスティングと parent-bridge.js 共通化
`/apps/{app_id}/` でホスト時も iframe-rpc 機能を利用するため parent-bridge.js を共通化する。
CanvasPane と HostingShell で同一 relay ロジックを共有。
関連 ADR: [0019](../docs/adr/0019-canvas-app-standalone-hosting-parent-bridge.md)

### React Router v7 URL ルーティング
BrowserRouter + Routes でアプリ種別・thread_id を URL に反映する。
APP_PREFIX 対応は `basename` prop で実現。nginx SPA fallback（`try_files`）が必要。
関連 ADR: [0028](../docs/adr/0028-react-router-v7-url-based-routing-for-spa.md)

### ai() モデル指定エイリアスホワイトリスト
Canvas iframe RPC の ai() に model パラメータを追加する際、任意モデル名を通すのではなく
YAML ホワイトリストでエイリアスを管理する。
関連 ADR: [0033](../docs/adr/0033-canvas-ai-model-selection-with-alias-whitelist.md)

### Frontend Bun 移行
フロントエンドランタイムを Node.js/npm から Bun に移行した。
Docker Compose build の `bun install` + `bun run build`。パッケージマネージャーとして npm の代替。
D-10 により primary カテゴリは Frontend・UI（secondary: Infra・Deploy）。
関連 ADR: [0027](../docs/adr/0027-migrate-frontend-runtime-from-nodejs-to-bun.md)

### Mermaid.js オンデマンド render パターン
mermaid パッケージ（~1MB）は lazy load し、描画は View ボタンクリック時のみ実行する。
デフォルト View にすると複数ブロックの同時 render で OS ハングの危険がある。
SVG は `dangerouslySetInnerHTML` でインライン表示（blob URL + `<img>` は foreignObject が描画されない）。
固定 width/height を除去し viewBox ベースのスケーリングでコンテナにフィットさせる。
関連 ADR: [0037](../docs/adr/0037-chat-ui-batch-enhancements.md)

### SSE キャンセルの Phase 分離
AI 応答キャンセルは Phase 1（フロントのみ: EventSource.close + 状態リセット）と
Phase 2（バックエンド: ジョブキャンセル API）に分離する。
Copilot SDK の `send_and_wait` がブロッキングのため、Phase 1 だけでも十分実用的。
関連 ADR: [0037](../docs/adr/0037-chat-ui-batch-enhancements.md)

### Mermaid 画像コピー — 一時スタイル変更 + html-to-image
View モードの Copy ボタンでダイアグラムを PNG としてクリップボードにコピーする。
コンテナの flex レイアウトを一時的に `fit-content` に変更してキャプチャし、直後に復元する。
`skipFonts: true` で cross-origin CSS エラーを回避、`pixelRatio: 3` で高解像度キャプチャ。
関連 ADR: [0040](../docs/adr/0040-ui-improvements-batch-mermaid-copy-thread-grouping-authflow.md)

### スレッドサイドバー日付グループ + 折りたたみ
スレッド一覧を `updated_at` 基準で 5 グループ（今日/昨日/今週/先週/それ以前）に分類。
「それ以前」はデフォルト折りたたみ。フロントエンドのみの変更で API ページネーションは不要。
関連 ADR: [0040](../docs/adr/0040-ui-improvements-batch-mermaid-copy-thread-grouping-authflow.md)

### AskUserQuestion — システムプロンプト注入 + フロントエンド検出
AI に `<ask_user_question>` XML タグで構造化質問を出力させ、フロントエンドで検出して QuestionPanel UI を表示する。
SuperChat 経由の応答は `orchestrator_result` JSON でラップされるため、外側を先にアンラップしてから AUQ 検出する。
履歴ロード時のタグ除去はデータ取得層（`client.ts`）で行い、レンダリング層（`MarkdownMessage`）では行わない。
関連 ADR: [0039](../docs/adr/0039-askuserquestion-auq-protocol.md)

---

## Infra・Deploy

### ADR カタログ化と patterns.md による GSD プランニング統合
ADR を 7 カテゴリの索引（`docs/adr/INDEX.md`）とパターンカタログ（`.planning/patterns.md`）に分離し、GSD フェーズの CONTEXT.md の canonical_refs に両ファイルを毎回記載する運用で過去意思決定を自動参照させる。INDEX.md は pre-commit hook で自動生成、patterns.md は手動更新。
関連 ADR: [0034](../docs/adr/0034-adr-catalog-patterns-md-gsd-integration.md)

---

## Data・Persistence

### db_pools.yaml 駆動の接続プールチューニング
DB 接続プールパラメータ（min_size/max_size/timeout 等）を `config/db_pools.yaml` で宣言する。
コード変更なしに環境別チューニングが可能。
関連 ADR: [0032](../docs/adr/0032-db-pools-yaml-driven-tuning-params.md)

### Gem is_public フラグによる公開共有
Gem 公開は DB カラム `is_public` フラグで制御する。
共有 Gem は全ユーザーが読み取り可能で、GemsScreen に Shared Gems セクションを表示。
関連 ADR: [0010](../docs/adr/0010-gem-public-sharing-is-public-flag.md)
