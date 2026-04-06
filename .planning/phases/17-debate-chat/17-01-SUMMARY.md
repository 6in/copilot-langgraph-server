---
phase: 17-debate-chat
plan: "01"
subsystem: orchestrator
tags: [tdd, langgraph, multi-agent, debate-graph]
dependency_graph:
  requires: []
  provides: [build_debate_graph, DebateState, _make_pseudo_agent_state]
  affects: [app/orchestrator/debate_graph.py, tests/test_debate_graph.py]
tech_stack:
  added: []
  patterns:
    - LangGraph StateGraph with conditional edges for round-robin dispatch
    - TDD RED-GREEN cycle with mock agents and mock LLM
    - MemorySaver checkpointer for re-enqueue continuation tests
key_files:
  created:
    - app/orchestrator/debate_graph.py
    - tests/test_debate_graph.py
  modified: []
decisions:
  - "panel パターンは max_turns * len(participants) 総発言数でループ終了（1ターン = 1ラウンド）"
  - "debate/panel は同一 dispatcher ノードで分岐、chain は per-agent ノードで線形チェーン"
  - "T-17-01: participants (2-10) + max_turns (1-20) をファクトリ先頭でバリデーション"
metrics:
  duration: "2min"
  completed_date: "2026-04-06"
  tasks_completed: 2
  files_created: 2
---

# Phase 17 Plan 01: DebateGraph コア実装 Summary

**One-liner:** LangGraph StateGraph による debate/chain/panel 3パターン対応ターン制マルチエージェント会話グラフを TDD で実装（13テスト PASS）

## What Was Built

`app/orchestrator/debate_graph.py` に `build_debate_graph` ファクトリ関数と `DebateState` TypedDict を実装した。

### 実装内容

**DebateState (TypedDict)**
- `turn: int`, `max_turns: int`, `pattern: str`, `participants: list[str]`
- `messages: Annotated[list[BaseMessage], operator.add]`
- `current_agent_idx: int`, `awaiting_extension: bool`

**3パターンのエッジ構造**

| パターン | エッジ構造 | 終了条件 |
|---------|-----------|---------|
| debate | dispatcher -> (条件分岐) -> dispatcher/aggregator -> END | turn >= max_turns |
| panel | debate と同じ dispatcher | turn >= max_turns * len(participants) |
| chain | agent_A -> agent_B -> agent_C -> aggregator -> END | 線形、固定 |

**ヘルパー関数**
- `_extract_last_human_message(state)` — 最後の HumanMessage content を返す
- `_make_pseudo_agent_state(state)` — AgentState 互換 dict を返す（T-17-02）

**セキュリティ (T-17-01)**
- participants: 2 <= N <= 10
- max_turns: 1 <= N <= 20

## Test Results

```
13 passed in 0.21s
```

| テストクラス | テスト数 | 内容 |
|-------------|---------|------|
| TestValidation | 5 | participants/max_turns バリデーション |
| TestMakePseudoAgentState | 3 | AgentState 互換 dict 構造確認 |
| TestDebatePattern | 2 | max_turns=4(5 AI msg) + max_turns=2(3 AI msg) |
| TestChainPattern | 1 | 3 participants => 4 AI messages |
| TestPanelPattern | 1 | 3 participants max_turns=3 => 10 AI messages |
| TestReEnqueue | 1 | 同一 thread_id への 2 回目 ainvoke で継続 |

## Commits

| Hash | Type | Description |
|------|------|-------------|
| d6ea13d | test | TDD RED: failing tests for DebateGraph |
| 964f42b | feat | TDD GREEN: implement build_debate_graph + DebateState |

## Deviations from Plan

**1. [Rule 1 - Bug] panel パターンのターン終了条件を修正**
- **Found during:** GREEN フェーズ初回テスト実行
- **Issue:** debate/panel 共通で `turn >= max_turns` を使っていたため、panel の max_turns=3 が「3発言後」で終了していた（期待は「3ラウンド=9発言」）
- **Fix:** panel パターンでは `total_turns = max_turns * len(participants)` を終了条件に使用
- **Files modified:** app/orchestrator/debate_graph.py
- **Commit:** 964f42b（実装コミットに統合済み）

## Known Stubs

なし — すべてのフィールドが実装されており、モックを使ったテストで動作確認済み。

## Threat Flags

なし — 新規ネットワークエンドポイントや認証パスは追加していない。`build_debate_graph` は内部ファクトリ関数で、T-17-01/T-17-02 のバリデーション対応済み。

## Self-Check: PASSED

- [x] `app/orchestrator/debate_graph.py` 存在確認: FOUND
- [x] `tests/test_debate_graph.py` 存在確認: FOUND
- [x] コミット d6ea13d 存在確認: FOUND
- [x] コミット 964f42b 存在確認: FOUND
- [x] `python -m pytest tests/test_debate_graph.py -x -q`: 13 passed
