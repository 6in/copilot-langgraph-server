# Technology Stack

**Project:** Copilot LangGraph Chat
**Researched:** 2026-03-31
**Overall confidence:** MEDIUM-HIGH (core stack HIGH; Copilot SDK LOW due to Technical Preview status)

---

## Recommended Stack

### Runtime

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Python | 3.12 | Runtime | 3.12 is the stable sweet spot: full support from LangGraph, FastAPI, and github-copilot-sdk (>=3.11). 3.13 is supported but less battle-tested in the ecosystem. | HIGH |

### Core AI Framework

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| `langgraph` | 1.1.3 | Stateful conversation graph | The project's core orchestration layer. Provides StateGraph, MessagesState, compiled graph with checkpointer support. Production/Stable (status 5 on PyPI). Python 3.10+ required; 3.13 now officially supported. | HIGH |
| `langchain-core` | 1.2.23 | BaseChatModel base class | Required for the `ChatCopilot` custom provider. Provides `BaseChatModel`, `HumanMessage`, `AIMessage`, `ChatResult`, `ChatGeneration`. Do NOT install the full `langchain` package — `langchain-core` is the slim, stable dependency surface needed. | HIGH |

### Custom Provider

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| `github-copilot-sdk` | 0.2.0 | GitHub Copilot JSON-RPC client | The SDK bundles platform-specific Copilot CLI binaries into Python wheels — no separate CLI install needed. Communicates via JSON-RPC (not HTTP/OpenAI-compatible), so `ChatOpenAI(base_url=...)` is not an option. A thin `BaseChatModel` wrapper isolates breaking changes. Technical Preview: pin to an exact version. | LOW (Technical Preview, breaking changes possible) |

### Web Backend

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| `fastapi` | 0.135.2 | HTTP + WebSocket API server | FastAPI is the standard choice for async Python APIs in 2025 (78.9k GitHub stars vs Flask's 68.4k; ASGI vs WSGI). Native `async def` routes integrate naturally with LangGraph's `ainvoke`. Built-in Pydantic validation and OpenAPI docs. LangGraph + FastAPI is the most documented integration pattern in 2025. | HIGH |
| `uvicorn` | 0.42.0 | ASGI server | Standard ASGI server for FastAPI. Use `uvicorn[standard]` for production (includes `uvloop` and `httptools`). | HIGH |

### Frontend

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Vanilla JS + HTML/CSS | — | Chat UI | Single-user personal tool: no build toolchain, no npm, no bundler. Plain `fetch` POST for sending messages, DOM manipulation for rendering. This project has explicitly ruled out streaming, so SSE/WebSocket is not needed for v1 — simple request/response via `fetch` is sufficient. Served as static files from FastAPI (`StaticFiles`). | HIGH |
| Jinja2 | 3.x (FastAPI ships with it) | HTML templating | Optional: FastAPI's `TemplateResponse` lets you serve the chat page as a rendered template. Avoids a separate SPA deployment. Zero additional dependency cost since FastAPI already pulls it in. | MEDIUM |

**Why NOT React/HTMX:** React adds a build pipeline and SPA complexity that is unjustified for a personal tool with no streaming. HTMX is a reasonable alternative but adds an external JS dependency and SSE/WebSocket wiring for real-time — overkill when synchronous request/response is acceptable.

### Persistence / Session State

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| `langgraph-checkpoint-sqlite` | 3.0.3 | Conversation thread persistence | SQLite is the right fit for a single-user local tool: zero operational overhead (no Redis server), file-based durability across process restarts, and `AsyncSqliteSaver` integrates cleanly with async FastAPI. `MemorySaver` is in-memory only (lost on restart) — insufficient for a chat app where history should survive. Redis is explicitly ruled out in PROJECT.md ("個人ツールのため不要"). | HIGH |

Persistence pattern:
```python
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

async with AsyncSqliteSaver.from_conn_string("checkpoints.db") as checkpointer:
    graph = build_graph(llm).compile(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "session-abc123"}}
    result = await graph.ainvoke(input, config=config)
```

### Authentication / Security

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| `cryptography` | 46.0.6 | Fernet token encryption | Required by the concept doc's `CopilotAuthManager`. Encrypts the `ghu_` OAuth token at rest in `~/.copilot_sdk/token.enc`. Standard, well-maintained library. | HIGH |
| `httpx` | 0.28.1 | Async HTTP for Device Flow | Required for the GitHub Device Flow OAuth calls in `copilot_auth.py`. The concept doc already uses it. Do not add `requests` (sync) alongside `httpx` (async) — pick one. | HIGH |

### Packaging

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| `pyproject.toml` | PEP 621 | Project metadata + dependencies | Standard in 2025. Single source of truth. Works with pip, uv, and all modern build backends. `requirements.txt` is a legacy format — no rationale for using it in a new project. | HIGH |
| `uv` | latest | Dependency management + venv | 10–100x faster than pip. `uv.lock` for reproducible environments. `uv add` / `uv sync` replace `pip install`. Not required by users consuming the app, only for development workflow. | MEDIUM |

---

## LangGraph API Patterns for This Project

### State Definition

Use `MessagesState` (built-in) or define a custom TypedDict with `Annotated[list[AnyMessage], add_messages]`:

```python
from langgraph.graph import MessagesState

# Option A: extend the built-in (recommended for simple chat)
class CopilotState(MessagesState):
    model: str  # additional field for model selection
```

The `add_messages` reducer appends new messages rather than replacing the list — essential for multi-turn conversation.

### Graph Compilation

```python
from langgraph.graph import StateGraph, END

graph = StateGraph(CopilotState)
graph.add_node("agent", agent_node)
graph.set_entry_point("agent")
graph.add_edge("agent", END)
compiled = graph.compile(checkpointer=checkpointer)
```

### Thread-based Sessions

Each browser tab / conversation maps to a `thread_id` in the config. LangGraph loads the checkpoint for that thread automatically:

```python
config = {"configurable": {"thread_id": str(uuid.uuid4())}}
result = await compiled.ainvoke({"messages": [HumanMessage(content=user_input)]}, config=config)
```

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Web framework | FastAPI | Flask | Flask is WSGI; async requires workarounds. LangGraph is natively async — FastAPI is the path of least resistance. |
| Web framework | FastAPI | Django | Too heavy for a personal tool with no ORM needs. |
| Frontend | Vanilla JS | HTMX | HTMX is excellent but unnecessary; project has no streaming in v1 and is single-user. Zero-dependency vanilla JS is simpler to maintain. |
| Frontend | Vanilla JS | React/Next.js | Build pipeline, npm, SPA complexity — unjustified for a personal tool. |
| State persistence | SQLite (AsyncSqliteSaver) | MemorySaver | MemorySaver is lost on process restart; not suitable for a persistent chat app. |
| State persistence | SQLite (AsyncSqliteSaver) | Redis | Redis requires a running server. Explicitly out-of-scope in PROJECT.md. |
| Packaging | pyproject.toml | requirements.txt | requirements.txt has no metadata, no build system declaration, and no lock file story. pyproject.toml is the PEP 621 standard. |
| LangChain dependency | langchain-core | langchain (full) | Full `langchain` installs many unused integrations. `langchain-core` provides only what is needed: `BaseChatModel`, message types, output parsers. |
| HTTP client | httpx | requests | Project is fully async; `requests` is synchronous and would block the event loop inside `async def`. |

---

## Installation

```bash
# Using uv (recommended)
uv add fastapi "uvicorn[standard]" langgraph langchain-core \
    langgraph-checkpoint-sqlite github-copilot-sdk \
    cryptography httpx

# Dev dependencies
uv add --dev pytest pytest-asyncio ruff mypy

# Or using pip
pip install fastapi "uvicorn[standard]" langgraph langchain-core \
    langgraph-checkpoint-sqlite github-copilot-sdk \
    cryptography httpx
```

Minimum `pyproject.toml` structure:

```toml
[project]
name = "copilot-langgraph"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.135.2",
    "uvicorn[standard]>=0.42.0",
    "langgraph>=1.1.3",
    "langchain-core>=1.2.23",
    "langgraph-checkpoint-sqlite>=3.0.3",
    "github-copilot-sdk==0.2.0",   # pin exact: Technical Preview
    "cryptography>=46.0.6",
    "httpx>=0.28.1",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

Note: `github-copilot-sdk` is pinned with `==` (not `>=`) because it is Technical Preview and breaking changes are explicitly warned about in the project docs.

---

## Critical Constraints

1. **github-copilot-sdk is Technical Preview.** Pin to an exact version. Wrap all SDK calls behind a thin adapter class (`ChatCopilot`) so the blast radius of breaking changes is contained to one file.

2. **No OpenAI-compatible URL trick.** The SDK communicates via JSON-RPC to the bundled Copilot CLI binary. `ChatOpenAI(base_url=...)` will not work. `BaseChatModel` custom implementation is mandatory.

3. **No streaming in v1.** The concept doc explicitly states Copilot SDK's current spec does not support streaming. Do not design the frontend or graph around streaming. `send_and_wait` is the only available call pattern.

4. **github-copilot-sdk requires Python >=3.11.** Combined with LangGraph's >=3.10, the effective minimum is Python 3.11. Python 3.12 is recommended as the stable target.

---

## Sources

- LangGraph PyPI: https://pypi.org/project/langgraph/
- langchain-core PyPI: https://pypi.org/project/langchain-core/
- github-copilot-sdk PyPI: https://pypi.org/project/github-copilot-sdk/
- FastAPI PyPI: https://pypi.org/project/fastapi/
- uvicorn PyPI: https://pypi.org/project/uvicorn/
- langgraph-checkpoint-sqlite PyPI: https://pypi.org/project/langgraph-checkpoint-sqlite/
- cryptography PyPI: https://pypi.org/project/cryptography/
- httpx PyPI: https://pypi.org/project/httpx/
- LangGraph Python 3.13 compatibility announcement: https://changelog.langchain.com/announcements/langgraph-is-now-compatible-with-python-3-13
- FastAPI vs Flask 2025 comparison: https://strapi.io/blog/fastapi-vs-flask-python-framework-comparison
- LangGraph + FastAPI integration guide: https://www.zestminds.com/blog/build-ai-workflows-fastapi-langgraph/
- pyproject.toml packaging guide: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/
- GitHub Copilot SDK overview: https://github.blog/news-insights/company-news/build-an-agent-into-any-app-with-the-github-copilot-sdk/
- GitHub Copilot SDK Python deep-wiki: https://deepwiki.com/github/copilot-sdk/6.2-python-sdk
