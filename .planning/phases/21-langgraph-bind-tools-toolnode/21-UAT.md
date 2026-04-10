---
status: complete
phase: 21-langgraph-bind-tools-toolnode
source:
  - 21-01-SUMMARY.md
  - 21-02-SUMMARY.md
  - 21-03-SUMMARY.md
started: "2026-04-10T07:00:00.000Z"
updated: "2026-04-10T07:10:00.000Z"
---

## Current Test

number: 7
name: 全テスト完了
expected: 全7項目が確認済み
awaiting: complete

## Tests

### 1. Phase 21 テスト全通過
expected: pytest で Phase 21 の 14 テスト（bind_tools 5本・ToolEnabledSubAgent 3本・Registry 3本・e2e 3本）が全て PASSED になる。
result: pass — ユーザー確認済み (14 passed in 0.26s)

### 2. bind_tools() が BoundChatCopilot を返す
expected: `llm.bind_tools([...])` が `BoundChatCopilot` インスタンスを返す。
result: pass — test_bind_tools_returns_bound_copilot PASSED

### 3. BoundChatCopilot がシステムプロンプトにツールスキーマを注入する
expected: send_and_wait に渡されるプロンプトに "You have access to the following tools" とツール JSON スキーマが含まれる。
result: pass — test_bound_copilot_injects_system_prompt PASSED

### 4. ToolEnabledSubAgent が ReAct ループを実行する
expected: tool_call → ToolNode → ToolMessage → 最終応答の全フローが動作する。
result: pass — test_e2e_react_loop_with_tool_call PASSED

### 5. SubAgentRegistry が tools フラグを読んで ToolEnabledSubAgent を選択する
expected: AGENT.md に tools フラグ + mcp_tools あり → ToolEnabledSubAgent、なし → SubAgent。
result: pass — test_registry_creates_tool_enabled_agent / test_registry_creates_normal_agent_* PASSED

### 6. Worker startup で MCP tools が初期化される
expected: startup() が MCP サーバーに接続し ctx["mcp_tools"] にツールリストを格納。失敗時は [] で DEGRADED 継続。
result: pass — app/jobs/worker.py L71/83/88/99 にて実装確認済み

### 7. OrchestratorHandler が mcp_tools を SubAgentRegistry に渡す
expected: OrchestratorHandler.handle() 内で ctx.get("mcp_tools", []) を取得して SubAgentRegistry に渡す。
result: pass — app/jobs/handlers/orchestrator_handler.py L40-41 にて実装確認済み

## Summary

total: 7
passed: 7
issues: 0
pending: 0
skipped: 0

## Gaps

[none]
