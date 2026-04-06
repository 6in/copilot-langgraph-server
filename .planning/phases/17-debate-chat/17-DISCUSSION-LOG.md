# Phase 17: マルチエージェント討論チャット - Discussion Log (Assumptions Mode)

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the analysis.

**Date:** 2026-04-06
**Phase:** 17-debate-chat
**Mode:** assumptions
**Areas analyzed:** グラフトポロジー, ハンドラー設計, ターン延長承認, フロントエンド, パターン実装

## Assumptions Presented

### グラフトポロジー
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| OrchestratorGraph から独立した DebateGraph を新規実装 | Confident | app/orchestrator/graph.py — 線形トポロジーのみ |
| DebateState は AgentState を継承しない独自 TypedDict | Likely | app/orchestrator/state.py — 単一エージェント前提の型設計 |

### ハンドラー設計
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| task_type="debate" + DebateHandler を TASK_HANDLERS に追加 | Confident | app/jobs/worker.py L28-31 の動的ディスパッチパターン |
| participants/pattern/max_turns を process_chat に独立引数として追加 | Likely | agents と gem_ids が独立フィールドとして共存している既存パターン |

### ターン延長承認
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| interrupt_before は使わず再エンキュー方式を採用 | Likely | arq job lifetime モデルと interrupt の相性問題 |

### フロントエンド
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| DebateChatApp.tsx を SuperChatApp.tsx 参照で新規作成 | Confident | App.tsx Screen 型パターン、GemChatApp の流用実績 |
| 発言表示はプレフィックス方式（MVP） | Confident | ChatMessage 型が role: 'user'|'ai' のみ |

### パターン実装
| Assumption | Confidence | Evidence |
|------------|-----------|----------|
| 3パターンを単一 build_debate_graph 関数で実装 | Likely | build_orchestrator_graph ファクトリパターンの踏襲 |

## Corrections Made

なし — ユーザーが全仮定を承認（「まあ、やってみようか」）

## External Research

- LangGraph interrupt_before と arq の組み合わせ: 統合コストが高いため再エンキュー方式を採用することでスキップ
