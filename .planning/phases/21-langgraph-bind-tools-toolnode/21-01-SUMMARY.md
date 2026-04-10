---
phase: 21-langgraph-bind-tools-toolnode
plan: "01"
subsystem: providers
tags: [bind_tools, tool_calls, prompt_engineering, langchain, langgraph]
dependency_graph:
  requires: []
  provides: [BoundChatCopilot, ChatCopilot.bind_tools]
  affects: [app/graph/builder.py, app/jobs/worker.py]
tech_stack:
  added:
    - "langchain_core.messages.tool.ToolCall — ToolCall 型を AIMessage.tool_calls に注入"
    - "langchain_core.tools.BaseTool — bind_tools() の型チェックに使用"
  patterns:
    - "Prompt Engineering approach (D-01) — JSON-RPC SDK は native tool_call 不可のため、システムプロンプト注入 + テキストパースで実現"
    - "PrivateAttr + object.__setattr__ — Pydantic v2 でサブクラスの状態を保持するパターン"
key_files:
  created:
    - tests/test_copilot_bind_tools.py
  modified:
    - app/providers/copilot.py
decisions:
  - "D-01: Approach A (プロンプト注入 + JSON パース) — Copilot SDK は JSON-RPC のため native function_call API なし。TOOL_SYSTEM_PROMPT_TEMPLATE でスキーマ注入、_try_parse_tool_call() で 2段階パース（直接 JSON → markdown フェンス除去 → JSON）"
  - "D-02: _bound_tools は PrivateAttr + object.__setattr__ — BoundChatCopilot はサブクラスなので __init__ で super() を先に呼ぶ必要があり、PrivateAttr の初期化を object.__setattr__ で行う"
  - "D-03: bind_tools() は BaseTool インスタンスのみフィルタリング — dict 形式ツールは Phase 22 以降で対応、現時点では型安全を優先"
metrics:
  duration: "~15 minutes"
  completed: "2026-04-10T06:43:09Z"
  tasks_completed: 2
  files_created: 1
  files_modified: 1
---

# Phase 21 Plan 01: bind_tools + BoundChatCopilot 実装 Summary

**One-liner:** ChatCopilot.bind_tools() がプロンプト注入でツールスキーマを注入し、JSON レスポンスを AIMessage(tool_calls=[ToolCall(...)]) に変換する BoundChatCopilot を実装した

## Objective

ChatCopilot に `bind_tools()` メソッドと `BoundChatCopilot` サブクラスを追加することで、LangGraph ToolNode との連携基盤（TOOL-01）を整備する。

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Wave 0 テストスタブ + bind_tools ユニットテスト作成 | `94d469a` | tests/test_copilot_bind_tools.py (+129 lines) |
| 2 | BoundChatCopilot + ChatCopilot.bind_tools() 実装 | `96dd85a` | app/providers/copilot.py (+150 lines) |

## What Was Built

### `app/providers/copilot.py` への追加

**`ChatCopilot.bind_tools(tools, ...)` メソッド:**
- `Sequence[BaseTool]` を受け取り、`BoundChatCopilot` インスタンスを返す
- `BaseTool` 以外のオブジェクトはフィルタリング除外（型安全）

**`TOOL_SYSTEM_PROMPT_TEMPLATE` 定数:**
- ツールスキーマ JSON の注入フォーマットを定義
- LLM に JSON のみで応答するよう指示

**`BoundChatCopilot(ChatCopilot)` クラス:**
- `_bound_tools: list = PrivateAttr` — Pydantic スキーマ汚染を回避
- `_agenerate()` でシステムプロンプトにツールスキーマを注入してから親 `_agenerate()` を呼ぶ
- LLM レスポンスを `_try_parse_tool_call()` でパース、ToolCall が得られれば `AIMessage(tool_calls=[...])` で返す

**`_try_parse_tool_call(content)` ヘルパー:**
- 直接 JSON パース → markdown コードブロック除去 → JSON パースの 2 段階
- `"tool"` キーの存在を必須チェック（T-21-01 mitigate）

### `tests/test_copilot_bind_tools.py` の追加

5 つのテストケース:
1. `test_bind_tools_returns_bound_copilot` — bind_tools() が BoundChatCopilot を返す
2. `test_bound_copilot_parses_tool_call_json` — JSON レスポンスが tool_calls に変換される
3. `test_bound_copilot_normal_text_response` — 通常テキストは tool_calls が空で返る
4. `test_bound_copilot_injects_system_prompt` — send_and_wait 引数に "You have access to the following tools" が含まれる
5. `test_bound_copilot_handles_markdown_wrapped_json` — markdown ````json` ブロックも正しくパースされる

## Verification Results

```
tests/test_copilot_bind_tools.py::test_bind_tools_returns_bound_copilot PASSED
tests/test_copilot_bind_tools.py::test_bound_copilot_parses_tool_call_json PASSED
tests/test_copilot_bind_tools.py::test_bound_copilot_normal_text_response PASSED
tests/test_copilot_bind_tools.py::test_bound_copilot_injects_system_prompt PASSED
tests/test_copilot_bind_tools.py::test_bound_copilot_handles_markdown_wrapped_json PASSED
tests/test_provider.py::test_instantiation PASSED
tests/test_provider.py::test_llm_type PASSED
tests/test_provider.py::test_sync_raises PASSED
tests/test_provider.py::test_agenerate_mocked PASSED
tests/test_provider.py::test_model_param PASSED
tests/test_provider.py::test_close PASSED
tests/test_provider.py::test_error_resets_client PASSED
tests/test_provider.py::test_messages_to_prompt PASSED
tests/test_provider.py::test_ensure_client_no_token_no_manager PASSED
tests/test_provider.py::test_send_and_wait_called_with_string PASSED

15 passed in 0.17s
```

## Deviations from Plan

なし — プランの指示通りに実装した。

## Threat Flags

なし — 新しいネットワークエンドポイント、認証パス、ファイルアクセスは導入していない。

`_try_parse_tool_call()` の T-21-01 （LLM レスポンス → ToolCall の改ざんリスク）はプラン記載の通り `json.loads` 厳密パース + `"tool"` キー必須チェックで対応済み。

## Known Stubs

なし — テストも実装もスタブなし。

## Self-Check: PASSED

- `app/providers/copilot.py`: 存在確認済み (324 lines)
- `tests/test_copilot_bind_tools.py`: 存在確認済み (129 lines)
- `class BoundChatCopilot`: copilot.py に存在確認済み
- `def bind_tools`: copilot.py に存在確認済み
- `TOOL_SYSTEM_PROMPT_TEMPLATE`: copilot.py に存在確認済み
- コミット `94d469a`: 確認済み (test(21-01))
- コミット `96dd85a`: 確認済み (feat(21-01))
- 15 tests all PASSED: 確認済み
