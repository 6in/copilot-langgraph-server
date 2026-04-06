---
phase: 16-superchat-gem-gem-orchestratorgraph
plan: "01"
subsystem: orchestrator
status: complete
tags: [gem, sub-agent, orchestrator, langgraph]
one_liner: "GemSubAgent クラス新規実装と OrchestratorHandler への gem_ids 統合で、Gem をルーティング対象エージェントとして扱う基盤を構築"

dependency_graph:
  requires: []
  provides:
    - "GemSubAgent: Gem DB レコードを OrchestratorGraph 互換のエージェントとして包む軽量ラッパー"
    - "OrchestratorHandler.gem_ids: job ペイロードから gem_ids を受け取り DB から Gem を取得して registry にマージ"
  affects:
    - "app/orchestrator/graph.py (変更なし — GemSubAgent が同一インターフェースを実装)"
    - "app/orchestrator/agent.py (変更なし — SubAgentRegistry.close() との互換は GemSubAgent.close() no-op で対応)"

tech_stack:
  added: []
  patterns:
    - "BaseChatModel.ainvoke パターン: GemSubAgent は SubAgent と同一の run(state) → AgentState 形式"
    - "psycopg パラメタライズドクエリ: gem_ids の DB フェッチに psycopg AsyncConnection を使用"
    - "keywords=[] 固定: Stage-1 キーワードルーターをスキップして Stage-2 LLM ルーターのみで評価"

key_files:
  created:
    - "app/orchestrator/gem_agent.py"
  modified:
    - "app/jobs/handlers/orchestrator_handler.py"

decisions:
  - "D-01: GemSubAgent は SubAgent を継承しない独立クラス（from_dir / ChatCopilot 生成ロジック不要）"
  - "D-02: コンストラクタで system_prompt + knowledge を結合（knowledge 空なら system_prompt のみ）"
  - "D-03: keywords=[] 固定で Stage-1 をスキップし Stage-2 LLM ルーターで評価"
  - "D-04: BaseChatModel.ainvoke で応答生成、SubAgent.run と同一形式の AgentState を返す"
  - "D-05: graph.py 変更不要（agent.name / agent.description / agent.run の参照のみ）"
  - "D-06: job.get('gem_ids') or [] で None と空リストを統一処理"
  - "D-07: WHERE gem_id = ANY(%s::uuid[]) AND (is_public = true OR github_login = %s) で所有者・公開 Gem のみ取得"
  - "D-08: GemSubAgent を registry.agents dict に直接マージ（agents_filter フィルタリング後）"
  - "D-09: gem_ids が空の場合は if gem_ids: ガードで既存動作を完全維持（後方互換）"

metrics:
  duration_minutes: 10
  completed_date: "2026-04-06"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 1
---

# Phase 16 Plan 01: GemSubAgent & OrchestratorHandler gem_ids 統合 Summary

## 実装内容

### Task 1: GemSubAgent クラス新規作成

`app/orchestrator/gem_agent.py` を新規作成。

- `GemSubAgent(name, description, system_prompt, knowledge, llm)` で初期化
- `keywords: list[str] = []` 固定（Stage-1 キーワードルーターをスキップ）
- `_full_prompt`: `f"{system_prompt}\n\n{knowledge}"` if knowledge else `system_prompt`
- `async def run(state: AgentState) -> AgentState`: `SystemMessage(_full_prompt) + HumanMessage(state["input"])` で `llm.ainvoke` を呼び出し、`{"output": ..., "messages": [...]}` を返す
- `async def close(self) -> None: pass`: `SubAgentRegistry.close()` の `for agent in self.agents.values(): await agent.close()` と互換

### Task 2: OrchestratorHandler gem_ids 統合

`app/jobs/handlers/orchestrator_handler.py` を修正。

- `import psycopg`, `from psycopg.rows import dict_row`, `from app.orchestrator.gem_agent import GemSubAgent` を追加
- `github_login` 定義の直後に gem_ids 処理ブロックを挿入
- `gem_ids: list[str] = job.get("gem_ids") or []` で None / 未指定を統一処理
- `if gem_ids:` ガードで後方互換を保証（D-09）
- DB クエリはパラメタライズド形式で SQL インジェクション対策（T-16-01 脅威を mitigate）
- DB フェッチ失敗時は `logger.warning` して `gem_rows = []` にフォールバック（処理継続）
- `registry.agents[gem_agent.name] = gem_agent` で直接マージ

## 適用した設計決定

D-01 〜 D-09 すべてを計画通り実装。追加偏差なし。

## 検証結果

```
python -c "from app.orchestrator.gem_agent import GemSubAgent; print('GemSubAgent import OK')"
# → GemSubAgent import OK

python -c "from app.jobs.handlers.orchestrator_handler import OrchestratorHandler; print('OrchestratorHandler import OK')"
# → OrchestratorHandler import OK
```

## コミット

- `8c0b8a9`: feat(16): implement GemSubAgent class and orchestrator gem_ids integration

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

なし。GemSubAgent は実際の `BaseChatModel.ainvoke` を呼び出す完全実装。

## Threat Flags

なし。T-16-01 の mitigate（所有者/公開フィルタ付き DB クエリ）は計画通り実装済み。

## Self-Check: PASSED

- `app/orchestrator/gem_agent.py`: FOUND
- `app/jobs/handlers/orchestrator_handler.py`: FOUND (gem_ids 処理ブロック含む)
- commit `8c0b8a9`: FOUND
