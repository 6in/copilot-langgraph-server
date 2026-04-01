# Phase 4: 非同期ジョブキュー + SSE ストリーミング移行 — Research

**Researched:** 2026-04-01
**Domain:** Async job queue, SSE streaming, Redis, LangGraph worker, Copilot SDK event API
**Confidence:** HIGH (architecture verified against project codebase and installed SDK; queue library choice requires final decision)

---

## Summary

Phase 4 migrates the current synchronous `POST /api/chat → LangGraph ainvoke → response` flow to an
async decoupled architecture: Gateway enqueues a job and returns `job_id` immediately; a Worker
process picks it up, runs LangGraph, saves the result in Redis via JobStore, then signals completion;
the frontend receives that signal over SSE and fetches the result from `GET /job/{job_id}`.

The design is fully specified in `docs/pre/async_chat_sse_polling.md`. The research confirms it is
implementable with the current stack (SDK 0.2.0, FastAPI, LangGraph 1.1.4) with two additions: the
`redis` package and a job queue library. The key architectural question — whether to use `arq` (async
Python queue) or a hand-rolled Redis list queue — is resolved in favour of `arq` for production
reliability. However, the design spec's custom `JobStore` + `Notifier` pattern sits _above_ any queue
library and must be implemented regardless of the queue choice.

**Scope decision required:** The design spec includes Slack Bot support. The research recommends
deferring Slack Bot to Phase 5 to keep Phase 4 tractable. Slack adds `slack-bolt`, Socket Mode async
app lifecycle, and `SlackNotifier` — all independent of the core async flow. The core Web flow
(`WebNotifier` path only) should be the Phase 4 boundary.

**Primary recommendation:** Use `redis[asyncio]` (redis-py 7.x, already installed system-wide)
for the Redis client, `arq` for the background worker, and FastAPI `StreamingResponse` + `asyncio.Queue`
for SSE. Implement `JobStore` and `Notifier` (Strategy pattern) as described in the spec. Run the
worker as a separate `arq worker` process alongside the FastAPI server.

---

## User Constraints (from CONTEXT.md)

No CONTEXT.md exists for Phase 4. The constraints below come from `CLAUDE.md`, `STATE.md`, and prior
phase decisions.

### Locked Decisions (from prior phases)

- SDK pinned to `github-copilot-sdk==0.2.0` — Technical Preview, isolated to `app/providers/copilot.py`
- `send_and_wait(prompt: str)` is the current SDK call in `ChatCopilot._agenerate()` — confirmed working
- In-memory JTI blocklist — no Redis dependency for JWT (acceptable for personal tool); Phase 4 adds Redis only for job queue
- JWT HS256 session cookie (`session` cookie) — Auth stays unchanged in Phase 4
- `github-copilot-sdk==0.2.0` uses `session.on(handler)` for event listener registration
- Python/FastAPI/LangGraph stack; no Node.js; BullMQ is Node.js-only — must use Python queue equivalent
- No Redis currently in project; Redis must be added as a new dependency

### Claude's Discretion

- Job queue library choice (arq vs hand-rolled Redis list)
- Whether to use `session.on()` event streaming in Worker or keep `send_and_wait()` for MVP simplicity
- Whether to use Docker Compose or bare `redis-server` for local development
- Scope of Phase 4: Web-only vs Web + Slack Bot

### Deferred Ideas (OUT OF SCOPE for Phase 4)

- Slack Bot Gateway + SlackNotifier (recommend Phase 5)
- Multi-node worker scaling (personal tool, single worker sufficient)
- Redis Streams vs Redis List (List-based `arq` queue is sufficient)

---

## Standard Stack

### Core New Additions

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `redis[asyncio]` | 7.4.0 | Redis client with asyncio support | `redis-py` 4.2+ bundles `redis.asyncio`; no separate `aioredis` needed. System already has redis 7.1.0; project needs `>=7.0` pinned. Confirmed: `from redis.asyncio import Redis` works. |
| `arq` | 0.27.0 | Async job queue on Redis | Pure-asyncio Python queue built on redis-py. Natural fit for the async FastAPI + LangGraph stack. Worker runs as `arq mymodule.WorkerSettings`. No Celery/kombu overhead. Latest: 0.27.0. |
| `redis-server` | 6.x (system) or Docker | Redis daemon | apt: `redis-server` version 6.0.16 available. Docker Compose: use `redis:7-alpine`. Docker is available (Docker Engine 29.3.1, Compose v5.1.1). |

### Existing Stack (unchanged)

| Library | Version | Purpose |
|---------|---------|---------|
| `fastapi` | 0.135.2 | HTTP Gateway + SSE via `StreamingResponse` |
| `langgraph` | 1.1.4 | Graph execution in Worker |
| `langchain-core` | latest | HumanMessage, AIMessage |
| `github-copilot-sdk` | 0.2.0 | Copilot session in Worker |
| `PyJWT` | 2.9.0 | JWT auth (unchanged) |
| `aiosqlite` + `langgraph-checkpoint-sqlite` | — | Conversation checkpoints (unchanged) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `arq` | Celery | Celery is sync-first, heavy, requires kombu. No native asyncio. Already in system packages but wrong for async LangGraph execution. |
| `arq` | `rq` | rq is sync workers only. Cannot run `await graph.ainvoke()` natively. |
| `arq` | Hand-rolled Redis LPUSH/BRPOP | More control, fewer dependencies, but loses retry logic, job expiry, error tracking. Acceptable for MVP but fragile in production. |
| `arq` | `dramatiq` | dramatiq has async support via `dramatiq-async` but smaller ecosystem and less active. |
| `redis.asyncio` | `aioredis` | `aioredis` is now deprecated/merged into redis-py 4.2+. Do NOT add `aioredis`. |

**Installation:**

```bash
uv add "redis[asyncio]>=7.0" arq
```

**Version verification (run before coding):**

```bash
uv run python -c "import redis; print(redis.__version__)"   # should be 7.x
uv run python -c "import arq; print(arq.__version__)"       # should be 0.27.0
```

---

## Architecture Patterns

### Recommended Project Structure

```
app/
├── api/
│   ├── main.py              # Add redis_client + job_store to lifespan
│   ├── models.py            # Add JobStatusResponse, job_id to ChatResponse
│   └── routes/
│       ├── chat.py          # POST /api/chat → job_id; GET /api/chat/{job_id}/stream (SSE)
│       └── jobs.py          # GET /api/job/{job_id} — polling / result fetch
├── jobs/
│   ├── __init__.py
│   ├── job_store.py         # JobStore: Redis result store + asyncio.Queue for SSE
│   ├── notifier.py          # BaseNotifier, WebNotifier; SlackNotifier deferred to Phase 5
│   └── worker.py            # arq WorkerSettings + process() function
└── providers/
    └── copilot.py           # Unchanged
static/
└── app.js                   # Update: POST → get job_id → SSE → poll fallback
```

### Pattern 1: JobStore — Result store + SSE signal hub

**What:** Owns two things: Redis hash for persistent result storage (polling/recovery), and in-memory
`asyncio.Queue` per `job_id` for live SSE signal delivery. These two concerns are intentionally
separate because SSE queues are process-local while Redis results survive restarts.

**When to use:** Always. Every path (SSE and polling) reads results from `job_store.get()`.

```python
# Source: docs/pre/async_chat_sse_polling.md (adapted for arq / redis.asyncio)
import asyncio
import json
from typing import Optional
from redis.asyncio import Redis


class JobStore:
    def __init__(self, redis: Redis):
        self.redis = redis
        self.queues: dict[str, asyncio.Queue] = {}

    def register_sse(self, job_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self.queues[job_id] = q
        return q

    def unregister_sse(self, job_id: str) -> None:
        self.queues.pop(job_id, None)

    async def save_result(self, job_id: str, result: str) -> None:
        await self.redis.set(
            f"job:{job_id}",
            json.dumps({"status": "done", "result": result}),
            ex=3600,  # 1-hour TTL
        )

    async def notify(self, job_id: str, status: str) -> None:
        if job_id in self.queues:
            await self.queues[job_id].put({"status": status})

    async def get(self, job_id: str) -> Optional[dict]:
        raw = await self.redis.get(f"job:{job_id}")
        return json.loads(raw) if raw else None
```

### Pattern 2: arq Worker — Async job processor

**What:** `arq` calls an `async def` function with the job payload. The worker initialises its own
`CopilotClient` + `LangGraph` graph per job. Because the Worker is a separate process, it cannot
share `app.state` from FastAPI — it connects to the same Redis and re-creates its own `JobStore`.

**Critical ordering:** `save_result()` MUST be called BEFORE `notifier.done()` so the SSE client
can immediately fetch the result when it receives the `done` signal.

```python
# Source: docs/pre/async_chat_sse_polling.md + arq worker pattern
# app/jobs/worker.py
from langchain_core.messages import HumanMessage
from redis.asyncio import Redis

from app.jobs.job_store import JobStore
from app.jobs.notifier import build_notifier
from app.providers.copilot import ChatCopilot
from app.graph.builder import build_graph

# arq requires a synchronous Redis pool factory in WorkerSettings
async def startup(ctx: dict) -> None:
    ctx["redis_client"] = Redis.from_url("redis://localhost:6379")
    ctx["job_store"] = JobStore(ctx["redis_client"])

async def shutdown(ctx: dict) -> None:
    await ctx["redis_client"].aclose()

async def process_chat(ctx: dict, job: dict) -> dict:
    """arq job function — must be async, receives ctx + job kwargs."""
    job_id = job["job_id"]
    job_store: JobStore = ctx["job_store"]
    notifier = build_notifier(job["reply_to"], job_store)

    llm = ChatCopilot(github_token=job["github_token"], model=job.get("model", "claude-sonnet-4.5"))
    from langgraph.checkpoint.memory import MemorySaver
    graph = build_graph(llm, MemorySaver())

    await notifier.progress("thinking")

    try:
        config = {"configurable": {"thread_id": job["thread_id"]}}
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=job["prompt"])]},
            config=config,
        )
        final_text = result["messages"][-1].content

        # ① Save result FIRST
        await job_store.save_result(job_id, final_text)
        # ② Then signal done
        await notifier.done()

    except Exception as e:
        await job_store.save_result(job_id, f"Error: {e}")
        await notifier.done()
    finally:
        await llm.close()

    return {"job_id": job_id, "status": "done"}

class WorkerSettings:
    functions = [process_chat]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = None  # Uses default REDIS_URL env var; override via RedisSettings
```

### Pattern 3: FastAPI SSE Endpoint

**What:** SSE uses `StreamingResponse` with `media_type="text/event-stream"`. The async generator
registers an `asyncio.Queue` in `JobStore`, yields events, and unregisters in `finally`.

**Critical:** Always check if job is already complete _before_ registering the queue. This handles
page-reload / re-connection scenarios.

```python
# Source: docs/pre/async_chat_sse_polling.md
# app/api/routes/chat.py — SSE stream endpoint
import json
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

@router.get("/api/chat/{job_id}/stream")
async def stream_job(job_id: str, request: Request):
    job_store = request.app.state.job_store

    # 1. Check already done — return immediate SSE event
    saved = await job_store.get(job_id)
    if saved and saved["status"] == "done":
        async def immediate():
            yield f"data: {json.dumps({'status': 'done'})}\n\n"
        return StreamingResponse(immediate(), media_type="text/event-stream")

    # 2. Still in progress — register queue and wait
    queue = job_store.register_sse(job_id)

    async def generator():
        try:
            while True:
                event = await queue.get()
                yield f"data: {json.dumps(event)}\n\n"
                if event["status"] == "done":
                    break
        finally:
            job_store.unregister_sse(job_id)

    return StreamingResponse(generator(), media_type="text/event-stream")
```

### Pattern 4: arq Job Enqueueing from FastAPI

**What:** The Gateway `POST /api/chat` enqueues a job using arq's `ArqRedis` pool and immediately
returns `job_id`.

```python
# app/api/routes/chat.py — POST endpoint refactored for async
import uuid
from arq import ArqRedis

@router.post("/api/chat")
async def post_chat(request: Request, body: ChatRequest, github_token: str = Depends(get_github_token)):
    arq_redis: ArqRedis = request.app.state.arq_redis
    job_id = str(uuid.uuid4())

    await arq_redis.enqueue_job(
        "process_chat",
        {
            "job_id": job_id,
            "thread_id": body.thread_id,
            "prompt": body.message,
            "model": body.model,
            "github_token": github_token,  # pass decrypted token to worker
            "reply_to": {"type": "web", "job_id": job_id},
        },
    )
    return {"job_id": job_id, "thread_id": body.thread_id}
```

### Pattern 5: Notifier Strategy Pattern

```python
# app/jobs/notifier.py
class BaseNotifier:
    async def progress(self, status: str) -> None: ...
    async def done(self) -> None: ...

class WebNotifier(BaseNotifier):
    def __init__(self, job_id: str, job_store):
        self.job_id = job_id
        self.job_store = job_store

    async def progress(self, status: str) -> None:
        await self.job_store.notify(self.job_id, status)

    async def done(self) -> None:
        await self.job_store.notify(self.job_id, "done")

def build_notifier(reply_to: dict, job_store) -> BaseNotifier:
    if reply_to["type"] == "web":
        return WebNotifier(reply_to["job_id"], job_store)
    # SlackNotifier deferred to Phase 5
    raise ValueError(f"Unknown reply_to type: {reply_to['type']}")
```

### Pattern 6: Frontend JS — SSE + Polling Fallback

The current `app.js` does a blocking `POST /api/chat` and waits for the response. Phase 4 changes it to:

1. `POST /api/chat` → get `job_id` immediately
2. Check `GET /api/job/{job_id}` (already done? skip SSE)
3. Open `EventSource` on `GET /api/chat/{job_id}/stream`
4. On `done` signal: close ES, `GET /api/job/{job_id}` for final result
5. On `es.onerror`: close ES, fall back to polling `GET /api/job/{job_id}` every 2 seconds

EventSource does not support custom headers (JWT cookie). Since the existing auth uses an HttpOnly
cookie (`session`), EventSource will include it automatically — no extra auth work needed.

### Anti-Patterns to Avoid

- **Putting result in the SSE event**: SSE events carry _status signals only_ (e.g. `{"status":"done"}`), never the AI result. Result always comes from `GET /api/job/{job_id}`. This ensures polling and SSE use the same code path.
- **Sharing app.state between FastAPI and Worker**: The Worker is a separate process. It initialises its own Redis client and LangGraph graph in `on_startup`.
- **Using MemorySaver for the Worker's checkpointer**: The Worker creates a fresh `MemorySaver()` per-startup. This is intentional — conversation history is encoded in the prompt via the JWT flow, and the Worker does not need cross-process checkpoint sharing for a personal tool.
- **Calling `notifier.done()` before `save_result()`**: If the client gets the `done` signal and calls `GET /api/job/{job_id}` before the result is saved, it gets `not_found`. Always save first, signal second.
- **Not calling `unregister_sse()` in `finally`**: A disconnected browser leaves a dangling queue in `job_store.queues`. Always unregister in `finally`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Job retry logic | Custom retry loop | `arq` (built-in retry + backoff) | arq has `retry`, `max_tries`, dead-letter tracking built in. |
| Redis connection pooling | Manual connection management | `redis.asyncio.Redis.from_url()` | redis-py manages the connection pool automatically. |
| Worker process lifecycle | `subprocess.Popen` + signal handlers | `arq worker` CLI command | arq handles graceful shutdown, signal handling, and health checks. |
| Job expiry / TTL | Custom cleanup cron | Redis `ex=3600` on `SET` | Redis natively expires keys; set TTL on `save_result()`. |

**Key insight:** The design spec's `JobStore` + `Notifier` pattern _is_ the custom layer. Everything
below it (Redis connectivity, worker lifecycle, job retry) should use libraries, not hand-rolled code.

---

## SDK 0.2.0 Findings — Critical

### `session.on()` is confirmed available in SDK 0.2.0

The project venv has `github-copilot-sdk==0.2.0` installed (the `.dist-info` confirms `0.2.0`; the
`__version__` attribute reads `"0.1.0"` due to an internal string — this is a known SDK quirk).

Verified API surface in SDK 0.2.0:

```python
# session.on() — confirmed signature
session.on(handler: Callable[[SessionEvent], None]) -> Callable[[], None]

# send() — fire-and-forget, returns message_id immediately (non-blocking)
await session.send(prompt: str, *, attachments=None, mode=None) -> str  # returns message_id

# send_and_wait() — blocks until session.idle event
await session.send_and_wait(prompt: str, ..., timeout=60.0) -> SessionEvent | None
```

### Two options for Worker's Copilot call

**Option A: Keep `send_and_wait()` (current pattern)**
- Worker calls `await session.send_and_wait(prompt)` and gets back the final `SessionEvent`
- Simpler: no event handler wiring needed
- No streaming progress (LangGraph node names not visible to frontend during processing)
- Currently used in `ChatCopilot._agenerate()` — same pattern, tested, working

**Option B: Use `session.on()` + `session.send()` (streaming progress)**
- Register handler for `ASSISTANT_MESSAGE_DELTA`, `TOOL_EXECUTION_START`, `SESSION_IDLE` etc.
- Can forward LangGraph node-level progress via `notifier.progress("running:node_x")`
- Matches PoC code_review.py pattern (uses `session.on()` + `done.set()`)
- More complex; handler is a sync callback (event loop bridging needed for async notifier calls)

**Recommendation for Phase 4:** Use Option A for MVP. The Worker wraps `ChatCopilot` via LangGraph
`ainvoke()` (not direct SDK calls). The `graph.ainvoke()` path already uses `send_and_wait()` via
`ChatCopilot._agenerate()`. Streaming _within_ the Copilot response is not the Phase 4 goal;
Phase 4's goal is decoupling the HTTP request from the AI execution. Streaming deltas can be added
in Phase 5 if needed.

### Important: `session.on()` handler is synchronous

The `on()` handler signature is `Callable[[SessionEvent], None]` — it is a sync callback called from
a `threading.Lock`-protected dispatch loop. If you need to call `await notifier.progress()` from
within a handler, you must use `asyncio.run_coroutine_threadsafe()` or collect events and flush
them after `send_and_wait()` returns.

### Key SessionEventType values for Phase 5 (if streaming added)

| Event Type | Value | Use |
|------------|-------|-----|
| `ASSISTANT_MESSAGE` | `"assistant.message"` | Final complete message |
| `ASSISTANT_MESSAGE_DELTA` | `"assistant.message_delta"` | Streaming token chunk |
| `SESSION_IDLE` | `"session.idle"` | Processing complete |
| `SESSION_ERROR` | `"session.error"` | Error occurred |
| `TOOL_EXECUTION_START` | `"tool.execution_start"` | Agent tool use started |

---

## LangGraph astream() Patterns

LangGraph 1.1.4 exposes `astream()` with `stream_mode` supporting:

```
'values' | 'updates' | 'checkpoints' | 'tasks' | 'debug' | 'messages' | 'custom'
```

For Phase 4, **`ainvoke()` is sufficient** — the async decoupling is achieved by running it in a
Worker process, not by streaming tokens. `astream()` would be needed for sub-token streaming in the
future. The current `graph.ainvoke()` call in chat.py can be reused in the Worker unchanged.

If node-level progress events are desired (showing "thinking...", "running:chat_node" in the UI),
use `astream(stream_mode="updates")`:

```python
# Each iteration yields {node_name: state_update}
async for event in graph.astream(input, config=config, stream_mode="updates"):
    node_name = list(event.keys())[0]
    await notifier.progress(f"running:{node_name}")
```

This is available and works in 1.1.4 but is OPTIONAL for Phase 4 MVP.

---

## Common Pitfalls

### Pitfall 1: arq requires its own Redis connection type (`ArqRedis`)

**What goes wrong:** Creating a regular `redis.asyncio.Redis` client and passing it to `arq.enqueue_job()` raises a type error — arq expects `ArqRedis`, its own subclass of the async Redis client.

**How to avoid:** Use `arq.create_pool(RedisSettings(...))` to get an `ArqRedis` instance for the
FastAPI lifespan. Store it as `app.state.arq_redis`. The Worker's `ctx["redis"]` is also `ArqRedis`.
The plain `redis.asyncio.Redis` used for `JobStore` is a separate client for direct Redis ops.

```python
# Correct — two separate clients
from arq import create_pool
from arq.connections import RedisSettings
from redis.asyncio import Redis

arq_redis = await create_pool(RedisSettings())      # for arq.enqueue_job()
plain_redis = Redis.from_url("redis://localhost:6379")  # for JobStore set/get
```

### Pitfall 2: SSE headers and CORS

**What goes wrong:** Browser EventSource does not support custom request headers. If CORS or auth
middleware rejects the SSE request, the client sees an error immediately.

**How to avoid:** The `session` cookie is already an HttpOnly cookie sent automatically by the
browser. The SSE endpoint should use `Depends(get_github_token)` — the cookie is included. Add
explicit `Cache-Control: no-cache` and `X-Accel-Buffering: no` headers to the `StreamingResponse`
to prevent proxy buffering.

```python
return StreamingResponse(
    generator(),
    media_type="text/event-stream",
    headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
        "Connection": "keep-alive",
    },
)
```

### Pitfall 3: Worker cannot share `app.state` — reinitialise everything

**What goes wrong:** The Worker runs as `arq worker app.jobs.worker.WorkerSettings` in a separate
process. Any `app.state.graph`, `app.state.job_store`, or `app.state.arq_redis` set during FastAPI
lifespan are not accessible.

**How to avoid:** Worker `on_startup` reinitialises: `Redis.from_url(...)`, `JobStore(redis)`, and
`build_graph(llm, checkpointer)`. The Worker owns its own LangGraph compilation. The `MemorySaver`
checkpointer in the Worker is process-local, which is acceptable for the personal tool use case
(thread history lives in the main app's SQLite via the regular chat route checkpoint; the Worker
uses a fresh in-memory graph for the async path).

### Pitfall 4: GitHub token in job payload security concern

**What goes wrong:** The decrypted `github_token` is stored in the arq job payload in Redis. Redis
keys are not encrypted by default.

**How to avoid:** For a personal tool running on localhost, this is acceptable. For the planner to
note: use `ex=300` (5-minute TTL) on the arq job key, or re-encrypt the token in the job payload.
At minimum, document this in the implementation note.

### Pitfall 5: asyncio.Queue is process-local — SSE only works if Gateway and Worker are on the same machine

**What goes wrong:** `job_store.queues` is an in-memory `dict[str, asyncio.Queue]`. If Worker runs
on a different machine than FastAPI, `notifier.notify()` in the Worker cannot reach the SSE queue
in the Gateway process.

**How to avoid:** For a single-machine personal tool, this is fine. Worker and Gateway run on the
same host. If scaling is needed later, replace `asyncio.Queue` with Redis Pub/Sub. Document this
constraint explicitly.

### Pitfall 6: `send_and_wait()` 60-second timeout

**What goes wrong:** `session.send_and_wait()` has a default 60-second timeout. Long Copilot responses
(e.g., detailed code reviews) may exceed this.

**How to avoid:** Pass `timeout=300.0` (5 minutes) or a configurable value. The arq job has its own
`timeout` setting in `WorkerSettings` — set `job_timeout` to match or exceed.

---

## Code Examples

### Redis + arq lifespan in FastAPI

```python
# app/api/main.py — updated lifespan
from arq import create_pool
from arq.connections import RedisSettings
from redis.asyncio import Redis
from app.jobs.job_store import JobStore

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ... existing setup ...
    redis_client = Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
    arq_redis = await create_pool(RedisSettings.from_dsn(
        os.getenv("REDIS_URL", "redis://localhost:6379")
    ))
    job_store = JobStore(redis_client)

    app.state.redis = redis_client
    app.state.arq_redis = arq_redis
    app.state.job_store = job_store
    # ... rest of existing state ...
    yield

    await redis_client.aclose()
    await arq_redis.aclose()
```

### arq Worker startup

```bash
# Run worker (separate terminal / process)
uv run arq app.jobs.worker.WorkerSettings
```

### Polling endpoint

```python
# app/api/routes/jobs.py
@router.get("/api/job/{job_id}")
async def get_job(job_id: str, request: Request):
    job = await request.app.state.job_store.get(job_id)
    if not job:
        return {"status": "pending"}
    return job
```

### Frontend SSE + polling flow

```javascript
// static/app.js — replace synchronous fetch with async flow
async function sendMessage(message, threadId, model) {
    const { job_id } = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, thread_id: threadId, model }),
    }).then(r => r.json());

    // Check if already done (reload/reconnect case)
    const immediate = await fetch(`/api/job/${job_id}`).then(r => r.json());
    if (immediate.status === "done") {
        renderMessage(immediate.result);
        return;
    }

    // Connect SSE
    const es = new EventSource(`/api/chat/${job_id}/stream`);
    es.onmessage = async (e) => {
        const { status } = JSON.parse(e.data);
        updateLoadingStatus(status);  // "thinking", "running:chat_node", "done"
        if (status === "done") {
            es.close();
            const result = await fetch(`/api/job/${job_id}`).then(r => r.json());
            renderMessage(result.result);
        }
    };
    es.onerror = () => {
        es.close();
        startPolling(job_id);
    };
}

function startPolling(job_id) {
    const timer = setInterval(async () => {
        const job = await fetch(`/api/job/${job_id}`).then(r => r.json());
        if (job.status === "done") {
            renderMessage(job.result);
            clearInterval(timer);
        }
    }, 2000);
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `aioredis` (separate package) | `redis.asyncio` (built into redis-py) | redis-py 4.2 (2022) | Do NOT install `aioredis`; it is deprecated |
| arq uses its own Redis client class | arq 0.26+ uses redis-py directly | arq 0.22+ | `ArqRedis` is a subclass of `redis.asyncio.Redis` |
| `EventSource` custom headers | Cookie-based auth works automatically | Always true | No special SSE auth needed when using HttpOnly cookie |

**Deprecated/outdated:**
- `aioredis`: Do not use. Merged into redis-py. No new development.
- `BullMQ`: Node.js only. Not applicable to this Python project.

---

## Scope Decision: Slack Bot

The design spec (`docs/pre/async_chat_sse_polling.md`) includes Slack Bot support with `SlackNotifier`
and `slack_gateway.py`. Research recommends **deferring Slack to Phase 5** because:

1. Slack Bot requires `slack-bolt` + Socket Mode + async app lifecycle — non-trivial setup
2. The `build_notifier()` function already has the extension point (`elif reply_to["type"] == "slack"`)
3. Phase 4 goal is web async UX improvement; Slack is a separate channel
4. Scope creep risk: the Web path is ~5-6 new files + tests; Slack adds another 3-4 files

**Phase 4 boundary:** `WebNotifier` path only. `build_notifier()` raises `ValueError` for unknown
types (safe forward-compatibility).

---

## Open Questions

1. **Worker checkpointer: MemorySaver vs AsyncSqliteSaver**
   - What we know: Worker is a separate process; it cannot share the FastAPI SQLite checkpointer
   - What's unclear: Should the Worker write to the same `data/chat.db` using its own `AsyncSqliteSaver` connection? If yes, thread history accumulates correctly; if no (MemorySaver), history is lost per job
   - Recommendation: Use `AsyncSqliteSaver.from_conn_string("./data/chat.db")` in the Worker for correct multi-turn conversation support. SQLite supports multiple readers, one writer.

2. **`github_token` in arq job payload**
   - What we know: arq serialises job kwargs to Redis JSON; the token is plaintext in Redis
   - What's unclear: Is this acceptable for the personal tool use case?
   - Recommendation: Acceptable for localhost personal tool. Document as a known limitation.

3. **SSE concurrent connections vs `asyncio.Queue` per `job_id`**
   - What we know: `job_store.queues` is a plain Python dict, one queue per job
   - What's unclear: What if a user opens two browser tabs for the same job_id?
   - Recommendation: Last `register_sse()` call wins (overwrites dict entry). For personal tool, this is acceptable. Document as a known limitation.

4. **arq `process_chat` uses `build_graph(llm, MemorySaver())` vs `AsyncSqliteSaver`**
   - What we know: Worker must use its own graph instance; SQLite path is `./data/chat.db`
   - Recommendation: Use `AsyncSqliteSaver` in Worker to ensure thread history is consistent between the sync and async chat paths. Requires `async with AsyncSqliteSaver.from_conn_string(...)` in worker startup.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Redis server | JobStore, arq | Docker: YES (Docker Engine 29.3.1) | 6.0.16 (apt) | `docker run redis:7-alpine` |
| `redis[asyncio]` Python | JobStore, FastAPI lifespan | NOT in project venv (needs `uv add`) | 7.4.0 available | — |
| `arq` Python | Worker, enqueue | NOT in project venv (needs `uv add`) | 0.27.0 available | — |
| Docker | Redis via Docker Compose | YES | 29.3.1 | Install redis-server via apt (needs sudo) |
| `slack-bolt` | SlackNotifier (Phase 5) | NOT installed | — | Defer to Phase 5 |

**Missing dependencies with no fallback:**
- Redis server daemon must be running. Use `docker run -d -p 6379:6379 redis:7-alpine` or `sudo apt-get install redis-server && sudo service redis-server start`.
- `redis[asyncio]` and `arq` must be added to `pyproject.toml` and installed.

**Missing dependencies with fallback:**
- Redis server: Docker is available. A `docker-compose.yml` snippet (Redis service only) covers local development without requiring system package installation.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (`asyncio_mode = "auto"`) |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -v` |

Current test count: 53 tests collected and passing.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ASYNC-01 | `POST /api/chat` returns `job_id` immediately (does not block) | unit | `pytest tests/test_api_chat.py -k "test_post_chat_returns_job_id"` | NO — Wave 0 |
| ASYNC-02 | `GET /api/job/{job_id}` returns `{"status":"pending"}` before completion | unit | `pytest tests/test_api_jobs.py -k "test_get_job_pending"` | NO — Wave 0 |
| ASYNC-03 | `GET /api/job/{job_id}` returns `{"status":"done","result":...}` after `save_result()` | unit | `pytest tests/test_job_store.py -k "test_save_and_get"` | NO — Wave 0 |
| ASYNC-04 | SSE endpoint yields `{"status":"done"}` after Worker calls `notifier.done()` | integration | `pytest tests/test_sse.py -k "test_sse_done_signal"` | NO — Wave 0 |
| ASYNC-05 | `JobStore.notify()` with no registered queue is a no-op (no crash) | unit | `pytest tests/test_job_store.py -k "test_notify_no_queue"` | NO — Wave 0 |
| ASYNC-06 | SSE endpoint returns immediate `done` event if job already complete | unit | `pytest tests/test_sse.py -k "test_sse_already_done"` | NO — Wave 0 |
| ASYNC-07 | Worker `process_chat` saves result and calls notifier.done | unit (mock) | `pytest tests/test_worker.py -k "test_process_chat_saves_result"` | NO — Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -v`
- **Phase gate:** Full suite green (all 53 existing + new Phase 4 tests) before `/gsd:verify-work`

### Wave 0 Gaps

- `tests/test_job_store.py` — covers ASYNC-03, ASYNC-05 (requires mock Redis client)
- `tests/test_sse.py` — covers ASYNC-04, ASYNC-06 (requires mock JobStore)
- `tests/test_api_chat.py` — extend existing file for ASYNC-01, ASYNC-02
- `tests/test_worker.py` — covers ASYNC-07 (mock graph, mock job_store)
- `tests/test_api_jobs.py` — covers ASYNC-02 polling endpoint

**Mock strategy:** Redis client (`redis.asyncio.Redis`) should be mocked with `AsyncMock`.
`JobStore` can be tested with a real `asyncio.Queue` and a mock Redis. SSE tests use
`httpx.AsyncClient` with `ASGITransport` + manually injected mock `job_store` in `app.state`.

---

## Sources

### Primary (HIGH confidence)

- SDK 0.2.0 installed at `.venv/lib/python3.12/site-packages/copilot/session.py` — verified `on()` signature, `SessionEventType` enum, `send_and_wait()` signature
- `docs/pre/async_chat_sse_polling.md` — authoritative design spec, code examples verified against SDK
- `app/providers/copilot.py` — current `send_and_wait()` usage confirmed
- `app/api/routes/chat.py` — current synchronous flow to be replaced
- LangGraph `CompiledStateGraph.astream()` signature — verified via `uv run python -c "..."`

### Secondary (MEDIUM confidence)

- arq 0.27.0 on PyPI — package index confirmed; full API docs not fetched but package confirmed installable
- redis-py 7.4.0 on PyPI — `from redis.asyncio import Redis` confirmed working in system Python 3.12
- Docker Engine 29.3.1 + Compose v5.1.1 — `docker info` confirmed available
- redis-server apt package 6.0.16 — `apt-cache show` confirmed available (requires sudo to install)

### Tertiary (LOW confidence)

- arq `ArqRedis` as subclass of `redis.asyncio.Redis` — from arq changelog knowledge; not live-verified
- LangGraph `AsyncSqliteSaver` multi-process read safety — SQLite WAL mode supports multiple readers; not tested with concurrent Worker

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — redis-py 7.x confirmed in system; arq 0.27.0 confirmed on PyPI; SDK 0.2.0 `session.on()` verified in installed package
- Architecture: HIGH — design spec matches verified SDK API surface; patterns confirmed against FastAPI docs
- Pitfalls: HIGH — process isolation pitfall (#3) and `save_result()` ordering (#4) are both verifiable from code
- Worker checkpointer choice: MEDIUM — SQLite multi-process access needs validation

**Research date:** 2026-04-01
**Valid until:** 2026-05-01 (SDK Technical Preview — may change sooner; recheck before executing)
