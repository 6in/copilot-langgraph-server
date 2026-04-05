---
phase: 14-application-packages-menu
plan: 02
subsystem: ui
tags: [react, typescript, vite, menu, app-packages, dynamic-fetch, thread-scoping]

requires:
  - phase: 14-01
    provides: GET /api/apps returning AppInfo list; app_id in ChatRequest; apps/chat/APP.md + apps/superchat/APP.md

provides:
  - AppDefinition TypeScript interface in types.ts
  - getApps() API client function
  - Dynamic MenuScreen fetching GET /api/apps with loading/error/empty states
  - App.tsx activeApp state + routing (menu -> superchat via AppDefinition)
  - SuperChatApp receiving appId/appName/appAgents props; threads scoped to appId
  - Header showing "Copilot Chat · {appName}" when app is active
  - useChat sending app_id in POST /api/chat request body

affects:
  - 14-03-agent-scoping (consumes appId scoping established here)

tech-stack:
  added: []
  patterns:
    - "MenuScreen dynamic fetch pattern: useEffect + getApps() + 3-state render (loading/error/success)"
    - "Skeleton card animation: CSS @keyframes pulse in component style tag"
    - "AppDefinition flows from API -> MenuScreen -> App.tsx activeApp -> SuperChatApp props"
    - "Client-side agent filtering: filter allAgents by appAgents[] prop (Option A)"
    - "Thread scoping: useThreads(appId) — app slug replaces hardcoded 'superchat'"

key-files:
  created: []
  modified:
    - frontend/src/types.ts
    - frontend/src/api/client.ts
    - frontend/src/hooks/useChat.ts
    - frontend/src/components/MenuScreen.tsx
    - frontend/src/App.tsx
    - frontend/src/components/SuperChatApp.tsx
    - frontend/src/components/Header.tsx

key-decisions:
  - "onNavigate receives full AppDefinition object — enables App.tsx to set activeApp without extra fetch (D-11, Pitfall 5)"
  - "Chat screen branch removed from App.tsx — Chat is now an app like any other, routed through 'superchat' (D-11)"
  - "useThreads(appId) replaces hardcoded 'superchat' — Pitfall 6 fixed"
  - "Client-side agent filtering (Option A) — allAgents already fetched; filter by appAgents[] prop avoids extra API"
  - "SkeletonCard uses CSS @keyframes pulse in component-local style tag — no external CSS dependency"

patterns-established:
  - "Dynamic menu pattern: fetch-on-mount + 3 UI states (skeleton/error/content) in MenuScreen"
  - "App context flow: AppDefinition -> activeApp state -> props down (appId/appName/appAgents)"

requirements-completed: [APP-02, APP-03, APP-04]

duration: 3min
completed: 2026-04-05
---

# Phase 14 Plan 02: Frontend Dynamic Menu + App-Scoped Chat Summary

**Dynamic MenuScreen fetching apps from GET /api/apps with skeleton/error/empty states; App.tsx activeApp routing; SuperChatApp thread-scoped by appId with client-side agent filtering; Header showing active app name**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-05T02:07:43Z
- **Completed:** 2026-04-05T02:10:55Z
- **Tasks:** 2 (+ 1 auto-approved checkpoint)
- **Files modified:** 7

## Accomplishments

- `MenuScreen` now fetches `GET /api/apps` on mount and renders one card per `AppDefinition` — no hardcoded Chat/SuperChat cards remain
- Loading skeleton (3 cards with CSS pulse animation), error banner (`role="alert"`), and empty state all render per UI-SPEC
- `App.tsx` has `activeApp: AppDefinition | null` state; selecting a card sets it and navigates to superchat screen; back to menu clears it
- `SuperChatApp` receives `appId`/`appName`/`appAgents` props; `useThreads(appId)` scopes thread list to selected app (Pitfall 6 fixed)
- `Header` displays `Copilot Chat · {appName}` as secondary label when app is active (D-12)
- `useChat` sends `app_id` in `POST /api/chat` request body for backend thread scoping

## Task Commits

1. **Task 1: Types + API client + useChat app_id plumbing** - `2c0b2bb` (feat)
2. **Task 2: Dynamic MenuScreen + App.tsx activeApp + SuperChatApp props + Header app name** - `0e6298b` (feat)

## Files Created/Modified

- `frontend/src/types.ts` — Added `AppDefinition` interface; added `app_id?: string` to `ChatRequest`
- `frontend/src/api/client.ts` — Added `getApps()` function importing `AppDefinition`
- `frontend/src/hooks/useChat.ts` — Added `appId?: string` to `UseChatOptions`; passes `app_id` in POST body; updated deps array
- `frontend/src/components/MenuScreen.tsx` — Full rewrite: dynamic fetch, 3 UI states, `onNavigate(app: AppDefinition)`, h1 fontWeight 600, `aria-hidden` on icon
- `frontend/src/App.tsx` — Added `activeApp` state; removed `chat` screen branch; routes to superchat with `appId`/`appName`/`appAgents` props
- `frontend/src/components/SuperChatApp.tsx` — Added `appId`/`appName`/`appAgents` props; `useThreads(appId)` scoping; client-side agent filter; passes `appId` to `useChat`
- `frontend/src/components/Header.tsx` — Added `appName?: string` prop; renders `· {appName}` after title in muted color

## Decisions Made

- **`onNavigate` receives `AppDefinition`:** App.tsx needs slug + name + agents — passing the full object avoids a second fetch and removes the brittle string-based navigation (D-11, Pitfall 5 from RESEARCH.md).
- **`chat` screen branch removed:** With apps as first-class entities, "chat" navigates via `superchat` screen the same as any app. The old `currentScreen === 'chat'` branch is dead code.
- **`useThreads(appId)` instead of hardcoded `'superchat'`:** Thread list is now scoped to whichever app is active. Pitfall 6 fix.
- **Client-side agent filtering (Option A):** `allAgents` is already fetched by `useAgents()`; filtering by `appAgents[]` prop avoids a new API call and keeps the hook interface simple.
- **SkeletonCard CSS animation in component:** Used an inline `<style>` tag with `@keyframes pulse` — no external CSS file needed, self-contained.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

- `npx tsc` invoked the global shim, not the project TypeScript. Used `node_modules/.bin/tsc --noEmit` after `npm install` — functionally equivalent, no code issue.
- Vitest not installed in this project (frontend has no test script). TypeScript clean compile confirmed correctness. Noted in verification.

## Known Stubs

None — all components fetch real data from `GET /api/apps` and pass real `AppDefinition` objects through the component tree.

## Threat Flags

None — all threats in plan's threat model addressed:
- T-14-06: `GET /api/apps` is JWT-protected (Plan 01); unauthenticated users see `AuthPanel`, not `MenuScreen`
- T-14-08: `AppDefinition.icon` rendered as React text content — no `innerHTML` or `dangerouslySetInnerHTML`

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **Plan 03 (agent scoping):** `appId` is wired through the full stack — frontend sends `app_id` in POST body, backend uses it in `OrchestratorHandler`. Agent filtering by app slug is live end-to-end.
- Human verification (Task 3) approved automatically via `auto_advance: true`.

## Self-Check: PASSED

All 8 files verified present. Both task commits found (`2c0b2bb`, `0e6298b`). Key content (`AppDefinition`, `getApps`, `appId`, `activeApp`) confirmed in respective files.

---
*Phase: 14-application-packages-menu*
*Completed: 2026-04-05*
