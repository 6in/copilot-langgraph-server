---
phase: 10-superchat-thread-labels-mode
plan: 05
subsystem: frontend
tags: [react, typescript, hooks, thread-filtering, mode-separation]
dependency_graph:
  requires: [10-03]
  provides: [FE-01, FE-02]
  affects: [frontend/src/api/client.ts, frontend/src/hooks/useThreads.ts, frontend/src/components/ChatApp.tsx, frontend/src/components/SuperChatApp.tsx]
tech_stack:
  added: []
  patterns: [mode query param forwarding, optional hook parameter with useCallback dependency]
key_files:
  created: []
  modified:
    - frontend/src/api/client.ts
    - frontend/src/hooks/useThreads.ts
    - frontend/src/components/ChatApp.tsx
    - frontend/src/components/SuperChatApp.tsx
decisions:
  - "useThreads accepts optional 'chat' | 'superchat' mode; no default so backward-compatible with future callers"
  - "mode added to refreshThreads useCallback dependency array — required for correct memoization"
metrics:
  duration: 1min
  completed: 2026-04-04
  tasks_completed: 2
  files_modified: 4
---

# Phase 10 Plan 05: Mode-Aware useThreads + listThreads Query Param Summary

**One-liner:** Mode-filtered thread listing via listThreads(mode?) query param, useThreads('chat'/'superchat') hook, and explicit call sites in ChatApp and SuperChatApp.

## Objective

Complete the mode separation at the UI layer: each app (ChatApp, SuperChatApp) now shows only its own threads by passing a `mode=` query parameter to `GET /api/threads`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add mode parameter to listThreads in client.ts | d1b228f | frontend/src/api/client.ts |
| 2 | Add mode parameter to useThreads hook + update call sites | bd582e6 | frontend/src/hooks/useThreads.ts, ChatApp.tsx, SuperChatApp.tsx |

## Changes Made

### frontend/src/api/client.ts

`listThreads` changed from no-arg to optional `mode?: string`:

```typescript
export const listThreads = (mode?: string) =>
  apiFetch<ThreadInfo[]>(
    `${API_BASE}/api/threads${mode ? `?mode=${encodeURIComponent(mode)}` : ''}`
  );
```

Backward-compatible: calling without argument still fetches all threads.

### frontend/src/hooks/useThreads.ts

- Signature changed from `useThreads()` to `useThreads(mode?: 'chat' | 'superchat')`
- `refreshThreads` useCallback now calls `listThreads(mode)` and includes `mode` in dependency array

### frontend/src/components/ChatApp.tsx

- `useThreads()` → `useThreads('chat')`

### frontend/src/components/SuperChatApp.tsx

- `useThreads()` → `useThreads('superchat')`

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all data flows are wired (the backend GET /api/threads with ?mode= filter was implemented in plan 10-03).

## Self-Check: PASSED

- frontend/src/api/client.ts: FOUND (modified)
- frontend/src/hooks/useThreads.ts: FOUND (modified)
- frontend/src/components/ChatApp.tsx: FOUND (modified)
- frontend/src/components/SuperChatApp.tsx: FOUND (modified)
- Commit d1b228f: FOUND
- Commit bd582e6: FOUND
- ChatApp uses `useThreads('chat')`: VERIFIED
- SuperChatApp uses `useThreads('superchat')`: VERIFIED
- useThreads passes mode to listThreads: VERIFIED
- TypeScript check: deferred to Docker build (node_modules not in worktree environment — same known constraint as Phase 09)
