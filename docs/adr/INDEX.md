# ADR Index

**Total:** 40 件（欠番 3 件: 0015, 0016, 0017）

> このファイルは `scripts/generate_adr_index.py` により自動生成されます。手動編集しないこと。

## Auth

| No. | タイトル | Date |
|-----|---------|------|
| [0014](0014-phase17-security-hardening-jwt-blocklist-redis-and-endpoint-auth.md) | Phase 17 セキュリティ強化 — JWT ブロックリスト Redis 移行と未認証エンドポイントの修正 | 2026-04-07 |

## LangGraph・Graph

| No. | タイトル | Date |
|-----|---------|------|
| [0004](0004-super-agent-sample-standalone-with-chatcopilot.md) | Super-Agent サンプルをスタンドアロン実装し ChatCopilot を利用する | 2026-04-03 |
| [0005](0005-orchestratorgraph-integration-per-job-construction.md) | OrchestratorGraph Integration — Per-Job Construction over Shared State | 2026-04-04 |
| [0007](0007-application-packages-app-md-pattern.md) | Application Packages — APP.md Definition Pattern | 2026-04-05 |
| [0011](0011-debate-chat-multi-agent-turn-based-platform.md) | マルチエージェント討論チャット — ターン制会話プラットフォーム | 2026-04-06 |
| [0021](0021-langgraph-bind-tools-toolnode-via-prompt-engineering.md) | LangGraph bind_tools + ToolNode の実装: プロンプトエンジニアリング方式 | 2026-04-10 |
| [0025](0025-datetime-and-user-context-injection-into-agent-prompts.md) | 全エージェントへの現在日時・ログインユーザー自動注入 | 2026-04-13 |
| [0031](0031-copilot-sdk-token-streaming-three-layer-plumbing.md) | Copilot SDK トークンストリーミング実装 — 3 層配管の発見と修正 | 2026-04-15 |
| [0038](0038-superchat-context-messages-and-agent-name-persistence.md) | SuperChat 過去メッセージコンテキスト注入とエージェント名永続化 | 2026-04-16 |
| [0042](0042-user-model-override-propagation-to-subagents.md) | SuperChat ユーザー選択モデルを SubAgent デフォルトより優先する `model_override` 伝播 | 2026-04-18 |

## MCP・Tools

| No. | タイトル | Date |
|-----|---------|------|
| [0020](0020-fastmcp-docker-service-infrastructure.md) | FastMCP Docker サービス基盤 (Phase 20) | 2026-04-10 |
| [0022](0022-tavily-web-search-json-tool-calling-model-compatibility.md) | Tavily Web Search と JSON ベースツール呼び出しのモデル互換性 | 2026-04-13 |
| [0023](0023-mcp-db-query-and-claude-code-tools.md) | MCP ツール本番実装 — db_query（SELECT-only ガード）と claude_code（サブプロセス + env sanitization） | 2026-04-13 |
| [0024](0024-mcp-tool-catalog-validation.md) | MCP ツールカタログ検証（ToolRegistry）と関連バグ修正 | 2026-04-13 |
| [0030](0030-canvas-db-access-via-mcp-db-query.md) | Canvas DB アクセスを MCP db_query ツール経由に移行 | 2026-04-14 |
| [0041](0041-codeact-direct-execution-over-react.md) | CodeAct は ReAct ループではなく直接実行方式を採用する | 2026-04-18 |

## Worker・Jobs

| No. | タイトル | Date |
|-----|---------|------|
| [0003](0003-worker-pluggable-task-routing-facade.md) | Worker Pluggable Task Routing Facade | 2026-04-03 |

## Frontend・UI

| No. | タイトル | Date |
|-----|---------|------|
| [0002](0002-api-path-prefix-management-in-react-spa.md) | API Path Prefix Management in React SPA | 2026-04-03 |
| [0006](0006-superchat-agent-selection-ui-and-mode-split.md) | SuperChat Agent Selection UI and Mode Split | 2026-04-04 |
| [0008](0008-gem-ux-navigation-gemchatapp-screen-model.md) | Gem UX ナビゲーション — GemsScreen・GemChatApp・4画面スクリーンモデル | 2026-04-06 |
| [0009](0009-gem-ux-navigation-and-thread-isolation.md) | Gem UX 強化 — 専用ナビゲーション・スレッド分離・description/knowledge フィールド | 2026-04-06 |
| [0012](0012-gemchatapp-flex-layout-height-fix.md) | GemChatApp フレックスレイアウト修正 — height:100% から flex:1/minHeight:0 へ | 2026-04-07 |
| [0013](0013-agent-identity-in-chat-ui-color-and-name.md) | Agent Identity in Chat UI — Per-Agent Color and Name Display | 2026-04-08 |
| [0018](0018-canvas-iframe-postmessage-json-rpc-bridge.md) | Canvas iframe postMessage JSON-RPC ブリッジ | 2026-04-09 |
| [0019](0019-canvas-app-standalone-hosting-parent-bridge.md) | Canvas アプリのスタンドアロンホスティングと parent-bridge.js 共通化 | 2026-04-09 |
| [0027](0027-migrate-frontend-runtime-from-nodejs-to-bun.md) | フロントエンドランタイムを Node.js/npm から Bun に移行 | 2026-04-14 |
| [0028](0028-react-router-v7-url-based-routing-for-spa.md) | React Router v7 による URL ベースルーティングの導入 | 2026-04-14 |
| [0029](0029-ui-todo-batch-orochi-branding-canvas-debate-fixes.md) | UI Todo バッチ実装 — Orochi ブランディング・Canvas/DebateChat 機能改善 | 2026-04-14 |
| [0033](0033-canvas-ai-model-selection-with-alias-whitelist.md) | Canvas iframe RPC `ai()` モデル指定機能とエイリアスホワイトリスト | 2026-04-15 |
| [0037](0037-chat-ui-batch-enhancements.md) | チャット UI 一括機能強化（レンダリング・操作・AG Grid） | 2026-04-16 |
| [0039](0039-askuserquestion-auq-protocol.md) | AskUserQuestion — AI-UI 対話的質問プロトコル | 2026-04-18 |
| [0040](0040-ui-improvements-batch-mermaid-copy-thread-grouping-authflow.md) | UI 改善バッチ — Mermaid 画像コピー・スレッド日付グループ・Device Flow UX・ツールカタログ埋め込み | 2026-04-17 |
| [0043](0043-chat-history-content-normalization-defense-in-depth.md) | チャット履歴の BaseMessage.content 正規化と ReactMarkdown 防御ガード（defense-in-depth） | 2026-04-18 |

## Infra・Deploy

| No. | タイトル | Date |
|-----|---------|------|
| [0001](0001-nginx-prefix-strip-for-url-routing.md) | nginx prefix-strip approach for URL routing | 2026-04-03 |
| [0034](0034-adr-catalog-patterns-md-gsd-integration.md) | ADR カタログ化と patterns.md による GSD プランニング統合 | 2026-04-15 |
| [0035](0035-architecture-slides-generated-by-python-pptx.md) | アーキテクチャ説明資料を python-pptx で生成する | 2026-04-15 |

## Data・Persistence

| No. | タイトル | Date |
|-----|---------|------|
| [0010](0010-gem-public-sharing-is-public-flag.md) | Gem 公開共有機能 — is_public フラグと Shared Gems セクション | 2026-04-06 |
| [0026](0026-thread-deletion-also-removes-threads-table-row.md) | スレッド削除時に threads テーブルの行も削除する | 2026-04-14 |
| [0032](0032-db-pools-yaml-driven-tuning-params.md) | db_pools.yaml 駆動の接続プールチューニングパラメータ | 2026-04-15 |

## 欠番

| No. | 備考 |
|-----|------|
| 0015 | — 欠番 — |
| 0016 | — 欠番 — |
| 0017 | — 欠番 — |
