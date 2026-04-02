# GSD Debug Knowledge Base

Resolved debug sessions. Used by `gsd-debugger` to surface known-pattern hypotheses at the start of new investigations.

---

## fix-chat-not-responding-to-single-line-messages — stale React closure silently drops first message of a session
- **Date:** 2026-04-02
- **Error patterns:** single-line message, no response, silent drop, stale closure, activeThreadId null, useCallback, sendMessage, first message, useChat
- **Root cause:** sendMessage's useCallback closed over activeThreadId=null at creation time. handleSend called createNewThread() (which scheduled a setActiveThreadId state update) then immediately called sendMessage — before React re-rendered — so the closure still saw null and hit the early-return guard, silently discarding the message with no UI feedback.
- **Fix:** sendMessage now accepts an optional threadId parameter; callers that just created a thread pass the fresh id directly to bypass the stale closure. ChatApp.handleSend passes the threadId returned by createNewThread() directly to sendMessage(text, threadId).
- **Files changed:** frontend/src/hooks/useChat.ts, frontend/src/components/ChatApp.tsx
---

