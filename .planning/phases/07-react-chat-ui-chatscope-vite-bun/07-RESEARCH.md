# Phase 7: React Chat UI (chatscope + Vite + Bun) - Research

**Researched:** 2026-04-02
**Domain:** React frontend — chatscope, Vite, Bun, FastAPI StaticFiles, SSE, react-markdown
**Confidence:** HIGH (core stack verified via npm registry + official docs + GitHub source)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Full feature parity with Vanilla JS: Device Flow auth, multi-turn chat with Markdown rendering, thread history sidebar, model selector (gpt-4.1 default), GitHub user info (avatar + login), SSE + polling fallback, logout.
- **D-02:** React auth is self-contained — no dependency on Vanilla JS auth page.
- **D-03:** chatscope default CSS only. No dark theme customization. Minimal custom CSS.
- **D-04:** `bun run build` → `frontend/dist/` → FastAPI serves at `/react`. Vanilla JS stays at `/`. Dev: Vite dev server `:5173` + FastAPI `:8000` in parallel. CORS added to FastAPI for `localhost:5173`.
- **D-05:** User messages right (outgoing), AI messages left (incoming). chatscope standard layout.
- **D-06:** Left sidebar: thread history list + New Chat button.
- **D-07:** Model selector default: `gpt-4.1`.
- **D-08:** AI thinking state uses chatscope `TypingIndicator`.

### Claude's Discretion

- SSE client: `EventSource` native vs `@microsoft/fetch-event-source`
- Markdown rendering library choice
- Thread label display (first message excerpt vs datetime)
- Error display method (inline vs toast)
- `frontend/` directory structure and component design
- docker-compose integration (only if judged necessary)

### Deferred Ideas (OUT OF SCOPE)

- nginx routing between `/` and `/react`
- Docker Compose frontend build service
- Streaming responses
- Mobile responsiveness
</user_constraints>

---

## Summary

Phase 7 adds a React chat UI served at `/react` alongside the existing Vanilla JS UI at `/`. The stack is `@chatscope/chat-ui-kit-react` 2.1.1 + Vite 8.0.3 + Bun (installer only; bun not installed on this machine, `npm`/`node` v22 are available as fallback). The backend requires two additions: CORS middleware for dev (allowing `localhost:5173`) and a second StaticFiles mount for `frontend/dist/` at `/react`. The existing API surface is complete — no new backend routes needed.

The SSE flow from Vanilla JS maps cleanly to React: `POST /api/chat` → `job_id` → `EventSource(/api/chat/{job_id}/stream)` → done event → `GET /api/job/{job_id}`. Native `EventSource` is sufficient because the SSE subscription is a GET request (the job_id is in the URL path, not in a POST body).

For Markdown rendering, `react-markdown` 10.x with `remark-gfm` and `rehype-highlight` is the correct choice — ESM-native, no dangerouslySetInnerHTML, Vite-compatible. Render AI messages as `<ReactMarkdown>` children inside a chatscope `Message` with `type="custom"`.

**Primary recommendation:** Use native `EventSource`, `react-markdown` 10, and `useState`/`useContext` for state. No Zustand needed. Do NOT use `Message type="html"` — use `type="custom"` with `<Message.CustomContent>` to host the ReactMarkdown component safely.

---

## Standard Stack

### Core (new packages for this phase)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `@chatscope/chat-ui-kit-react` | 2.1.1 | Chat UI components | Locked decision. React 19 compatible since v2.1.1. |
| `@chatscope/chat-ui-kit-styles` | 1.4.0 | Default CSS theme | Required companion package for styles. |
| `react-markdown` | 10.1.0 | Markdown rendering | ESM-only, no dangerouslySetInnerHTML, Vite-compatible. |
| `remark-gfm` | 4.0.1 | GitHub Flavored Markdown | Tables, strikethrough, task lists. |
| `rehype-highlight` | 7.0.2 | Syntax highlighting | Integrates highlight.js via rehype. |

### Scaffold + runtime (already decided)

| Tool | Version | Purpose | Notes |
|------|---------|---------|-------|
| Vite | 8.0.3 | Build tool / dev server | Latest stable. Rolldown default bundler in v8. |
| Bun | 1.3.11 (npm install target) | Package manager | NOT installed on this machine — see Environment section. |
| React | 19.2.4 | UI framework | Latest stable. chatscope 2.1.1 added React 19 to peer deps. |
| TypeScript | 6.0.2 | Type safety | Scaffolded by `--template react-ts`. |

### NOT needed

| Instead of | Rationale |
|------------|-----------|
| `@microsoft/fetch-event-source` | SSE subscription is a GET (job_id in URL). Native `EventSource` is sufficient. |
| Zustand / Jotai | useState + useContext covers: auth state, thread list, active thread, messages, loading. This is a personal single-user tool. |
| React Router | No client-side routing needed. App is a single view (auth panel or chat). |

**Installation (inside `frontend/`):**
```bash
# If bun is available:
bun add @chatscope/chat-ui-kit-react @chatscope/chat-ui-kit-styles react-markdown remark-gfm rehype-highlight

# If bun is not installed (fallback — node v22 + npm available):
npm install @chatscope/chat-ui-kit-react @chatscope/chat-ui-kit-styles react-markdown remark-gfm rehype-highlight
```

**Version verification (run before writing the plan):**
```bash
npm view @chatscope/chat-ui-kit-react version   # 2.1.1
npm view @chatscope/chat-ui-kit-styles version  # 1.4.0
npm view react-markdown version                 # 10.1.0
npm view remark-gfm version                     # 4.0.1
npm view rehype-highlight version               # 7.0.2
npm view vite version                           # 8.0.3
```

---

## Architecture Patterns

### Recommended Project Structure

```
frontend/
├── public/                  # Static assets (favicon, etc.)
├── src/
│   ├── main.tsx             # React entrypoint
│   ├── App.tsx              # Root: AuthGate → ChatApp
│   ├── api/
│   │   └── client.ts        # All fetch wrappers (typed)
│   ├── components/
│   │   ├── AuthPanel.tsx    # Device Flow UI (code + polling)
│   │   ├── ChatApp.tsx      # MainContainer layout root
│   │   ├── ThreadSidebar.tsx # Sidebar + thread list + New Chat
│   │   ├── MessageArea.tsx  # ChatContainer + MessageList + MessageInput
│   │   ├── Header.tsx       # Model selector + user avatar + logout
│   │   └── MarkdownMessage.tsx # ReactMarkdown wrapper for AI messages
│   ├── hooks/
│   │   ├── useAuth.ts       # checkAuthStatus, startFlow, pollAuth, logout
│   │   ├── useThreads.ts    # list, create, delete, switch, loadMessages
│   │   └── useChat.ts       # sendMessage, SSE, polling fallback
│   └── types.ts             # Shared TypeScript types
├── index.html
├── vite.config.ts
├── tsconfig.json
└── package.json
```

### Pattern 1: chatscope Component Hierarchy

chatscope imposes a strict nesting requirement. All the following must nest correctly or components will not render/style properly.

```tsx
// Source: github.com/chatscope/chat-ui-kit-react README + source inspection
import '@chatscope/chat-ui-kit-styles/dist/default/styles.min.css';
import {
  MainContainer,
  ChatContainer,
  MessageList,
  Message,
  MessageInput,
  Sidebar,
  TypingIndicator,
} from '@chatscope/chat-ui-kit-react';

// Outer div MUST have explicit height — chatscope uses 100% height internally
<div style={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
  <Header />  {/* Outside MainContainer — model select + user info + logout */}
  <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
    <MainContainer>
      <Sidebar position="left">
        {/* Thread list goes here */}
      </Sidebar>
      <ChatContainer>
        <MessageList
          typingIndicator={isThinking ? <TypingIndicator content="Copilot is thinking..." /> : null}
        >
          {messages.map((msg, i) => (
            <Message key={i} model={{
              direction: msg.role === 'user' ? 'outgoing' : 'incoming',
              position: 'single',
              type: msg.role === 'ai' ? 'custom' : 'text',
              message: msg.role === 'user' ? msg.content : undefined,
            }}>
              {msg.role === 'ai' && (
                <Message.CustomContent>
                  <MarkdownMessage content={msg.content} />
                </Message.CustomContent>
              )}
            </Message>
          ))}
        </MessageList>
        <MessageInput
          placeholder="Ask Copilot anything... (Enter to send)"
          onSend={handleSend}
          attachButton={false}
        />
      </ChatContainer>
    </MainContainer>
  </div>
</div>
```

### Pattern 2: Message type="custom" for Markdown (CRITICAL)

Do NOT use `type="html"` with `payload` — it sets innerHTML directly which bypasses React's XSS protection. Use `type="custom"` with `<Message.CustomContent>` to host a `<ReactMarkdown>` component. This keeps rendering inside React's VDOM.

```tsx
// Source: chatscope Message.jsx source inspection + react-markdown docs
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github.css';  // or any hljs theme

function MarkdownMessage({ content }: { content: string }) {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
      {content}
    </ReactMarkdown>
  );
}

// In MessageList:
<Message model={{ direction: 'incoming', position: 'single', type: 'custom' }}>
  <Message.CustomContent>
    <MarkdownMessage content={aiMessage} />
  </Message.CustomContent>
</Message>
```

### Pattern 3: SSE + Polling Fallback

Mirrors Vanilla JS exactly. Native `EventSource` is correct because the SSE URL is a GET (`/api/chat/{job_id}/stream`).

```tsx
// Source: static/app.js lines 387-430 + MDN EventSource API
async function sendMessage(text: string) {
  // 1. POST /api/chat → { job_id, thread_id }
  const { job_id } = await postChat(text, activeThreadId, selectedModel);

  // 2. Check if already done (reconnect edge case)
  const immediate = await getJob(job_id);
  if (immediate.status === 'done') {
    setMessages(msgs => [...msgs, { role: 'ai', content: immediate.result }]);
    return;
  }

  // 3. SSE stream
  const es = new EventSource(`/api/chat/${job_id}/stream`);
  es.onmessage = async (e) => {
    const { status } = JSON.parse(e.data);
    if (status === 'done') {
      es.close();
      const result = await getJob(job_id);
      setMessages(msgs => [...msgs, { role: 'ai', content: result.result }]);
      setIsThinking(false);
    }
  };
  es.onerror = () => {
    es.close();
    // Polling fallback: poll every 2 seconds
    const timer = setInterval(async () => {
      const job = await getJob(job_id);
      if (job.status === 'done') {
        clearInterval(timer);
        setMessages(msgs => [...msgs, { role: 'ai', content: job.result }]);
        setIsThinking(false);
      }
    }, 2000);
  };
}
```

### Pattern 4: Device Flow Auth in React

```tsx
// Source: static/app.js lines 169-239
function useAuth() {
  const [authState, setAuthState] = useState<'unknown' | 'authenticated' | 'unauthenticated' | 'expired'>('unknown');
  const [flowData, setFlowData] = useState<{ user_code: string; verification_uri: string; flow_id: string } | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // On mount: check current auth status
  useEffect(() => {
    fetch('/api/auth/status')
      .then(r => r.json())
      .then(data => {
        if (data.authenticated) setAuthState('authenticated');
        else if (data.expired) setAuthState('expired');
        else setAuthState('unauthenticated');
      });
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  const startFlow = async () => {
    const data = await fetch('/api/auth/start', { method: 'POST' }).then(r => r.json());
    setFlowData({ user_code: data.user_code, verification_uri: data.verification_uri, flow_id: data.flow_id });
    pollRef.current = setInterval(() => pollAuth(data.flow_id), 5000);
  };

  const pollAuth = async (flowId: string) => {
    const data = await fetch(`/api/auth/poll?flow_id=${flowId}`).then(r => r.json());
    if (data.done) {
      clearInterval(pollRef.current!);
      setFlowData(null);
      setAuthState('authenticated');
    } else if (data.retry_after) {
      clearInterval(pollRef.current!);
      pollRef.current = setInterval(() => pollAuth(flowId), data.retry_after * 1000);
    } else if (data.error && !data.done) {
      clearInterval(pollRef.current!);
    }
  };

  return { authState, flowData, startFlow };
}
```

### Pattern 5: Vite Proxy Config (eliminates CORS in dev)

```typescript
// Source: vite.dev/config/server-options.html
// vite.config.ts — inside frontend/
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // NO rewrite — FastAPI routes are already at /api/...
      },
    },
  },
});
```

**Key point:** Do NOT add `rewrite`. The FastAPI routes are all under `/api/` prefix. If rewrite strips `/api`, all routes break.

CORS middleware in FastAPI is still required for production (when Vite dev server is not running and the browser hits `localhost:8000` directly from `localhost:8000/react`). Because same-origin requests (`/react` served by FastAPI hitting `/api` on the same origin) don't need CORS, production CORS is technically optional — but adding it for `localhost:5173` dev is mandatory.

### Pattern 6: FastAPI StaticFiles Mount

```python
# Source: FastAPI StaticFiles docs + current app/api/main.py pattern
# app/api/main.py — add BEFORE the existing "/" mount

from fastapi.middleware.cors import CORSMiddleware

# CORS for Vite dev server (must be added BEFORE routes and mounts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ... existing route includes ...

# React dist BEFORE the catch-all "/" mount
app.mount("/react", StaticFiles(directory="frontend/dist", html=True), name="react")

# Existing Vanilla JS — stays at "/"
app.mount("/", StaticFiles(directory="static", html=True), name="static")
```

**Critical: mount order.** The existing comment in `main.py` already says "Static files LAST". The new `/react` mount must appear AFTER API routes but BEFORE (above) the `/` mount. `html=True` enables the SPA-style fallback — any path under `/react/` that doesn't match a file returns `index.html`, which lets React handle routing.

**No React Router.** This app has no client-side routing. One single view: unauthenticated (auth panel) or authenticated (chat). `html=True` is still correct — it serves `index.html` for `/react` and any subpath.

### Anti-Patterns to Avoid

- **`Message type="html"`:** Sets innerHTML directly. Use `type="custom"` with `<Message.CustomContent>` + `<ReactMarkdown>` instead.
- **Forgetting the height wrapper:** chatscope components use `height: 100%` internally. Without an explicit height on the parent div, the UI collapses to 0px.
- **Rewriting `/api` in Vite proxy:** Strips the prefix needed by FastAPI. Use proxy with no `rewrite`.
- **Placing `/react` mount after `/`:** FastAPI processes mounts in order; `/` is a catch-all and will eat the `/react` path if it comes first.
- **Using `CORSMiddleware` after route includes:** Middleware must be added before routes are included or it won't apply to those routes.
- **`bun run dev` without Vite flag:** On some setups `bun dev` without `--bun` flag runs the node Vite binary. Prefer `bunx --bun vite` or configure `package.json` scripts explicitly.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Markdown rendering | Custom innerHTML + DOMPurify | `react-markdown` + `remark-gfm` + `rehype-highlight` | react-markdown has no dangerouslySetInnerHTML, XSS-safe by design |
| Typing indicator animation | CSS dots | `TypingIndicator` from chatscope | Built-in, accessible, matches kit styling |
| Message bubble layout | CSS flexbox from scratch | chatscope `Message` + `direction` prop | Handles position, grouping, alignment automatically |
| Chat scrolling | Custom scroll-to-bottom | chatscope `MessageList` with `autoScrollToBottom` | Handles edge cases (content resize, new message arrival) |
| SSE reconnection | Custom retry loop | `EventSource` built-in reconnect + manual `onerror` fallback | Browser EventSource auto-reconnects on network drops; add polling only on explicit error |

---

## Common Pitfalls

### Pitfall 1: chatscope Container Height Collapse
**What goes wrong:** The entire chat UI renders as a zero-height block. Nothing is visible.
**Why it happens:** chatscope's `MainContainer`, `ChatContainer`, and `MessageList` all use `height: 100%` CSS internally. If no ancestor has an explicit pixel/vh height, they collapse.
**How to avoid:** Wrap the chatscope section in a `div` with `height: 100vh` (or a calculated height that accounts for the header). Set `position: relative` on the wrapper.
**Warning signs:** UI appears blank; inspecting in DevTools shows 0px height elements.

### Pitfall 2: Vite Proxy Path Rewrite Breaks API
**What goes wrong:** All API calls return 404 or hit wrong routes.
**Why it happens:** A common Vite proxy example adds `rewrite: (path) => path.replace(/^\/api/, '')`. This strips the `/api` prefix that FastAPI routes expect.
**How to avoid:** In this project, FastAPI routes are defined under `/api` prefix in each router. Do NOT rewrite. The proxy should forward `/api/auth/start` as `/api/auth/start` to `localhost:8000`.
**Warning signs:** 404 on `/api/auth/status` in dev mode.

### Pitfall 3: CORSMiddleware Placement
**What goes wrong:** CORS headers missing on API responses during dev, even after adding middleware.
**Why it happens:** FastAPI processes middleware in reverse registration order. If `app.add_middleware(CORSMiddleware, ...)` is called after `app.include_router(...)`, the middleware may not wrap the routes correctly in some FastAPI versions.
**How to avoid:** Add `CORSMiddleware` at the top of the `main.py` app setup, before any `include_router` calls. The current `main.py` already has the `# API routes FIRST` comment — add middleware even before that block.
**Warning signs:** `Access-Control-Allow-Origin` header absent on preflight OPTIONS responses.

### Pitfall 4: StaticFiles Mount Order
**What goes wrong:** `/react` paths return the Vanilla JS index.html instead of the React index.html.
**Why it happens:** The existing `app.mount("/", ...)` is a catch-all. If it appears before `app.mount("/react", ...)`, it matches `/react/*` paths first.
**How to avoid:** The `/react` mount must appear above the `/` mount in `main.py`.
**Warning signs:** React app shows old Vanilla JS UI when navigating to `/react`.

### Pitfall 5: `frontend/dist/` Missing at Server Startup
**What goes wrong:** FastAPI crashes on startup with `StaticFiles directory 'frontend/dist' does not exist`.
**Why it happens:** `frontend/dist/` is the build output; it doesn't exist until `bun run build` is run.
**How to avoid:** Either (a) check for directory existence before mounting, or (b) run the build before starting the server, or (c) wrap the mount in a try/except and log a warning. Document in the project README that `cd frontend && bun run build` must run before the server.
**Warning signs:** Server startup exception mentioning `StaticFiles`.

### Pitfall 6: react-markdown ESM + Vite
**What goes wrong:** Build fails or runtime errors with `react-markdown`.
**Why it happens:** `react-markdown` v10 is ESM-only. This is fully compatible with Vite (which handles ESM natively), but can cause issues if any CommonJS-only config exists.
**How to avoid:** Use Vite's default React TypeScript template — it already handles ESM. Do not add `"type": "commonjs"` to `frontend/package.json`.
**Warning signs:** `ERR_REQUIRE_ESM` at runtime; `SyntaxError: Cannot use import statement` in tests.

### Pitfall 7: bun Not Installed (Environment)
**What goes wrong:** `bun create vite frontend --template react-ts` fails with `command not found: bun`.
**Why it happens:** Bun is not installed on this machine (verified). Node 22 + npm 10 are available as fallback.
**How to avoid:** Use `npm create vite@latest frontend -- --template react-ts` as the scaffold command. Install packages with `npm install`. All Bun-specific dev scripts (`bun run dev`, `bun run build`) work with `npm run dev` / `npm run build` equivalently via Vite CLI.
**Warning signs:** `command not found: bun` on first scaffold attempt.

---

## Code Examples

### CSS Import (required, top of main.tsx)
```tsx
// Source: github.com/chatscope/chat-ui-kit-react README
import '@chatscope/chat-ui-kit-styles/dist/default/styles.min.css';
```

### All chatscope Imports
```tsx
// Source: chatscope GitHub README + source inspection
import {
  MainContainer,
  ChatContainer,
  MessageList,
  Message,
  MessageInput,
  Sidebar,
  TypingIndicator,
} from '@chatscope/chat-ui-kit-react';
```

### TypingIndicator as MessageList Prop
```tsx
// Source: chatscope MessageList.jsx source inspection
// typingIndicator is a PROP on MessageList, not a child element
<MessageList
  typingIndicator={isThinking ? <TypingIndicator content="Copilot is thinking..." /> : null}
>
  {/* Message children here */}
</MessageList>
```

### react-markdown with Syntax Highlighting
```tsx
// Source: react-markdown docs + rehype-highlight docs
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github.css';

<ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
  {content}
</ReactMarkdown>
```

### TypeScript Types Derived from API (app/api/models.py)
```typescript
// Derived from backend app/api/models.py
interface AuthStartResponse {
  user_code: string;
  verification_uri: string;
  flow_id: string;
  device_code: string;
}
interface AuthPollResponse {
  done: boolean;
  error?: string;
  retry_after?: number;
}
interface AuthStatusResponse {
  authenticated: boolean;
  expired: boolean;
}
interface ChatAsyncResponse {
  job_id: string;
  thread_id: string;
}
interface JobStatusResponse {
  status: 'pending' | 'done';
  result?: string;
}
interface ThreadInfo {
  thread_id: string;
  updated_at: string;
  label: string;
}
interface UserInfoResponse {
  login: string;
  name?: string;
  avatar_url: string;
}
interface Message {
  role: 'user' | 'ai';
  content: string;
}
```

---

## State Management Recommendation

**Use `useState` + `useContext`. No external state library needed.**

The app has four distinct concerns, each local to a hook:

| State | Hook | Shared via |
|-------|------|-----------|
| Auth (state, flowData, user info) | `useAuth` | Context provider at App root |
| Threads (list, activeThreadId) | `useThreads` | Context or prop drilling (shallow) |
| Messages (current thread messages) | `useChat` | Local to `MessageArea` |
| UI flags (isThinking, isSending) | Local useState | Local to `MessageArea` |

Context is only needed to share auth state between `Header` (shows avatar/logout) and `ChatApp` (gates access). Thread + message state is local to the chat area and doesn't need to cross the component tree.

---

## Backend Changes Required

Only two changes to `app/api/main.py`:

1. **Add CORSMiddleware** (dev: allow `localhost:5173`; prod: harmless since same-origin)
2. **Add `/react` StaticFiles mount** for `frontend/dist/`

No new API routes are needed. The existing endpoints cover all required functionality:

| Feature | Endpoint | Already exists |
|---------|----------|----------------|
| Auth status | `GET /api/auth/status` | Yes |
| Start Device Flow | `POST /api/auth/start` | Yes |
| Poll Device Flow | `GET /api/auth/poll?flow_id=...` | Yes |
| Logout | `POST /api/auth/logout` | Yes |
| User info | `GET /api/me` | Yes |
| Send chat | `POST /api/chat` | Yes |
| SSE stream | `GET /api/chat/{job_id}/stream` | Yes |
| Job result | `GET /api/job/{job_id}` | Yes |
| List threads | `GET /api/threads` | Yes |
| Create thread | `POST /api/threads` | Yes |
| Delete thread | `DELETE /api/threads/{thread_id}` | Yes |
| Thread messages | `GET /api/threads/{thread_id}/messages` | Yes |

---

## Build + Serve Integration

**Build output:** `frontend/dist/` — standard Vite build output. Contains `index.html` + hashed asset files.

**`.gitignore`:** Add `frontend/dist/` and `frontend/node_modules/`. Build artifacts should not be committed. The built files are reproducible from source.

**Startup sequence:**
```bash
# Terminal 1: Backend
uvicorn app.api.main:app --reload

# Terminal 2: Frontend (dev mode — Vite proxy handles /api)
cd frontend && npm run dev     # or bun run dev if bun is installed

# Production build (before starting backend in production):
cd frontend && npm run build   # output: frontend/dist/
```

**`frontend/dist/` missing on server start:** FastAPI will raise a startup exception if the directory doesn't exist. The planner should include a build step in the wave that adds the StaticFiles mount, or add a guard:
```python
import os
if os.path.isdir("frontend/dist"):
    app.mount("/react", StaticFiles(directory="frontend/dist", html=True), name="react")
```

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | Vite scaffold + build | Yes | v22.19.0 | — |
| npm | Package installation | Yes | 10.9.3 | — |
| Bun | Decided stack | No | — | Use npm + npx (full compatibility) |
| Python 3.x | FastAPI backend | Assumed yes (existing project) | — | — |

**Bun not installed — action required:** The phase scaffold command must use `npm create vite@latest` instead of `bun create vite`. All `bun run` commands in scripts become `npm run`. This is a drop-in replacement; Vite is agnostic about the runner. Document in PLAN.md that bun can be installed later if desired, but npm is the fallback for all task execution.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | None detected for frontend. Backend uses pytest (inferred from Python stack). |
| Frontend testing | Not established — this phase creates the first React code. |
| Quick run command | `npm run build` (build smoke test — TypeScript compiler + Vite bundler catch type errors) |
| Full suite command | Not applicable for this phase |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| UI-01 (implicit) | `bun run build` produces `frontend/dist/index.html` | smoke | `npm run build` in `frontend/` | No — created in Wave 0 |
| UI-02 (implicit) | TypeScript compiles without errors | type-check | `npx tsc --noEmit` | No — created in Wave 0 |
| AUTH parity | Device Flow renders code + verification URL | manual | Observe in browser | N/A |
| CHAT parity | Message sends, AI response renders with markdown | manual | Observe in browser | N/A |
| SESS parity | Thread sidebar shows + switching works | manual | Observe in browser | N/A |

**Note:** This phase is UI-heavy. Automated testing of chatscope component rendering requires a DOM testing environment (Vitest + Testing Library). That setup is out of scope for this phase per CONTEXT.md constraints. Use TypeScript build success as the automated gate, and browser walkthrough for functional validation.

### Wave 0 Gaps

- [ ] `frontend/` directory does not exist — scaffold with `npm create vite@latest`
- [ ] `frontend/package.json` test script not yet defined
- [ ] `npm run build` as smoke test — created during scaffold

---

## Open Questions

1. **`frontend/dist/` conditional mount**
   - What we know: FastAPI crashes at startup if the directory is missing.
   - What's unclear: Whether to guard with `os.path.isdir()` or enforce a pre-start build step.
   - Recommendation: Add the `os.path.isdir` guard in `main.py` and print a warning. This lets the server start without the frontend build (useful in CI / early development).

2. **Thread label display**
   - What we know: Backend returns `label = f"Chat {thread_id[:8]}"` (8-char UUID prefix). The Vanilla JS shows `thread.label || thread.thread_id`.
   - What's unclear: Whether the React UI should attempt to show the first message content as the thread name (would require a separate fetch per thread).
   - Recommendation: Use the server-returned `label` as-is (datetime or UUID prefix). Do not fetch message content per thread for labeling — adds N API calls on sidebar load.

3. **Model list hardcoding**
   - What we know: Vanilla JS has a `<select>` with hardcoded model names. Default is `claude-sonnet-4.5` in Vanilla JS but `gpt-4.1` is the D-07 decision for React.
   - What's unclear: Full list of models to offer.
   - Recommendation: Use the same model list as the Vanilla JS `<select>` element in `static/index.html`, but set `gpt-4.1` as the default value per D-07.

---

## Sources

### Primary (HIGH confidence)
- `github.com/chatscope/chat-ui-kit-react` (README, releases, source) — component API, CSS import, version history
- `github.com/chatscope/chat-ui-kit-react/blob/master/src/components/MessageList/MessageList.jsx` — `typingIndicator` prop, autoScrollToBottom
- `github.com/chatscope/chat-ui-kit-react/blob/master/src/components/Message/Message.jsx` — direction, position, type="custom", Message.CustomContent
- `vite.dev/config/server-options.html` — server.proxy configuration shape
- npm registry — verified versions for all packages
- `static/app.js` — authoritative reference for all API patterns (SSE, polling, auth, threads)
- `app/api/main.py`, `app/api/routes/*.py` — confirmed complete API surface, no new routes needed

### Secondary (MEDIUM confidence)
- FastAPI CORS docs (`fastapi.tiangolo.com/tutorial/cors/`) — CORSMiddleware setup pattern
- `bun.com/docs/guides/ecosystem/vite` — Bun + Vite scaffold and run commands
- WebSearch: chatscope v2 breaking changes — confirmed v2.0 only removed defaultProps (minor), v2.1.1 adds React 19 peer dep

### Tertiary (LOW confidence)
- WebSearch: Bun known issues — ENOENT on Windows (not applicable on Linux); `base: './'` needed for some Bun+Vite static builds. Flag for testing.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified via npm registry
- Architecture: HIGH — derived directly from chatscope source + existing app.js patterns
- Pitfalls: HIGH — mount order / CORS placement verified against FastAPI docs and existing main.py; height collapse is documented chatscope behavior
- Environment: HIGH — bun absence confirmed by `command -v bun`

**Research date:** 2026-04-02
**Valid until:** 2026-05-02 (chatscope and react-markdown are stable; Vite 8 released 2025-01-xx)
