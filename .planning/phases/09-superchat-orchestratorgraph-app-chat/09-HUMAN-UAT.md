---
status: partial
phase: 09-superchat-orchestratorgraph-app-chat
source: [09-VERIFICATION.md]
started: 2026-04-04T00:00:00Z
updated: 2026-04-04T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Visual toggle appearance and click behavior
expected: Toggle shows "Simple" and "Super" buttons in input bar; active button highlighted blue; clicking switches modes

result: [pending]

### 2. Super mode routes to SubAgent (code-reviewer)
expected: Sending "Review this Python code: print('hello')" in super mode returns code review feedback from the code-reviewer SubAgent

result: [pending]

### 3. Error resilience with empty/missing AGENT_DIR
expected: If agents/ directory is empty or missing, super mode returns an error message (not crash the UI or backend)

result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
