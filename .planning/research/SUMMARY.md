# Project Research Summary

**Project:** Copilot LangGraph Chat
**Domain:** Personal LLM chat web app — custom LangChain provider over GitHub Copilot JSON-RPC SDK
**Researched:** 2026-03-31
**Confidence:** MEDIUM-HIGH (core stack HIGH; Copilot SDK specifics LOW due to Technical Preview)

## Executive Summary

This is a single-user, locally-run Python web app that wraps GitHub Copilot as a LangChain-compatible chat provider and exposes it through a browser UI with multi-turn conversation history. The central technical challenge is that the Copilot SDK communicates via JSON-RPC to a bundled CLI binary — not via an OpenAI-compatible HTTP API — so the usual shortcut of pointing `ChatOpenAI` at a custom URL does not apply. A custom `ChatCopilot(BaseChatModel)` implementation is mandatory, and this file is the highest-risk surface in the entire codebase because the SDK is Technical Preview and subject to breaking changes.

The recommended approach is a four-layer Python monolith: FastAPI web layer → LangGraph graph layer → `ChatCopilot` provider layer → `CopilotAuthManager` auth layer. Each layer communicates only downward. LangGraph's thread-based checkpointing (`MemorySaver` for v1, upgradeable to SQLite without changing the graph) handles multi-turn context automatically once the `add_messages` reducer is in place. The frontend is deliberately vanilla JS served as static files — no build toolchain, no streaming, simple `fetch` POST to `/chat`.

The primary risks are in Phase 1 (BaseChatModel implementation): Pydantic v2 incompatibility, incorrect async patterns that deadlock inside ASGI, calling private `_agenerate()` directly from graph nodes, and missing the `add_messages` reducer that silently destroys conversation history. All of these are well-documented and preventable with the right signatures and patterns from the start. The SDK isolation boundary (only `app/providers/copilot.py` imports the SDK) is the key architectural constraint that limits the blast radius of any future SDK breaking change.

---

## Key Findings

### Recommended Stack

The stack is minimal and strongly opinionated toward async Python. FastAPI + LangGraph is the most documented integration pattern in 2025 and the natural fit: both are natively async, and `await graph.ainvoke()` integrates directly into `async def` FastAPI routes. The only unusual element is the Copilot SDK, which must be pinned to an exact version and isolated behind a single adapter file.

**Core technologies:**

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.12 | Runtime — stable sweet spot for all dependencies |
| `langgraph` | 1.1.3 | Stateful conversation graph with thread checkpointing |
| `langchain-core` | 1.2.23 | `BaseChatModel` base class — slim, not full `langchain` |
| `github-copilot-sdk` | 0.2.0 | Copilot JSON-RPC client — **pin exact, Technical Preview** |
| `fastapi` | 0.135.2 | Async HTTP API server |
| `uvicorn[standard]` | 0.42.0 | ASGI server |
| `langgraph-checkpoint-sqlite` | 3.0.3 | Durable thread persistence (v2 upgrade path) |
| `cryptography` | 46.0.6 | Fernet token encryption for auth |
| `httpx` | 0.28.1 | Async HTTP for Device Flow OAuth |
| Vanilla JS + HTML/CSS | — | Chat UI — no build toolchain needed |

**Excluded by design:** React/HTMX (unjustified complexity for single-user tool), `langchain` full package (use `langchain-core` only), `requests` (sync, would block ASGI event loop), Redis (out of scope per PROJECT.md).

See `.planning/research/STACK.md` for full rationale and pyproject.toml template.

### Expected Features

**Must have (table stakes) — v1:**
- Message history display — user/assistant bubbles, chronological scroll
- Multi-turn thread with context accumulation — LangGraph `add_messages` state
- Send/receive flow with loading indicator — disable input during LLM call (2-15s round-trip)
- New chat button — resets thread, starts fresh LangGraph state
- Markdown + syntax-highlighted code rendering in assistant bubbles
- Inline error display — auth errors must surface re-auth trigger, not a generic 500
- Device Flow auth trigger + status display — gates the entire app
- Keyboard send (Enter / Shift+Enter for newline)
- Auto-scroll to latest message

**Should have — include in v1 for quality of life:**
- Model selector dropdown (gpt-4.1, claude-sonnet-4-5, gemini-2.5-pro curated list)
- Token expiry detection with re-auth prompt (not just a 401 log)
- Copy response button (per-message clipboard API)

**Defer to v2+:**
- Session sidebar / conversation list (requires persistence layer)
- Auto-generated conversation titles (depends on sidebar)
- Conversation search, export, prompt templates
- Streaming (Copilot SDK `send_and_wait` is blocking; no fake streaming)

**Anti-features — explicitly do not build:**
- User accounts / login screen (personal tool, localhost only)
- Dark/light mode toggle (use OS `prefers-color-scheme`)
- Regenerate/edit message branching (increases state complexity unnecessarily)

See `.planning/research/FEATURES.md` for dependency chain and MVP phasing.

### Architecture Approach

The application is a single-process Python server with four strictly-layered components communicating only downward. No layer reaches back up. The LangGraph checkpointer (keyed by `thread_id` UUID generated in the browser) is the sole source of truth for conversation history — the web layer holds nothing. One graph instance per process is created at startup via FastAPI `lifespan` and stored in `app.state`.

**Major components:**

| Component | File | Responsibility |
|-----------|------|---------------|
| Auth Layer | `app/auth/manager.py` | Device Flow OAuth, Fernet encrypt/decrypt, token file I/O |
| Provider Layer | `app/providers/copilot.py` | `ChatCopilot(BaseChatModel)` — only file that imports Copilot SDK |
| Graph Layer | `app/graph/` | `StateGraph` definition, `ChatState` with `add_messages`, node wiring |
| Web Layer | `app/api/` | FastAPI routes, lifespan startup, request/response shaping |
| Frontend | `frontend/index.html` | Vanilla JS chat UI, `fetch` POST, localStorage `thread_id` |

**Build order follows dependency direction:** Auth → Provider → Graph → Web → Frontend. Each layer is independently testable before the next is built.

**v1 endpoints:** `POST /chat`, `GET /auth/status`, `POST /auth/login`

See `.planning/research/ARCHITECTURE.md` for full data flow, async patterns, and directory structure.

### Critical Pitfalls

1. **Calling `llm._agenerate()` directly in graph nodes** — bypasses callbacks, tracing, and retry logic; breaks when langchain-core changes the private signature. Always use `await llm.ainvoke(messages)` from nodes.

2. **`_generate` using `asyncio.get_event_loop().run_until_complete()`** — raises `RuntimeError: This event loop is already running` inside ASGI. Implement `_generate` to raise `NotImplementedError`; use only the async path (`ainvoke` → `_agenerate`).

3. **Missing `add_messages` reducer on graph state** — without `Annotated[list, add_messages]`, nodes that return `{"messages": [new_msg]}` silently overwrite the entire conversation history. Use `MessagesState` or the `Annotated` pattern from day one.

4. **Pydantic v2 incompatibility in `ChatCopilot`** — `class Config: arbitrary_types_allowed = True` is Pydantic v1 syntax. Use `model_config = ConfigDict(arbitrary_types_allowed=True)` and `_client: Any = PrivateAttr(default=None)`.

5. **Copilot SDK session not closed on error** — exceptions during `_agenerate` leave the JSON-RPC subprocess in a broken state; subsequent calls reuse a corrupted client. Wrap `_agenerate` in `try/except` that resets `_client = None` on connection errors; always call `llm.close()` in FastAPI lifespan shutdown.

6. **Co-locating Fernet key with encrypted token** — `~/.copilot_sdk/.enc_key` next to `token.enc` provides no security. Prefer `COPILOT_TOKEN_ENC_KEY` env var; add `~/.copilot_sdk/` to `.gitignore`.

7. **Tech Preview SDK breaking changes** — pin `github-copilot-sdk==0.2.0` (exact); isolate all imports behind `app/providers/copilot.py` only.

See `.planning/research/PITFALLS.md` for full list (16 pitfalls with phase assignments).

---

## Implications for Roadmap

### Phase 1: Auth + Provider Foundation
**Rationale:** The entire app is gated on a valid Copilot token and a working `ChatCopilot` client. These have the most implementation risk (Technical Preview SDK, Pydantic v2 patterns, async lifecycle). Build and validate in isolation before touching graph or web layers.
**Delivers:** `CopilotAuthManager` (Device Flow, token encrypt/decrypt) + `ChatCopilot(BaseChatModel)` passing LangChain interface tests. A Python REPL or CLI script can get a Copilot response end-to-end.
**Features addressed:** Device Flow auth, `ChatCopilot` provider, model selection parameter
**Pitfalls to avoid:** Pydantic v2 Config syntax (use `ConfigDict`/`PrivateAttr`); full `_generate`/`_agenerate` canonical signatures; SDK pinning and import isolation; client lifecycle error handling

### Phase 2: Graph Layer
**Rationale:** LangGraph graph depends on the provider being stable. The state design (`add_messages` reducer) must be correct from the start — retrofitting is painful because it silently breaks multi-turn behavior.
**Delivers:** `build_graph()` producing a compiled `StateGraph` that round-trips a multi-turn conversation with correct history accumulation. `MemorySaver` checkpointer keyed by `thread_id`.
**Features addressed:** Multi-turn thread, conversation history persistence (in-memory), thread_id session abstraction
**Pitfalls to avoid:** `add_messages` reducer missing; calling `_agenerate` directly; graph recompilation per request (compile once at startup)

### Phase 3: Web API Layer
**Rationale:** FastAPI wraps the graph with HTTP. Auth flow is the most complex endpoint — Device Flow must be decoupled from request handlers (dedicated `/auth/login` endpoint with frontend polling pattern).
**Delivers:** Running HTTP server with `POST /chat`, `GET /auth/status`, `POST /auth/login`. FastAPI lifespan initializes all shared resources once. Testable with `curl` or HTTPie.
**Features addressed:** Send/receive flow, auth status gating, inline error responses, token expiry → re-auth trigger
**Pitfalls to avoid:** Sync `invoke()` inside async endpoints; device flow blocking request handlers; graph created per-request; no try/except distinguishing auth errors from SDK errors

### Phase 4: Frontend UI
**Rationale:** Depends on the API contract being stable. Vanilla JS keeps this phase simple — no build toolchain, no npm, no bundler.
**Delivers:** Browser chat UI with all table-stakes features: message bubbles, loading indicator, markdown + syntax highlighting, new chat, keyboard send, auto-scroll, auth status in header with Device Flow trigger.
**Features addressed:** All table-stakes from FEATURES.md; model selector dropdown; copy button; inline error display
**Pitfalls to avoid:** Building streaming UI (SDK does not support it); using React/HTMX (unjustified complexity)

### Phase Ordering Rationale

- **Dependency direction is strict:** Auth → Provider → Graph → Web → Frontend. Each phase produces something independently runnable before the next layer is added.
- **Highest risk first:** The Copilot SDK is the biggest unknown. Isolating it in Phase 1 means Phase 2+ can proceed even if the SDK interface requires iteration.
- **MemorySaver is intentionally v1:** The `thread_id` abstraction is established in Phase 2 so upgrading to `langgraph-checkpoint-sqlite` in a future phase is a one-line swap in `build_graph()`.
- **No streaming complexity:** The entire stack is designed around synchronous `send_and_wait`. The frontend uses simple `fetch` POST. If streaming is added later, the API endpoint should be designed as `StreamingResponse` (single-chunk for now) to avoid a contract break.

### Research Flags

**Needs validation during implementation:**
- **Phase 1 — Copilot SDK session API:** The exact interface of `CopilotClient`, `session.send_and_wait()`, and whether the session accepts structured turn-based input (vs. a concatenated flat string) must be validated against the pinned `0.2.0` SDK. The `_messages_to_prompt()` serialization strategy depends on this.
- **Phase 1 — Device Flow client ID:** `CLIENT_ID = "Iv1.b507a08c87ecfe98"` is described as non-official use of the Copilot CLI client ID. Validate this still works for personal tool use.
- **Phase 4 — Model list:** Copilot model availability is dynamic (some marked preview, deprecation dates). Curate a static list (gpt-4.1, claude-sonnet-4-5, gemini-2.5-pro) from current docs rather than hardcoding from research-time assumptions.

**Standard patterns — no additional research needed:**
- **Phase 2 — LangGraph StateGraph + MessagesState:** Well-documented, multiple corroborating sources, HIGH confidence.
- **Phase 3 — FastAPI lifespan + `app.state`:** Official FastAPI docs, HIGH confidence.
- **Phase 4 — Vanilla JS chat UI:** No framework, standard DOM APIs, HIGH confidence.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All dependencies verified on PyPI with current versions; alternatives explicitly evaluated |
| Features | HIGH | Grounded in analysis of comparable tools (Open WebUI, LibreChat) and Copilot-specific constraints |
| Architecture | HIGH | LangGraph + FastAPI integration pattern is well-documented with multiple corroborating sources |
| Pitfalls | HIGH (core) / MEDIUM (SDK-specific) | LangGraph/LangChain pitfalls verified against official docs; Copilot SDK pitfalls inferred from limited Technical Preview docs |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Copilot SDK `send_and_wait` exact API shape:** Whether it accepts a structured list of turns or only a single prompt string determines the `_messages_to_prompt()` implementation. Validate in Phase 1 against the pinned SDK wheel before finalizing the serialization strategy.
- **GitHub Device Flow token lifetime:** GitHub does not document a specific expiry period for `ghu_` tokens issued to the Copilot CLI OAuth app. The error-handling path (catch 401, delete token, re-trigger Device Flow) is the safe fallback, but a proactive "re-auth if unused > 30 days" heuristic may be warranted.
- **Copilot model list stability:** Models are subject to deprecation (some variants noted as deprecated 2026-04-01 in research). The model selector must use a config-file or docs-derived list, not a hardcoded assumption from this research.

---

## Sources

### Primary (HIGH confidence)
- LangGraph PyPI / official docs — StateGraph, MessagesState, MemorySaver, ainvoke patterns
- FastAPI official docs — lifespan events, `app.state`, async endpoints
- langchain-core PyPI / API reference — BaseChatModel abstract interface, Pydantic v2 migration
- `docs/pre/copilot_langgraph_provider.md` — primary design reference for ChatCopilot and auth flow

### Secondary (MEDIUM confidence)
- DeepWiki: github/copilot-sdk — Python SDK architecture and session lifecycle
- LangGraph agent service toolkit (JoshuaC215) — production architecture reference
- LangChain v0.3 blog post — Pydantic v2 migration details
- Open WebUI / LibreChat feature analysis — feature completeness baseline

### Tertiary (LOW confidence)
- GitHub Copilot SDK Technical Preview docs — breaking changes possible; validate against pinned 0.2.0
- Copilot CLI client ID (`Iv1.b507a08c87ecfe98`) — non-official use, validate still functional

---
*Research completed: 2026-03-31*
*Ready for roadmap: yes*
