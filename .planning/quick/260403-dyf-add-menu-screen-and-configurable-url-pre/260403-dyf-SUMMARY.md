---
phase: quick
plan: 260403-dyf
subsystem: frontend
tags: [menu-screen, routing, api-client, vite-env, react]
dependency_graph:
  requires: []
  provides: [menu-screen, screen-routing, configurable-api-base-url]
  affects: [frontend/src/App.tsx, frontend/src/components/MenuScreen.tsx, frontend/src/components/Header.tsx, frontend/src/api/client.ts]
tech_stack:
  added: []
  patterns: [screen-state-routing, conditional-prop-callbacks, vite-env-prefix]
key_files:
  created:
    - frontend/src/components/MenuScreen.tsx
  modified:
    - frontend/src/api/client.ts
    - frontend/src/App.tsx
    - frontend/src/components/Header.tsx
decisions:
  - "currentScreen state in App.tsx drives menu/chat branching — single source of truth, no router needed for 2-screen app"
  - "onBackToMenu is optional prop on Header — menu screen omits it, chat screen provides it; avoids separate Header variant"
  - "MenuScreen imports useCurrentTheme from ThemeContext — consistent with existing pattern from Header and ChatApp"
metrics:
  duration: 2min
  completed: "2026-04-03T01:06:50Z"
  tasks_completed: 2
  files_changed: 4
---

# Quick 260403-dyf: Add Menu Screen and Configurable URL Prefix

**One-liner:** Menu home screen with Chat feature card after login, screen routing in App.tsx via useState, Header back button, and VITE_BASE_URL prefix on all API calls.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Add VITE_BASE_URL support to API client | 208b9eb | frontend/src/api/client.ts |
| 2 | Create MenuScreen, wire routing in App.tsx + Header back button | f99d0d2 | frontend/src/components/MenuScreen.tsx, frontend/src/App.tsx, frontend/src/components/Header.tsx |

## What Was Built

**Task 1 — VITE_BASE_URL in client.ts:**
- Added `const BASE_URL = import.meta.env.VITE_BASE_URL ?? ''` at file top
- Prepended `BASE_URL` in `apiFetch` (covers all standard endpoints), `streamJob` (EventSource URL), and `deleteThread` (raw fetch bypass)
- Default is empty string — zero behavior change when env var is unset

**Task 2 — MenuScreen + App routing + Header back button:**
- New `MenuScreen` component: centered title, subtitle, responsive card grid (max-width 600px), single "Chat" feature card with icon, description, hover shadow/translate effect
- Theme-aware colors via `useCurrentTheme()` — dark/light palettes consistent with Header
- `App.tsx`: added `currentScreen` state (`'menu' | 'chat'`); menu screen renders `<MenuScreen onNavigate=...>`, chat screen renders `<ChatApp>` — both under the same `<Header>` in their respective branches
- `Header.tsx`: added optional `onBackToMenu?: () => void` prop; when provided, renders a "&lsaquo; Menu" button before the title with the same transparent button style as Logout

## Verification

- `npx tsc --noEmit`: no type errors
- `npx vite build`: production build succeeded (553 kB JS, 42 kB CSS)
- Chunk size warning is pre-existing (all dependencies, not introduced by this task)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — MenuScreen renders the Chat card which navigates to the fully functional ChatApp.

## Self-Check: PASSED

- frontend/src/components/MenuScreen.tsx: FOUND
- frontend/src/api/client.ts BASE_URL: FOUND (5 occurrences)
- App.tsx currentScreen state: FOUND
- Header.tsx onBackToMenu prop: FOUND
- Commits 208b9eb and f99d0d2: FOUND
