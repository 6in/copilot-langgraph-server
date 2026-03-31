---
phase: 260331-uy2
plan: 01
type: quick
subsystem: provider
tags: [bugfix, sdk, copilot, send_and_wait]
dependency_graph:
  requires: []
  provides: [correct-send_and_wait-call]
  affects: [app/providers/copilot.py]
tech_stack:
  added: []
  patterns: [TDD red-green]
key_files:
  created: []
  modified:
    - app/providers/copilot.py
    - tests/test_provider.py
decisions:
  - "send_and_wait() takes a plain string argument; test assertion uses the formatted prompt string [User]: hello not the raw input"
metrics:
  duration: 5min
  completed: 2026-03-31
---

# Quick Task 260331-uy2: Fix send_and_wait dict-arg bug Summary

**One-liner:** Fixed `_agenerate` passing `{"prompt": prompt}` dict to `send_and_wait` — SDK 0.2.0 signature requires a plain string, causing runtime TypeError on every real invocation.

## What Was Done

Corrected the single-argument call in `ChatCopilot._agenerate` (line 95 of `app/providers/copilot.py`) from:

```python
response = await session.send_and_wait({"prompt": prompt})
```

to:

```python
response = await session.send_and_wait(prompt)
```

Added a regression test `test_send_and_wait_called_with_string` that verifies `send_and_wait` receives the formatted prompt string (not a dict).

## Task Execution

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Add failing test for string call | 2d02975 | tests/test_provider.py |
| 1 (GREEN) | Apply one-line fix + all tests pass | 2d02975 | app/providers/copilot.py, tests/test_provider.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test assertion corrected to use formatted prompt string**
- **Found during:** Task 1, RED phase
- **Issue:** The plan's example used `assert_called_once_with("hello")` but `_messages_to_prompt` formats HumanMessage content as `[User]: hello`, so the actual call uses `"[User]: hello"`.
- **Fix:** Updated the test assertion to `assert_called_once_with("[User]: hello")` to match actual behavior.
- **Files modified:** tests/test_provider.py
- **Commit:** 2d02975

## Verification Results

- `uv run pytest tests/test_provider.py -x -q`: 10 passed
- `uv run pytest -x -q`: 23 passed (no cross-module regressions)

## Known Stubs

None.

## Self-Check: PASSED

- `app/providers/copilot.py` confirmed: `session.send_and_wait(prompt)` at line 95
- `tests/test_provider.py` confirmed: contains `test_send_and_wait_called_with_string`
- Commit 2d02975 confirmed in git log
