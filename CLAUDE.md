<!-- GSD:project-start source:PROJECT.md -->
## Project

**Copilot LangGraph Chat**

GitHub Copilot を LangGraph の AI プロバイダーとして使う、個人用の汎用チャット Web アプリ。
`ChatCopilot`（`BaseChatModel` のカスタム実装）を通じて Copilot の推論能力を活用しながら、LangGraph のグラフ構造により将来のエージェント化・ツール呼び出し拡張に対応できる設計を目指す。

**Core Value:** Copilot の JSON-RPC ベース SDK を LangChain 互換プロバイダーとして動かし、スレッド維持付きのチャット UI から使えること。

### Constraints

- **Tech Stack**: Python（LangChain / LangGraph / Copilot SDK） — ドキュメントのサンプルコードが Python ベース
- **Auth**: Device Flow のみ — 非インタラクティブ環境向け PAT 方式は今回対象外
- **SDK 安定性**: Copilot SDK は Technical Preview — 外部インターフェースを薄いラッパーで隔離しておく
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

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
### Persistence / Session State
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| `langgraph-checkpoint-sqlite` | 3.0.3 | Conversation thread persistence | SQLite is the right fit for a single-user local tool: zero operational overhead (no Redis server), file-based durability across process restarts, and `AsyncSqliteSaver` integrates cleanly with async FastAPI. `MemorySaver` is in-memory only (lost on restart) — insufficient for a chat app where history should survive. Redis is explicitly ruled out in PROJECT.md ("個人ツールのため不要"). | HIGH |
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
## LangGraph API Patterns for This Project
### State Definition
# Option A: extend the built-in (recommended for simple chat)
### Graph Compilation
### Thread-based Sessions
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
## Installation
# Using uv (recommended)
# Dev dependencies
# Or using pip
## Critical Constraints
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
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
