---
phase: quick
plan: 260404-eoj
subsystem: superchat-ui
tags: [agents, superchat, frontend, backend, multi-agent]
dependency_graph:
  requires: [phase-09-orchestratorgraph]
  provides: [GET /api/agents, SuperChatApp with agent selection]
  affects: [app/api/routes/agents.py, app/api/models.py, app/api/routes/chat.py, app/jobs/worker.py, app/jobs/handlers/orchestrator_handler.py, frontend/src/components/SuperChatApp.tsx]
tech_stack:
  added: []
  patterns: [agent chip toggle UI, agent filter pass-through via job dict, frontmatter metadata scan]
key_files:
  created:
    - app/api/routes/agents.py
    - frontend/src/components/SuperChatApp.tsx
    - frontend/src/hooks/useAgents.ts
  modified:
    - app/api/models.py
    - app/api/routes/chat.py
    - app/jobs/worker.py
    - app/jobs/handlers/orchestrator_handler.py
    - app/api/main.py
    - frontend/src/types.ts
    - frontend/src/api/client.ts
    - frontend/src/hooks/useChat.ts
    - frontend/src/components/MenuScreen.tsx
    - frontend/src/App.tsx
decisions:
  - "GET /api/agents scans AGENT_DIR via frontmatter only — no SubAgent/ChatCopilot instantiation, no github_token needed"
  - "agents filter in OrchestratorHandler: registry.agents dict reassigned after build — SubAgentRegistry.close() still covers all loaded agents"
  - "useAgents minimum-1 constraint: Set<string> enforced in toggleAgent; if prev.size <= 1 returns prev unchanged"
  - "agents passed to postChat only when selectedMode === 'super' — simple mode always uses all agents (undefined)"
metrics:
  duration: 15min
  completed_date: "2026-04-04"
  tasks_completed: 2
  files_changed: 11
---

# Phase quick Plan 260404-eoj: SuperChat UI with Agent Selection — Summary

**One-liner:** SuperChat page with toggle chip UI and GET /api/agents endpoint backed by AGENT.md frontmatter scan, wired through arq job dict to OrchestratorHandler agent filter.

## Tasks Completed

| # | Task | Commit | Key Files |
|---|------|--------|-----------|
| 1 | Backend — GET /api/agents + agents[] pass-through + OrchestratorHandler filtering | 1ba767e | app/api/routes/agents.py, app/api/models.py, app/api/routes/chat.py, app/jobs/worker.py, app/jobs/handlers/orchestrator_handler.py, app/api/main.py |
| 2 | Frontend — SuperChat page with agent selection toggle UI | 13c0c19 | frontend/src/components/SuperChatApp.tsx, frontend/src/hooks/useAgents.ts, frontend/src/types.ts, frontend/src/api/client.ts, frontend/src/hooks/useChat.ts, frontend/src/components/MenuScreen.tsx, frontend/src/App.tsx |

## What Was Built

### Backend

**GET /api/agents** (`app/api/routes/agents.py`):
- JWT-protected endpoint that scans `AGENT_DIR` (env var, default `./agents`) for `**/AGENT.md` files
- Reads `name` and `description` from each file's frontmatter (using `python-frontmatter`)
- Returns `list[AgentInfo]` — metadata only, no github_token or SDK instantiation needed

**ChatRequest agents field** (`app/api/models.py`):
- Added `AgentInfo(name, description)` model
- Added `agents: list[str] | None = None` to `ChatRequest` — optional list of selected agent names

**Chat route pass-through** (`app/api/routes/chat.py`):
- `send_message()` passes `agents=body.agents` to `arq_redis.enqueue_job()`

**Worker agents param** (`app/jobs/worker.py`):
- `process_chat()` accepts `agents: list[str] | None = None`
- Included in job dict forwarded to handler

**OrchestratorHandler filtering** (`app/jobs/handlers/orchestrator_handler.py`):
- Reads `agents_filter = job.get("agents")`
- After `SubAgentRegistry` is built, filters `registry.agents` dict to only keys in `agents_filter`
- If filter results in empty dict, raises `RuntimeError` with helpful message
- When `agents_filter` is `None`, all agents used (backward compatible)

### Frontend

**`useAgents` hook** (`frontend/src/hooks/useAgents.ts`):
- Fetches from `GET /api/agents` on mount
- Initializes `Set<string>` with all agent names selected by default
- `toggleAgent(name)`: enforces minimum 1 selected (ignores deselect when set size is 1)
- Returns `agents: AgentInfo[]`, `selectedAgents: string[]`, `toggleAgent`, `isLoading`

**`SuperChatApp` component** (`frontend/src/components/SuperChatApp.tsx`):
- Layout: ThreadSidebar + divider + (AgentSelector chip row + MessageArea)
- `AgentSelector`: horizontal scrollable chip row with agent name buttons
- Each chip: `#0366d6` background when selected, transparent when not, description as `title` attribute
- Always `mode: 'super'` — no toggle needed (SuperChat is always orchestration mode)
- Reuses `useThreads`, `useChat`, drag-resize sidebar pattern from `ChatApp`

**MenuScreen** (`frontend/src/components/MenuScreen.tsx`):
- Added SuperChat card: lightning bolt (U+26A1), title "SuperChat", navigates to `'superchat'` screen

**App.tsx**:
- Added `'superchat'` to `currentScreen` state union type
- Added branch: when `currentScreen === 'superchat'`, renders `<SuperChatApp selectedModel={selectedModel} />`

## Verification Results

**Backend verification:**
```
Agent scan OK: ['sql-analyst', 'code-reviewer']
Models OK
```

**Frontend TypeScript check:**
```
Exit: 0  (no errors)
```

## Deviations from Plan

### Setup deviation (not tracked as Rule)

The worktree (`worktree-agent-a0fc9fe0`) was behind `feature/superchat-agent-toggle` — it lacked Phase 09 code (orchestrator_handler.py, SubAgentRegistry, etc.) needed for this task. Merged the feature branch into the worktree branch before executing the plan. This is the expected workflow for a worktree-based task.

### None — plan executed exactly as written

All 6 backend changes and 7 frontend changes implemented as specified.

## Known Stubs

None. All data flows are wired:
- Agent list: fetched from real `/api/agents` endpoint backed by AGENT.md files
- Agent selection: passed via `postChat` → `enqueue_job` → `process_chat` → `OrchestratorHandler`
- SuperChat renders real messages from the arq job result

## Self-Check: PASSED

- `app/api/routes/agents.py`: EXISTS
- `frontend/src/components/SuperChatApp.tsx`: EXISTS
- `frontend/src/hooks/useAgents.ts`: EXISTS
- Commit 1ba767e: EXISTS (backend)
- Commit 13c0c19: EXISTS (frontend)
