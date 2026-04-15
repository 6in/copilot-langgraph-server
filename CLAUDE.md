<!-- GSD:project-start source:PROJECT.md -->
## Project

**Copilot LangGraph Chat**

GitHub Copilot を LangGraph の AI プロバイダーとして使う、社内向け汎用チャット Web アプリ。
`ChatCopilot`（`BaseChatModel` のカスタム実装）を通じて Copilot の推論能力を活用しながら、LangGraph のグラフ構造によりエージェント化・ツール呼び出しに対応できる設計。

> **利用コンテキスト:** 社内プロジェクト向けシステム。想定ユーザー規模は **200名程度**。マルチユーザー・マルチアプリケーションの運用に耐える設計（ユーザー分離、アプリケーション管理、監査ログ）を整備中。

**Core Value:** Copilot の JSON-RPC ベース SDK を LangChain 互換プロバイダーとして動かし、アプリケーション（Chat / SuperChat / Gems / Canvas / DebateChat）＋ユーザーという単位でスレッドを管理できるチャット UI から使えること。

### Constraints

- **Tech Stack**: Python（LangChain / LangGraph / Copilot SDK） — ドキュメントのサンプルコードが Python ベース
- **Auth**: Device Flow のみ — 非インタラクティブ環境向け PAT 方式は今回対象外
- **SDK 安定性**: Copilot SDK は Technical Preview — 外部インターフェースを薄いラッパーで隔離しておく
- **スケール感**: 200名規模・社内利用 — 高トラフィック対策より運用性（監査ログ・アプリ管理）を優先する
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

| Category | Technology | Purpose |
|----------|-----------|---------|
| Runtime | Python 3.12 | メイン実行環境 |
| AI Framework | `langgraph` | Stateful conversation graph・ReAct ループ |
| AI Framework | `langchain-core` | `BaseChatModel`・メッセージ型・ToolNode |
| AI Framework | `langchain-community` | TavilySearchResults 等の外部ツール統合 |
| Custom Provider | `github-copilot-sdk` 0.2.0 (pinned) | Copilot JSON-RPC クライアント（Technical Preview） |
| MCP | `fastmcp` | MCP サーバー実装（mcp_server/） |
| MCP | `langchain-mcp-adapters` | MCP ツール → LangChain BaseTool 変換 |
| Web Backend | `fastapi` + `uvicorn` | HTTP + SSE API サーバー |
| Frontend | React 19 + TypeScript + Vite | SPA チャット UI |
| Frontend | `@chatscope/chat-ui-kit-react` | チャット UI コンポーネント |
| Frontend | Bun | フロントエンドのパッケージマネージャー（Docker） |
| Persistence | PostgreSQL + `langgraph-checkpoint-postgres` | 会話スレッド永続化 |
| Job Queue | Redis + `arq` | バックグラウンドジョブキュー |
| Auth | JWT HS256 + Device Flow | httpOnly cookie 認証 |
| Packaging | `uv` + `pyproject.toml` | 依存管理・仮想環境 |
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

### 応答言語

**すべての応答は日本語で行うこと。** GSD ワークフロー（バナー・チェックポイント・Next Up ブロックなど）を含め、ユーザーへの出力は日本語を使用する。コードやコマンド、ファイルパス、技術的な固有名詞はそのまま英語で記載してよい。

### Merge Workflow

「マージして」と指示された場合、マージを実行する前に必ず次を確認する:

> 「`/create-adr` でこのブランチの振り返りを記録しますか？」

- 了解なら `/create-adr` を実行してから マージへ進む
- 不要なら即マージへ進む

マージは **squash merge** で行う（作業ブランチの細かいコミットを1つにまとめる）:

```bash
git checkout main
git merge --squash <branch>
git commit -m "feat(phase-XX): <内容の要約>"
git branch -D <branch>
```

`git merge --no-edit` や Fast-forward merge は使わない。

マージ完了後、不要な worktree を削除する:

```bash
git worktree list
# main 以外の worktree があれば削除
git worktree remove <path>          # 変更なしの場合
git worktree remove --force <path>  # 強制削除が必要な場合
git worktree prune                  # 参照だけ残っているゴミを掃除
```

### ADR Pattern Reference (GSD Integration)

`/gsd-discuss-phase` を実行する際は、CONTEXT.md の `canonical_refs` セクションに以下の 2 ファイルを必ず追加すること:

- `.planning/patterns.md` — ADR 由来のパターンカタログ（設計判断の前に参照）
- `docs/adr/INDEX.md` — ADR カテゴリ別索引（関連 ADR 特定に使用）

これにより `/gsd-research-phase` と `/gsd-plan-phase` が過去の意思決定パターンを自動的に参照できる。
`@import` 形式での常時ロードはしない（コンテキスト肥大回避 — D-12）。必要なフェーズでのみ canonical_refs 経由で読み込む。

**新規 ADR 追加時の義務:**

- `/create-adr` で新規 ADR を作成した直後、パターンとして記録すべき設計判断があれば `.planning/patterns.md` に**手動で追記**する（D-15）
- patterns.md は自動生成しない — 要約の粒度は人間判断が必要
- ADR にないパターンは patterns.md に載せない（ADR が唯一の真実源 — D-08）
- 1 エントリは 5-10 行（パターン名 + 要約 + 関連 ADR リンク）
- カテゴリは 7 種: `Auth` / `LangGraph・Graph` / `MCP・Tools` / `Worker・Jobs` / `Frontend・UI` / `Infra・Deploy` / `Data・Persistence`
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

### Backend (Python / FastAPI)

```
app/
  api/
    main.py               — FastAPI app factory, lifespan, CORS, static mounts
    models.py             — Pydantic request/response models
    routes/
      auth.py             — Device Flow OAuth + JWT login/logout
      chat.py             — POST /api/chat (enqueue), GET /api/chat/history
      jobs.py             — GET /api/job/{id}, GET /api/job/{id}/stream (SSE)
      me.py               — GET /api/me (GitHub user info)
      agents.py           — GET /api/agents (SubAgentRegistry リスト)
      gems.py             — Gems CRUD
      canvas.py           — Canvas アプリ管理
      apps.py             — Canvas apps 一覧
      hosted_apps.py      — /apps/{app-id}/ ホスティング
      iframe_rpc.py       — iframe postMessage JSON-RPC ブリッジ
      health.py           — GET /health (ヘルスチェック)
  auth/
    jwt_utils.py          — JWT HS256 encode/decode, JTI blocklist
    manager.py            — CopilotAuthManager (Device Flow + token encryption)
  graph/
    builder.py            — LangGraph StateGraph (chat 用シンプルグラフ)
  jobs/
    job_store.py          — In-memory job result store with asyncio.Queue SSE
    notifier.py           — SSE notification bridge (worker -> client)
    worker.py             — arq worker: process_chat + MCP Singleton 管理
    handlers/
      base.py             — TaskHandler 基底クラス
      langgraph_handler.py    — Chat / Canvas 用 LangGraph handler
      orchestrator_handler.py — SuperChat 用 OrchestratorGraph handler
      debate_handler.py       — DebateChat 用 handler
      iframe_rpc_handler.py   — iframe RPC 用 handler
  orchestrator/
    state.py              — AgentState (TypedDict)
    context.py            — RPCContext (user_id, app_id, thread_id)
    agent.py              — SubAgent, SubAgentRegistry (AGENT.md 自動ロード)
    tool_agent.py         — ToolEnabledSubAgent, build_react_graph (ReAct ループ)
    graph.py              — OrchestratorGraph (Router → SubAgent → END)
    gem_agent.py          — GemAgent (Gem 設定ベースのエージェント)
    debate_graph.py       — DebateGraph
    dispatcher.py         — タスクタイプ別ハンドラールーティング
    script_backend.py     — Script ベースツール実行
    apps.py               — Canvas アプリ管理ロジック
  providers/
    copilot.py            — ChatCopilot + BoundChatCopilot (BaseChatModel wrapper)

mcp_server/
  server.py               — FastMCP サーバー本体
  tools/
    stubs.py              — ping / web_search_stub / db_query_stub / claude_code_stub
```

### Frontend (React 19 + TypeScript + Vite)

```
frontend/src/
  App.tsx                 — Root component, AuthContext.Provider, 画面ルーティング
  main.tsx                — ReactDOM entry point
  types.ts                — 共有 TypeScript 型定義
  api/
    client.ts             — apiFetch wrapper (JWT cookie auth)
  components/
    AuthPanel.tsx         — Device Flow login UI
    MenuScreen.tsx        — アプリ選択メニュー
    ChatApp.tsx           — 通常チャット
    SuperChatApp.tsx      — SuperChat（エージェント切り替え）
    GemChatApp.tsx        — Gem チャット
    GemsScreen.tsx        — Gem 一覧・管理
    GemSelector.tsx       — Gem 選択コンポーネント
    CanvasChatApp.tsx     — Canvas チャット
    CanvasPane.tsx        — iframe Canvas プレビュー
    CanvasScreen.tsx      — Canvas アプリ一覧
    DebateChatApp.tsx     — DebateChat
    Header.tsx            — ヘッダー（ユーザー情報・ダーク/ライト切替）
    MarkdownMessage.tsx   — Markdown + シンタックスハイライト
    MessageArea.tsx       — メッセージリスト + 入力欄
    ThreadSidebar.tsx     — スレッド一覧・CRUD
    ConfirmModal.tsx      — 確認ダイアログ
  contexts/
    ThemeContext.ts       — ダーク/ライトモード
  hooks/
    useAuth.ts            — 認証状態管理
    useChat.ts            — チャット送受信 + SSE ジョブポーリング
    useThreads.ts         — スレッド CRUD
    useAgents.ts          — エージェント一覧取得
    useGems.ts            — Gem CRUD
    useCanvas.ts          — Canvas アプリ管理
    useTheme.ts           — テーマ切り替え
  utils/
    agentColor.ts         — エージェント別カラーマッピング
```

### Infrastructure

- Docker Compose: FastAPI + PostgreSQL + Redis + React frontend (Bun/Vite) + MCP server
- **Primary startup method: `docker compose up`** — direct `uvicorn` / `bun run dev` は使わない
- **開発時アクセス URL: `http://localhost:5173/orochi/`**（Vite dev server）
- React UI: Vite dev server が `/api` を FastAPI にプロキシ（開発時）、`frontend/dist/` を FastAPI が配信（本番）
- MCP server: `mcp-server:8001`（内部ネットワーク専用、worker から streamable-http でアクセス）
- Reverse-proxy URL prefix (e.g. `/orochi`) は `APP_PREFIX`（FastAPI）+ `VITE_APP_BASE`（Vite）で設定; nginx がプレフィックスを strip して転送 — `docs/nginx.md` 参照

### Key Patterns

- **Async-first**: 全ルートが `async def`、arq worker でバックグラウンドジョブ
- **SSE** でジョブ完了通知（WebSocket 不使用）
- **JWT HS256** を httpOnly cookie に格納して認証
- **ChatCopilot**: Copilot SDK を `BaseChatModel` インターフェースでラップ
- **BoundChatCopilot**: `bind_tools()` でツールスキーマをシステムプロンプトに注入し、JSON レスポンスを `AIMessage(tool_calls=[...])` に変換
- **ToolEnabledSubAgent**: LangGraph mini ReAct グラフ（agent → ToolNode → agent → END）でツール呼び出しループを実行
- **SubAgentRegistry**: `agents/*/AGENT.md` を自動ロード。`tools:` フラグ + `mcp_tools` があれば `ToolEnabledSubAgent` を生成
- **MCP Singleton**: `worker.startup()` で `MultiServerMCPClient` を初期化し `ctx["mcp_tools"]` に格納。接続失敗時は `[]` で DEGRADED 継続
- **LangGraph checkpointer**: `AsyncConnectionPool`（PostgreSQL）で会話スレッドを永続化。起動時にコンパイル、ライフサイクルは caller が管理
<!-- GSD:architecture-end -->

## Chrome DevTools MCP

`chrome-devtools` MCP（`.mcp.json`）は `http://127.0.0.1:9222` で動作する Chromium に接続する。

### Chromium の起動

chrome-devtools MCP を使う前に、Chromium がリモートデバッグモードで起動していることを確認する。

**起動コマンド（ユーザーが手動実行）:**
```bash
chromium --remote-debugging-port=9222 --no-first-run --no-default-browser-check &
```

**Claude が使う前に確認すべきこと:**

1. 起動確認:
   ```bash
   curl -s http://127.0.0.1:9222/json/version
   ```
2. 接続できない（エラーまたは空レスポンス）場合は、ユーザーに以下を依頼する:
   ```
   ! chromium --remote-debugging-port=9222 --no-first-run --no-default-browser-check &
   ```
   `!` プレフィックスでセッション内実行できる。
3. 起動確認後、chrome-devtools ツールを使用する。

<!-- GSD:workflow-start source:GSD defaults -->
## Merge Safety Rules

worktree マージを実行する前に必ず以下を確認すること。**これを省くと大量削除マージが起きる。**

### マージ前チェックリスト

```bash
# 1. マージ対象ブランチの起点が正しいか確認
git merge-base <worktree-branch> <current-branch>
# → current-branch の HEAD と一致していなければマージしない

# 2. 削除・変更ファイル数を事前確認
git diff --stat HEAD <worktree-branch>
# → 削除行数が追加行数を大きく上回る場合は必ず内容を精査する

# 3. アプリコードの削除が含まれていないか確認
git diff --name-only --diff-filter=D HEAD <worktree-branch> | grep -v "^\.planning/"
# → .planning/ 以外のファイルが削除される場合は手動で一件ずつ確認
```

### 判断基準

| 状況 | 対応 |
|------|------|
| 削除ファイルが `.planning/` のみ | 通常マージしてよい |
| アプリコード（`app/`, `static/`, `tests/` 等）が削除される | **必ず理由を確認してからマージ** |
| 削除行数 > 追加行数 × 2 | **ストップ。worktree の起点ブランチを確認する** |
| `.continue-here.md` が別ブランチのもの | マージ後すぐに削除 |

### なぜこのルールが必要か

2026-04-10 の Phase 20 実行時、`isolation="worktree"` で生成された worktree が `main` を起点にしていたため、`gsd/phase-20-fastmcp-docker` との差分が大量削除マージとして現れた（81 files, 8933 deletions）。`static/js/iframe-rpc.js` 削除・Canvas アプリエラー等のデグレが発生した。ワークフロー手順の実行に集中し、マージ結果が目的と整合しているか検証しなかったことが根本原因。

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.

**ブランチ必須:** `/gsd:quick`・`/gsd:execute-phase`・`/gsd:debug`・`/gsd:do` など GSD コマンドで作業を開始する際は、必ず最初にブランチを作成すること。`main` ブランチ上で直接コミットしない。

### ADR INDEX 自動生成 hook のインストール

`docs/adr/INDEX.md` は `scripts/generate_adr_index.py` により自動生成される。新規クローン直後は以下を 1 回実行して pre-commit hook を有効化すること:

```bash
bash scripts/install-hooks.sh
```

これにより `docs/adr/NNNN-*.md` がコミットに含まれる際、hook が自動で `INDEX.md` を再生成・ステージングする。
カテゴリマッピングは `.planning/adr-categories.yaml` で管理する。新規 ADR を追加したら YAML にも番号とカテゴリを追記すること。
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
