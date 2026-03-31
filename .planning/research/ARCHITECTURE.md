# Architecture Patterns

**Domain:** LangGraph-powered chat web application with custom Copilot provider
**Researched:** 2026-03-31
**Confidence:** HIGH (LangGraph/FastAPI patterns verified via official docs and multiple corroborating sources)

---

## Recommended Architecture

The application is a single-process Python server. It has four clearly bounded layers that
communicate in one direction: the web layer calls the graph layer, which calls the provider
layer, which calls the auth layer. No layer reaches back up.

```
Browser
  │  HTTP POST /chat  (JSON: thread_id, message)
  │  HTTP GET  /auth/status
  ▼
┌─────────────────────────────────┐
│  Web Layer  (FastAPI)           │  Owns: HTTP routing, request/response shape,
│  app/api/                       │        lifespan startup, thread_id generation
└─────────────────┬───────────────┘
                  │ await graph.ainvoke(state, config)
                  ▼
┌─────────────────────────────────┐
│  Graph Layer  (LangGraph)       │  Owns: StateGraph definition, node wiring,
│  app/graph/                     │        MemorySaver checkpointer, thread state
└─────────────────┬───────────────┘
                  │ await llm._agenerate(messages)
                  ▼
┌─────────────────────────────────┐
│  Provider Layer  (ChatCopilot)  │  Owns: BaseChatModel contract, message
│  app/providers/                 │        serialization, CopilotClient lifecycle
└─────────────────┬───────────────┘
                  │ await auth_manager.get_token()
                  ▼
┌─────────────────────────────────┐
│  Auth Layer  (CopilotAuth)      │  Owns: Device Flow OAuth, Fernet
│  app/auth/                      │        encryption, token file I/O
└─────────────────────────────────┘
                  │ JSON-RPC
                  ▼
            Copilot CLI (server mode)
```

---

## Component Boundaries

| Component | Responsibility | Communicates With | Must NOT Touch |
|-----------|---------------|-------------------|----------------|
| `app/api/routes.py` | HTTP endpoints, request validation, response formatting | Graph layer only | LangChain, Copilot SDK directly |
| `app/api/lifespan.py` | FastAPI lifespan: build graph, init checkpointer, attach to `app.state` | Graph layer, Auth layer | Business logic |
| `app/graph/graph.py` | `build_graph()` factory, `StateGraph` definition, node wiring, `MemorySaver` | Provider layer | Web layer |
| `app/graph/state.py` | `ChatState` TypedDict with `add_messages` reducer | Nothing | — |
| `app/graph/nodes.py` | Pure node functions: receive state, call LLM, return state delta | Provider layer (via injected `llm`) | Auth, web framework |
| `app/providers/copilot.py` | `ChatCopilot(BaseChatModel)`: message format translation, `CopilotClient` lifecycle | Auth layer | Web layer, graph internals |
| `app/auth/manager.py` | `CopilotAuthManager`: Device Flow, Fernet encrypt/decrypt, token file | `httpx`, filesystem | Everything else |

---

## State Design

Use `MessagesState` from `langgraph.graph.message` (or an equivalent TypedDict) for the
graph state. This is the standard LangGraph pattern for chat — the `add_messages` reducer
appends rather than overwrites, which is what multi-turn conversation requires.

```python
# app/graph/state.py
from typing import Annotated
from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    # v1: no extra fields needed
    # future: model_name: str, tool_results: list, etc.
```

**Why not store messages in the web layer or a separate store?** The LangGraph checkpointer
(keyed by `thread_id`) IS the store. The graph state is the source of truth for conversation
history. The web layer holds nothing — it reads the last message from the state returned by
`ainvoke()`.

**What `messages` contains:** A flat list of `HumanMessage`, `AIMessage`, and optionally
`SystemMessage`. The `add_messages` reducer handles deduplication by message ID, so
re-delivering the same user message is safe.

---

## Graph Node Design

The v1 graph is intentionally minimal — one node, one edge to END. This is the correct
starting point for a chat app with no tool calls. The node structure is designed to accept
tools later without rewiring.

```
ENTRY → [agent_node] → END
```

```python
# app/graph/nodes.py
async def agent_node(state: ChatState, llm: BaseChatModel) -> dict:
    response = await llm.ainvoke(state["messages"])
    return {"messages": [response]}  # add_messages appends this
```

The node receives the full message history via `state["messages"]` and returns only the
new AI message. The `add_messages` reducer merges it. The LLM receives the full history,
giving it multi-turn context automatically.

**Injecting the LLM into the node:** Use a closure (factory function) rather than a global.
This keeps the node testable and makes the Copilot dependency replaceable.

```python
# app/graph/graph.py
def build_graph(llm: BaseChatModel) -> CompiledGraph:
    checkpointer = MemorySaver()
    builder = StateGraph(ChatState)
    builder.add_node("agent", partial(agent_node, llm=llm))
    builder.set_entry_point("agent")
    builder.add_edge("agent", END)
    return builder.compile(checkpointer=checkpointer)
```

**Future-proofing for tools:** When `bind_tools()` is added, the graph gains a `tools_node`
and conditional edges. The `agent_node` and `ChatState` do not need to change.

---

## Provider Isolation Pattern

`ChatCopilot` is the only place in the codebase that imports `copilot` (the SDK). No other
module touches the SDK. This is enforced by convention, not a language boundary, but it
means replacing the SDK requires editing exactly one file.

The `BaseChatModel` contract is the seam:

```
Graph nodes use: BaseChatModel (abstract)
                        ↑
                 ChatCopilot (concrete, isolates SDK)
```

If GitHub changes the SDK's API, only `ChatCopilot._agenerate()` needs updating. If the
SDK is abandoned, `ChatCopilot` is swapped for `ChatOpenAI` or any other `BaseChatModel`
subclass with zero changes to graph nodes.

**`CopilotClient` lifecycle:** The client is initialized lazily on first `_agenerate()` call
(via `_ensure_client()`) and held on the instance. The `ChatCopilot` instance is created
once at app startup in lifespan and stored in `app.state`. This means one client per process
— correct for a single-user personal tool.

---

## Conversation Thread Persistence

**v1: `MemorySaver` (in-memory)**

`MemorySaver` is instantiated inside `build_graph()` and lives for the process lifetime.
All thread state is in RAM. On server restart, history is lost. This is acceptable for v1.

**Thread ID management:** The web layer owns thread IDs. Each browser session gets a UUID
`thread_id` that the client sends with every request. The server passes it to the graph
as config:

```python
config = {"configurable": {"thread_id": thread_id}}
result = await graph.ainvoke({"messages": [HumanMessage(content=user_text)]}, config=config)
```

LangGraph loads the checkpoint for that `thread_id`, appends the new message, runs the
node, and saves the updated checkpoint — all transparently.

**Thread ID generation strategy:** Generate a `thread_id` UUID in the browser (localStorage)
on first load. Send it with every `/chat` request. This means the server is stateless about
sessions — it only needs the `thread_id` to look up the LangGraph checkpoint.

**v2 path to persistence:** Replace `MemorySaver` with `langgraph-checkpoint-sqlite` or
`langgraph-checkpoint-postgres`. Because the thread ID scheme and graph invocation pattern
do not change, this is a one-line swap at `build_graph()`.

---

## Web Layer Design

FastAPI is the web framework. Use its `lifespan` context manager to initialize all shared
resources (auth, LLM, graph) once at startup. Store them in `app.state`.

```python
# app/api/lifespan.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    auth = CopilotAuthManager()
    llm = ChatCopilot(model="gpt-4.1", auth_manager=auth)
    graph = build_graph(llm)
    app.state.graph = graph
    app.state.llm = llm
    yield
    await llm.close()  # clean CopilotClient shutdown
```

**Endpoints (v1):**

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/chat` | Send a message, get a reply |
| `GET` | `/auth/status` | Check if token exists (for UI gate) |
| `POST` | `/auth/login` | Trigger Device Flow; returns verification URI and user code |

**`POST /chat` contract:**

```json
Request:  { "thread_id": "uuid", "message": "string" }
Response: { "reply": "string", "thread_id": "uuid" }
```

The endpoint is a thin adapter: unpack the request, call `app.state.graph.ainvoke()`, return
the last AI message content. No business logic in routes.

**Auth flow for the UI:** On startup, the frontend calls `GET /auth/status`. If not
authenticated, it calls `POST /auth/login` which starts Device Flow and returns the
verification URI and user code. The UI displays these. The frontend polls `GET /auth/status`
until authenticated, then allows the chat form.

---

## Async Patterns

**Rule:** All I/O is async throughout. Never block the FastAPI event loop.

| Layer | Pattern | Reason |
|-------|---------|--------|
| FastAPI endpoints | `async def` + `await graph.ainvoke()` | Non-blocking, shares event loop |
| LangGraph invocation | `await graph.ainvoke()` (not `invoke()`) | Graph nodes are async; sync invoke creates a new event loop inside an existing one — breaks on Python 3.12+ |
| `ChatCopilot._generate()` | Override to raise `NotImplementedError`; only `_agenerate` is implemented | Forces async path; avoids `loop.run_until_complete()` inside an existing event loop |
| `CopilotAuthManager.device_login()` | `async def` + `await asyncio.sleep()` | Polling loop must not block |
| `CopilotClient` | Already async (SDK design) | Pass-through |

**Key known issue:** LangGraph's `.ainvoke()` has a known ASGI context propagation edge case
(forum.langchain.com issue noted in 2025). Use Python >= 3.11 and call `ainvoke` directly
from the `async def` endpoint — do not wrap in `asyncio.run()` or `run_in_executor()`.

---

## Directory Structure

```
copilot-langgraph/
├── app/
│   ├── main.py               # FastAPI app creation, lifespan wiring
│   ├── api/
│   │   ├── lifespan.py       # @asynccontextmanager startup/shutdown
│   │   └── routes.py         # HTTP endpoint handlers (thin)
│   ├── graph/
│   │   ├── graph.py          # build_graph() factory
│   │   ├── nodes.py          # agent_node and future nodes
│   │   └── state.py          # ChatState TypedDict
│   ├── providers/
│   │   └── copilot.py        # ChatCopilot(BaseChatModel)
│   └── auth/
│       └── manager.py        # CopilotAuthManager
├── frontend/
│   └── index.html            # Single-page chat UI (vanilla JS)
├── pyproject.toml
└── .env.example
```

---

## Data Flow

### Happy path — user sends a message:

```
1. Browser  →  POST /chat  { thread_id, message }
2. routes.py   unpacks request, calls app.state.graph.ainvoke(
                   {"messages": [HumanMessage(message)]},
                   config={"configurable": {"thread_id": thread_id}}
               )
3. LangGraph   loads checkpoint for thread_id from MemorySaver
               appends new HumanMessage via add_messages reducer
4. agent_node  receives full message history in state["messages"]
               calls await llm.ainvoke(state["messages"])
5. ChatCopilot calls _ensure_client() (noop if already connected)
               serializes messages to Copilot prompt string
               calls session.send_and_wait({"prompt": ...})
6. Copilot CLI responds via JSON-RPC
7. ChatCopilot wraps response in AIMessage, returns ChatResult
8. agent_node  returns {"messages": [AIMessage(...)]}
9. LangGraph   add_messages reducer appends AIMessage to state
               saves new checkpoint to MemorySaver
               returns final state
10. routes.py  extracts state["messages"][-1].content
               returns { reply: "...", thread_id: "..." }
11. Browser    displays reply
```

### Auth flow — first launch:

```
1. Browser  →  GET /auth/status  → { authenticated: false }
2. Browser  →  POST /auth/login
               routes.py calls auth_manager.device_login() [async]
               returns { verification_uri, user_code }
3. User        opens browser, enters code at github.com/login/device
4. Browser     polls GET /auth/status every 3s
5. Device Flow completes → token saved to ~/.copilot_sdk/token.enc
6. GET /auth/status  → { authenticated: true }
7. Browser     enables chat form
```

---

## Suggested Build Order

The dependency graph between components determines build order. Lower layers must
be built and tested before upper layers can use them.

```
Phase 1: Auth Layer
  app/auth/manager.py
  → No dependencies. Can be built and tested in isolation with httpx mocks.
  → Deliverable: CopilotAuthManager with get_token(), save_token()

Phase 2: Provider Layer
  app/providers/copilot.py
  → Depends on: Auth layer, copilot SDK
  → Deliverable: ChatCopilot passing LangChain's BaseChatModel interface test

Phase 3: Graph Layer
  app/graph/state.py → app/graph/nodes.py → app/graph/graph.py
  → Depends on: Provider layer
  → Deliverable: build_graph() producing a compiled graph that round-trips a message

Phase 4: Web Layer
  app/api/lifespan.py → app/api/routes.py → app/main.py
  → Depends on: Graph layer
  → Deliverable: HTTP server that accepts POST /chat and returns replies

Phase 5: Frontend
  frontend/index.html
  → Depends on: Web layer (API contract)
  → Deliverable: Browser chat UI that calls /chat and /auth/*
```

Each phase produces something independently runnable (or testable in isolation), reducing
integration risk. The provider layer is the highest-risk phase (SDK is Technical Preview)
and is deliberately isolated so its instability cannot propagate up.

---

## Anti-Patterns to Avoid

### Importing the Copilot SDK outside the provider layer
**Why bad:** Breaks the isolation boundary. A SDK change forces edits in multiple files.
**Instead:** Only `app/providers/copilot.py` imports `from copilot import ...`.

### Storing conversation history in the web layer
**Why bad:** Duplicates the checkpointer's job. Creates two sources of truth.
**Instead:** History lives exclusively in LangGraph checkpoints, keyed by `thread_id`.

### Creating the graph per-request
**Why bad:** Reconnects `CopilotClient` on every request (expensive JSON-RPC handshake).
**Instead:** One graph instance per process, created in lifespan, stored in `app.state`.

### Using synchronous `graph.invoke()` inside `async def` endpoints
**Why bad:** `invoke()` calls `asyncio.run()` internally, which raises `RuntimeError` if
an event loop is already running (standard in ASGI servers).
**Instead:** Always use `await graph.ainvoke()` from async endpoints.

### Implementing `_generate()` as `loop.run_until_complete(_agenerate())`
**Why bad:** Same problem — deadlocks when called from within an async context.
**Instead:** Override `_generate()` to raise `NotImplementedError`. The async path
(`_agenerate`) is the only one needed when the graph is invoked via `ainvoke`.

---

## Scalability Considerations

This is explicitly a single-user personal tool. The architecture reflects that.

| Concern | v1 (personal tool) | If ever multi-user |
|---------|--------------------|--------------------|
| Thread storage | MemorySaver (RAM) | langgraph-checkpoint-sqlite or postgres |
| Token storage | Single file `~/.copilot_sdk/token.enc` | Per-user Redis store (see token_store.py in docs/pre) |
| LLM instance | Singleton per process | One per authenticated user, or pooled |
| Concurrency | Single user, no problem | FastAPI handles concurrent requests; MemorySaver is not thread-safe across processes — needs external store |

---

## Sources

- LangGraph MessagesState and add_messages: https://deepwiki.com/langchain-ai/langchain-academy/3.1-stategraph-and-messagesstate
- LangGraph memory / MemorySaver: https://docs.langchain.com/oss/python/langgraph/add-memory
- LangGraph checkpointer tutorial: https://langchain-tutorials.github.io/implement-conversation-memory-langgraph-checkpointer/
- FastAPI lifespan events (official): https://fastapi.tiangolo.com/advanced/events/
- LangGraph + FastAPI integration pattern: https://dev.to/anuragkanojiya/how-to-use-langgraph-within-a-fastapi-backend-amm
- LangGraph agent service toolkit (architecture reference): https://github.com/JoshuaC215/agent-service-toolkit
- LangGraph ainvoke ASGI context issue: https://forum.langchain.com/t/langgraph-ainvoke-breaks-asgi-async-context/99
- LangGraph production patterns 2026: https://use-apify.com/blog/langgraph-agents-production
- Project context: docs/pre/copilot_langgraph_provider.md (HIGH confidence — primary design reference)
