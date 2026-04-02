# Phase 7 Human UAT — React Chat UI (chatscope + Vite)

**Phase:** 07-react-chat-ui-chatscope-vite-bun
**Date:** (fill in when running)
**Tester:** (fill in)

## Setup

Before running these tests:

1. Start the backend:
   ```bash
   uvicorn app.api.main:app --reload
   ```

2. Start the Vite dev server (for SC-01 through SC-09):
   ```bash
   cd frontend && npm run dev
   ```
   Dev server runs at http://localhost:5173

3. For SC-09 (FastAPI serving /react from dist), ensure frontend is built:
   ```bash
   cd frontend && npm run build
   ```
   Then test at http://localhost:8000/react

---

## Test Cases

### SC-01: Vite scaffold builds successfully

**Where:** Terminal
**Steps:**
1. Run `cd frontend && npm run build`
2. Check exit code is 0

**Expected:** No TypeScript errors. `frontend/dist/index.html` exists.
**Result:** [ ] PASS  [ ] FAIL
**Notes:**

---

### SC-02: All components exist

**Where:** Filesystem
**Steps:**
1. Run:
   ```bash
   ls frontend/src/components/ frontend/src/hooks/ frontend/src/api/ frontend/src/types.ts
   ```

**Expected:** AuthPanel.tsx, ChatApp.tsx, ThreadSidebar.tsx, MessageArea.tsx, Header.tsx, MarkdownMessage.tsx, useAuth.ts, useThreads.ts, useChat.ts, client.ts, types.ts all present.
**Result:** [ ] PASS  [ ] FAIL
**Notes:**

---

### SC-03: POST /api/chat SSE → Markdown response renders

**Where:** http://localhost:5173
**Steps:**
1. Authenticate (see SC-05 for Device Flow steps).
2. Click "New Chat" in the sidebar.
3. Type a message with Markdown content, e.g.:
   > "Write a Python hello world function and explain it."
4. Press Enter to send.
5. Observe:
   - TypingIndicator ("Copilot is thinking...") appears while waiting
   - AI response renders with code block and prose text formatted
   - Response appears as an incoming (left-aligned) bubble

**Expected:** Markdown rendered. Code block has syntax highlighting. TypingIndicator disappears after response arrives.
**Result:** [ ] PASS  [ ] FAIL
**Notes:**

---

### SC-04: Thread sidebar and switching

**Where:** http://localhost:5173
**Steps:**
1. Send at least one message (creates Thread A in sidebar).
2. Click "New Chat" — a fresh empty chat area appears.
3. Send a message in the new thread (creates Thread B).
4. Click Thread A in the sidebar.
5. Verify Thread A's messages load in the message area.
6. Click Thread B — Thread B's messages load.

**Expected:** Thread sidebar shows Thread A and Thread B. Switching loads the correct history for each. Active thread is visually highlighted.
**Result:** [ ] PASS  [ ] FAIL
**Notes:**

---

### SC-05: Device Flow renders and completes

**Where:** http://localhost:5173 (start with a fresh session — clear cookies or use incognito)
**Steps:**
1. Navigate to http://localhost:5173.
2. Click "Start GitHub Authentication".
3. Observe:
   - `user_code` (e.g. "ABCD-1234") displayed in large monospace font
   - `verification_uri` shown as a clickable link
   - "Copy" button copies the code to clipboard
   - "Waiting for authentication..." spinner/text shown
4. Open the verification_uri, enter the user_code, approve.
5. Within 5-10 seconds (next poll cycle), the app transitions to the chat view.

**Expected:** Device Flow completes without page reload. Chat UI appears.
**Result:** [ ] PASS  [ ] FAIL
**Notes:**

---

### SC-06: GitHub avatar + login in header

**Where:** http://localhost:5173 (authenticated)
**Steps:**
1. Authenticate via Device Flow.
2. Observe the header (top bar).
3. Check for:
   - GitHub avatar (small circle image, top-right area)
   - GitHub login name displayed next to avatar
   - Logout button visible

**Expected:** Avatar and login visible. Clicking Logout prompts for confirmation, then returns to AuthPanel.
**Result:** [ ] PASS  [ ] FAIL
**Notes:**

---

### SC-07: Model selector defaults to gpt-4.1

**Where:** http://localhost:5173 (authenticated)
**Steps:**
1. Observe the model selector in the header.
2. Confirm the initial selection is "GPT-4.1 (free)".
3. Change the model to another (e.g., "Claude Sonnet 4.5 (1x)").
4. Send a message — the selected model persists.

**Expected:** Default is gpt-4.1. Changing the selector and sending uses the new model (no UI error; backend accepts the model name).
**Result:** [ ] PASS  [ ] FAIL
**Notes:**

---

### SC-08: `npm run build` produces frontend/dist/index.html

**Where:** Terminal
**Steps:**
1. Run `cd frontend && npm run build`
2. Check `ls frontend/dist/index.html`

**Expected:** File exists. Build exits 0.
**Result:** [ ] PASS  [ ] FAIL
**Notes:**

---

### SC-09: FastAPI serves /react — React app loads from dist

**Where:** http://localhost:8000/react (backend only, no Vite dev server)
**Steps:**
1. Stop the Vite dev server if running.
2. Ensure `frontend/dist/` is built (run `npm run build` if needed).
3. Start FastAPI: `uvicorn app.api.main:app --reload`
4. Navigate to http://localhost:8000/react
5. Verify the React app loads (AuthPanel or chat UI).
6. Navigate to http://localhost:8000/ — verify Vanilla JS app still loads.

**Expected:** /react serves the React UI from frontend/dist/. / still serves the Vanilla JS UI. No 404 or wrong app served.
**Result:** [ ] PASS  [ ] FAIL
**Notes:**

---

### SC-10: CORS for localhost:5173

**Where:** Browser DevTools Network tab (authenticated)
**Steps:**
1. Open http://localhost:5173 in browser.
2. Open DevTools → Network tab.
3. Send a message or reload the page (triggers API calls to localhost:8000).
4. Inspect an /api/* request.
5. Check Response Headers for `Access-Control-Allow-Origin: http://localhost:5173`.

**Expected:** No CORS errors in console. API requests succeed from the Vite dev origin.
**Result:** [ ] PASS  [ ] FAIL
**Notes:**

---

## Summary

| SC | Description | Result |
|----|-------------|--------|
| SC-01 | npm run build succeeds | |
| SC-02 | All components exist | |
| SC-03 | SSE + Markdown renders | |
| SC-04 | Thread sidebar + switching | |
| SC-05 | Device Flow completes | |
| SC-06 | Avatar + login in header | |
| SC-07 | gpt-4.1 default model | |
| SC-08 | dist/index.html produced | |
| SC-09 | FastAPI /react serves React | |
| SC-10 | CORS for localhost:5173 | |

**Overall result:** [ ] ALL PASS  [ ] ISSUES FOUND

**Issues to fix:**
(list any failures and describe fixes applied)
