# Phase 9: SuperChat メインアプリ統合 - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

`super-agent-sample/` で実証した OrchestratorGraph + SubAgent + MenuDispatcher アーキテクチャを
`app/` に統合し、既存の Chat 機能と共存させる。

具体的には:
- `app/orchestrator/` モジュールを新設し、super-agent-sample/src/ から移植・リファクタリング
- 既存 `/api/chat` エンドポイントに `mode` パラメータ（`'simple'` / `'super'`）を追加
- `agents/` と `menus/` はリポジトリルートのファイルを流用
- React UI にモードトグルを追加し、`mode` をリクエストに含める

**スコープ外（このフェーズには含めない）:**
- 新規エージェント定義の追加
- LangGraph ツール呼び出し（bind_tools）
- ストリーミング応答
- Vanilla JS UI 側のモード対応（React UI のみ）

</domain>

<decisions>
## Implementation Decisions

### Module Placement

- **D-01:** orchestrator コードは `app/orchestrator/` に新設する
  - `agent.py` (SubAgent, SubAgentRegistry)
  - `graph.py` (RouterNode, OrchestratorGraph, build_orchestrator_graph, build_simple_graph)
  - `dispatcher.py` (MenuRegistry, MenuDispatcher)
  - `state.py` (AgentState)
- **D-02:** `super-agent-sample/src/` にあったスタンドアロンの `chat_copilot.py` / `auth_manager.py` コピーは削除し、
  `app/providers/copilot.py` と `app/auth/manager.py` を直接 import する形に修正する
- **D-03:** `super-agent-sample/` ディレクトリはサンプルとして維持（削除しない）

### API Surface

- **D-04:** 既存の `POST /api/chat` に `mode: Literal['simple', 'super'] = 'simple'` を追加する
  - `mode` を省略した既存クライアントは引き続き `'simple'`（既存 LangGraph）で動作する
  - `mode='super'` を指定した場合は OrchestratorGraph 経由でルーティングする
- **D-05:** arq worker の `process_chat` 関数内で `mode` に応じてグラフを選択する
  - `simple` → 既存の `app.state.graph`（build_graph の結果）
  - `super` → OrchestratorGraph（起動時に初期化して `app.state.orchestrator_graph` に保存）
- **D-06:** ジョブ返却・SSE・ポーリングのパターンは変えない（同一 `/api/job/{id}` / `/api/job/{id}/stream`）

### Agent/Menu Files Location

- **D-07:** `agents/` と `menus/` ディレクトリはリポジトリルートに置く（super-agent-sample/ から移動またはシンボリックリンク不使用で直接配置）
  - Docker Compose では volume mount で `/app/agents` / `/app/menus` として参照
  - SubAgentRegistry と MenuRegistry のパスは環境変数 `AGENT_DIR`（デフォルト: `./agents`）と `MENU_DIR`（デフォルト: `./menus`）で設定可能にする

### Frontend Coexistence

- **D-08:** React UI のメッセージ入力エリアにモードトグル（`💬 Simple` / `🚀 Super`）を追加する
  - デフォルトは `simple`
  - トグル状態は React ローカル state で管理（スレッドに紐付けない）
  - `useChat` フックの `sendMessage` が `mode` を受け取り、POST /api/chat に含める

### Claude's Discretion

- `AgentState` と既存 `MessagesState` の相互変換の具体的実装（orchestrator が完了したら result を MessagesState 形式に変換するか、独立した AgentState のまま返すか）
- lifespan での OrchestratorGraph 初期化の具体的コード
- モードトグルの UI 配置（送信ボタン横 or 入力欄上部）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 8 成果物（移植元）
- `super-agent-sample/src/agent.py` — SubAgent, SubAgentRegistry 実装（ChatCopilot + CopilotAuthManager 使用版）
- `super-agent-sample/src/graph.py` — RouterNode, OrchestratorGraph, build_orchestrator_graph, build_simple_graph
- `super-agent-sample/src/dispatcher.py` — MenuRegistry, MenuDispatcher
- `super-agent-sample/src/state.py` — AgentState TypedDict
- `super-agent-sample/agents/` — code-reviewer / sql-analyst の AGENT.md サンプル
- `super-agent-sample/menus/` — super-chat.yaml / simple-chat.yaml サンプル

### 既存メインアプリ（統合先）
- `app/api/main.py` — FastAPI lifespan, app.state 管理、既存モジュール構成
- `app/api/routes/chat.py` — POST /api/chat の現在の実装
- `app/jobs/worker.py` — arq worker の process_chat 関数
- `app/providers/copilot.py` — ChatCopilot（移植コードが import すべき本家）
- `app/auth/manager.py` — CopilotAuthManager（同上）
- `app/graph/builder.py` — build_graph（simple モードで引き続き使用）

### フロントエンド
- `frontend/src/hooks/useChat.ts` — sendMessage の現在の実装
- `frontend/src/components/MessageArea.tsx` — メッセージ入力エリア（トグル追加箇所）

### 仕様・設計
- `docs/pre/phase1_spec.md` — OrchestratorGraph アーキテクチャの原典仕様

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/providers/copilot.py`: ChatCopilot — super-agent-sample のスタンドアロンコピーと同等（移植コードはこちらを import する）
- `app/auth/manager.py`: CopilotAuthManager — 同上
- `app/jobs/worker.py`: process_chat — mode パラメータを受け取るよう拡張するベースコード
- `app/jobs/job_store.py`: JobStore — ジョブ結果保存（変更不要）
- `frontend/src/hooks/useChat.ts`: sendMessage — mode: string を追加するだけで対応可

### Established Patterns
- arq worker でのグラフ実行: `app.state.graph` からグラフを取得して `ainvoke()` — orchestrator も同じ pattern で `app.state.orchestrator_graph` を使う
- lifespan での初期化: `app.state.X = ...` パターン — orchestrator_graph も lifespan で初期化
- API モデル: `app/api/models.py` の Pydantic モデル — ChatRequest に `mode` フィールドを追加

### Integration Points
- `app/api/main.py` lifespan: OrchestratorGraph の初期化を追加
- `app/jobs/worker.py` process_chat: mode による分岐ロジックを追加
- `app/api/routes/chat.py`: ChatRequest モデルに mode フィールドを受け取る
- `frontend/src/hooks/useChat.ts`: POST body に mode を追加

</code_context>

<specifics>
## Specific Ideas

- ブランチ名: `feat/phase-09-superchat-integration`（または類似）
- モードトグルのアイコン: `💬 Simple` / `🚀 Super`（ユーザー指定通り）
- `AGENT_DIR` / `MENU_DIR` 環境変数: Docker Compose の `api` / `worker` サービスに追加

</specifics>

<deferred>
## Deferred Ideas

- Vanilla JS UI 側のモード対応 — Phase 9 スコープ外、必要なら将来フェーズ
- 新規エージェント定義の追加 — agents/ の中身は現在のサンプルエージェントをそのまま使用
- LangGraph checkpointer を OrchestratorGraph にも適用（AgentState の会話履歴永続化）— v2 候補

### Reviewed Todos (not folded)
- 「チャットのコンテキストにてユーザー情報も入れるようにする」— スコープ外。Phase 9 は mode 切り替えに集中。将来フェーズで対応。

</deferred>

---

*Phase: 09-superchat-orchestratorgraph-app-chat*
*Context gathered: 2026-04-04*
