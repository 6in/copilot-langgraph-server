---
phase: quick
plan: 260401-fwh
type: quick-task
subsystem: provider,graph
tags: [sdk-tools, permission-handler, chatbot-node, cleanup]
tech-stack:
  added: []
  patterns: [PermissionHandler.approve_all, direct state["messages"] passthrough]
key-files:
  modified:
    - app/providers/copilot.py
    - app/graph/builder.py
  created: []
decisions:
  - "Option A (approve_all) selected: SDK native tool execution loop enabled, hallucination workaround removed"
  - "SystemMessage prepend removed from chatbot_node: graph layer no longer injects tool-suppression instructions"
metrics:
  duration: 5min
  completed: "2026-04-01T02:29:48Z"
  tasks: 2
  files: 2
---

# Quick Task 260401-fwh: Enable SDK Tools via approve_all (Option A) Summary

**One-liner:** Restored PermissionHandler.approve_all in copilot.py and removed the "no tools" SystemMessage from builder.py, enabling SDK native tool execution.

## What Was Done

Reverted the hallucination-avoidance workaround introduced in 260401-f4x (which used `lambda _: False` and a SystemMessage to block SDK tools). Both files now use the clean, SDK-intended pattern.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | copilot.py — on_permission_request to approve_all | 634a640 | app/providers/copilot.py |
| 2 | builder.py — remove SystemMessage, simplify chatbot_node | 32fa1a3 | app/graph/builder.py |

## Changes Made

### app/providers/copilot.py
- `create_session(on_permission_request=lambda _: False, ...)` → `create_session(on_permission_request=PermissionHandler.approve_all, ...)`
- Removed inline comment `# deny all SDK tools to prevent hallucination`

### app/graph/builder.py
- Removed `_system_msg = SystemMessage(content="You have no tools available. Respond to all requests using text only.")`
- Removed `messages = [_system_msg] + list(state["messages"])` prepend in `chatbot_node`
- `chatbot_node` now calls `llm.ainvoke(state["messages"])` directly
- Removed `from langchain_core.messages import SystemMessage` import (no longer used)

## Verification

```
36 passed in 0.77s
```

All 36 existing tests pass. No regressions.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

- app/providers/copilot.py: modified (PermissionHandler.approve_all present, lambda _: False absent)
- app/graph/builder.py: modified (_system_msg absent, SystemMessage import absent, state["messages"] passed directly)
- Commits 634a640 and 32fa1a3 exist in git log
- 36 tests pass
