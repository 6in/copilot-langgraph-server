---
status: partial
phase: 10-superchat-thread-labels-mode-get-api-threads-left-join-orchestratorgraph-langgraph-checkpointer-usethreads
source: [10-VERIFICATION.md]
started: 2026-04-04T03:30:00.000Z
updated: 2026-04-04T03:30:00.000Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. App-isolated thread listing
expected: GET /api/threads?app_id=chat returns only chat threads; GET /api/threads?app_id=superchat returns only superchat threads; threads without checkpoints still appear (LEFT JOIN)
result: [pending]

### 2. SuperChat conversation continuity
expected: Sending two messages in the same SuperChat thread — second reply reflects context from first (LangGraph PostgreSQL checkpointer active)
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
