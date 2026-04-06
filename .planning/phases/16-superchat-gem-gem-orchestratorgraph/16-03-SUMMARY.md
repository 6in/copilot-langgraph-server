---
phase: 16-superchat-gem-gem-orchestratorgraph
plan: "03"
status: complete
completed: "2026-04-06"
subsystem: orchestrator/tests
tags: [testing, gem-agent, orchestrator, unit-tests]
dependency_graph:
  requires: [16-01, 16-02]
  provides: [GEM-SUB-01, GEM-SUB-02, GEM-SUB-03, GEM-SUB-04]
  affects: [tests/]
tech_stack:
  added: []
  patterns:
    - pytest-asyncio AUTO モードでの非同期テスト
    - AsyncMock + MagicMock を使った LLM モック
    - DB に依存しないロジック切り出しユニットテスト
key_files:
  created:
    - tests/test_gem_agent.py
    - tests/test_orchestrator_handler_gems.py
  modified: []
decisions:
  - "DB 依存ロジック（gem_ids DB クエリ）はモック不要のロジック分解でユニットテスト"
  - "asyncio_mode=auto（pyproject.toml 設定済み）につき @pytest.mark.asyncio は任意だが明示的に付与"
metrics:
  duration_minutes: 15
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 0
---

# Phase 16 Plan 03: GemSubAgent ユニットテスト & gem_ids 統合テスト Summary

GemSubAgent の全コアロジックと OrchestratorHandler の gem_ids 処理をカバーする自動テストを追加した。
8 + 8 = 16 テストケースがすべて PASS し、既存テスト 141 件へのリグレッションもない。

## What Was Implemented

### Task 1: GemSubAgent ユニットテスト (`tests/test_gem_agent.py`)

8 テストケースを実装:

| テスト名 | 検証内容 |
|---------|---------|
| `test_keywords_always_empty` | `keywords == []` 固定（D-03 検証） |
| `test_name_and_description` | コンストラクタで name/description が正しく設定される |
| `test_full_prompt_with_knowledge` | `system_prompt + "\n\n" + knowledge` に結合される（D-02） |
| `test_full_prompt_without_knowledge` | knowledge="" → `system_prompt` のみ（D-02） |
| `test_run_returns_correct_state` | `{"output": ..., "messages": [AIMessage(...)]}` 形式（D-05） |
| `test_run_uses_combined_system_prompt` | `ainvoke` に `SystemMessage + HumanMessage` が渡される |
| `test_run_uses_system_prompt_only_when_no_knowledge` | knowledge なし時のシステムプロンプト |
| `test_close_is_noop` | `close()` が例外なく終了する（D-01） |

### Task 2: OrchestratorHandler gem_ids 統合テスト (`tests/test_orchestrator_handler_gems.py`)

8 テストケースを 2 クラスに分けて実装:

**`TestChatRequestGemIds`** (3 テスト):
- `gem_ids` フィールドのデフォルト値 `None`
- リスト形式の受け付け
- `gem_id`（単数）との独立共存（D-12）

**`TestGemAgentMergeLogic`** (5 テスト):
- DB 行から `GemSubAgent` 生成時の name 反映
- description 空文字のフォールバック（`"Gem: {name}"`）
- `registry.agents` へのマージ（既存エージェント保持確認、D-08）
- `gem_ids=None/[]` のガード検証（後方互換、D-09）
- `keywords=[]` による Stage-2 ルーター評価（D-03）

## Test Results

```
tests/test_gem_agent.py: 8 passed in 0.10s
tests/test_orchestrator_handler_gems.py: 8 passed in 0.09s
全テストスイート: 141 passed, 11 failed (既存失敗), 8 skipped
```

既存の 11 件の失敗は Plan 16-03 着手前から存在する不具合（`test_api_chat`, `test_graph`, `test_worker`）であり、今回の変更によるリグレッションではない。

## Commits

| Hash | 内容 |
|------|------|
| `ef09d51` | `test(16-03): add GemSubAgent unit tests` |
| `fb62e41` | `test(16-03): add gem_ids integration tests for OrchestratorHandler` |

## Deviations from Plan

None - プランに記載されたコードをそのまま実装。`asyncio_mode = "auto"` が既に `pyproject.toml` に設定されていたため `pytest-asyncio` の追加インストールは不要だった。

## Self-Check: PASSED

- `tests/test_gem_agent.py` 存在確認: FOUND
- `tests/test_orchestrator_handler_gems.py` 存在確認: FOUND
- コミット `ef09d51` 確認: FOUND
- コミット `fb62e41` 確認: FOUND
