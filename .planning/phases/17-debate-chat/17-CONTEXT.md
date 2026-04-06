# Phase 17: マルチエージェント討論チャット — ターン制マルチエージェント会話プラットフォーム - Context

**Gathered:** 2026-04-06 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

複数の Gem / SubAgent をターン制で会話させる新アプリ「討論チャット」を実装する。ユーザーが会話パターン（討論・パネル・チェーン）と参加エージェントを選択し、お題を投稿すると、指定ターン数でエージェント同士が順番に発言する。討論終了後にユーザーが延長を承認できる。

### このフェーズで実装すること

1. **DebateGraph** — OrchestratorGraph とは独立した新しい LangGraph StateGraph（ラウンドロビン型）
2. **DebateHandler** — arq worker に登録する新ハンドラー（task_type="debate"）
3. **DebateChatApp** — パターン選択・参加エージェント選択・ターン制チャット UI
4. **API 拡張** — ChatRequest に `participants`, `pattern`, `max_turns` フィールド追加

### スコープ外

- OrchestratorGraph / SuperChat への変更
- エージェント別カラー表示（MVP はプレフィックス方式）
- 討論結果のサマリー自動生成（将来フェーズ候補）

</domain>

<decisions>
## Implementation Decisions

### グラフトポロジー

- **D-01:** `DebateGraph` は `app/orchestrator/debate_graph.py` に `build_debate_graph(participants, pattern, max_turns, llm, checkpointer=None)` ファクトリ関数として実装する。OrchestratorGraph から独立した完全に新しい `StateGraph`
- **D-02:** 3パターン（debate/panel/chain）は同一の `build_debate_graph` 関数で実装し、`pattern` パラメータによってエッジ構造を分岐させる。パターン別に独立グラフを作らない
- **D-03:** `DebateState` は独自 TypedDict として定義する（`AgentState` は継承しない）。必要フィールド: `turn: int`, `max_turns: int`, `pattern: str`, `participants: list[str]`, `messages: Annotated[list[BaseMessage], operator.add]`, `current_agent_idx: int`, `awaiting_extension: bool`
- **D-04:** 討論パターン（debate）: A→B→A→B→...のラウンドロビン後 → aggregator → END。チェーン（chain）: A→B→C→END。パネル（panel）: A・B・C を順次実行後 → aggregator → END（並列は arq の単一タスク前提で順次で代用）

### ターン制御と延長承認

- **D-05:** ターン終了後の延長承認は **再エンキュー方式** で実装する。`interrupt_before` は採用しない（arq バックグラウンド worker との相性が悪いため）
- **D-06:** フロントエンドがターン終了を検知したら「延長しますか？」UI を表示し、ユーザーが承認すると追加 `max_turns` を付けて同一 `thread_id` で再度 `POST /api/chat` を送る
- **D-07:** DebateGraph は LangGraph checkpointer を使い、`thread_id` をキーに会話履歴を継続する（再エンキュー時に過去の発言が失われないようにする）

### ハンドラー設計

- **D-08:** `task_type="debate"` を新規登録。`app/jobs/handlers/debate_handler.py` として `DebateHandler` を実装し、`worker.py` の `TASK_HANDLERS` dict に1行追加
- **D-09:** `ChatRequest` に `participants: list[str] | None = None`, `pattern: str = "debate"`, `max_turns: int = 3` を追加。`agents` フィールドとは独立（意味が異なる）
- **D-10:** `process_chat` 関数のシグネチャに同フィールドを追加し、`job` dict に含めて `DebateHandler` に渡す

### フロントエンド

- **D-11:** `frontend/src/components/DebateChatApp.tsx` を新規作成。`SuperChatApp.tsx` を参考パターンとして `useThreads`, `useChat`, `MessageArea`, `ThreadSidebar` を流用
- **D-12:** `App.tsx` の `Screen` 型に `'debate'` を追加し、`MenuScreen` からナビゲートできるようにする
- **D-13:** 各エージェントの発言は `[エージェント名]: 発言内容` プレフィックス形式で既存 `MessageArea` に積み上げる（MVP）。`ChatMessage` 型の変更なし
- **D-14:** DebateChatApp の設定 UI: パターン選択（debate/panel/chain）ラジオ + 参加エージェント/Gem チェックリスト + ターン数入力。チャット開始前に1回だけ設定する

### Claude's Discretion

- aggregator ノードの実装（専用 LLM コールで統合するか、最後のエージェントが自然に締めるか）
- DebateChatApp の設定 UI の具体的なスタイリング
- ターン終了の検知方法（DebateHandler が job result に `status: "turn_complete"` を含めるか、通常の `done` と同じにするか）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### バックエンド — グラフ・ハンドラーパターン
- `app/orchestrator/graph.py` — build_orchestrator_graph() ファクトリ関数パターン（DebateGraph の参照実装）
- `app/orchestrator/state.py` — AgentState 定義（DebateState の設計参照）
- `app/orchestrator/agent.py` — SubAgent インターフェース（run(state) パターン）
- `app/orchestrator/gem_agent.py` — GemSubAgent（Gem をエージェントとして使う実装）
- `app/jobs/handlers/orchestrator_handler.py` — DebateHandler の参照実装
- `app/jobs/worker.py` — TASK_HANDLERS 登録パターン・process_chat シグネチャ

### バックエンド — API
- `app/api/models.py` — ChatRequest モデル（participants/pattern/max_turns 追加箇所）
- `app/api/routes/chat.py` — POST /api/chat・enqueue_job 呼び出しパターン

### フロントエンド
- `frontend/src/components/SuperChatApp.tsx` — DebateChatApp の参照実装
- `frontend/src/App.tsx` — Screen 型・navigate パターン
- `frontend/src/components/MenuScreen.tsx` — アプリカード追加パターン
- `frontend/src/hooks/useChat.ts` — sendMessage・gem_ids/agents 送信パターン
- `frontend/src/types.ts` — ChatMessage 型・ChatRequest インターフェース

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `OrchestratorHandler.handle()` — DebateHandler の骨格として流用。DB 接続・registry 構築・llm 初期化パターンが再利用可能
- `GemSubAgent` / `SubAgent` — 討論参加者として使う既存クラス。`run(state)` インターフェースがそのまま使える
- `useThreads`, `useChat`, `MessageArea`, `ThreadSidebar` — DebateChatApp で流用するフック・コンポーネント
- `AgentSelector.tsx` + `GemSelector.tsx` — 参加エージェント/Gem 選択 UI の参照実装
- LangGraph checkpointer (`AsyncPostgresSaver`) — DebateGraph でも同じ checkpointer を使い thread_id で会話継続

### Established Patterns

- `build_graph(llm, checkpointer)` ファクトリ関数パターン — グラフはコンパイル済みを渡す、checkpointer は呼び出し側管理
- arq job dict — handler は `job.get("key")` でパラメータ取得
- `Screen` 型 + `handleNavigate()` — 新アプリ追加のフロントエンドパターン
- SSE + polling — job 完了通知の既存インフラ（再エンキュー方式でそのまま流用）

### Integration Points

- `worker.py:TASK_HANDLERS` — DebateHandler の登録場所
- `app/api/models.py:ChatRequest` — participants/pattern/max_turns フィールド追加
- `process_chat()` シグネチャ — 同フィールドを arq 引数として追加
- `frontend/src/App.tsx:Screen` 型 + `MenuScreen` — DebateChatApp へのナビゲーション追加

</code_context>

<specifics>
## Specific Ideas

- ターン数のデフォルトは 3（各エージェントが3回ずつ発言）
- 延長時は「あと N ターン」を入力できる UI
- 討論終了後の集計: 将来フェーズ候補（今回は各エージェントの発言をそのまま表示するだけ）
- Gem のみ・SubAgent のみ・混在のいずれの参加者構成でも動作すること

</specifics>

<deferred>
## Deferred Ideas

- エージェント別カラーバブル表示 — MVP はプレフィックス方式、次フェーズで強化
- 討論サマリーの自動生成（「この討論の結論は...」） — 将来フェーズ
- 討論結果の保存・共有機能 — 将来フェーズ
- パネル型の真の並列実行（asyncio.gather） — 現状は arq 単一タスクで順次代用
- LangGraph interrupt_before による中断・再開パターン — arq との統合研究が必要

</deferred>

---

*Phase: 17-debate-chat*
*Context gathered: 2026-04-06*
