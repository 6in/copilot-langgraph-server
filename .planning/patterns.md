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

### JWT_SECRET の生成規格と Docker 環境での env 明示指定
HS256 用キーは `secrets.token_hex(32)` = 32 バイト (hex 64 文字) を生成規格とする。
Docker 環境ではコンテナ再作成で消える file fallback (`~/.copilot_sdk/.jwt_secret`) に依存せず、
`JWT_SECRET` 環境変数を明示指定する運用ガイドライン。ローテーションは全ユーザー強制ログアウトを伴う。
関連 ADR: [0056](../docs/adr/0056-jwt-secret-generation-spec-and-docker-env-override.md)

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

### model_override 3 段フォールバック伝播
SuperChat UI 選択モデルを Handler → Registry → SubAgent の 3 層に伝播させる。
`override or AGENT.md meta or ハードコード既定` の 3 段フォールバックで統一。
空文字送信は `job.get("model") or None` で falsy 正規化（`dict.get(k, None)` では空文字が素通しする罠）。
folder / folder+tools / codeact / gem の 4 種別 SubAgent で同一パターン、code-type は対象外。
関連 ADR: [0042](../docs/adr/0042-user-model-override-propagation-to-subagents.md)

### Checkpointer 復元を想定した state reducer 設計
LangGraph `AsyncPostgresSaver` は thread_id 単位で state を checkpoint/復元するため、
`request-scoped で fresh であるべきフィールド` に first-wins reducer (`return a if a is not None else b`)
を使うと、2 回目以降の invoke で stale な前回値が復元・固定されてしまう。
`context.correlation_id` を trace_id として使う設計で実際に全 child span が stale trace_id を引き継ぐ silent failure が発生 (Phase 31 Wave 6)。
`context` のようなフィールドは **last-wins + None guard** (`return b if b is not None else a`) とする。
unit test は**再 invoke シナリオ** (checkpointer 付きでの 2 回目の ainvoke) を含めて検証する。
関連 ADR: [0046](../docs/adr/0046-integration-check-surfaced-silent-failures.md)

### HumanMessage.additional_kwargs サイドカー envelope (per-turn メタデータ搬送)
per-turn のメッセージメタデータ（添付ファイル・引用・tool_call_id 等）を `HumanMessage.additional_kwargs: dict` に載せることで、
追加 state フィールド不要で LangGraph `add_messages` reducer + PostgreSQL checkpointer (AsyncPostgresSaver JSONB) に透過永続化する。
`AIMessage.name` が checkpoint 経由で落ちる既知問題 (ADR-0038) とは別系統で `additional_kwargs` は保持される (Phase 36 Wave 0 で round-trip 検証済)。
provider 側 (`ChatCopilot._extract_attachments`) で最後の HumanMessage の `additional_kwargs["attachments"]` を読み、SDK 型に変換して SDK call に渡す。
`additional_kwargs` 経路は v6.1+ で token usage / 引用 / tool_call_id の per-message metadata 搬送にも応用可能。
関連 ADR: [0050](../docs/adr/0050-copilot-sdk-multimodal-attachments.md), [0038](../docs/adr/0038-superchat-context-messages-and-agent-name-persistence.md)

### Vision / model capability fallback の 2 段構造 (UI 事前通知 + worker defense-in-depth)
モデル能力依存の機能（vision / tool-calling / context length 等）で UI bypass を防ぐには、UI 側で事前通知 + 推奨モデル提示 +
ワンクリック切替（graceful guidance）を行い、worker 側で再検証 + drop + SystemMessage 警告注入（enforcement）を行う 2 段構造が有効。
hardcoded allowlist は持たず、SDK `list_models()` 経由でモデル能力 (`ModelInfo.capabilities.supports.vision` 等) を single source of truth にする
(TTL 1h キャッシュで新規モデル追加時の UI 更新を不要化)。SystemMessage 警告注入は ADR-0025 の datetime/user injection と同じ pattern を踏襲。
関連 ADR: [0050](../docs/adr/0050-copilot-sdk-multimodal-attachments.md), [0025](../docs/adr/0025-datetime-and-user-context-injection-into-agent-prompts.md)

### Wave 0 risk-gate — checkpointer round-trip を MVP 前に潰す
新規機能が LangGraph checkpointer (PostgreSQL JSONB) 経由で保存される `BaseMessage` 系フィールドに新規データを載せる場合、Plan 01 (Wave 0)
に round-trip 検証 (`MemorySaver` + `AsyncPostgresSaver` 両方) を必ず置く。ADR-0038 (AIMessage.name 喪失) 同系統の risk を実装完了後に
発見するとデータモデル全体の手戻りになるため、1 plan 使って先取りすると Plan 02-06 の並列展開が安全になる。対象判定: per-message metadata
を新規 field で運ぶ (`additional_kwargs` / 新規 reducer) / `BaseMessage` の追加属性 / 外部 SDK の Technical Preview API 依存。
関連 ADR: [0051](../docs/adr/0051-multi-app-rollout-process-patterns.md), [0038](../docs/adr/0038-superchat-context-messages-and-agent-name-persistence.md)

### AIMessage.additional_kwargs.attachments で AI 生成ファイルを turn 単位で bundle
Phase 36 で HumanMessage 側に確立した `additional_kwargs` envelope パターンを AIMessage 側にも適用する。
turn 完了時 (final_state 確定直後) に handler が `_generated/` の delta を再 scan し、
final AIMessage の `additional_kwargs` に `{"attachments": [...]}` を None-guard + dict union (`existing or {} | {…}`) で merge する。
`AsyncPostgresSaver` の JSONB に round-trip 保存され、スレッド再オープン時に frontend へ自動復元される。
Wave 0 (Plan 01) で AIMessage 側 round-trip を独立検証することで、AIMessage.name 喪失問題 (ADR-0038) と分離して扱える。
tool wrapper 側の post-process rename とは独立 — handler は再 scan で kind=generated delta を抽出するのみで二重カウントしない。
関連 ADR: [0052](../docs/adr/0052-worker-generated-outputs-storage-and-preview.md), [0050](../docs/adr/0050-copilot-sdk-multimodal-attachments.md), [0038](../docs/adr/0038-superchat-context-messages-and-agent-name-persistence.md)

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

### iframe-rpc.js ツールカタログは独立 ES module 参照
`static/js/iframe-rpc.js` の `AVAILABLE_TOOLS` 埋め込みは Phase 30 で廃止。`static/js/tool-catalog-generated.js` に分離し、`iframe-rpc.js` は `export { AVAILABLE_TOOLS } from './tool-catalog-generated.js'` で re-export するのみ。
旧 `scripts/sync-tool-list-to-js.py` は削除され、`scripts/generate_mcp_artifacts.py --target js` に責務が統合された。
関連 ADR: [0040](../docs/adr/0040-ui-improvements-batch-mermaid-copy-thread-grouping-authflow.md), [0044](../docs/adr/0044-mcp-tool-catalog-single-source-of-truth.md)

### MCP ツール single-source-of-truth 化
`config/mcp_tools.yaml` を MCP ツールカタログの唯一の宣言源とし、以下 3 ファイルは全て `scripts/generate_mcp_artifacts.py` から決定論的に自動生成する:
- `mcp_server/tools/mcp_helper.py`（sandbox 用 Python ラッパー）
- `static/js/tool-catalog-generated.js`（iframe-rpc が import する JS カタログ）
- `docs/mcp-tools.md`（人間向けドキュメント）

手書き基盤 (`_call_tool` / `_clean_content`) は `mcp_server/tools/mcp_helper_utils.py` に分離。生成ファイルの手動編集は pre-commit hook (`scripts/install-hooks.sh`) の `--check` モードで drift 検知・commit ブロックされる。
関連 ADR: [0044](../docs/adr/0044-mcp-tool-catalog-single-source-of-truth.md)

### Tavily JSON モード互換性
Copilot モデルは関数呼び出し非対応のため、Tavily 検索結果を JSON スキーマとして prompt に注入し
text 応答から parse する。

### CodeAct 直接実行方式（ReAct ループ回避）
Copilot SDK モデルがプロンプトベースのツール呼び出し JSON に安定して従わないため、
`CodeActSubAgent` は ReAct ループを使わず、LLM にコード生成だけさせて agent が execute_python を直接呼ぶ。
MCP ツール（web_search 等）は `mcp_helper` ラッパー経由で Python コード内から呼び出す。
`AGENT.md` に `agent_type: codeact` で SubAgentRegistry が自動選択。
関連 ADR: [0041](../docs/adr/0041-codeact-direct-execution-over-react.md)
関連 ADR: [0022](../docs/adr/0022-tavily-web-search-json-tool-calling-model-compatibility.md)

### LangChain BaseTool を透過 wrap する TracedTool で tool_call span を統一
MCP / LangChain BaseTool を `TracedTool(wrapped, privileged_tool_names, common_attrs_provider)` で wrap し、
`ainvoke` 実行前後に `tool_call` span を自動 emit する。`privileged` attribute は `config/mcp_tools.yaml` の
`sandbox_exposed=false` 集合で判定（ADR-0024 の延長）。args/result は env var `TRACE_ARGS_MAX_CHARS` /
`TRACE_RESULT_MAX_CHARS` で truncate し、PII / 秘匿情報の span 混入を防ぐ。
ToolEnabledSubAgent の ReAct ループ（軸 B 経路 1）に適用し、CodeAct（経路 2）と iframe_rpc_handler（経路 3）は
直接 `async with trace_span("tool_call")` で包む。3 経路すべてが同一 span schema で記録される。
関連 ADR: [0045](../docs/adr/0045-phase-31-observability-jsonl.md), [0024](../docs/adr/0024-mcp-tool-catalog-validation.md), [0041](../docs/adr/0041-codeact-direct-execution-over-react.md)

### Per-job MCP client ライフサイクル判断
ジョブ単位で `MultiServerMCPClient` を生成するのは、その client から得たツールを実際に graph / registry / ToolNode に渡す handler だけに限る（OrchestratorHandler は該当、通常チャットの LangGraphHandler は非該当で dead code だった）。cleanup は `async with` / `__aexit__` を使わず、`getattr(client, "aclose") or getattr(client, "close")` で存在するクロースメソッドのみを呼ぶ前方互換パターン。`langchain-mcp-adapters` 0.1.x は stateless で事実上 no-op だが、将来 stateful に戻った場合にコード変更不要。
関連 ADR: [0049](../docs/adr/0049-per-job-mcp-client-lifecycle-and-cancel-safe-exceptions.md), [0020](../docs/adr/0020-fastmcp-docker-service-infrastructure.md)

### MCP ツールの Cancel-safe 例外処理
MCP ツールコア関数で長時間非同期処理を囲むときは `except BaseException` を使わない。Python 3.8+ で `asyncio.CancelledError` は `BaseException` 直下のため arq worker キャンセルを握り潰して協調シャットダウンを壊す。`except asyncio.CancelledError: raise` + `except Exception` の 2 段構えを契約とし、さらに `_classify_error` 系で返すメッセージには内部例外の `str(exc)` を埋め込まない（LLM コンテキストに内部パスが漏れるため）。
関連 ADR: [0049](../docs/adr/0049-per-job-mcp-client-lifecycle-and-cancel-safe-exceptions.md)

### snapshot-diff 方式の post-process rename パターン
sandbox subprocess (execute_python / claude_code) が cwd に書いた新規ファイルを、
MCP tool wrapper が実行前後の `os.listdir` snapshot 差分で検出して `{ts}_{basename}` にリネームする。
mtime 判定は Docker volume の NFS / 9p mount で 1s 解像度に劣化する既知問題で取りこぼしが出るため不採用、
inotify は Linux 専用で過剰。snapshot diff は ≤ 20 LOC で実装でき、`.pyc` / symlink / 既に prefix 付きファイル を 3 段ガードで除外する。
tool wrapper のみが authoritative — handler 側 (turn-delta scan) と二重 rename しないよう責務を分離。
fallback 経路 (`/tmp` 等) では set diff が爆発しないよう `if folder != "/tmp"` ガードを必ず置く。
helper 重複定義を避け、execute_python.py を single source of truth として claude_code.py から import 再利用する DRY 構造。
関連 ADR: [0052](../docs/adr/0052-worker-generated-outputs-storage-and-preview.md)

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

### BaseMessage.content 正規化 + ReactMarkdown 防御ガード（defense-in-depth）
LangGraph チェックポイントから復元される `AIMessage.content` は tool_use / CodeAct 応答で `list[dict]` になり、ReactMarkdown の string children 制約に違反して UI 全体が白画面になる。
バックエンド `_normalize_content` で text ブロックを抽出して string 化し、ToolMessage は履歴から除外（根本治療）。フロントの `MarkdownMessage` / `CopyAllButton` は typeof + JSON.stringify で非 string をガード（既存 DB データに対する後方互換）。
型定義 `ChatMessage.content: string` は変更せず、ガードは「出るべきでない」例外処理として位置づける。
関連 ADR: [0043](../docs/adr/0043-chat-history-content-normalization-defense-in-depth.md)

### 3 入り口統一 staging hook (click / drop / paste)
ファイル添付の 3 入力経路（`<input type="file">` クリック / DataTransfer drop / ClipboardData paste）を単一 React hook (`useAttachments`) に集約し、
各入口から呼ばれる `upload(files: File[])` 一本で state / AbortController / サーバー連動 CRUD (POST/DELETE) を管理する。
入口ごとのブラウザ差異（drop の `preventDefault` / paste の `clipboardData.items.kind === 'file'` filter / image-only paste など）は hook 内部または call site で吸収。
サーバー側は Plan 03 の multipart REST (`POST /api/threads/{tid}/attachments`) と対応付く。
削除も同 hook の `remove(storage_name)` から `DELETE /api/threads/{tid}/attachments/{name}` 1 本に集約され、staging chip × ボタンと履歴非破壊の両立を担保する。
関連 ADR: [0050](../docs/adr/0050-copilot-sdk-multimodal-attachments.md), [0048](../docs/adr/0048-thread-files-folder-convention.md)

### kind discriminator による input/output 統一 UX (チップ + モーダルプレビュー)
`AttachmentMeta` に `kind: 'user_upload' | 'generated'` 単一 discriminator を持たせ、
MCP 戻り値 (`attachments_list`) / SystemMessage prepend / AIMessage bundle / AttachmentChipRow props / URL 解決すべてで同 enum を通す。
URL 解決は `kind === 'generated' ? '/outputs/' : '/attachments/'` の segment 切替で 1 関数 (`buildFileUrl`) に集約、
AI 応答テキスト内の inline 描画 (`![]()` 経路) は明示的に避けて Phase 36 アップロード添付との UX 不連続を解消する。
4 種 renderer (image=`<img>` / markdown=react-markdown / csv=ag-grid / text=Monaco) を `React.lazy` + Suspense で dispatch、
MarkdownPreview は重い MarkdownMessage を呼ばず react-markdown を薄ラッパーで直接呼ぶ (preview 用は軽量化)。
新規 npm dep ゼロ / 新規 CSS 変数ゼロ で実装可能 (既存 token と Phase 35/36 で導入済 dep のみ流用)。
チップに `[✨ AI 生成]` / `[📎 添付]` micro-badge を出して input/output 属性を視覚化、accent-subtle vs surface-elevated の弱コントラストペアで「同重要度の属性タグ」として位置づける。
関連 ADR: [0052](../docs/adr/0052-worker-generated-outputs-storage-and-preview.md)

---

## Infra・Deploy

### ADR カタログ化と patterns.md による GSD プランニング統合
ADR を 7 カテゴリの索引（`docs/adr/INDEX.md`）とパターンカタログ（`.planning/patterns.md`）に分離し、GSD フェーズの CONTEXT.md の canonical_refs に両ファイルを毎回記載する運用で過去意思決定を自動参照させる。INDEX.md は pre-commit hook で自動生成、patterns.md は手動更新。
関連 ADR: [0034](../docs/adr/0034-adr-catalog-patterns-md-gsd-integration.md)

### 基盤モジュールの self-bootstrap 設定（logger / emitter の silent failure 回避）
`main.py` lifespan で設定されるべき基盤系 (logger / emitter / tracer) を、module import 時に自己設定する。
`logging.getLogger("trace")` のような named logger は Python default root が WARNING のため、
handler 未 attach の状態では `logger.info()` が silently drop される。
`app/observability/trace.py` では module 末尾で `_configure_trace_logger()` を idempotent に呼び、
stdout StreamHandler + INFO level を attach する。root / uvicorn / arq logger は触らないためスコープ限定。
arq worker・pytest・ad-hoc script 等、`main.py` を経由しない import path からも自動的に稼働する副次メリットあり。
関連 ADR: [0046](../docs/adr/0046-integration-check-surfaced-silent-failures.md)

### Integration check gate（unit test green でも surface しない silent failure を捕捉）
Phase 完了前に docker compose 実環境で 1 経路以上を end-to-end 手動 / 自動操作し、
observe された実トレースを phase SUMMARY に貼付する gate。Phase 31 Wave 6 で 3 件の silent failure
(Python logging root level / LangGraph checkpointer state 復元 / route→worker シグネチャ不整合) を
unit test 60/60 green の後で初めて捕捉した経験則から、全 phase で必須化する運用。
観察結果は `docs/phase-XX-integration-check.md` として他 phase からも参照可能な形で残す。
関連 ADR: [0046](../docs/adr/0046-integration-check-surfaced-silent-failures.md)

### Milestone cleanup phase — decimal phase で帳簿整合 bookkeeping を分離
`/gsd-complete-milestone` 直前に `gsd-integration-checker` が functional PASS / 帳簿 drift を切り分けたとき、
decimal phase (例: `31.1`) を立てて bookkeeping 作業だけを集約する。
ROADMAP / REQUIREMENTS の drift は setup commit (phase 作成時) で一括修正、
VALIDATION.md backfill や新規 artifact 作成のように atomic commit が効く作業だけ plan → execute に載せる。
VALIDATION.md の遡及 `status: validated` 更新は「VERIFICATION.md が PASS 済み + Approval 行に backfill 経路明記 + `created:` 保持 / `validated:` を更新日」の 3 点セットで正当化する。
Audit レポート本体は不変（時点スナップショット）、解消は target artifact 側のみで表現。
関連 ADR: [0047](../docs/adr/0047-milestone-cleanup-phase-pattern.md)

### dev server の watch スコープを GSD worktree から隔離
GSD `isolation="worktree"` で `.claude/worktrees/agent-*` 配下にファイルが大量に生成・削除されると、`uvicorn --reload` がリロード暴発 (60s で 136 events → 401 連発 → JWT 失効)、Vite WatchFiles が transform cache 破損 (古いバンドル配信) を起こす。
api 側は `--reload-dir app` で `/app/app` のみ watch するホワイトリスト化、frontend 側は `vite.config.ts` の `server.watch.ignored` に `.claude/.planning/.git/node_modules` を明示。
`--reload-exclude` (fnmatch) は絶対パスへの再帰マッチが弱いので不採用。`docker compose restart` では `command:` 変更は反映されないため `up -d` (recreate) が必須なのも併せて記録。
関連 ADR: [0054](../docs/adr/0054-dev-server-watch-scope-narrowing-for-gsd-worktrees.md)

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

### Stdout 1 行 JSONL による observability 永続化
エージェント実行とツール呼び出しのトレースを、OpenTelemetry SDK や外部集約基盤を追加せずに
`logger.info(json.dumps(span_dict, ensure_ascii=False, default=str))` で stdout へ 1 行 1 span emit する。
docker logging driver の rotation (`max-size` / `max-file`) をそのまま永続層として使う。
社内 200 名規模・単一 docker compose クラスタ・可視化 UI 不要・CLI + jq で運用完結の運用コンテキスト向け。
鍵となる実装は `app/observability/trace.py` の `async with trace_span(...)` context manager、
`ContextVar` による親 span_id 伝搬、`RPCContext.correlation_id` を `trace_id` として再利用する構造。
関連 ADR: [0045](../docs/adr/0045-phase-31-observability-jsonl.md)

### thread-files 共有フォルダ規約
Phase 37 で導入。`/shared/thread-files/<github_login>/<thread_id>/` の 2 階層 named volume で
api:RW / mcp-server:RW / worker:RO。thread 削除 (`adelete_thread` 直後の realpath guard + `shutil.rmtree`) と同期。
ファイル命名は `YYYYMMDDTHHMMSS_<original>.<ext>`。`THREAD_FILES_DIR` 環境変数で base path を差し替え可能。
抽出失敗 0 文字 PDF は `error` ではなく `content: ""` を返す (D-08)。
Phase 36 (アップロード UI) / Phase 38 (出力ストレージ) が同じ規約で接続する。
関連 ADR: [0048](../docs/adr/0048-thread-files-folder-convention.md)

### thread-files `_generated/` サブフォルダで input/output を分離
Phase 37 で確立した `/shared/thread-files/<login>/<tid>/` 規約 (ADR-0048) を `_generated/` サブフォルダで拡張し、
ユーザーアップロード (Phase 36 入力側) と AI 生成成果物 (Phase 38 出力側) を **同 volume 内で明示分離** する。
ライフサイクルは親フォルダ単位 — thread 削除 hook (chat.delete_thread → shutil.rmtree) で `_generated/` も一括削除、新規 hook 不要。
命名規約 `YYYYMMDDTHHMMSS_{name}` は MCP tool wrapper の post-process で必ず付与し、
AI / UI / API レイヤーで同一 identity 文字列を扱う (timestamp prefix が AI 応答 / Modal URL / DL filename で共通)。
multi-user isolation は Phase 36 helper (`_resolve_thread_folder` / `_safe_resolve_file`) を outputs route が import 再利用するだけで自動継承される。
Pitfall 10 対策で `os.path.join(thread_folder, "_generated")` を `_safe_resolve_file` に渡し realpath prefix guard を `_generated/` 配下に絞る。
関連 ADR: [0052](../docs/adr/0052-worker-generated-outputs-storage-and-preview.md), [0048](../docs/adr/0048-thread-files-folder-convention.md)
