---
phase: quick
plan: 260403-auth
subsystem: super-agent-sample/auth
tags: [auth, copilot, device-flow, super-agent-sample]
dependency_graph:
  requires: []
  provides: [CopilotAuthManager standalone module, auth_manager-based ChatCopilot instantiation]
  affects: [super-agent-sample/src/agent.py, super-agent-sample/src/graph.py, super-agent-sample/src/auth_manager.py]
tech_stack:
  added: [httpx>=0.27]
  patterns: [CopilotAuthManager injected into ChatCopilot via auth_manager= parameter]
key_files:
  created:
    - super-agent-sample/src/auth_manager.py
  modified:
    - super-agent-sample/src/agent.py
    - super-agent-sample/src/graph.py
    - super-agent-sample/pyproject.toml
decisions:
  - CopilotAuthManager copied verbatim from app/auth/manager.py — preserves super-agent-sample independence from app/ package
  - httpx>=0.27 added to pyproject.toml — CopilotAuthManager uses httpx for Device Flow HTTP calls
  - os import removed from agent.py and graph.py — no other os.environ usage remained after github_token removal
metrics:
  duration: 2min
  completed_date: "2026-04-03"
  tasks_completed: 2
  files_changed: 4
---

# Quick 260403-auth: Integrate CopilotAuthManager into super-agent-sample Summary

**One-liner:** CopilotAuthManager standalone copy added to super-agent-sample; all 3 ChatCopilot instantiations migrated from GITHUB_TOKEN env var to auth_manager= for encrypted token persistence with Device Flow fallback.

## What Was Built

- `super-agent-sample/src/auth_manager.py` — verbatim copy of `app/auth/manager.py`. No `app/` imports; standalone dependency on `httpx` and `cryptography` only.
- `super-agent-sample/pyproject.toml` — added `httpx>=0.27` dependency.
- `super-agent-sample/src/agent.py` — replaced `github_token=os.environ.get("GITHUB_TOKEN", "")` with `auth_manager=CopilotAuthManager()` in `SubAgent.__init__`. Removed unused `import os`. Added `from auth_manager import CopilotAuthManager`.
- `super-agent-sample/src/graph.py` — replaced `github_token=...` in `RouterNode.__init__` and `simple_node` (2 sites). Removed unused `import os`. Added `from auth_manager import CopilotAuthManager`.

## Verification Results

1. `grep -rn "github_token" super-agent-sample/src/agent.py super-agent-sample/src/graph.py` — no matches (exit 1). Correct.
2. `grep -rn "auth_manager=CopilotAuthManager" super-agent-sample/src/` — 3 matches. Correct.
3. Import check: `from agent import SubAgent; from graph import build_simple_graph` — **imports OK**.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | ec6b398 | feat(quick-260403-auth-01): add CopilotAuthManager standalone copy to super-agent-sample |
| Task 2 | 3be4e4c | feat(quick-260403-auth-02): replace github_token with auth_manager in ChatCopilot instantiations |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

- `/home/parallels/workspaces/copilot-langgraph/super-agent-sample/src/auth_manager.py` — FOUND
- `/home/parallels/workspaces/copilot-langgraph/super-agent-sample/src/agent.py` — FOUND (auth_manager=CopilotAuthManager() on line 15)
- `/home/parallels/workspaces/copilot-langgraph/super-agent-sample/src/graph.py` — FOUND (auth_manager=CopilotAuthManager() on lines 30 and 86)
- Commits ec6b398, 3be4e4c — verified in git log
