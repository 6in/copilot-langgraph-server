---
phase: 28-codeact-llm
plan: "02"
subsystem: orchestrator
tags: [codeact, recursion-limit, tool-agent, agent-definition]
dependency_graph:
  requires: [28-01]
  provides: [codeact-agent, recursion-limit-per-agent]
  affects: [app/orchestrator/tool_agent.py, agents/codeact/AGENT.md]
tech_stack:
  added: []
  patterns:
    - "AGENT.md frontmatter で per-agent recursion_limit を宣言"
    - "ToolEnabledSubAgent.from_dir() が meta.get('recursion_limit') で読み込み"
key_files:
  created:
    - agents/codeact/AGENT.md
  modified:
    - app/orchestrator/tool_agent.py
    - tests/test_subagent_registry_tools.py
decisions:
  - "recursion_limit の設定を AGENT.md フィールドで行う（Option A: AGENT.md フィールド拡張）— コード変更不要でエージェント単位カスタマイズ可能"
  - "CodeAct エージェントの recursion_limit を 12 に設定（5 ステップ x 2 ノード + バッファ）— DoS 軽減 T-28-06"
metrics:
  duration_minutes: 8
  completed_date: "2026-04-17"
  tasks_completed: 2
  files_changed: 3
---

# Phase 28 Plan 02: CodeAct エージェント定義 + recursion_limit 拡張 Summary

**One-liner:** AGENT.md フィールド方式で per-agent recursion_limit を実現し、CodeAct エージェント（recursion_limit: 12）を SubAgentRegistry に自動登録

## What Was Built

### Task 1: ToolEnabledSubAgent recursion_limit フィールド対応 (commit: a8751e3)

`app/orchestrator/tool_agent.py` に以下の変更を加えた:

1. `__init__` に `recursion_limit: int | None = None` パラメータを追加
2. `self.recursion_limit = recursion_limit or self.DEFAULT_RECURSION_LIMIT` で初期化（`keywords` 代入の直後）
3. `from_dir()` で `recursion_limit=meta.get("recursion_limit")` を読み込む
4. `run()` の `ainvoke` config を `self.recursion_limit` に変更（`DEFAULT_RECURSION_LIMIT` ではなく）
5. `GraphRecursionError` ログも `self.recursion_limit` を参照
6. docstring に per-agent カスタマイズ可能である旨を追記

### Task 2: CodeAct エージェント定義 + テスト (commit: 4aa5f5b)

- `agents/codeact/AGENT.md` を新規作成
  - `recursion_limit: 12`（5 ステップ x 2 ノード + バッファ — D-05）
  - `tools: [execute_python]`（Phase 28-01 で実装済み）
  - keywords: コード実行 / Python実行 / データ分析 / 計算 / スクリプト実行 / グラフ作成 / アルゴリズム
  - `対象外: コードレビュー / SQL クエリ / Web検索が主目的のタスク`
- `tests/test_subagent_registry_tools.py` に 2 テストを追加
  - `test_tool_enabled_agent_reads_recursion_limit`: EXEC-07 — recursion_limit: 12 が正しく読み込まれる
  - `test_tool_enabled_agent_default_recursion_limit`: 未指定時は DEFAULT_RECURSION_LIMIT = 25 を使用

## Verification

```
$ python3 -m pytest tests/test_subagent_registry_tools.py -v
5 passed in 0.19s

$ grep "recursion_limit" app/orchestrator/tool_agent.py | wc -l
6

$ grep "recursion_limit: 12" agents/codeact/AGENT.md
recursion_limit: 12

$ grep "execute_python" agents/codeact/AGENT.md
  - execute_python
```

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Option A: AGENT.md フィールド拡張 | コード変更不要でエージェント単位のカスタマイズが可能。新エージェント追加時もフィールドを宣言するだけ |
| recursion_limit: 12 for CodeAct | 5 ステップ（コード生成 → 実行 → 観察サイクル）x 2 ノード（agent + tools）+ バッファ — D-05 |
| DEFAULT_RECURSION_LIMIT = 25 維持 | 後方互換性を保つ。未指定エージェントは既存動作と同じ |

## Deviations from Plan

None - plan executed exactly as written.

## Threat Surface Scan

| Flag | File | Description |
|------|------|-------------|
| T-28-06 mitigated | agents/codeact/AGENT.md | recursion_limit: 12 による DoS 軽減を実装済み |

## Self-Check: PASSED

- [x] `agents/codeact/AGENT.md` exists
- [x] `app/orchestrator/tool_agent.py` updated with recursion_limit support
- [x] `tests/test_subagent_registry_tools.py` has 2 new tests (5 total, all PASS)
- [x] commit a8751e3 exists (Task 1)
- [x] commit 4aa5f5b exists (Task 2)
