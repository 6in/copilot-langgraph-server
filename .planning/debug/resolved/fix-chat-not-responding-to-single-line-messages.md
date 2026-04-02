---
status: resolved
trigger: "fix-chat-not-responding-to-single-line-messages"
created: 2026-04-02T00:00:00Z
updated: 2026-04-02T00:10:00Z
---

## Current Focus

hypothesis: CONFIRMED — stale React closure in useChat.sendMessage silently discards messages when activeThreadId is null
test: Traced exact execution path; confirmed fix passes threadId explicitly to bypass stale closure
expecting: Single-line messages now respond correctly on first send in a fresh session
next_action: Human verify fix works end-to-end

## Symptoms

expected: AI responds normally — same as multi-line messages
actual: No response at all — no loading indicator, no reply, nothing happens
errors: None visible in browser console or server logs
reproduction: Always — every single-line message fails, every multi-line message works
started: Observed now; unclear if it ever worked

## Eliminated

- hypothesis: trim() or validation strips single-line content
  evidence: inputValue.trim() for single-line "hello" → "hello" (truthy), identical code path as multi-line
  timestamp: 2026-04-02T00:01:00Z

- hypothesis: Backend Pydantic validation rejects single-line messages
  evidence: ChatRequest model has message: str with no constraints; no min_length or pattern validator
  timestamp: 2026-04-02T00:01:00Z

- hypothesis: Backend LangGraph/ChatCopilot provider filters by line count
  evidence: worker.py, builder.py, copilot.py all pass the prompt through with no line-count checks
  timestamp: 2026-04-02T00:01:00Z

- hypothesis: Enter key sends single-line message vs Ctrl+Enter for multi-line
  evidence: Both vanilla JS and React UI require Ctrl+Enter or button click; plain Enter inserts newline in both
  timestamp: 2026-04-02T00:01:00Z

## Evidence

- timestamp: 2026-04-02T00:00:30Z
  checked: static/app.js sendMessage()
  found: Uses text = userInput.value.trim(); if (!text) return; — no newline check; clean path
  implication: Vanilla JS UI is not the source of the single-line bug

- timestamp: 2026-04-02T00:00:35Z
  checked: app/api/models.py ChatRequest
  found: message: str with no constraints; thread_id: str; model: str = "gpt-4.1"
  implication: Backend Pydantic validation cannot reject single-line content

- timestamp: 2026-04-02T00:00:40Z
  checked: frontend/src/hooks/useChat.ts sendMessage useCallback
  found: sendMessage checks `if (!activeThreadId) return` using stale closure value; activeThreadId is in dependency array but captured at creation time
  implication: If activeThreadId is null when the callback is created, it remains null in the closure even after setActiveThreadId() is called

- timestamp: 2026-04-02T00:00:45Z
  checked: frontend/src/components/ChatApp.tsx handleSend
  found: Calls `threadId = await createNewThread()` (which calls setActiveThreadId internally), then immediately calls `await sendMessage(text)` — React state update from setActiveThreadId has NOT caused re-render yet, so sendMessage's closure still sees activeThreadId=null
  implication: ROOT CAUSE — stale closure causes sendMessage to return early on every first message of a session

- timestamp: 2026-04-02T00:00:50Z
  checked: Why single-line specifically?
  found: Pattern matches: user opens fresh session (activeThreadId=null), types short first message → fails silently. On second attempt (often more elaborate/multi-line), component has re-rendered with the thread created in attempt #1 → succeeds. The single/multi-line split is actually a first/subsequent message split that users perceive as single/multi-line.
  implication: Confirms root cause — NOT a character count or newline check

- timestamp: 2026-04-02T00:01:30Z
  checked: TypeScript compilation after fix
  found: npx tsc --noEmit exits cleanly with no errors
  implication: Fix is type-correct

## Resolution

root_cause: Stale React closure in useChat.sendMessage captures activeThreadId=null at hook creation time. ChatApp.handleSend calls createNewThread() (which schedules a setActiveThreadId state update) then immediately calls sendMessage(text). Because React hasn't re-rendered yet, sendMessage's closure still sees activeThreadId=null and hits the early return guard `if (!activeThreadId) return`, silently discarding the message with no user bubble, no loading indicator, no error.

fix: |
  1. frontend/src/hooks/useChat.ts — sendMessage now accepts optional threadId parameter.
     Uses `const resolvedThreadId = threadId ?? activeThreadId` so explicit callers bypass stale closure.
  2. frontend/src/components/ChatApp.tsx — handleSend passes the threadId returned by
     createNewThread() directly to sendMessage(text, threadId).

verification: TypeScript compilation clean. Human confirmed fix works end-to-end — single-line first messages now respond correctly.

files_changed:
  - frontend/src/hooks/useChat.ts
  - frontend/src/components/ChatApp.tsx
