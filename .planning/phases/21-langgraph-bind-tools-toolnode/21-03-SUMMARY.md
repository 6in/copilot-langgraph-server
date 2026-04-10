---
phase: 21-langgraph-bind-tools-toolnode
plan: "03"
subsystem: jobs/worker + orchestrator
tags: [mcp_client, worker, orchestrator_handler, e2e_test, react_loop, tool_node]
dependency_graph:
  requires: [21-01, 21-02]
  provides: [worker_mcp_singleton, orchestrator_mcp_wiring, e2e_react_test]
  affects: [app/jobs/worker.py, app/jobs/handlers/orchestrator_handler.py]
tech_stack:
  added:
    - "langchain_mcp_adapters.client.MultiServerMCPClient — Worker startup で MCP ツール取得 (try ブロック内)"
  patterns:
    - "DEGRADED startup: MCP 接続失敗時に ctx['mcp_tools'] = [] で継続（T-21-06 mitigate）"
    - "Singleton in arq ctx: MCP client を ctx に保持し全 job で共有"
    - "_agenerate patch pattern: BoundChatCopilot の _agenerate を直接パッチして e2e テストを実 SDK なしで実行"
key_files:
  created:
    - tests/test_react_e2e.py
  modified:
    - app/jobs/worker.py
    - app/jobs/handlers/orchestrator_handler.py
decisions:
  - "ctx['mcp_tools'] or None パターン: 空リスト時に None を渡すことで SubAgentRegistry がツールフィルタをスキップ（後方互換）"
  - "_agenerate パッチ方式: BoundChatCopilot は _agenerate を直接持つため、ainvoke 全体でなく _agenerate をパッチするとプロンプト注入 + ToolNode の実フローが通る"
metrics:
  duration: "~10 minutes"
  completed: "2026-04-10T06:59:04Z"
  tasks_completed: 2
  files_created: 1
  files_modified: 2
---

# Phase 21 Plan 03: Worker MCP Singleton + e2e テスト統合 Summary

**One-liner:** Worker startup に MultiServerMCPClient Singleton を追加し DEGRADED フォールバックを実装、OrchestratorHandler が mcp_tools を SubAgentRegistry に渡す配線を完成させ、e2e テストで ReAct 全フローを検証した

## Objective

Worker に MCP クライアント Singleton を追加し、OrchestratorHandler 経由で SubAgentRegistry にツールを渡す配線を完成させ、e2e テストで全体フローを検証する（Phase 21 最終統合）。

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Worker startup MCP Singleton + OrchestratorHandler 配線 | `1c4ca6c` | app/jobs/worker.py, app/jobs/handlers/orchestrator_handler.py |
| 2 | e2e テスト作成 + 全スイート確認 | `047918a` | tests/test_react_e2e.py (+242 lines) |

## What Was Built

### `app/jobs/worker.py` の変更

**`import logging` + `logger = logging.getLogger(__name__)` 追加:**
- モジュールレベルの logger を確立

**`startup()` に MCP Singleton 初期化ブロック追加:**
- `ctx["mcp_tools"] = []` と `ctx["mcp_client"] = None` を初期化（try ブロック前）
- `langchain_mcp_adapters.client.MultiServerMCPClient` で `copilot-tools` サーバーに接続
- `MCP_SERVER_URL` 環境変数（デフォルト `http://mcp-server:8001`）から URL を組み立て
- `await mcp_client.get_tools()` でツールリストを取得し `ctx["mcp_tools"]` に格納
- `except Exception as e:` で DEGRADED 継続（T-21-06: DoS mitigation）

**`shutdown()` に MCP cleanup 追加:**
- `ctx.pop("mcp_client", None)` と `ctx.pop("mcp_tools", None)` で参照を解放

### `app/jobs/handlers/orchestrator_handler.py` の変更

`handle()` メソッド内の `SubAgentRegistry` 呼び出しを変更:
```python
# Before:
registry = SubAgentRegistry(AGENT_DIR, github_token)

# After:
mcp_tools = ctx.get("mcp_tools", [])
registry = SubAgentRegistry(AGENT_DIR, github_token, mcp_tools=mcp_tools or None)
```

`mcp_tools or None` により空リスト時は None を渡し、SubAgentRegistry がツールフィルタ処理をスキップする（後方互換性確保）。

### `tests/test_react_e2e.py` (新規, 242 lines)

3 つの e2e テストケース:

1. **`test_e2e_react_loop_with_tool_call`** — TOOL-01 + TOOL-03:
   - LLM 1回目: tool_call JSON → ToolNode が `ping` を呼ぶ → `ToolMessage("pong: hello")`
   - LLM 2回目: 最終テキスト → result["output"] に "pong" が含まれる
   - `result["messages"]` に ToolMessage と tool_calls を持つ AIMessage が存在することを確認

2. **`test_e2e_no_tool_call_passthrough`** — ツール不要時:
   - LLM が通常テキスト → ToolMessage なし、messages は 3件（Sys+Human+AI）

3. **`test_e2e_tool_message_recorded_in_messages`** — TOOL-03 集中検証:
   - `ToolMessage.content == "pong: hello"`, `.name == "ping"`, `.tool_call_id` 非空を確認

**テスト実装の判断:** プランでは `send_and_wait` の side_effect を用いる方法が提案されていたが、`BoundChatCopilot` が `_agenerate` を override しているため、`_agenerate` を直接パッチする方が確実でシンプルな実装となった（`send_and_wait` は SDK レイヤーで、`_agenerate` は LangChain レイヤー）。

## Verification Results

```
tests/test_react_e2e.py::test_e2e_react_loop_with_tool_call PASSED
tests/test_react_e2e.py::test_e2e_no_tool_call_passthrough PASSED
tests/test_react_e2e.py::test_e2e_tool_message_recorded_in_messages PASSED

Phase 21 全テスト:
tests/test_react_e2e.py (3) + tests/test_copilot_bind_tools.py (5) +
tests/test_tool_enabled_subagent.py (3) + tests/test_subagent_registry_tools.py (3) = 14 passed
```

## Deviations from Plan

### Auto-fixed Issues

なし — プランの指示通りに実装した。

### 実装アプローチの調整（逸脱ではない）

**テストでの `send_and_wait` パッチ vs `_agenerate` パッチ:**

プランは `send_and_wait` の side_effect によるモック方法を例示していたが、`BoundChatCopilot` は `_agenerate()` を override するため、`_agenerate` をパッチする方が実際のプロンプト注入 + ToolNode の実行フローを正確に再現できた。テストの目的（TOOL-01/03 の e2e 検証）は達成されており、これはプランの趣旨に沿った実装である。

## Threat Surface Scan

T-21-06（worker startup MCP init の DoS）: `try/except Exception` で DEGRADED 動作を実装済み。worker 起動を妨げない。

T-21-07（MCP ツール結果のログ情報漏洩）: 現時点ではスタブツールのみ。Phase 22/23 で実データ扱い時にログレベルを見直す予定（plan 記載通り accept）。

新規ネットワークエンドポイント、認証パスは追加なし。

## Known Stubs

なし — Phase 03 で追加したコードにスタブなし。`agents/general-assistant/AGENT.md` の `tools: [web_search_stub, ping]` は Plan 02 からの既知スタブ（21-02-SUMMARY.md に記録済み）。

## Self-Check: PASSED

- `app/jobs/worker.py`: 変更確認済み (startup に mcp_tools 初期化、shutdown に cleanup)
- `app/jobs/handlers/orchestrator_handler.py`: `mcp_tools = ctx.get("mcp_tools", [])` 確認済み
- `tests/test_react_e2e.py`: 存在確認済み (242 lines, 3 test functions)
- コミット `1c4ca6c`: 確認済み (feat(21-03))
- コミット `047918a`: 確認済み (test(21-03))
- Phase 21 全 14 テスト PASSED: 確認済み
- 既存テスト regression なし（test_worker.py 5件失敗は Phase 21 以前からの既存問題）
