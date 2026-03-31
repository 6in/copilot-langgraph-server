# Domain Pitfalls

**Domain:** LangGraph chat web app with custom BaseChatModel (GitHub Copilot SDK / JSON-RPC)
**Researched:** 2026-03-31
**Confidence:** HIGH (core LangGraph/LangChain patterns), MEDIUM (Copilot SDK specifics — Technical Preview, limited public docs)

---

## Critical Pitfalls

Mistakes that cause runtime failures, silent data corruption, or mandatory rewrites.

---

### Pitfall 1: Calling `llm._agenerate()` Directly Inside Graph Nodes

**What goes wrong:** The reference implementation in `docs/pre/copilot_langgraph_provider.md` calls `llm._agenerate(state["messages"])` directly in the graph node. This bypasses LangChain's public invocation path (`llm.invoke` / `llm.ainvoke`), which means callbacks, tracing, retry logic, and future middleware (e.g., LangSmith observability) are all skipped. Private methods are not part of the stable API and can change between minor langchain-core releases without a deprecation warning.

**Why it happens:** The example code shortcuts to the internal async method for simplicity, which appears to work but violates the intended extension boundary.

**Consequences:**
- No callback propagation — streaming hooks and LangSmith tracing will not fire.
- If langchain-core changes `_agenerate`'s signature (e.g., adds a required `run_manager` parameter), node breaks silently at runtime.
- Tool calling (`bind_tools`) will never work via the public interface if bypassed here.

**Prevention:** In graph nodes, always call `await llm.ainvoke(messages)` (async) or `llm.invoke(messages)` (sync). Reserve `_agenerate` as the internal method that the public interface ultimately delegates to — it should never be called from outside the model class itself.

**Warning signs:** Grep for `._agenerate(` or `._generate(` outside the `ChatCopilot` class body.

**Phase:** Address in Phase 1 (BaseChatModel implementation and graph wiring).

---

### Pitfall 2: `_generate` Using `asyncio.get_event_loop().run_until_complete()` in a Web Context

**What goes wrong:** The reference implementation's `_generate` calls `loop.run_until_complete(self._agenerate(...))`. This pattern raises `RuntimeError: This event loop is already running` when called inside an ASGI framework (FastAPI, Starlette) or any other async context, because Python's asyncio does not permit nested `run_until_complete` calls.

**Why it happens:** The sync wrapper was written assuming a standalone script context (`asyncio.run(main())`), but a web server has a persistent running event loop.

**Consequences:**
- Every synchronous call path from within the web server crashes immediately.
- The workaround (`nest_asyncio`) is not production-grade and masks deeper design issues.

**Prevention:**
- Always call `await llm.ainvoke(...)` from async endpoints — never the sync `llm.invoke(...)` path when inside an ASGI app.
- Implement `_generate` to raise `NotImplementedError` with a clear message ("Use ainvoke in async context") rather than attempting the event-loop hack. This forces callers to the async path.
- Alternatively, use `asyncio.run_coroutine_threadsafe` with a background thread's dedicated event loop if sync compatibility is truly needed.

**Warning signs:** Any `run_until_complete` or `asyncio.get_event_loop()` call inside `ChatCopilot._generate`; any sync FastAPI endpoint (`def` not `async def`) that calls the LLM.

**Phase:** Address in Phase 1 (BaseChatModel) and Phase 2 (web backend wiring).

---

### Pitfall 3: `BaseChatModel._generate` / `_agenerate` Missing Required Signature Parameters

**What goes wrong:** LangChain's `BaseChatModel` expects `_generate` and `_agenerate` to accept `stop: Optional[List[str]] = None` and `run_manager: Optional[CallbackManagerForLLMRun] = None` as keyword arguments. If these are absent, LangChain's internal dispatch will pass them anyway via `**kwargs` and they are silently dropped — but if the signature uses `**kwargs` without absorbing them, a `TypeError` surfaces when callbacks are active.

**Why it happens:** Minimal examples omit optional parameters. The reference implementation signature `def _generate(self, messages, **kwargs)` technically works but is fragile.

**Consequences:**
- Callback-based features (LangSmith tracing, streaming hooks) will not function correctly.
- Adding `stop` words (used by some tool-calling patterns) will have no effect.

**Prevention:** Implement both methods with the full canonical signature:
```python
def _generate(
    self,
    messages: List[BaseMessage],
    stop: Optional[List[str]] = None,
    run_manager: Optional[CallbackManagerForLLMRun] = None,
    **kwargs: Any,
) -> ChatResult: ...

async def _agenerate(
    self,
    messages: List[BaseMessage],
    stop: Optional[List[str]] = None,
    run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
    **kwargs: Any,
) -> ChatResult: ...
```

**Warning signs:** `_generate` or `_agenerate` signatures with no `stop` or `run_manager` parameter.

**Phase:** Address in Phase 1 (BaseChatModel implementation).

---

### Pitfall 4: LangGraph State Mutation — Overwriting Instead of Appending Messages

**What goes wrong:** If the `messages` field in `AgentState` is a plain `list` without a reducer, LangGraph uses last-write-wins semantics. A node that returns `{"messages": [new_ai_msg]}` will replace the entire conversation history with a single message, destroying all prior turns.

**Why it happens:** The reference `example_graph.py` manually constructs `state["messages"] + [ai_msg]`, which works but is fragile — it depends on the node always having the full history in state, and fails silently if a node ever returns a partial update.

**Consequences:**
- Multi-turn conversation history disappears after each turn.
- Bugs are invisible until manually inspecting state (no exception is raised).

**Prevention:** Use `Annotated` with `add_messages` reducer from `langgraph.graph.message`:
```python
from typing import Annotated
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
```
With this, nodes only need to return the new message(s); the reducer appends automatically. Alternatively, use `MessagesState` from `langgraph.graph` which includes this reducer by default.

**Warning signs:** `AgentState` with `messages: list` (no `Annotated`); node functions that return `state["messages"] + [...]`.

**Phase:** Address in Phase 1 (graph state design).

---

### Pitfall 5: Pydantic v2 Incompatibility with `class Config` and `_client` Private Attribute

**What goes wrong:** The reference `ChatCopilot` uses `class Config: arbitrary_types_allowed = True` (Pydantic v1 style) and assigns `_client: Any = None` as a class-level annotation. In Pydantic v2 (used by langchain-core >= 0.3), `class Config` is deprecated in favor of `model_config = ConfigDict(...)`. The `_client` annotation without `PrivateAttr()` may be treated as a model field (breaking serialization/validation) or silently ignored, depending on Pydantic's underscore handling rules.

**Why it happens:** LangChain migrated to Pydantic v2 internally in langchain-core 0.3.0 (released 2024). Pre-migration examples use v1 patterns. The `langchain_core.pydantic_v1` shim was removed.

**Consequences:**
- `TypeError` when instantiating `ChatCopilot` if Pydantic rejects the old `Config` syntax.
- `_client` may appear in model JSON schema or be reset on serialization.
- `ValidationError` if `auth_manager: Any = None` causes issues without `arbitrary_types_allowed`.

**Prevention:**
```python
from pydantic import ConfigDict, PrivateAttr

class ChatCopilot(BaseChatModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    model: str = "gpt-4.1"
    github_token: Optional[str] = None
    auth_manager: Optional[Any] = None
    _client: Any = PrivateAttr(default=None)
```
Use `PrivateAttr` for `_client` so Pydantic tracks it correctly as instance state outside the model schema.

**Warning signs:** `class Config:` inside any `BaseChatModel` subclass; `_client: Any = None` as a class-level annotation without `PrivateAttr`.

**Phase:** Address in Phase 1 (BaseChatModel implementation).

---

### Pitfall 6: GitHub Copilot SDK Session Not Closed on Error / CopilotClient Lifecycle Mismanagement

**What goes wrong:** `_ensure_client()` lazily initializes `_client` and `_client.start()` opens a JSON-RPC subprocess connection to the Copilot CLI. If an exception occurs during `_agenerate` (e.g., network timeout, bad response), the client is left in an open/partially-failed state. Subsequent calls may reuse a broken client, producing cryptic errors or hangs. Additionally, `close()` is only called if the caller explicitly invokes it — there is no `__del__` or context manager safety net.

**Why it happens:** The reference implementation's lazy initialization has no error recovery path and no automatic lifecycle management.

**Consequences:**
- Leaked subprocess connections accumulate over server lifetime.
- A single failed request can corrupt all subsequent requests in the same server instance.
- The Copilot CLI subprocess may zombie-process if `_client.stop()` is never called.

**Prevention:**
- Wrap `_agenerate` with try/except that resets `_client = None` on connection-level errors so the next call gets a fresh client.
- Implement `ChatCopilot` as an async context manager (`__aenter__`/`__aexit__`) or use a lifespan handler in the web framework to ensure `close()` is always called.
- Consider creating a new session per request (not a new client per request) — reuse the `CopilotClient` but create a fresh session object for each inference call, as sessions represent individual conversation contexts.

**Warning signs:** No `try/finally` in `_agenerate`; no lifespan shutdown hook calling `llm.close()`.

**Phase:** Address in Phase 1 (BaseChatModel) and Phase 2 (web server lifespan wiring).

---

### Pitfall 7: GitHub Copilot OAuth Token Stored Without Expiry Validation

**What goes wrong:** The `load_token()` method reads the encrypted token and returns it without checking whether it is still valid. GitHub device flow tokens (`ghu_` prefix) can be revoked by the user, expire per GitHub's token policy, or be invalidated when the user's Copilot subscription changes. Passing a stale token to `CopilotClient` will produce an authentication error at SDK call time — potentially mid-conversation.

**Why it happens:** The saved payload includes `saved_at` but there is no expiry check in `load_token()`. GitHub's token lifetime for device flow tokens issued to third-party OAuth apps is not deterministically documented, but tokens can become invalid at any time.

**Consequences:**
- Users get an opaque SDK error mid-session rather than a clean "please re-authenticate" flow.
- If the token error is not distinguished from other errors, the app may retry forever or crash.

**Prevention:**
- Wrap the `CopilotClient` call in a try/except that catches authentication errors, deletes the stored token, and triggers `device_login()` again.
- Surface a clear "Token expired — please re-authenticate" response to the UI rather than a generic 500.
- Consider storing a `last_used_at` timestamp and proactively re-authenticating if the token hasn't been used in > 30 days.

**Warning signs:** `load_token()` returning a value without any validity check; no exception handler distinguishing auth errors from other SDK errors.

**Phase:** Address in Phase 2 (auth flow and error handling).

---

### Pitfall 8: Fernet Encryption Key Stored Next to the Encrypted File

**What goes wrong:** The reference implementation stores the Fernet key at `~/.copilot_sdk/.enc_key` and the encrypted token at `~/.copilot_sdk/token.enc` — in the same directory. If an attacker (or a backup/sync tool) reads both files, the encryption provides no protection. The key and ciphertext must be separate secrets; co-locating them makes encryption theater.

**Why it happens:** Convenience — keeping both in the same directory simplifies path management.

**Consequences:**
- Anyone with filesystem read access to `~/.copilot_sdk/` can decrypt the GitHub token.
- Backup tools (Time Machine, Dropbox, rsync) that sync `~` may upload both files to cloud storage.

**Prevention:**
- Prefer `COPILOT_TOKEN_ENC_KEY` environment variable (already supported in the reference code) as the primary key source, using the file-based key only as a developer fallback.
- Document clearly that `.enc_key` must not be committed to version control or synced to cloud storage (add to `.gitignore`).
- Consider using system keychain (macOS Keychain, Linux Secret Service via `keyring` library) instead of a file-based key for production use.
- Add `~/.copilot_sdk/` to `.gitignore`.

**Warning signs:** `~/.copilot_sdk/.enc_key` committed to git; no `.gitignore` entry for the key.

**Phase:** Address in Phase 2 (auth/token storage setup).

---

## Moderate Pitfalls

---

### Pitfall 9: LangGraph Graph Not Compiled Before Use / Recompilation on Every Request

**What goes wrong:** `build_graph()` calls `graph.compile()` each time it is invoked. If `build_graph` is called inside a request handler, compilation overhead is paid on every request. More critically, if `compile()` is called without adding all required edges (e.g., forgetting `graph.set_entry_point()` or leaving a node without outgoing edges), the graph silently produces no output rather than raising at construction time.

**Prevention:** Compile the graph once at application startup (module level or in the lifespan handler) and store the compiled graph as a singleton. Verify compilation produces the expected graph structure with a startup smoke test.

**Warning signs:** `build_graph()` called inside a request handler; no startup validation of the compiled graph.

**Phase:** Address in Phase 2 (web server wiring).

---

### Pitfall 10: `_messages_to_prompt()` Converts Structured Messages to a Flat String

**What goes wrong:** The reference implementation collapses the LangChain `BaseMessage` list into a single string with `[User]: / [Assistant]:` prefixes. This loses structured message metadata and makes it impossible to later pass tool call results (which have their own message type `ToolMessage`) or use native system prompt handling. The Copilot SDK may have its own session context management that expects prompts in a specific format.

**Prevention:**
- Investigate whether the Copilot SDK `session.send_and_wait()` accepts structured turn-based input rather than a single concatenated string.
- If flat string is required, ensure the format exactly matches what the Copilot model was trained to recognize as a conversation delimiter. Test with multi-turn conversations early.
- Design the prompt serialization as a separate injectable function so it can be swapped without touching the core model class.

**Warning signs:** `_messages_to_prompt` returning a joined string; test cases with multi-turn conversations are absent.

**Phase:** Address in Phase 1 (BaseChatModel implementation) with multi-turn test validation.

---

### Pitfall 11: Missing `_llm_type` Property Causes Silent Serialization Failures

**What goes wrong:** `_llm_type` is an abstract property required by `BaseChatModel`. While the reference code includes it, if it is accidentally omitted in a refactor, LangChain will raise `NotImplementedError` only when serialization or certain introspection paths are triggered — not at instantiation time.

**Prevention:** Add a unit test that instantiates `ChatCopilot` and asserts `llm._llm_type == "github-copilot"`. This also confirms the class can be constructed without credentials in test environments (using `github_token="test"`).

**Warning signs:** No unit test covering `ChatCopilot` instantiation.

**Phase:** Address in Phase 1 (BaseChatModel implementation).

---

### Pitfall 12: LangGraph `MemorySaver` Is Not Safe for Production / Multi-Process Deployment

**What goes wrong:** `MemorySaver` (in-memory checkpointer) stores all thread state in the Python process's heap. If the web server restarts, all conversation history is lost. If multiple worker processes are used (e.g., Uvicorn with `--workers 2`), each process has its own disconnected memory and requests will be routed to the wrong state.

**Prevention:**
- For v1 (single-process personal tool), `MemorySaver` is acceptable but document the restart-loses-history limitation.
- Use `thread_id` per conversation and pass it consistently via the LangGraph config: `graph.ainvoke(state, config={"configurable": {"thread_id": session_id}})`.
- Design the thread_id → conversation mapping in the web layer so it can be swapped for a persistent checkpointer later without graph changes.

**Warning signs:** Deploying with `--workers > 1` while using `MemorySaver`; no `thread_id` in graph invocation config.

**Phase:** Note in Phase 2 (web architecture); upgrade path documented for future milestone.

---

### Pitfall 13: Device Flow `device_login()` Cannot Run Inside a Web Request Handler

**What goes wrong:** `device_login()` is an interactive flow that prints instructions to stdout and polls in a loop with `asyncio.sleep`. If a web request triggers `get_token()` and the token is missing, the request handler will block indefinitely waiting for the user to authenticate in a browser — with no timeout and no feedback to the HTTP client.

**Prevention:**
- Treat authentication as a prerequisite: validate token presence at app startup, not lazily inside request handlers.
- Expose a dedicated `/auth/login` endpoint that streams the device code URL to the frontend, then poll `/auth/status` until the token is stored.
- Add a timeout to the `device_login()` loop (GitHub device codes expire after 15 minutes).

**Warning signs:** `auth_manager.get_token()` called inside a FastAPI route handler without prior token validation.

**Phase:** Address in Phase 2 (auth endpoint design).

---

### Pitfall 14: Technical Preview SDK Breaking Changes Without Notice

**What goes wrong:** `github/copilot-sdk` is explicitly labeled Technical Preview. Breaking changes to the Python package (`github-copilot-sdk` on PyPI) — including renamed classes, changed constructor parameters, or altered JSON-RPC protocol — can occur in any minor version bump without a deprecation window.

**Prevention:**
- Pin the SDK to an exact version in `requirements.txt` or `pyproject.toml` (e.g., `github-copilot-sdk==x.y.z`).
- Isolate all SDK calls behind a thin adapter layer (`copilot_langchain.py` already partially achieves this) — the rest of the codebase should never import from `copilot` directly.
- Add a `CHANGELOG` watch or GitHub release notification for `github/copilot-sdk`.
- Write integration tests that run against the pinned SDK version so regressions from upgrades are caught before deployment.

**Warning signs:** Unpinned `github-copilot-sdk` dependency; `from copilot import ...` imports outside the adapter module.

**Phase:** Address in Phase 1 (dependency pinning and adapter boundary design).

---

## Minor Pitfalls

---

### Pitfall 15: Frontend SSE / Streaming Not Planned For, Causing Architectural Rework Later

**What goes wrong:** Streaming is out of scope for v1, but the architecture chosen now will determine how easy it is to add. Using a simple request/response JSON API (`POST /chat → full response`) makes streaming a backward-incompatible change to the API contract, requiring frontend rewrites.

**Prevention:**
- Design the backend endpoint with streaming in mind even if not implemented: use FastAPI's `StreamingResponse` with a generator that currently yields a single chunk (the full response). This keeps the API contract streaming-compatible.
- On the frontend, if using `fetch`, write the response consumer as a streaming reader even if it currently just reads the whole body.

**Warning signs:** Backend endpoint returning `{"response": "..."}` JSON rather than an NDJSON or SSE-compatible format.

**Phase:** Note in Phase 2 (API design); no implementation required until streaming is added.

---

### Pitfall 16: GitHub Device Code Polling Does Not Handle `slow_down` Correctly

**What goes wrong:** The reference `device_login()` adds 5 seconds to `interval` on `slow_down` but does not also `await asyncio.sleep(interval)` before retrying — the `continue` statement skips the sleep at the top of the loop. This means the app may hammer the GitHub token endpoint faster than allowed, causing further `slow_down` responses and eventual rate-limit errors.

**Prevention:** Restructure the polling loop so the sleep always occurs at the beginning (or end) of every iteration, regardless of the error code received.

**Warning signs:** `slow_down` branch does not explicitly sleep before the next poll.

**Phase:** Address in Phase 2 (auth flow implementation).

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|---|---|---|
| Phase 1: BaseChatModel implementation | Pydantic v2 Config syntax; private `_client` field; missing `stop`/`run_manager` params; calling `_agenerate` directly in graph | Write full canonical signature; use `PrivateAttr`; use `model_config = ConfigDict` |
| Phase 1: Graph state design | Missing `add_messages` reducer; last-write-wins destroying history | Use `Annotated[list, add_messages]` from day one |
| Phase 1: SDK adapter boundary | Technical Preview breaking changes; `from copilot import` scattered | Pin version; single adapter module |
| Phase 2: Web server wiring | Event loop conflict in `_generate`; graph recompilation per request; device flow blocking requests | ASGI-only path (`ainvoke`); compile at startup; prerequisite token check |
| Phase 2: Auth endpoint | Device flow blocking; token expiry not handled; key co-located with ciphertext | Dedicated auth endpoints; try/except on auth errors; env-var key |
| Phase 2: Session lifecycle | CopilotClient leaked on error; zombie CLI subprocess | Context manager or lifespan hook; reset `_client` on error |
| Future: Streaming | Non-streaming API contract incompatible with SSE | Design endpoint as `StreamingResponse` even when yielding one chunk |
| Future: Persistent checkpointer | `MemorySaver` lost on restart; multi-worker split-brain | Document limitation; thread_id abstracted for easy swap |

---

## Sources

- LangGraph state management and reducers: [LangGraph Best Practices](https://www.swarnendu.de/blog/langgraph-best-practices/) | [LangGraph Notes: State Management](https://medium.com/@omeryalcin48/langgraph-notes-state-management-62ea5b5a5cdd)
- `add_messages` reducer pattern: [DeepWiki: StateGraph and MessagesState](https://deepwiki.com/langchain-ai/langchain-academy/3.1-stategraph-and-messagesstate) | [LangGraph Use Graph API](https://docs.langchain.com/oss/python/langgraph/use-graph-api)
- LangChain v0.3 Pydantic v2 migration: [Announcing LangChain v0.3](https://blog.langchain.com/announcing-langchain-v0-3/) | [LangChain Pydantic Compatibility](https://python.langchain.com/v0.2/docs/how_to/pydantic_compatibility/)
- `BaseChatModel` abstract method signatures: [LangChain API Reference](https://python.langchain.com/api_reference/core/language_models/langchain_core.language_models.chat_models.BaseChatModel.html) | [Custom Chat Model Implementation](https://sweets.chat/blog/article/implementing-a-custom-chat-model-with-langchain)
- asyncio nested event loop: [FastAPI Concurrency Guide](https://fastapi.tiangolo.com/async/) | [RuntimeError: asyncio.run() cannot be called from a running event loop](https://github.com/run-llama/llama_index/issues/9978)
- Copilot SDK architecture: [GitHub Copilot SDK](https://github.com/github/copilot-sdk) | [DeepWiki: Copilot SDK](https://deepwiki.com/github/copilot-sdk) | [DeepWiki: Authentication and Token Management](https://deepwiki.com/github/copilot-cli/6.7-authentication-and-token-management)
- Fernet key management: [Cryptography Fernet docs](https://cryptography.io/en/latest/fernet/) | [MultiFernet key rotation](https://www.geeksforgeeks.org/multifernet-module-in-python/)
- LangGraph checkpoint and thread_id: [Mastering Persistence in LangGraph](https://medium.com/@vinodkrane/mastering-persistence-in-langgraph-checkpoints-threads-and-beyond-21e412aaed60) | [LangGraph Checkpointing Best Practices 2025](https://sparkco.ai/blog/mastering-langgraph-checkpointing-best-practices-for-2025)
- SSE and streaming future-proofing: [SSE with FastAPI and LangGraph](https://www.softgrade.org/sse-with-fastapi-react-langgraph/) | [sse-starlette PyPI](https://pypi.org/project/sse-starlette/)
- Pydantic PrivateAttr: [Pydantic Models docs](https://docs.pydantic.dev/latest/concepts/models/)
