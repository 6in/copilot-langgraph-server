# Phase 16: SuperChat × Gem 招待 - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-04-06
**Phase:** 16-superchat-gem-gem-orchestratorgraph
**Mode:** assumptions
**Areas analyzed:** GemSubAgent 実装形状, OrchestratorHandler 統合方法, API 実装方法, フロントエンド UI 実装

## Assumptions Presented

### GemSubAgent の実装形状

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| `SubAgent` 継承なし・`run(state)` シグネチャのみ一致する独立クラス | Likely | `app/orchestrator/graph.py` L98-116 — `agent.run` を LangGraph ノードとして直接登録、継承不要 |
| `keywords=[]` 固定で Stage-1 スキップ | Confident | `app/orchestrator/agent.py` — keywords フィールドの空リストが Stage-1 スキップ条件 |
| `system_prompt` + `knowledge` を結合してシステムプロンプトに使用 | Confident | `app/api/routes/gems.py` — Gem DB スキーマに両フィールド存在確認済み |

### OrchestratorHandler への gem_ids 統合方法

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| `registry.agents` dict に直接マージ（agents_filter の後） | Likely | `app/jobs/handlers/orchestrator_handler.py` L38-74 — `registry.agents = {k: v ...}` で dict 上書きフィルタリング |
| DB アクセスは Handler 内で完結（GemSubAgentRegistry 新設なし） | Likely | handler が既に DB_URI 定義済み・AsyncPostgresSaver で接続スコープあり |

### API 拡張

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| 独立した `gem_ids: list[str] | None = None` フィールドを追加 | Likely | `app/api/models.py` L34 — `agents: list[str] | None = None` と同パターンが存在 |
| `"gem_id:xxx"` プレフィックス方式は不採用 | Likely | 独立フィールドの方が型安全・ハンドラ側のパース不要 |

### フロントエンド — Gem マルチセレクタ

| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| 独立 `GemSelector` + `useGems` フック（AgentSelector と並列） | Likely | `frontend/src/hooks/useChat.ts` — `gemId?: string` 既存パラメータから `gem_ids` 追加が最小変更 |
| `useChat` に `gemIds?: string[]` を追加 | Likely | `useChat.ts` L9-21 — agents と同様のパラメータ拡張パターン |

## Corrections Made

すべての前提がユーザーにより推奨オプションで確認された（修正なし）。

## External Research

なし — コードベースに必要な情報はすべて存在した。
