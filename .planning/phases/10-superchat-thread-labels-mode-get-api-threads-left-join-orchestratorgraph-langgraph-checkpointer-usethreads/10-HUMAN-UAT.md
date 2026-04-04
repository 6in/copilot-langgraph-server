---
status: diagnosed
phase: 10-superchat-thread-labels-mode-get-api-threads-left-join-orchestratorgraph-langgraph-checkpointer-usethreads
source: [10-VERIFICATION.md]
started: 2026-04-04T03:30:00.000Z
updated: 2026-04-04T03:30:00.000Z
---

## Current Test

[testing complete]

## Tests

### 1. App-isolated thread listing
expected: GET /api/threads?app_id=chat returns only chat threads; GET /api/threads?app_id=superchat returns only superchat threads; threads without checkpoints still appear (LEFT JOIN)
result: pass

### 2. SuperChat conversation continuity
expected: Sending two messages in the same SuperChat thread — second reply reflects context from first (LangGraph PostgreSQL checkpointer active)
result: issue
reported: "AIが「対応できるエージェントが見つかりませんでした。」と返答した。会話が成立しない。"
severity: blocker

## Summary

total: 2
passed: 1
issues: 1
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "SuperChatで送信したメッセージにAIが正常に返答する（会話が成立する）"
  status: failed
  reason: "User reported: AIが「対応できるエージェントが見つかりませんでした。」と返答した。会話が成立しない。"
  severity: blocker
  test: 2
  root_cause: "SubAgentRegistry に汎用会話エージェントが存在しない。RouterNode の LLM が一般メッセージを 'fallback' にルーティングし、fallback_node() が固定エラー文字列を返す"
  artifacts:
    - path: "app/orchestrator/graph.py"
      issue: "fallback_node() が固定エラー文字列を返す (line 55)。RouterNode に汎用会話パスがない"
    - path: "agents/"
      issue: "sql-analyst と code-reviewer のみ存在。汎用会話エージェントなし"
  missing:
    - "agents/general-assistant/ に汎用会話エージェントを追加する、またはfallback_node を LLM 呼び出しに変更する"
  debug_session: ".planning/debug/superchat-agent-routing-failure.md"
