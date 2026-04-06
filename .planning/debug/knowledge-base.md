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

## debate-chat-history-not-saved — debate app_id missing from applications table causes silent FK violation
- **Date:** 2026-04-06
- **Error patterns:** chat history not saved, thread not saved, silent failure, no error, debate, app_id, FK constraint, applications table
- **Root cause:** applications テーブルに 'debate' レコードが登録されていないため、threads テーブルへの INSERT が app_id の外部キー制約違反で失敗する。エラーは except Exception: pass で握り潰されるため症状がサイレントになる。
- **Fix:** app/api/main.py の applications シード INSERT に ('debate', 'Debate Chat', true, now()) を追加。ON CONFLICT DO NOTHING によりべき等。コンテナ再起動時に自動適用される。
- **Files changed:** app/api/main.py
---

