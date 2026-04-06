# Phase 16: SuperChat × Gem 招待 — Gem をプロンプトエージェントとして OrchestratorGraph に統合 - Context

**Gathered:** 2026-04-06 (assumptions mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

SuperChat のオーケストレーターが、`./agents/`（ツールエージェント）と Gem（プロンプトエージェント）の両方をルーティング候補として扱えるようにする。ユーザーは SuperChat チャット開始時に招待する Gem を選択でき、OrchestratorGraph が動的に GemSubAgent ラッパーを生成して通常の SubAgent と同じインターフェースで処理する。

### このフェーズで実装すること

1. **GemSubAgent クラス** — 独立クラスとして `run(state: AgentState) -> AgentState` を実装する軽量ラッパー
2. **OrchestratorHandler 拡張** — `gem_ids` を受け取り、DB から Gem を取得して `registry.agents` にマージ
3. **API 拡張** — `ChatRequest` に独立した `gem_ids: list[str] | None = None` フィールドを追加
4. **フロントエンド** — SuperChatApp に独立した `GemSelector` コンポーネント + `useGems` フックを追加

### スコープ外

- GemSubAgentRegistry クラスの新設（Handler 内で直接処理）
- Canvas 関連機能の変更
- Gem 招待なしの SuperChat 動作への変更（後方互換必須）

</domain>

<decisions>
## Implementation Decisions

### GemSubAgent クラス設計

- **D-01:** `GemSubAgent` は `app/orchestrator/agent.py`（または新規 `app/orchestrator/gem_agent.py`）に独立クラスとして実装する。`SubAgent` は継承しない
- **D-02:** コンストラクタは `(name, description, system_prompt, knowledge, llm)` を受け取る。`system_prompt` + `knowledge` を結合してシステムプロンプトに使用
- **D-03:** `keywords: list[str] = []`（空リスト固定）— Stage-1 キーワードルーターをスキップし、常に Stage-2 LLM ルーターで評価される
- **D-04:** `run(state: AgentState) -> AgentState` を実装し、`BaseChatModel.ainvoke([SystemMessage(prompt), *state['messages']])` で応答を生成する
- **D-05:** `graph.py` の `build_orchestrator_graph()` は変更不要 — `agent.run` と `agent.name`/`agent.description` の参照のみのため

### OrchestratorHandler 統合

- **D-06:** `orchestrator_handler.py` の `handle()` メソッドで `job.get("gem_ids", [])` を読み取る
- **D-07:** DB から `SELECT * FROM gems WHERE gem_id = ANY($1) AND (is_public = true OR github_login = $2)` で招待 Gem を一括取得する（所有者または公開 Gem のみ許可）
- **D-08:** `GemSubAgent` インスタンスを生成後、既存の `agents_filter` 処理の後に `registry.agents[gem.name] = gem_agent` で dict に直接マージする
- **D-09:** `gem_ids` が空または None の場合は既存動作を変えない（後方互換）

### API 拡張

- **D-10:** `app/api/models.py` の `ChatRequest` に `gem_ids: list[str] | None = None` を追加する（`agents: list[str] | None = None` と同パターン）
- **D-11:** `app/api/routes/chat.py` の `enqueue_job` 呼び出しに `gem_ids=body.gem_ids` を追加する
- **D-12:** `"gem_id:xxx"` プレフィックス方式は採用しない — 独立フィールドで型安全性を保証する

### フロントエンド — GemSelector

- **D-13:** `frontend/src/components/GemSelector.tsx` を新規作成する（`AgentSelector.tsx` と対称的な実装）
- **D-14:** `frontend/src/hooks/useGems.ts` を新規作成する — `GET /api/gems` で公開 Gem + ユーザー所有 Gem を取得
- **D-15:** `SuperChatApp.tsx` の `AgentSelector` と並列に `GemSelector` を配置する（同一 chip 行エリア内に追加）
- **D-16:** `useChat` に `gemIds?: string[]` パラメータを追加し、`sendMessage()` の POST ボディに含める
- **D-17:** Gem 選択は SuperChat セッション単位（スレッドまたは会話開始時）で保持する。スレッド切り替え時はリセットしない（ユーザーが意図的に選択したものを維持）

### Claude's Discretion

- `GemSubAgent` の配置ファイル（`agent.py` に追記 vs 独立した `gem_agent.py`）
- `GemSelector` の具体的なスタイリング（AgentSelector と同一スタイルを踏襲）
- Gem 取得時のエラーハンドリング（Gem が DB に存在しない gem_id をリクエストした場合のフォールバック）

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### バックエンド — SubAgent / オーケストレーター
- `app/orchestrator/agent.py` — SubAgent 基底クラス・`run(state)` インターフェース・`keywords` フィールド
- `app/orchestrator/graph.py` — `build_orchestrator_graph()` — エージェント登録パターンと routing ロジック
- `app/jobs/handlers/orchestrator_handler.py` — OrchestratorHandler — `gem_ids` 受け取り箇所と `registry.agents` フィルタリングロジック
- `app/orchestrator/state.py` — `AgentState` 型定義（`GemSubAgent.run()` の引数型）

### バックエンド — Gem DB / API
- `app/api/routes/gems.py` — Gem CRUD API・DB スキーマ（`gem_id`, `name`, `description`, `system_prompt`, `knowledge`, `is_public`, `github_login`）
- `app/api/models.py` — `ChatRequest` モデル（`gem_ids` 追加箇所）
- `app/api/routes/chat.py` — `POST /api/chat` ルート・`enqueue_job` 呼び出しパターン

### フロントエンド
- `frontend/src/components/SuperChatApp.tsx` — `AgentSelector` 統合パターン・`useAgents` フック使用例
- `frontend/src/components/GemChatApp.tsx` — Gem チャット参考実装（gem_id 送信パターン）
- `frontend/src/hooks/useChat.ts` — `gemId?: string` 既存パラメータ・`sendMessage` ペイロード構造

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `AgentSelector.tsx` — GemSelector の参照実装。chip UI・マルチ選択パターンを流用できる
- `useAgents.ts`（または `SuperChatApp.tsx` 内の agents fetch ロジック）— `useGems.ts` の参照実装
- `app/api/routes/gems.py` の `GET /api/gems` — すでに `is_public` フィルタリングと所有者フィルタを実装済み
- `orchestrator_handler.py` の `registry.agents` フィルタリング（L38-74）— GemSubAgent マージの挿入点

### Established Patterns

- `run(state: AgentState) -> AgentState` が SubAgent の統一インターフェース — GemSubAgent もこれに従う
- `build_orchestrator_graph()` は `agent.name` と `agent.description` を参照するだけ — GemSubAgent が同フィールドを持てばグラフ変更不要
- `keywords=[]`（空）の SubAgent は Stage-1 をスキップし Stage-2 LLM ルーターで評価される（Phase 13 で検証済み）
- `ChatRequest.agents` → `enqueue_job(agents=...)` → `job.get("agents")` の流れが gem_ids の参照パターン

### Integration Points

- `orchestrator_handler.py:handle()` — gem_ids 受け取り・GemSubAgent 生成・registry マージの主な変更箇所
- `app/api/models.py:ChatRequest` — gem_ids フィールド追加
- `app/api/routes/chat.py` — enqueue_job に gem_ids 追加
- `SuperChatApp.tsx` — GemSelector コンポーネントの追加場所
- `useChat.ts` — gemIds パラメータ追加と POST ペイロードへの組み込み

</code_context>

<specifics>
## Specific Ideas

- Gem の `system_prompt` と `knowledge` は改行2つで結合する（`f"{system_prompt}\n\n{knowledge}"` if knowledge else `system_prompt`）
- GemSelector の chip UI は AgentSelector と同じスタイルを流用し、Gem 名をラベルにする
- 招待 Gem がルーティング対象にならなかった場合（OrchestratorGraph のフォールスルー）の動作は通常の general-assistant にフォールバックする既存挙動を維持

</specifics>

<deferred>
## Deferred Ideas

- GemSubAgentRegistry クラスの新設 — 今フェーズでは Handler 内直接処理で十分。エージェント数が増えた場合の将来フェーズ候補
- Gem 招待をスレッド単位で DB 永続化 — 今フェーズはセッション（React state）のみ。将来の拡張候補
- Canvas Gem の SuperChat 特別対応 — Canvas フェーズで扱う

### Reviewed Todos (not folded)

- 「インストールされているスキルを活用してコードレビューを実施する」— Phase 16 スコープ外、独立タスクとして保留
- 「Investigate Agent-Skills integration mechanism」— Phase 16 スコープ外、別フェーズ候補
- 「Integrate LangGraph tool calling with async worker execution」— Phase 16 スコープ外、将来フェーズ

</deferred>

---

*Phase: 16-superchat-gem-gem-orchestratorgraph*
*Context gathered: 2026-04-06*
