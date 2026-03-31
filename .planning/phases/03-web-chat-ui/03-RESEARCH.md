# Phase 3: Web + Chat UI - Research

**Researched:** 2026-04-01
**Domain:** FastAPI + Vanilla JS Chat UI + Device Flow UX + Markdown rendering
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Auth Flow UX**
- D-01: GitHub Device Flow の URL 表示は `window.open()` による自動オープンなし。クリック可能なリンクとして表示するのみ。
- D-02: デバイスコードは Copy ボタン付きで大きく表示する（クリックでクリップボードにコピー）。
- D-03: 認証完了の検知はポーリング（5秒間隔）で自動検知し、完了後にページを自動更新する。ユーザーによる手動操作不要。
- D-04: AUTH-03（トークン期限切れ時）— ヘッダーの認証ステータス表示が "期限切れ — Click to re-auth" に変わる。バナーやモーダルは使わない。クリックで再認証フローを起動。

**Layout & Structure**
- D-05: サイドバーあり（左側）。スレッド履歴一覧を表示する。SESS-01/02 を v1 に前倒し。
- D-06: サイドバー上部に "New Chat" ボタンを配置する（CHAT-04）。
- D-07: ヘッダーは最小限: アプリ名 + 認証ステータスのみ。
- D-08: メッセージバブルはユーザー右寄せ / AI 左寄せで区別する。

**Model Selection**
- D-09: ヘッダーまたはサイドバーにモデル選択ドロップダウンを配置する（配置位置は planner が決定）。
- D-10: モデルリストはフロントエンドにハードコード（gpt-4.1, gpt-4o, o3 など）。バックエンドへの動的取得は行わない。
- D-11: モデル切り替えは次の送信から反映される。

**Loading State**
- D-12: AI 応答待ち中は、AI 側に "..." 打鍵アニメーションバブルを表示する。
- D-13: 送信後は入力欄と送信ボタンを無効化。応答受信後に再有効化。

### Claude's Discretion

- Markdown レンダリングライブラリの選択（marked.js + highlight.js が標準）
- FastAPI エンドポイント設計（POST /chat, GET /threads など）
- thread_id の生成・管理方法（サーバーサイドで UUID 生成が自然）
- エラー時の表示方法（メッセージリスト内にインラインエラー or トースト）
- スレッドの命名表示（自動でメッセージ先頭を使うか、"Chat YYYY-MM-DD HH:mm" 形式か）

### Deferred Ideas (OUT OF SCOPE)

- SESS-03（セッション名付け）— v2 要件
- ツール呼び出し（bind_tools）— v2 要件
- ストリーミング応答 — SDK 対応後の将来拡張
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUTH-03 | トークン期限切れ時に UI 上で Re-authenticate ボタンを表示し、再認証フローを起動できる | Token expiry detection via API 401 response; backend `/api/auth/status` endpoint; frontend header status update with click-to-reauth pattern |
| CHAT-01 | ユーザー・AI の発言を時系列で表示するメッセージ一覧を持つ | FastAPI `POST /api/chat` → graph.ainvoke with thread_id; frontend DOM message bubble rendering |
| CHAT-02 | テキスト入力・送信ボタン・ローディング表示を含む送受信フローが動作する | disable-on-send pattern; "..." typing animation bubble; re-enable on response |
| CHAT-03 | AI 回答の Markdown およびコードブロックを整形レンダリングする | marked.js v17 + marked-highlight + highlight.js via CDN; `marked.parse()` on AI reply content |
| CHAT-04 | 新規チャットボタンで会話スレッドをリセットできる | `POST /api/threads` to generate new UUID thread_id; frontend clears message list and sets active thread |
| SESS-01 | チャット履歴を SQLite に永続化し、再起動後も閲覧できる | AsyncSqliteSaver already handles this via thread_id checkpoints; no extra work needed |
| SESS-02 | サイドバーに過去のチャットセッション一覧を表示できる | `SELECT DISTINCT thread_id, MAX(checkpoint_id) FROM checkpoints GROUP BY thread_id` query against AsyncSqliteSaver's `checkpoints` table |
</phase_requirements>

---

## Summary

Phase 3 wires together the existing Python backend components (graph, auth manager, ChatCopilot) into a FastAPI application and adds a Vanilla JS chat UI served as static files. The backend needs three categories of endpoints: auth management (Device Flow start/poll/status), chat (send message, list threads), and static file serving for the HTML/CSS/JS. The frontend uses marked.js v17 + highlight.js via CDN for Markdown rendering — no build step required.

The critical integration insight is the FastAPI lifespan pattern: `AsyncSqliteSaver.from_conn_string()` must be opened as an async context manager inside the lifespan function, the compiled graph stored on `app.state`, and routes access it via `request.app.state.graph`. This pattern is well-documented and directly compatible with the `build_graph(llm, checkpointer)` factory already in place.

For thread listing (SESS-02, front-loaded to v1), the `checkpoints` table schema is confirmed: `thread_id TEXT NOT NULL`, with one row per checkpoint. Listing threads requires `SELECT DISTINCT thread_id, MAX(checkpoint_id) as latest FROM checkpoints GROUP BY thread_id ORDER BY latest DESC` — there is no higher-level LangGraph API for this, so a thin direct SQL query via `aiosqlite` is the right approach.

**Primary recommendation:** Use FastAPI 0.135.2 + uvicorn 0.42.0 (add to pyproject.toml — not yet in project venv), FastAPI lifespan for resource lifecycle, `app.state` for shared graph/checkpointer, marked.js v17 via CDN for Markdown, and direct aiosqlite query for thread listing.

---

## Project Constraints (from CLAUDE.md)

| Directive | Constraint |
|-----------|-----------|
| Frontend | Vanilla JS + HTML/CSS only — no npm, no bundler, no React/HTMX |
| Backend | FastAPI + uvicorn — not Flask, not Django |
| Persistence | AsyncSqliteSaver — not Redis, not MemorySaver |
| Auth | Device Flow only — PAT out of scope |
| SDK isolation | Copilot SDK imports only in `app/providers/copilot.py` |
| Async pattern | All code uses `async def` — no `requests` (sync) |
| Pydantic | v2 patterns: `ConfigDict`, `PrivateAttr`, `model_dump()` |
| Packaging | `pyproject.toml` + `uv` — not requirements.txt |
| GSD workflow | Use `/gsd:execute-phase` for file changes — not direct edits outside GSD |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `fastapi` | 0.135.2 | HTTP API + static file serving | Already in CLAUDE.md tech stack; ASGI + async-native |
| `uvicorn[standard]` | 0.42.0 | ASGI server | Standard FastAPI server; `[standard]` adds uvloop |
| `python-multipart` | latest | Form data support (FastAPI dep) | Required when accepting form fields — needed for FastAPI's built-in form handling |
| marked.js | 17.0.5 (CDN) | Markdown → HTML in browser | Standard Markdown renderer for Vanilla JS; no build step via CDN |
| marked-highlight | 2.2.3 (CDN) | Code block syntax highlighting extension | Official marked.js plugin for highlight.js integration |
| highlight.js | 11.11.1 (CDN) | Syntax coloring for code blocks | Industry standard; 200+ languages; via CDN in `<script>` |

**Version verification:** Confirmed via `npm view` on 2026-04-01:
- marked: 17.0.5
- marked-highlight: 2.2.3
- highlight.js: 11.11.1

FastAPI 0.135.2 and uvicorn 0.42.0 confirmed as latest on PyPI (2026-04-01).

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `aiosqlite` | 0.22.1 | Direct async SQL queries against checkpoints DB | Thread listing (SESS-02) — `SELECT DISTINCT thread_id` query |
| `python-ulid` or `uuid` stdlib | stdlib | thread_id generation | `uuid.uuid4()` from stdlib is sufficient — no extra dep needed |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| marked.js CDN | DOMPurify + custom | marked.js handles all CommonMark edge cases; custom is risky |
| Direct SQL for threads | LangGraph `alist()` | `alist()` needs a `config` filter — no "list all threads" call without config; direct SQL is simpler |
| `app.state` for graph | Dependency injection | `app.state` is simpler for single-instance tools; DI adds boilerplate |

**Installation:**
```bash
uv add fastapi uvicorn[standard] python-multipart
```

---

## Architecture Patterns

### Recommended Project Structure

```
app/
├── api/
│   ├── __init__.py
│   ├── main.py          # FastAPI app, lifespan, static mount
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py      # /api/auth/* endpoints
│   │   ├── chat.py      # /api/chat, /api/threads endpoints
│   └── models.py        # Pydantic request/response models
static/
├── index.html           # Single page chat UI
├── app.js               # All frontend JS
└── style.css            # Layout and message bubble styles
tests/
├── test_api_chat.py     # Tests for /api/chat and /api/threads
└── test_api_auth.py     # Tests for /api/auth/* endpoints
```

### Pattern 1: FastAPI Lifespan with AsyncSqliteSaver + graph

**What:** Initialize AsyncSqliteSaver and compiled graph at startup, store on `app.state`, share across requests.

**When to use:** Always — this is the only correct pattern for async SQLite + LangGraph in FastAPI.

**Example:**
```python
# Source: https://fastapi.tiangolo.com/advanced/events/ + verified against langgraph-checkpoint-sqlite source
from contextlib import asynccontextmanager
from fastapi import FastAPI
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from app.graph.builder import build_graph
from app.auth.manager import CopilotAuthManager
from app.providers.copilot import ChatCopilot

@asynccontextmanager
async def lifespan(app: FastAPI):
    auth_manager = CopilotAuthManager()
    llm = ChatCopilot(auth_manager=auth_manager)

    async with AsyncSqliteSaver.from_conn_string("./data/chat.db") as checkpointer:
        app.state.graph = build_graph(llm, checkpointer)
        app.state.checkpointer = checkpointer
        app.state.auth_manager = auth_manager
        app.state.llm = llm
        yield
    # AsyncSqliteSaver context manager handles close automatically

app = FastAPI(lifespan=lifespan)
```

### Pattern 2: Route Access via app.state

**What:** Routes access the compiled graph via `request.app.state`.

**Example:**
```python
# Source: verified pattern from FastAPI + LangGraph integration
from fastapi import APIRouter, Request
from langchain_core.messages import HumanMessage

router = APIRouter()

@router.post("/api/chat")
async def chat(request: Request, body: ChatRequest):
    graph = request.app.state.graph
    config = {"configurable": {"thread_id": body.thread_id}}
    result = await graph.ainvoke(
        {"messages": [HumanMessage(content=body.message)]},
        config=config,
    )
    reply = result["messages"][-1].content
    return {"reply": reply, "thread_id": body.thread_id}
```

### Pattern 3: Thread Listing via Direct SQL

**What:** Query the `checkpoints` table directly via aiosqlite to get per-thread latest activity.

**When to use:** Sidebar thread list (SESS-02). LangGraph's `alist()` API requires a thread_id filter — there is no "list all threads" method.

**Example:**
```python
# Source: verified from AsyncSqliteSaver.setup() source — table: checkpoints(thread_id, checkpoint_id)
import aiosqlite

async def list_threads(db_path: str, limit: int = 50) -> list[dict]:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            """SELECT thread_id, MAX(checkpoint_id) as latest
               FROM checkpoints
               WHERE checkpoint_ns = ''
               GROUP BY thread_id
               ORDER BY latest DESC
               LIMIT ?""",
            (limit,),
        ) as cur:
            rows = await cur.fetchall()
    return [{"thread_id": row[0], "updated_at": row[1]} for row in rows]
```

**Note:** `checkpoint_ns` defaults to `''` (empty string) for the root namespace. Filter on `checkpoint_ns = ''` to avoid duplicates from nested subgraphs.

### Pattern 4: Device Flow Polling Endpoint Pair

**What:** Two endpoints — one to start Device Flow (returns user_code + verification_uri), one to poll for completion.

**When to use:** AUTH-03 re-auth flow and initial login.

**Example:**
```python
@router.post("/api/auth/start")
async def start_auth(request: Request):
    """Returns: {user_code, verification_uri, device_code}"""
    # Call CopilotAuthManager.device_login() in background or refactor
    # into a step-based approach: start returns codes, poll checks status
    ...

@router.get("/api/auth/status")
async def auth_status(request: Request):
    """Returns: {authenticated: bool, expired: bool}"""
    token = request.app.state.auth_manager.load_token()
    if token is None:
        return {"authenticated": False, "expired": False}
    # Attempt a lightweight API call to detect 401
    ...
```

**Important:** `CopilotAuthManager.device_login()` currently blocks the full polling loop internally. For the Web UI, the Device Flow needs to be split: (1) start — get codes, (2) frontend polls `/api/auth/poll` on a 5s interval, (3) backend checks GitHub once per poll call. This refactor is needed (see Pitfall 2).

### Pattern 5: Markdown Rendering in Browser

**What:** CDN-loaded marked.js + marked-highlight + highlight.js with `marked.parse()`.

**Example:**
```javascript
// Source: https://cdn.jsdelivr.net/npm/marked-highlight/README.md
// Include in index.html:
// <script src="https://cdn.jsdelivr.net/npm/marked/lib/marked.umd.js"></script>
// <script src="https://cdn.jsdelivr.net/npm/marked-highlight/lib/index.umd.js"></script>
// <script src="https://cdn.jsdelivr.net/npm/highlight.js@11.11.1/lib/core.min.js"></script>
// <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/highlight.js@11.11.1/styles/github.min.css">

const { Marked } = globalThis.marked;
const { markedHighlight } = globalThis.markedHighlight;

const md = new Marked(
  markedHighlight({
    emptyLangClass: 'hljs',
    langPrefix: 'hljs language-',
    highlight(code, lang) {
      const language = hljs.getLanguage(lang) ? lang : 'plaintext';
      return hljs.highlight(code, { language }).value;
    }
  })
);

function renderMessage(content) {
  return md.parse(content);
}
```

### Anti-Patterns to Avoid

- **Using `MemorySaver` in production FastAPI:** State lost on restart. Use `AsyncSqliteSaver` inside lifespan.
- **Creating graph outside lifespan:** Graph requires a running checkpointer. Must be inside `async with AsyncSqliteSaver.from_conn_string(...)`.
- **Polling Device Flow from the browser with the existing `device_login()` method:** The current `device_login()` blocks the event loop for the full polling cycle. Refactor into a start/poll split.
- **innerHTML with unsanitized LLM output:** marked.js v17 has XSS protections enabled by default (`sanitize` removed in v1, renderer uses safe mode). However, for defense in depth, avoid raw `innerHTML` injection of user-supplied content.
- **Mounting StaticFiles before API routes:** Mount order matters. API routes must be registered before `app.mount("/", StaticFiles(...))`, otherwise the static handler may intercept API calls.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Markdown parsing | Custom regex/parser | marked.js 17 | CommonMark compliance requires 1000+ edge cases |
| Code syntax highlighting | Custom highlighter | highlight.js 11 | 200+ languages, themes, battle-tested |
| ASGI lifecycle management | Custom startup hooks | FastAPI lifespan | lifespan `asynccontextmanager` is the canonical pattern |
| Request validation | Manual JSON parsing | Pydantic BaseModel in FastAPI | Auto-validation, 422 errors, OpenAPI docs |
| UUID generation | Custom ID scheme | `uuid.uuid4()` from stdlib | Already available, collision-resistant |
| Async SQLite connection | Raw sqlite3 | aiosqlite (already installed) | `sqlite3` blocks the event loop in async context |

**Key insight:** The project already has aiosqlite installed (it's a dependency of langgraph-checkpoint-sqlite). The thread listing query can use aiosqlite directly against the same database file that AsyncSqliteSaver uses.

---

## Common Pitfalls

### Pitfall 1: AsyncSqliteSaver Connection Sharing Between Lifespan and Route Queries

**What goes wrong:** If thread-listing code opens a second `aiosqlite` connection to the same `.db` file while AsyncSqliteSaver holds a WAL-mode connection, writes may stall if WAL is not configured.

**Why it happens:** SQLite WAL mode (enabled by AsyncSqliteSaver's `PRAGMA journal_mode=WAL`) allows concurrent readers. The separate `aiosqlite.connect()` in `list_threads()` opens a second connection that reads — this is safe in WAL mode.

**How to avoid:** Always read-only in the thread listing query. Never write to the `checkpoints` table directly. Store the `db_path` string on `app.state` so all code uses the same path.

**Warning signs:** `sqlite3.OperationalError: database is locked` — means a write is competing.

### Pitfall 2: device_login() Blocks the Lifespan or Route Handler

**What goes wrong:** `CopilotAuthManager.device_login()` runs an infinite polling loop internally. Calling it directly from a FastAPI route will block the event loop for up to 15 minutes.

**Why it happens:** The current `device_login()` was designed for CLI use, not Web use.

**How to avoid:** The Web UI pattern requires the Device Flow to be split across two endpoints:
1. `POST /api/auth/start` — calls GitHub to get `device_code`, `user_code`, `verification_uri`; stores `device_code` in a server-side dict (keyed by session or a temporary token); returns `user_code` + `verification_uri` to browser
2. `GET /api/auth/poll` — browser calls this every 5s; backend makes ONE poll POST to GitHub token URL; returns `{done: true, token: "..."}` or `{done: false}`

This requires extracting the single-shot poll from `device_login()` or adding a new method to `CopilotAuthManager`.

**Warning signs:** Route handler doesn't return for minutes; uvicorn logs show long-running request.

### Pitfall 3: Static Files Mount Intercepts API Routes

**What goes wrong:** Mounting `StaticFiles` on `/` before registering API routes causes 404 on all API calls because the static handler tries to serve them as files.

**Why it happens:** FastAPI/Starlette route matching is order-dependent.

**How to avoid:** Always register all `APIRouter` routes with `app.include_router()` **before** `app.mount("/", StaticFiles(..., html=True))`. Or mount static files at `/static` and serve `index.html` via a dedicated `GET /` route.

**Warning signs:** API returns `404` even though routes are defined; requests never hit route handlers.

### Pitfall 4: Token Expiry Not Detectable Without a Live API Call

**What goes wrong:** `auth_manager.load_token()` returns a token from disk, but that token may be expired. There is no expiry timestamp stored in the encrypted payload.

**Why it happens:** `CopilotAuthManager.save_token()` stores only `github_token` and `saved_at` — no expiry field. GitHub `ghu_` tokens have no advertised expiry but can be revoked. The Copilot SDK's `send_and_wait()` will raise if the token is invalid.

**How to avoid:** Detect expiry by catching exceptions from graph invocation. In the chat route: catch the specific exception from ChatCopilot when the SDK reports invalid token, set an "auth_expired" flag on `app.state`, and return `{"error": "auth_expired"}` to the frontend. The frontend checks this response field and updates the header status to "Expired — Click to re-auth".

**Warning signs:** Chat endpoint returns 500 after a period of inactivity; SDK logs show auth errors.

### Pitfall 5: Thread ID Not Passed From Frontend to Backend

**What goes wrong:** Frontend generates a local `thread_id` (e.g., `crypto.randomUUID()`) but doesn't send it with each message, causing the backend to start a new thread on every request.

**Why it happens:** Forgetting to include `thread_id` in the request body.

**How to avoid:** The backend generates `thread_id` with `uuid.uuid4()` when `POST /api/threads` is called (New Chat). The frontend stores the returned `thread_id` in memory (`let activeThreadId = ...`) and includes it in every `POST /api/chat` body. The backend never generates a thread_id inside the chat handler.

**Warning signs:** No conversation history on follow-up messages; each message appears to be a new session.

### Pitfall 6: marked.js v17 API Change — `marked` is no longer a direct function

**What goes wrong:** Code written for marked.js < v5 uses `marked(text)` (function call). In v17, the top-level export changed.

**Why it happens:** Breaking change in marked.js v5+ — the default export is an object, not a callable.

**How to avoid:** Use `const { Marked } = globalThis.marked; const md = new Marked(...); md.parse(text)` for the UMD browser build. Or use `marked.parse(text)` if using the simple (non-configurable) default instance. The UMD global `globalThis.marked` exposes both `Marked` (class) and `parse` (function).

**Warning signs:** `TypeError: marked is not a function` in browser console.

---

## Code Examples

### FastAPI App Entry Point with Lifespan

```python
# app/api/main.py
# Source: FastAPI docs https://fastapi.tiangolo.com/advanced/events/
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from app.api.routes import auth, chat
from app.auth.manager import CopilotAuthManager
from app.providers.copilot import ChatCopilot
from app.graph.builder import build_graph

DB_PATH = "./data/chat.db"

@asynccontextmanager
async def lifespan(app: FastAPI):
    Path("./data").mkdir(exist_ok=True)
    auth_manager = CopilotAuthManager()
    llm = ChatCopilot(auth_manager=auth_manager)
    async with AsyncSqliteSaver.from_conn_string(DB_PATH) as checkpointer:
        app.state.graph = build_graph(llm, checkpointer)
        app.state.checkpointer = checkpointer
        app.state.auth_manager = auth_manager
        app.state.llm = llm
        app.state.db_path = DB_PATH
        app.state.auth_expired = False
        yield
    await llm.close()

app = FastAPI(lifespan=lifespan)
app.include_router(auth.router)
app.include_router(chat.router)
# Static files LAST — must come after API routes
app.mount("/", StaticFiles(directory="static", html=True), name="static")
```

### Pydantic v2 Request/Response Models

```python
# app/api/models.py
from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str
    thread_id: str
    model: str = "gpt-4.1"

class ChatResponse(BaseModel):
    reply: str
    thread_id: str

class ThreadInfo(BaseModel):
    thread_id: str
    updated_at: str  # ISO-format checkpoint_id (ULIDv26 sortable)
    preview: str = ""  # first ~50 chars of first human message (optional)
```

### Frontend: Typing Animation Bubble (D-12)

```javascript
// app.js — add/remove typing indicator
function showTyping() {
  const bubble = document.createElement('div');
  bubble.id = 'typing-indicator';
  bubble.className = 'message ai';
  bubble.innerHTML = '<span class="dots"><span>.</span><span>.</span><span>.</span></span>';
  document.getElementById('message-list').appendChild(bubble);
  bubble.scrollIntoView({ behavior: 'smooth' });
}

function hideTyping() {
  document.getElementById('typing-indicator')?.remove();
}
```

### Frontend: Send Message Flow (D-13)

```javascript
async function sendMessage() {
  const input = document.getElementById('user-input');
  const sendBtn = document.getElementById('send-btn');
  const text = input.value.trim();
  if (!text || !activeThreadId) return;

  // Disable inputs (D-13)
  input.disabled = true;
  sendBtn.disabled = true;

  appendMessage('user', text);
  input.value = '';
  showTyping();  // D-12

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, thread_id: activeThreadId, model: selectedModel }),
    });
    const data = await res.json();
    hideTyping();

    if (data.error === 'auth_expired') {
      setAuthExpired();  // D-04
    } else {
      appendMessage('ai', data.reply);  // uses md.parse() for Markdown
      refreshThreadList();
    }
  } catch (e) {
    hideTyping();
    appendMessage('error', 'Network error. Please retry.');
  } finally {
    input.disabled = false;
    sendBtn.disabled = false;
    input.focus();
  }
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `app.on_event("startup")` | `lifespan` async context manager | FastAPI ~0.93 | Old approach deprecated; lifespan is canonical |
| `marked(text)` function call | `new Marked(...).parse(text)` or `marked.parse(text)` | marked.js v5 | Breaking API change — instantiate Marked class |
| `TestClient` for async routes | `httpx.AsyncClient` + `ASGITransport` | FastAPI async testing | TestClient is sync; async routes need async client |
| `MemorySaver` | `AsyncSqliteSaver` with lifespan | LangGraph 1.0 | MemorySaver lost on restart |

**Deprecated/outdated:**
- `marked.setOptions({ highlight: fn })`: Removed in marked.js v5. Use `markedHighlight` extension instead.
- `fastapi.on_event("startup")`: Deprecated since FastAPI 0.93. Use `lifespan` parameter.

---

## Open Questions

1. **CopilotAuthManager: split device_login() for Web use**
   - What we know: Current `device_login()` blocks for the full polling cycle — unsuitable for an HTTP route handler.
   - What's unclear: Best split point — new method on the class vs. inline logic in the auth route.
   - Recommendation: Add `start_device_flow() -> dict` (returns codes) and `check_device_flow(device_code) -> str | None` (single poll attempt, returns token or None) to `CopilotAuthManager`. Planner should create a task for this.

2. **Token expiry detection precision**
   - What we know: GitHub `ghu_` tokens can be revoked. The Copilot SDK raises on invalid token. No expiry timestamp is stored.
   - What's unclear: Exact exception type from SDK when token is invalid vs. network error.
   - Recommendation: Wrap `graph.ainvoke()` in `try/except Exception`; inspect exception message for auth-related strings; set `app.state.auth_expired = True` if detected. Implementer should add a targeted test.

3. **Thread preview text for sidebar (SESS-02)**
   - What we know: The `checkpoints` table stores full conversation state as a BLOB (serialized). Parsing it for a preview is feasible but adds complexity.
   - What's unclear: Whether a simple "Chat YYYY-MM-DD HH:mm" label is sufficient for v1 sidebar items.
   - Recommendation: Use "Chat YYYY-MM-DD HH:mm" format derived from the `checkpoint_id` (which is a ULID — first 10 chars encode timestamp). This avoids deserializing checkpoint BLOBs. Planner can defer rich previews to SESS-03/v2.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | Runtime | Yes | 3.12.3 | — |
| fastapi | HTTP backend | No (not in venv) | — | Add to pyproject.toml: Wave 0 task |
| uvicorn[standard] | ASGI server | No (not in venv) | — | Add to pyproject.toml: Wave 0 task |
| python-multipart | FastAPI form data | No (not in venv) | — | Add to pyproject.toml: Wave 0 task |
| aiosqlite | Thread listing SQL | Yes | 0.22.1 | — |
| httpx | Async HTTP (auth polling) | Yes | 0.28.1 | — |
| langgraph-checkpoint-sqlite | Persistence | Yes | 3.0.3 | — |
| marked.js (CDN) | Markdown render | CDN (no install) | 17.0.5 | — |
| highlight.js (CDN) | Code highlighting | CDN (no install) | 11.11.1 | — |
| Browser (any modern) | Frontend | Available | — | — |

**Missing dependencies with no fallback:**
- `fastapi`, `uvicorn[standard]`, `python-multipart` — must be added to pyproject.toml before any Wave 1 tasks can run the server.

**Missing dependencies with fallback:**
- None.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.25 |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`, `asyncio_mode = "auto"`) |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-03 | `/api/auth/status` returns `{expired: true}` when no token | unit | `uv run pytest tests/test_api_auth.py::test_auth_status_no_token -x` | Wave 0 |
| AUTH-03 | Header click triggers `/api/auth/start` → returns user_code | unit | `uv run pytest tests/test_api_auth.py::test_auth_start_returns_codes -x` | Wave 0 |
| CHAT-01 | `POST /api/chat` returns reply with same thread_id | unit (mock LLM) | `uv run pytest tests/test_api_chat.py::test_chat_returns_reply -x` | Wave 0 |
| CHAT-02 | `POST /api/chat` with empty message returns 422 | unit | `uv run pytest tests/test_api_chat.py::test_chat_rejects_empty_message -x` | Wave 0 |
| CHAT-03 | AI reply containing Markdown is passed through (rendering is client-side) | unit | `uv run pytest tests/test_api_chat.py::test_chat_markdown_passthrough -x` | Wave 0 |
| CHAT-04 | `POST /api/threads` returns a new UUID thread_id | unit | `uv run pytest tests/test_api_chat.py::test_new_thread_returns_uuid -x` | Wave 0 |
| SESS-01 | Second invocation on same thread_id includes prior message in LLM call | integration (AsyncSqliteSaver) | `uv run pytest tests/test_api_chat.py::test_thread_persistence -x` | Wave 0 |
| SESS-02 | `GET /api/threads` returns list with previously used thread_ids | unit | `uv run pytest tests/test_api_chat.py::test_list_threads -x` | Wave 0 |

**Note on test client:** Use `httpx.AsyncClient` with `ASGITransport` for all API tests (not `TestClient`). Project uses `asyncio_mode = "auto"` so `@pytest.mark.asyncio` is not needed explicitly. Lifespan events do NOT fire with `ASGITransport` — inject mocked graph/auth into `app.state` directly in test fixtures.

### Sampling Rate

- **Per task commit:** `uv run pytest tests/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green (23 existing + new tests) before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_api_chat.py` — covers CHAT-01, CHAT-02, CHAT-03, CHAT-04, SESS-01, SESS-02
- [ ] `tests/test_api_auth.py` — covers AUTH-03
- [ ] Add `fastapi`, `uvicorn[standard]`, `python-multipart` to pyproject.toml: `uv add fastapi uvicorn[standard] python-multipart`
- [ ] Add `anyio[trio]` or confirm `pytest-asyncio` covers async httpx tests (current `asyncio_mode=auto` should suffice — no gap)

---

## Sources

### Primary (HIGH confidence)

- FastAPI Lifespan Events: https://fastapi.tiangolo.com/advanced/events/ — lifespan pattern, app.state
- FastAPI StaticFiles: https://fastapi.tiangolo.com/tutorial/static-files/ — mounting static files
- FastAPI Async Tests: https://fastapi.tiangolo.com/advanced/async-tests/ — AsyncClient + ASGITransport
- AsyncSqliteSaver source code: `uv run python -c "import inspect; from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver; print(inspect.getsource(AsyncSqliteSaver.setup))"` — confirmed table schema and `from_conn_string` pattern
- AsyncSqliteSaver.alist() signature: verified from source — `(config, filter, before, limit)` — no "list all threads" without config
- marked-highlight CDN README: https://cdn.jsdelivr.net/npm/marked-highlight/README.md — verified UMD usage pattern
- npm versions: `npm view marked version` → 17.0.5; `npm view highlight.js version` → 11.11.1; `npm view marked-highlight version` → 2.2.3 (2026-04-01)
- PyPI versions: `pip index versions fastapi` → 0.135.2 latest; `pip index versions uvicorn` → 0.42.0 latest (2026-04-01)

### Secondary (MEDIUM confidence)

- LangGraph + AsyncSqliteSaver + FastAPI lifespan pattern: https://medium.com/@devwithll/simple-langgraph-implementation-with-memory-asyncsqlitesaver-checkpointer-fastapi-54f4e4879a2e — cross-verified with official FastAPI lifespan docs and source code inspection
- Thread listing via direct SQL: https://github.com/langchain-ai/langgraph/discussions/3640 — verified approach (alist() requires config filter; direct SQL is correct)
- GitHub Device Flow 401 detection: https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps — 401 = revoked/expired token

### Tertiary (LOW confidence)

- Token expiry exception type from Copilot SDK: Unknown — SDK is Technical Preview with no public exception taxonomy. Exception-catching should be broad (`except Exception`) with message inspection.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions confirmed via npm/PyPI registry queries on 2026-04-01
- Architecture: HIGH — patterns verified against official FastAPI docs and live source inspection of AsyncSqliteSaver
- Pitfalls: HIGH for pitfalls 1-5 (verified from source), MEDIUM for pitfall around token expiry exception types (SDK is Technical Preview)
- Test patterns: HIGH — official FastAPI async test docs

**Research date:** 2026-04-01
**Valid until:** 2026-05-01 (FastAPI/uvicorn/marked.js — stable; langgraph-checkpoint-sqlite schema — stable; Copilot SDK — Technical Preview, may change sooner)
