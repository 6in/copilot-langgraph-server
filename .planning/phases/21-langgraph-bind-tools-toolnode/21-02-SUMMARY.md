---
phase: 21-langgraph-bind-tools-toolnode
plan: "02"
subsystem: orchestrator
tags: [tool_agent, react_loop, toolnode, langgraph, subagent_registry]
dependency_graph:
  requires: [21-01]
  provides: [ToolEnabledSubAgent, build_react_graph, SubAgentRegistry.mcp_tools]
  affects: [app/orchestrator/agent.py, app/jobs/worker.py]
tech_stack:
  added:
    - "langgraph.prebuilt.ToolNode — mini ReAct グラフのツール実行ノード"
    - "langgraph.prebuilt.tools_condition — tool_calls ありなしの条件分岐"
    - "langgraph.errors.GraphRecursionError — recursion_limit 超過時のキャッチ"
  patterns:
    - "Mini ReAct subgraph (stateless) — チェックポインタなし。外側の AgentState が永続化を担当"
    - "Circular import avoidance — tool_agent.py は agent.py をインポートしない。SubAgent インターフェースを独立実装"
    - "real @tool decorator for tests — ToolNode は MagicMock(spec=BaseTool) で再帰エラーになるため実 BaseTool が必要"
key_files:
  created:
    - app/orchestrator/tool_agent.py
    - tests/test_tool_enabled_subagent.py
    - tests/test_subagent_registry_tools.py
  modified:
    - app/orchestrator/agent.py
    - agents/general-assistant/AGENT.md
decisions:
  - "循環インポート回避: tool_agent.py は agent.py を import せず SubAgent インターフェースを独立実装。agent.py -> tool_agent.py の一方向依存に整理"
  - "テストで @tool デコレータを使用: MagicMock(spec=BaseTool) は ToolNode の args_schema 内省で再帰エラーになるため、実 BaseTool インスタンスが必須"
  - "DEFAULT_RECURSION_LIMIT=25: 10 ループ × 2 ノード + バッファ。T-21-04 DoS 対策 (TOOL-02)"
metrics:
  duration: "~5 minutes"
  completed: "2026-04-10T06:51:28Z"
  tasks_completed: 3
  files_created: 3
  files_modified: 2
---

# Phase 21 Plan 02: ToolEnabledSubAgent + SubAgentRegistry 拡張 Summary

**One-liner:** ToolEnabledSubAgent が mini ReAct グラフ（LangGraph ToolNode）でツール呼び出しを実行し、SubAgentRegistry が AGENT.md の tools: フラグで自動切り替えする

## Objective

ToolEnabledSubAgent クラスと mini ReAct グラフを実装し、SubAgentRegistry を tools フラグ対応に拡張する（TOOL-01/02/03 のコア実装）。

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Wave 0 テストスタブ作成 | `abda2c8` | tests/test_tool_enabled_subagent.py, tests/test_subagent_registry_tools.py |
| 2 | ToolEnabledSubAgent + build_react_graph 実装 | `66d7c71` | app/orchestrator/tool_agent.py (新規), tests/test_tool_enabled_subagent.py 更新 |
| 3 | SubAgentRegistry 拡張 + AGENT.md 更新 | `fd83b69` | app/orchestrator/agent.py, agents/general-assistant/AGENT.md, tests/test_subagent_registry_tools.py 更新 |

## What Was Built

### `app/orchestrator/tool_agent.py` (新規)

**`MiniReActState(TypedDict)`:**
- `messages: Annotated[list[BaseMessage], operator.add]` — LangGraph のメッセージ自動アペンド用

**`build_react_graph(llm_with_tools, tool_node) -> CompiledGraph`:**
- `agent_node` -> `tools_condition` -> `ToolNode("tools")` -> `agent_node` のループ
- `graph.compile()` — チェックポインタなし (D-02 遵守)
- tool_calls が空の AIMessage で END に遷移

**`ToolEnabledSubAgent` クラス:**
- `SubAgent` の代わりに独立実装（循環インポート回避）
- `DEFAULT_RECURSION_LIMIT = 25` で DoS 対策 (TOOL-02, T-21-04)
- `GraphRecursionError` を catch して部分結果を返却
- `ToolMessage` が `all_messages` に蓄積される (TOOL-03)
- `close()` メソッドで `ChatCopilot` リソース解放

### `app/orchestrator/agent.py` の拡張

- `SubAgentRegistry.__init__` に `mcp_tools: list | None = None` 引数追加
- `tools_list = meta.get("tools", [])` で AGENT.md の tools フラグ読み取り
- `tools_list and mcp_tools` なら `ToolEnabledSubAgent` を生成 (`agent_type = "folder+tools"`)
- ツール名で `tool_map` を引いて選択 (D-03: 名前フィルタリング)
- `mcp_tools` なし / `tools:` 未設定なら従来の `SubAgent` (後方互換)
- `from app.orchestrator.tool_agent import ToolEnabledSubAgent` を追加

### `agents/general-assistant/AGENT.md` の更新

frontmatter に `tools: [web_search_stub, ping]` を追加。Phase 23 で実 MCP ツールに差し替え予定。

### テストファイル

**`tests/test_tool_enabled_subagent.py`** (3 テスト):
1. `test_tool_enabled_subagent_runs_react_loop` — ReAct ループ + ToolMessage 確認 (TOOL-01, TOOL-03)
2. `test_react_loop_stops_at_limit` — recursion_limit 超過時の部分結果返却 (TOOL-02)
3. `test_tool_enabled_subagent_no_tool_call` — tool_calls なしで直接 END

**`tests/test_subagent_registry_tools.py`** (3 テスト):
1. `test_registry_creates_tool_enabled_agent` — tools: あり + mcp_tools あり → ToolEnabledSubAgent
2. `test_registry_creates_normal_agent_without_tools` — tools: なし → SubAgent
3. `test_registry_creates_normal_agent_when_no_mcp_tools` — tools: あり + mcp_tools=None → SubAgent

## Verification Results

```
tests/test_tool_enabled_subagent.py::test_tool_enabled_subagent_runs_react_loop PASSED
tests/test_tool_enabled_subagent.py::test_react_loop_stops_at_limit PASSED
tests/test_tool_enabled_subagent.py::test_tool_enabled_subagent_no_tool_call PASSED
tests/test_subagent_registry_tools.py::test_registry_creates_tool_enabled_agent PASSED
tests/test_subagent_registry_tools.py::test_registry_creates_normal_agent_without_tools PASSED
tests/test_subagent_registry_tools.py::test_registry_creates_normal_agent_when_no_mcp_tools PASSED

6 passed in 0.24s
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] MagicMock(spec=BaseTool) が ToolNode で再帰エラー**
- **Found during:** Task 1/2 テスト実行時
- **Issue:** `ToolNode.__init__` が `_get_all_injected_args(tool)` を呼び、`MagicMock(spec=BaseTool)` の `args_schema` が再帰的に mock を返すことで `RecursionError: maximum recursion depth exceeded` が発生
- **Fix:** テスト内の全 mock ツールを `@tool` デコレータで作成した実際の `BaseTool` インスタンスに置き換えた
- **Files modified:** `tests/test_tool_enabled_subagent.py`, `tests/test_subagent_registry_tools.py`
- **Commits:** `66d7c71`, `fd83b69`

**2. [Rule 3 - Blocking] agent.py <-> tool_agent.py 循環インポート**
- **Found during:** Task 3 テスト実行時
- **Issue:** `agent.py` が `tool_agent.py` を import し、`tool_agent.py` が `agent.py` の `SubAgent` を import することで `ImportError: cannot import name 'SubAgent' from partially initialized module` が発生
- **Fix:** `tool_agent.py` から `agent.py` への import を除去。`ToolEnabledSubAgent` が `SubAgent` の必要インターフェース（`name`, `description`, `keywords`, `_llm`, `_system_prompt`, `run()`, `close()`）を独立実装する形に変更
- **Files modified:** `app/orchestrator/tool_agent.py`
- **Commit:** `66d7c71`

## Threat Surface Scan

新規ネットワークエンドポイント、認証パス、外部ファイルアクセスなし。

T-21-04（ReAct 無限ループ DoS）は `DEFAULT_RECURSION_LIMIT=25` + `GraphRecursionError` catch で対処済み。

## Known Stubs

- `agents/general-assistant/AGENT.md` の `tools: [web_search_stub, ping]` はスタブ名。Phase 23 で実際の MCP ツール（FastMCP サーバー経由）に差し替え予定。現時点では SubAgentRegistry の tool フィルタリングロジックのテスト用として機能する。

## Self-Check: PASSED

- `app/orchestrator/tool_agent.py`: 存在確認済み
- `app/orchestrator/agent.py`: `mcp_tools` パラメータ、`ToolEnabledSubAgent` import、`meta.get("tools", [])`, `agent_type = "folder+tools"` 確認済み
- `agents/general-assistant/AGENT.md`: `tools:` フィールド確認済み
- `tests/test_tool_enabled_subagent.py`: 存在確認済み (3 functions)
- `tests/test_subagent_registry_tools.py`: 存在確認済み (3 functions)
- コミット `abda2c8`: 確認済み (test(21-02))
- コミット `66d7c71`: 確認済み (feat(21-02))
- コミット `fd83b69`: 確認済み (feat(21-02))
- 6 tests all PASSED: 確認済み
