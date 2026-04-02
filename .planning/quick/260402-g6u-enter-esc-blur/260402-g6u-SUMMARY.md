---
phase: quick
plan: 260402-g6u
subsystem: frontend
tags: [ux, sidebar, react, keyboard-interaction]
key-files:
  modified:
    - frontend/src/components/ThreadSidebar.tsx
decisions:
  - cancelledRef pattern: useRef<boolean> set in cancelEdit(), checked in commitEdit() — prevents unmount-triggered onBlur from saving after Escape
  - Date display wraps label in flex column div so label+date stack without disrupting row layout
metrics:
  duration: 3min
  completed: "2026-04-02"
  tasks: 1
  files: 1
---

# Quick 260402-g6u: Date Display and Escape-blur Fix Summary

**One-liner:** Thread sidebar now shows `updated_at` dates and correctly cancels inline edits on Escape without the unmount-blur triggering a spurious save.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add date display and fix Escape-blur race in ThreadSidebar | dca349f | frontend/src/components/ThreadSidebar.tsx |

## What Was Built

### Date display
Each thread row in the sidebar now shows the formatted date (from `thread.updated_at`) below the title. Rendered via `new Date(thread.updated_at).toLocaleDateString()` in a muted `<span>` (fontSize 0.7rem, color #999). The label and date are stacked in a `flex column` wrapper `<div>` that holds `flex: 1` and `minWidth: 0` to maintain the existing row layout.

### Escape-blur race fix
The root cause: pressing Escape called `cancelEdit()` which set `editingId = null`, unmounting the `<input>`. The unmount fired `onBlur`, which then called `commitEdit()`, saving the edit value — overriding the cancel intent.

Fix applied using `cancelledRef = useRef<boolean>(false)`:
- `cancelEdit()` sets `cancelledRef.current = true` before `setEditingId(null)`
- `commitEdit()` checks `cancelledRef.current` at entry — returns early if true, then resets to false
- `startEdit()` resets `cancelledRef.current = false` to ensure clean state for subsequent edits

This guarantees Escape cancels without saving, Enter and blur both save as expected.

## Deviations from Plan

None — plan executed exactly as written.

## Verification

- `cd frontend && npx tsc --noEmit` passed with no errors
- All success criteria met:
  - Thread rows display date from `updated_at`
  - Escape cancels without saving
  - Enter saves
  - Blur (click away) saves
  - No TypeScript errors

## Self-Check: PASSED

- File exists: `frontend/src/components/ThreadSidebar.tsx` — FOUND
- Commit dca349f — FOUND
