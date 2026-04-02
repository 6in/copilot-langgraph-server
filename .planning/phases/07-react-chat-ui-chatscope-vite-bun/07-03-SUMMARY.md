---
phase: 07-react-chat-ui-chatscope-vite-bun
plan: 03
subsystem: ui
tags: [react, typescript, chatscope, sse, markdown, threads]

# Dependency graph
requires:
  - phase: 07-react-chat-ui-chatscope-vite-bun
    provides: Vite React-TS scaffold with chatscope packages, typed API client, auth hooks, AuthPanel, Header, ChatAppStub in App.tsx

provides:
  - frontend/src/hooks/useThreads.ts — thread list management (list/create/switch/delete/loadMessages)
  - frontend/src/hooks/useChat.ts — sendMessage with SSE stream + polling fallback, isThinking state
  - frontend/src/components/MarkdownMessage.tsx — ReactMarkdown wrapper with remark-gfm + rehype-highlight
  - frontend/src/components/ThreadSidebar.tsx — sidebar with thread list, active highlight, New Chat button, delete button
  - frontend/src/components/MessageArea.tsx — ChatContainer with TypingIndicator as prop, user/AI message rendering
  - frontend/src/components/ChatApp.tsx — MainContainer wrapped in flex:1 div for chatscope height propagation
  - frontend/src/App.tsx — ChatAppStub replaced with real ChatApp component
  - npm run build passes with no TypeScript errors

affects: [07-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "useThreads/useChat hook separation: thread lifecycle vs message send/receive are independent concerns"
    - "TypingIndicator as prop on MessageList (not JSX child) — chatscope API requires prop, not child element"
    - "AI messages use type=custom + Message.CustomContent: XSS-safe React rendering vs type=html innerHTML"
    - "SSE + polling fallback: EventSource.onmessage for completion, setInterval in onerror for disconnection recovery"
    - "ChatApp flex:1 + overflow:hidden wrapper: chatscope height propagation requires explicit ancestor height"

key-files:
  created:
    - frontend/src/hooks/useThreads.ts
    - frontend/src/hooks/useChat.ts
    - frontend/src/components/MarkdownMessage.tsx
    - frontend/src/components/ThreadSidebar.tsx
    - frontend/src/components/MessageArea.tsx
    - frontend/src/components/ChatApp.tsx
  modified:
    - frontend/src/App.tsx

key-decisions:
  - "onThreadCreated removed from useChat destructuring — unused param causes TS6133 error; param remains in interface for future use prefixed with _"
  - "removeThread missing from useThreads return — interface declared it but return object omitted it; auto-fixed (Rule 1 bug)"

patterns-established:
  - "All chatscope TypingIndicator usage: always as typingIndicator prop on MessageList, never as JSX child"
  - "Message type=custom for AI content: XSS-safe pattern — never use type=html for user-supplied Markdown"

requirements-completed: [D-01, D-05, D-06, D-08]

# Metrics
duration: 4min
completed: 2026-04-02
---

# Phase 7 Plan 03: Chat Components and Thread Management Summary

**Complete chatscope chat UI with SSE-driven AI responses, Markdown rendering, thread sidebar, and TypingIndicator — replacing ChatAppStub with the full ChatApp**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-02T00:16:56Z
- **Completed:** 2026-04-02T00:20:19Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Created `useThreads` hook with list/create/switch/delete/loadMessages and auto-refresh on mount
- Created `useChat` hook with SSE via EventSource.onmessage + setInterval polling fallback in onerror
- Built `MarkdownMessage` with ReactMarkdown + remark-gfm + rehype-highlight for syntax-highlighted AI responses
- Built `ThreadSidebar` with active thread highlight, New Chat button, and per-thread delete with confirmation
- Built `MessageArea` with TypingIndicator as prop (not child) on MessageList, custom content for AI messages
- Built `ChatApp` with MainContainer wrapped in flex:1 + overflow:hidden for correct chatscope height propagation
- Replaced `ChatAppStub` in `App.tsx` with real `ChatApp` — app now has feature parity with Vanilla JS version
- `npm run build` exits 0, 586 modules transformed, no TypeScript errors

## Task Commits

Each task was committed atomically:

1. **Task 1: Create useThreads and useChat hooks** - `c2c433e` (feat)
2. **Task 2: Create all chat components and wire ChatApp into App.tsx** - `aa1d7cb` (feat)

## Files Created/Modified

- `frontend/src/hooks/useThreads.ts` - Thread list management: list, create, switch, delete, loadMessages, refreshThreads
- `frontend/src/hooks/useChat.ts` - sendMessage with SSE stream + polling fallback, isThinking state
- `frontend/src/components/MarkdownMessage.tsx` - ReactMarkdown wrapper with remark-gfm + rehype-highlight
- `frontend/src/components/ThreadSidebar.tsx` - Thread list with active highlight, New Chat button, delete button
- `frontend/src/components/MessageArea.tsx` - ChatContainer with TypingIndicator prop, user/AI message rendering
- `frontend/src/components/ChatApp.tsx` - MainContainer layout with flex:1 height wrapper
- `frontend/src/App.tsx` - Replaced ChatAppStub with real ChatApp component

## Decisions Made

- **onThreadCreated unused param** — TypeScript TS6133 error on unused destructured param; renamed to `_onThreadCreated` in interface to signal intentionally unused, removed from destructuring
- **removeThread missing from return** — interface declared `removeThread` as required but the return object omitted it; added to return (auto-fix Rule 1 - Bug)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed two TypeScript errors blocking build**
- **Found during:** Task 2 (verify step — npm run build)
- **Issue 1:** `removeThread` declared in `UseThreadsReturn` interface but missing from the return object; TS2741
- **Issue 2:** `onThreadCreated` destructured but never used in useChat.ts; TS6133
- **Fix:** Added `removeThread` to useThreads return object; removed `onThreadCreated` from destructuring (kept in interface as `_onThreadCreated`)
- **Files modified:** frontend/src/hooks/useThreads.ts, frontend/src/hooks/useChat.ts
- **Verification:** npm run build exits 0, no TypeScript errors
- **Committed in:** aa1d7cb (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Required fix for build to pass. No scope creep.

## Issues Encountered

Two TypeScript errors on first build attempt — both straightforward: missing return value and unused parameter. Fixed inline within Task 2 commit.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Full chatscope chat UI is implemented and builds cleanly
- SSE + polling fallback wired to `/api/chat` and `/api/chat/{job_id}/stream`
- Thread management (create, switch, delete, load) fully functional
- App has feature parity with Vanilla JS version — ready for Plan 07-04 (final integration / deployment notes)

---
*Phase: 07-react-chat-ui-chatscope-vite-bun*
*Completed: 2026-04-02*

## Self-Check: PASSED

- FOUND: frontend/src/hooks/useThreads.ts
- FOUND: frontend/src/hooks/useChat.ts
- FOUND: frontend/src/components/MarkdownMessage.tsx
- FOUND: frontend/src/components/ThreadSidebar.tsx
- FOUND: frontend/src/components/MessageArea.tsx
- FOUND: frontend/src/components/ChatApp.tsx
- FOUND: frontend/src/App.tsx
- FOUND: frontend/dist/index.html
- FOUND commit: c2c433e (Task 1 — useThreads and useChat hooks)
- FOUND commit: aa1d7cb (Task 2 — chat components and App.tsx)
