# Deferred Items — Phase 40 UI Polish Round 2

Pre-existing issues discovered during plan execution that are **out of scope** for the current task. Tracked here per GSD executor scope-boundary rule.

## 40-01: Pre-existing frontend lint errors

**Discovered during:** 40-01 Task 2 verification (`cd frontend && bun run lint`)

**Status:** baseline `bun run lint` already returned `✖ 23 problems (22 errors, 1 warning)` **before** any 40-01 edits. Verified by `git stash` + lint + `git stash pop` cycle.

**Categories observed:**
- `react-hooks/set-state-in-effect` — multiple files call `setState` synchronously inside `useEffect`. Files: `CanvasChatApp.tsx`, `CanvasScreen.tsx` (L134), `ChatApp.tsx`, `Header.tsx`, `MessageArea.tsx`, `QuestionPanel.tsx`, `SuperChatApp.tsx`, `ThreadSidebar.tsx`, `useAgents.ts`, `useAttachments.ts`, `useChat.ts`, `useGems.ts`, `useModels.ts`, `useThreads.ts`, preview components.
- `react-refresh/only-export-components` — `AttachmentModal.tsx` L53, `CanvasPane.tsx` L9.
- `@typescript-eslint/no-unused-vars` — `SuperChatApp.tsx` L121 `_appName`.

**Why deferred:**
1. None of these errors are introduced by 40-01 edits (Back-button removal in GemsScreen / CanvasScreen).
2. The 40-01 acceptance criterion `bun run lint exit 0` is impossible against the existing codebase regardless of this plan.
3. Fixing `react-hooks/set-state-in-effect` requires careful refactoring of state-fetch flows (events vs effects) across many components — substantial structural work that warrants its own phase / plan.

**Files touched by 40-01 (no new lint errors):**
- `frontend/src/App.tsx` — 0 lint errors
- `frontend/src/components/GemsScreen.tsx` — 0 lint errors
- `frontend/src/components/CanvasScreen.tsx` — 1 pre-existing error at L134 (`useEffect` -> `setLoading(true)`), unchanged by 40-01.

**Recommendation:** Schedule a dedicated lint-cleanup plan in a later phase to address the 22 errors collectively, focusing on `react-hooks/set-state-in-effect` patterns.
