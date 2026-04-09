# Domain Pitfalls: v5.0 Agent Tool Platform

**Domain:** FastMCP + LangGraph bind_tools on non-OpenAI Copilot SDK stack
**Researched:** 2026-04-09
**Stack:** Python 3.12, LangGraph 1.1.3, langchain-core, ChatCopilot (BaseChatModel), arq worker, FastMCP, langchain-mcp-adapters, Docker Compose

---

## Pitfall Summary Table

| # | Issue | Severity | Prevention | Phase to Address |
|---|-------|----------|------------|-----------------|
| P1 | `ChatCopilot` has no `bind_tools` — `ToolNode` integration fails immediately | CRITICAL | Implement `bind_tools` + tool-call parsing in `copilot.py` first | MCP-02 (bind_tools integration) |
| P2 | Copilot SDK returns plain text, not structured `tool_calls` — LangGraph `ToolNode` never fires | CRITICAL | Prompt-injection tool-call parsing: parse JSON from response text; populate `AIMessage.tool_calls` manually | MCP-02 |
| P3 | `MultiServerMCPClient` async context manager removed in v0.1.0 — tutorials show broken pattern | HIGH | Use `session()` method or direct `.get_tools()` calls; never `async with client:` | MCP-01 (FastMCP setup) |
| P4 | MCP client re-initialized per arq job — connection overhead + race conditions | HIGH | Init `MultiServerMCPClient` in arq `startup()`, store in `ctx`; teardown in `shutdown()` | MCP-01 |
| P5 | Claude Code CLI subprocess blocks async event loop — all arq jobs stall | HIGH | Use `asyncio.create_subprocess_exec()` with `asyncio.wait_for()`; never `subprocess.run()` | MCP-03 (Claude Code tool) |
| P6 | Claude Code CLI subprocess inherits `CLAUDECODE=1` — nested session rejected | HIGH | Explicitly unset `CLAUDECODE` in subprocess env before spawning | MCP-03 |
| P7 | `tool_calls` infinite loop — agent never reaches terminal state | HIGH | Add iteration counter to `AgentState`; set `recursion_limit`; cap at 10 iterations | MCP-02 |
| P8 | Shell injection via tool arguments passed to Claude Code CLI | HIGH | Use `create_subprocess_exec()` (list args, not shell string); validate all args against schema | MCP-03 |
| P9 | FastMCP `stdio` transport incompatible with Docker multi-container networking | MEDIUM | Use `http` transport; add `mcp-server` Docker service; `worker` depends_on `mcp-server` | MCP-01 |
| P10 | Tool name collisions across MCP servers overwrite each other silently | MEDIUM | Enable `tool_name_prefix=True` in `MultiServerMCPClient`; use distinct tool names in FastMCP | MCP-01 |
| P11 | Tavily sync client (`TavilyClient`) blocks arq event loop | MEDIUM | Use `AsyncTavilyClient`; initialize in `startup()` and store in `ctx` | MCP-03 (web search tool) |
| P12 | Tavily full-page response overflows Copilot model context window | MEDIUM | Use `search_context(max_tokens=3000)` or limit to `max_results=3, include_raw_content=False` | MCP-03 |
| P13 | `ToolNode` silently drops `invalid_tool_calls` (JSON parse failures in tool args) | MEDIUM | Add explicit error edge in graph; log `invalid_tool_calls`; add error-recovery node | MCP-02 |
| P14 | FastMCP health check only available on `http` transport, not `stdio` | LOW | Add `@mcp.custom_route("/health")` explicitly; use in Docker `healthcheck` | MCP-01 |
| P15 | arq `job_timeout=300` too short for long-running Claude Code tasks; zombie subprocess on timeout | LOW | Add internal `asyncio.wait_for(timeout=120)` in handler; call `proc.kill()` on `TimeoutError` | MCP-03 |

---

## Critical Pitfalls

### P1: `ChatCopilot` Does Not Implement `bind_tools`

**What goes wrong:** `BaseChatModel.bind_tools()` raises `NotImplementedError` unless the subclass overrides it. `ChatCopilot` in `app/providers/copilot.py` currently has no `bind_tools` implementation. Calling `llm.bind_tools(tools)` at graph compile time — or inside `create_react_agent()` — throws immediately.

**Why it happens:** `bind_tools` is optional in the `BaseChatModel` interface. Only first-party LangChain providers (OpenAI, Anthropic, etc.) implement it. Custom wrappers do not get it for free. The method's default implementation in langchain-core simply raises `NotImplementedError`.

**Consequences:**
- Graph compilation fails with `NotImplementedError` the moment any tool-binding code runs
- `create_react_agent()` cannot be used at all with `ChatCopilot`
- Any `ToolNode` integration requires `AIMessage.tool_calls` to be populated — impossible without this implementation

**Prevention:**
Implement `bind_tools` in `app/providers/copilot.py`. Because the Copilot SDK does not natively emit structured `tool_calls` (see P2), the implementation must:
1. Accept a list of tools; store their schemas on the model instance
2. Inject tool schemas into the system prompt (prompt-injection pattern)
3. Parse the LLM text response for JSON tool-call patterns in `_agenerate`
4. Return `AIMessage(content="", tool_calls=[parsed_call])` when a tool call is detected

**Detection:** Immediate `NotImplementedError` on first `llm.bind_tools([...])` call or graph compile.

**Phase:** MCP-02. Must implement `bind_tools` in `copilot.py` before any tool-node graph work begins. This is the first thing to write in MCP-02, not the last.

---

### P2: Copilot SDK Returns Plain Text — `ToolNode` Never Dispatches

**What goes wrong:** The GitHub Copilot SDK communicates via JSON-RPC and returns `response.data.content` as a plain string. There is no native mechanism to emit an `AIMessage` with a populated `tool_calls` list. LangGraph's `ToolNode` only dispatches tools when `AIMessage.tool_calls` is non-empty. Without custom parsing, the tool is registered but never called — and no error is raised.

**Why it happens:** The Copilot SDK is designed for its own agent loop (the Copilot CLI), not for LangChain's tool-call protocol. The SDK's own tool system uses `@define_tool` decorators + `tool.call` events internally. It does not surface tool selections as OpenAI-format JSON structures.

**Consequences:**
- Standard `ToolNode` → model ReAct loop never triggers tool execution
- Tools appear registered but are silently ignored
- Agent always responds as if no tools are available

**Two viable approaches (must choose before MCP-02 design):**

*Approach A — Prompt-injection + text parsing (recommended):*
- `bind_tools` serializes tool schemas into a `[TOOLS]` block in the system message
- System prompt instructs: "When you need a tool, respond ONLY with `{"tool": "name", "args": {...}}`"
- `_agenerate` parses response text: success → `AIMessage(content="", tool_calls=[...])`, failure → `AIMessage(content=text)`
- This keeps tool invocations in LangGraph state as proper `ToolMessage` objects with full audit trail in PostgreSQL

*Approach B — Copilot SDK native tool events:*
- Register tools directly with `CopilotClient` via `@define_tool`
- Handle `tool.call` events inside the SDK session
- Return only the final text to LangGraph; tools are invisible to graph state
- Simpler to implement, but loses LangGraph tool-state tracking and audit trail in checkpoints

**Recommendation:** Approach A. The existing `_messages_to_prompt()` is already structured for extension; the codebase has PostgreSQL checkpoints that benefit from complete tool invocation history.

**Detection:** Tools registered, no `tool_calls` present in any `AIMessage` in graph state, no tool execution fires.

**Phase:** MCP-02. This architectural decision must precede graph design.

---

## High Severity Pitfalls

### P3: `MultiServerMCPClient` Async Context Manager Removed in v0.1.0

**What goes wrong:** Pre-0.1.0 examples and many tutorials show `async with MultiServerMCPClient(...) as client:`. This pattern was removed in v0.1.0. The new API uses direct method calls or the `session()` context manager. Using the old pattern raises `AttributeError` or `TypeError` at runtime.

**Why it happens:** Breaking API change between langchain-mcp-adapters releases.

**Consequences:**
- Worker startup fails if initialization uses the old pattern
- LLM-generated code and most online tutorials use the broken pattern

**Prevention:**
```python
# WRONG (pre-0.1.0):
async with MultiServerMCPClient(config) as client:
    tools = await client.get_tools()

# CORRECT (0.1.0+) — direct call:
client = MultiServerMCPClient(config)
tools = await client.get_tools()

# CORRECT (0.1.0+) — explicit session for performance:
async with client.session("mcp-server") as session:
    tools = await session.get_tools()
```

**Detection:** `AttributeError: __aenter__` or `TypeError` on `async with MultiServerMCPClient(...)`.

**Phase:** MCP-01. Pin `langchain-mcp-adapters>=0.1.0` and verify the API pattern on first install.

---

### P4: MCP Client Re-initialized Per arq Job

**What goes wrong:** If `MultiServerMCPClient` is instantiated inside `process_chat()` (the arq job function), a new HTTP connection is established for every job. Under concurrent job load, this can exhaust FastMCP's connection capacity. The tool schema is also re-fetched on every job, even though it never changes at runtime.

**Why it happens:** arq job functions share no state between invocations by default — only the `ctx` dict initialized in `startup()` is shared across job executions within the worker process.

**Consequences:**
- High per-job latency from repeated connection setup
- FastMCP server flooded with `initialize` handshakes under concurrency
- Tool list fetched redundantly on every job

**Prevention:**
Initialize in `startup()` and store in `ctx`:
```python
async def startup(ctx: dict) -> None:
    ...
    from langchain_mcp_adapters.client import MultiServerMCPClient
    ctx["mcp_client"] = MultiServerMCPClient({
        "mcp-server": {
            "url": "http://mcp-server:9000/mcp",
            "transport": "http",
        }
    })
    ctx["mcp_tools"] = await ctx["mcp_client"].get_tools()
```

The `MultiServerMCPClient` with HTTP transport does not hold a persistent connection by default (each `get_tools()` creates an ephemeral session); storing the client instance in `ctx` avoids repeated object creation overhead and allows tool list caching.

**Warning sign:** Latency spikes on first tool call per job; FastMCP logs showing repeated `initialize` handshakes.

**Phase:** MCP-01. Establish this lifecycle pattern before writing any job handler that uses MCP.

---

### P5: Claude Code CLI Subprocess Blocks Async Event Loop

**What goes wrong:** Using `subprocess.run()` or `subprocess.Popen()` (synchronous) inside an `async def` arq job blocks the entire asyncio event loop for the duration of CLI execution. All other queued arq jobs hang. The arq heartbeat to Redis may time out, causing Redis to mark jobs as dead and the worker to restart.

**Prevention:**
```python
# WRONG — blocks event loop:
result = subprocess.run(["claude", "--print", prompt], capture_output=True)

# CORRECT — non-blocking:
proc = await asyncio.create_subprocess_exec(
    "claude", "--print", prompt,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
    env=_build_claude_env(),  # see P6
)
try:
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120.0)
except asyncio.TimeoutError:
    proc.kill()
    await proc.wait()  # reap zombie — do not skip this
    raise RuntimeError("Claude Code CLI timed out after 120s")
```

**Detection:** Worker becomes unresponsive during Claude Code tool calls; other job types stall and time out in Redis.

**Phase:** MCP-03. Mandatory pattern from the first line of the Claude Code handler.

---

### P6: Claude Code CLI Inherits `CLAUDECODE=1` — Nested Session Rejection

**What goes wrong:** When the arq worker is run from within a Claude Code session (common in development), the `CLAUDECODE=1` environment variable is set in the parent process. The Claude Code CLI detects this and refuses to start, printing a "nested Claude Code session" error. The tool always fails in this context.

**Why it happens:** Claude Code sets `CLAUDECODE=1` to prevent recursive self-invocation. The arq worker inherits the full parent environment, including this flag.

**Real-world evidence:** Documented in GitHub issue anthropics/claude-agent-sdk-python#573. A related issue (anthropics/claude-code#18666) shows the subprocess also leaves zombie `claude` processes at 60-70% CPU on repeated failures.

**Consequences:**
- Claude Code tool consistently fails in dev when run from within Claude Code
- Error looks like a permissions or auth failure — misleading
- Zombie processes accumulate on the worker container

**Prevention:**
```python
import os

def _build_claude_env() -> dict[str, str]:
    """Build subprocess env with CLAUDECODE cleared to prevent nested session error."""
    env = os.environ.copy()
    env.pop("CLAUDECODE", None)
    env.pop("CLAUDE_CODE_ENTRYPOINT", None)
    return env
```

Always use `_build_claude_env()` in `create_subprocess_exec()`. Add this utility function to the Claude Code handler module.

**Detection:** Claude subprocess exits immediately with "cannot run inside another Claude Code session."

**Phase:** MCP-03. Add env sanitization before first test run; will save hours of debugging.

---

### P7: `tool_calls` Infinite Loop — Agent Never Terminates

**What goes wrong:** In a ReAct-style LangGraph loop, if the model continuously generates tool calls without ever producing a plain-text final answer, the graph runs until it hits the LangGraph `recursion_limit` (default: 25 steps). With `ChatCopilot` using the prompt-injection approach, a misformatted response or ambiguous termination instruction can cause this.

**Consequences:**
- arq job runs for the full `job_timeout=300s` (5 minutes of spinning)
- N parallel jobs × 300s = runaway Copilot API consumption
- User receives a timeout error with no partial result

**Prevention:**
Add an iteration counter to `AgentState`:
```python
class AgentState(TypedDict):
    ...
    tool_iterations: int  # annotated with operator.add for increment tracking
```

In the `should_continue` routing function:
```python
MAX_TOOL_ITERATIONS = 10

def should_continue(state: AgentState) -> str:
    last = state["messages"][-1]
    if not isinstance(last, AIMessage) or not last.tool_calls:
        return "end"
    if state.get("tool_iterations", 0) >= MAX_TOOL_ITERATIONS:
        return "end"
    return "continue"
```

Also set `recursion_limit` defensively at invoke time:
```python
await graph.ainvoke(state, config={"recursion_limit": 20, ...})
```

**Detection:** Job runs 30+ seconds on simple queries; same tool called repeatedly in state messages.

**Phase:** MCP-02. Bake into graph design from the first iteration — not a retrofit.

---

### P8: Shell Injection via Tool Arguments

**What goes wrong:** Interpolating LLM-generated tool arguments into a shell command string enables command injection. A jailbroken model or a malicious prompt can cause arbitrary code execution on the worker container, which has access to PostgreSQL credentials, Redis, and the GitHub token.

**Real-world evidence:** Multiple CVEs documented in 2025-2026:
- CVE-2025-59536: RCE via malicious Claude Code project configuration files
- CVE-2025-54795: Prompt injection turning Claude against itself
- phoenix.security: Three command injection flaws in Claude Code CLI enabling credential exfiltration

**Prevention:**
- Always use `asyncio.create_subprocess_exec(*args_list)` — the OS kernel handles argument quoting, not the shell
- Never use `shell=True` with any user-controlled or LLM-generated content
- Validate all tool arguments against a Pydantic schema before passing to subprocess
- Run Claude Code with a restricted working directory; consider a separate sandboxed container for untrusted code execution

**Detection:** Only caught by security audit or penetration test. No runtime warning.

**Phase:** MCP-03. Security requirement, not optional. Must be reviewed at phase completion before any deployment.

---

## Medium Severity Pitfalls

### P9: FastMCP `stdio` Transport Incompatible with Docker Multi-Container Setup

**What goes wrong:** FastMCP's default `stdio` transport spawns a subprocess and communicates over stdin/stdout. This only works when the MCP server is a child process of the client. In Docker Compose, `worker` and `mcp-server` are separate containers — they cannot share a process pipe.

**Consequences:**
- `langchain-mcp-adapters` with `stdio` transport fails to connect from `worker` to `mcp-server`
- Failure is at runtime (connection time), not at image build time

**Prevention:**
```python
# mcp_server/main.py
mcp.run(transport="http", host="0.0.0.0", port=9000)
```

```yaml
# docker-compose.yml additions
  mcp-server:
    build: ./mcp_server
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:9000/health || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 5

  worker:
    depends_on:
      mcp-server:
        condition: service_healthy  # worker waits for MCP server
```

Worker `MultiServerMCPClient` config must use `"transport": "http"` and address `http://mcp-server:9000/mcp`.

**Detection:** `BrokenPipeError` or `ConnectionRefusedError` in worker logs at MCP connection time.

**Phase:** MCP-01. Transport selection is a Docker architecture decision made before any code is written.

---

### P10: Tool Name Collisions Across MCP Servers

**What goes wrong:** If multiple MCP servers expose tools with the same name, `get_tools()` returns a flat list where later definitions silently override earlier ones. The wrong tool handler gets called with no error.

**Prevention:**
```python
client = MultiServerMCPClient(
    config,
    tool_name_prefix=True  # tools become "mcp-server__web_search" etc.
)
```

Or use distinct names in FastMCP from the start: `web_search`, `db_query`, `claude_code_run`. Do not use generic names like `search` or `query`.

**Phase:** MCP-01. Establish naming conventions when defining the first MCP tools.

---

### P11: Tavily Sync Client Blocks arq Event Loop

**What goes wrong:** The default `TavilyClient` uses the synchronous `requests` library. Calling it inside an async arq job blocks the entire event loop identically to P5.

**Prevention:**
```python
from tavily import AsyncTavilyClient

# In startup():
ctx["tavily_client"] = AsyncTavilyClient(api_key=os.environ["TAVILY_API_KEY"])

# In handler:
result = await ctx["tavily_client"].search(query, max_results=5)
```

The free tier allows 100 RPM; the production tier allows 1000 RPM. No special rate-limit handling needed for 200-user internal usage, but add error handling for 429 responses.

**Detection:** Event loop stalls during web search; other jobs time out concurrently.

**Phase:** MCP-03. Enforced from the first implementation of the web search tool.

---

### P12: Tavily Response Size Overflows Copilot Model Context Window

**What goes wrong:** Tavily's default search response includes full page content. When injected as a `ToolMessage` into the LangGraph message list and then serialized into `_messages_to_prompt()`, accumulated search results across multiple tool calls can exceed the Copilot model's context window.

**Prevention:**
```python
# Preferred: built-in token limiting
result = await client.search_context(query, max_tokens=3000)

# Alternative: limit results and exclude raw content
results = await client.search(query, max_results=3, include_raw_content=False)
```

Keep each `ToolMessage` content under 2000 tokens. If the Copilot model starts truncating or producing incoherent responses after several tool calls, this is the first thing to investigate.

**Phase:** MCP-03. Apply from the first web search implementation.

---

### P13: `ToolNode` Silently Drops `invalid_tool_calls`

**What goes wrong:** When the Copilot model generates tool call arguments that fail JSON parsing (which is more likely with the prompt-injection approach than with native tool-calling models), LangGraph creates `invalid_tool_calls` on the `AIMessage`. `ToolNode` ignores these entirely — no error is raised, no fallback fires, the graph proceeds as if no tool was requested.

**Why it happens:** `ToolNode` only processes `AIMessage.tool_calls` (valid, parsed calls). `invalid_tool_calls` is a documented field on `AIMessage` but is not handled by `ToolNode`'s default implementation.

**Consequences:**
- Silent tool failures especially likely with prompt-injection approach (P2/Approach A)
- User receives a generic empty response with no indication of failure
- Hard to debug without explicit logging

**Prevention:**
```python
def check_tool_errors(state: AgentState) -> str:
    # Check the message before the last ToolMessages
    for msg in reversed(state["messages"]):
        if isinstance(msg, AIMessage):
            if msg.invalid_tool_calls:
                logger.warning("invalid_tool_calls: %s", msg.invalid_tool_calls)
                return "error_recovery"
            break
    return "continue"
```

Add an explicit error-recovery node that returns a "I had trouble calling the tool, please rephrase" response.

**Phase:** MCP-02. Add to graph design as an explicit error edge from the start.

---

## Minor Pitfalls

### P14: FastMCP Health Check Only Works on HTTP Transport

**What goes wrong:** FastMCP's automatic health check endpoint is transport-dependent — it only exists for `http`/`httpStream` transports. Even with HTTP transport, the default path and configuration may not match Docker's `CMD-SHELL` expectations.

**Prevention:**
Always add an explicit custom health route to FastMCP:
```python
from starlette.requests import Request
from starlette.responses import PlainTextResponse

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")
```

This ensures the health check works regardless of transport configuration changes.

**Phase:** MCP-01.

---

### P15: arq Timeout + Claude Code Zombie Subprocess

**What goes wrong:** The current `WorkerSettings.job_timeout = 300` (5 minutes) applies to all job types. Claude Code tasks that exceed this limit cause arq to mark the job as failed — but the `claude` subprocess may continue running as a zombie on the container, consuming CPU (the documented 60-70% CPU zombie issue from claude-code#18666).

**Prevention:**
- Add `asyncio.wait_for(proc.communicate(), timeout=120)` inside the Claude Code handler (internal timeout shorter than arq's)
- In the `TimeoutError` handler: always call `proc.kill()` then `await proc.wait()` to reap the zombie process
- Consider a dedicated `claude_code` arq function with a higher per-function timeout if 120s is insufficient

**Phase:** MCP-03. Handle on first implementation; do not defer.

---

## The Hardest Problem: Copilot SDK vs. LangGraph Tool Protocol

P1 and P2 together represent the most architecturally significant challenge. This is not a configuration issue — it requires a deliberate design decision before MCP-02 begins.

**The core impedance mismatch:**
- LangGraph `ToolNode` expects: `AIMessage(tool_calls=[{"name": "...", "args": {...}, "id": "..."}])`
- Copilot SDK produces: `response.data.content = "some plain text string"`

**Option comparison:**

| Option | Complexity | Tool state in checkpoints | LangGraph ToolNode works |
|--------|------------|--------------------------|-------------------------|
| Prompt injection + text parsing (Approach A) | Medium | Yes — full `ToolMessage` history | Yes, with custom `_agenerate` parsing |
| Copilot SDK native tool events (Approach B) | Low | No — tools invisible to graph state | No — custom dispatch only |
| Separate OpenAI/Claude model for tool-calling turns | High | Yes | Yes |

**Recommended path:** Approach A (prompt injection + parsing).

Rationale:
- `_messages_to_prompt()` is already structured for extension
- PostgreSQL checkpoints capture complete tool invocation history (valuable for 200-user internal audit)
- Copilot models (Claude Sonnet, GPT-4.1) reliably produce structured JSON with clear prompting
- Avoids adding a second model provider dependency

**Recommended system prompt template for `bind_tools`:**
```
You have access to tools. When you need to use a tool, respond ONLY with valid JSON:
{"tool": "<tool_name>", "args": {<arguments>}}

When you have a final answer, respond with plain text (no JSON).

Available tools:
[TOOL_SCHEMAS_HERE]
```

The JSON-vs-text distinction is the termination condition that prevents P7 (infinite loop).

---

## Phase-Specific Warnings

| Phase | Topic | Likely Pitfall | Mitigation |
|-------|-------|---------------|------------|
| MCP-01 | FastMCP Docker service | `stdio` incompatible with Docker (P9) | Use `http` transport from the start |
| MCP-01 | langchain-mcp-adapters install | Async context manager API removed (P3) | Pin `>=0.1.0`; use `session()` or direct call pattern |
| MCP-01 | arq startup MCP lifecycle | Per-job connection overhead (P4) | Initialize in `startup()`; store in `ctx` |
| MCP-01 | FastMCP health check | Only works on HTTP transport (P14) | Add `@mcp.custom_route("/health")` explicitly |
| MCP-01 | Tool naming | Silent name collisions (P10) | Enable `tool_name_prefix=True`; use distinct names |
| MCP-02 | `bind_tools` in `ChatCopilot` | No implementation exists (P1) | Implement before any graph work |
| MCP-02 | Tool dispatch architecture | No native `tool_calls` from SDK (P2) | Decide Approach A vs B; design graph around the choice |
| MCP-02 | ReAct graph design | Infinite loop risk (P7) | Add `tool_iterations` counter to state; set `recursion_limit` |
| MCP-02 | Tool call error handling | Silent `invalid_tool_calls` drops (P13) | Add explicit error-recovery edge in graph |
| MCP-03 | Claude Code handler | Subprocess blocks event loop (P5) | Use `asyncio.create_subprocess_exec()` always |
| MCP-03 | Claude Code handler | Nested session env var (P6) | Unset `CLAUDECODE` in subprocess env |
| MCP-03 | Claude Code handler | Shell injection (P8) | List args only; never `shell=True`; schema-validate args |
| MCP-03 | Claude Code handler | Zombie subprocess on timeout (P15) | `proc.kill()` + `await proc.wait()` in `TimeoutError` handler |
| MCP-03 | Web search tool | Sync Tavily client (P11) | Use `AsyncTavilyClient`; init in `startup()` |
| MCP-03 | Web search tool | Response size overflow (P12) | Use `search_context(max_tokens=3000)` |

---

## Sources

- [LangChain Discussion #26146: Add bind_tools to custom BaseChatModel](https://github.com/langchain-ai/langchain/discussions/26146)
- [LangGraph Issue #5135: bind_tools raises NotImplementedError](https://github.com/langchain-ai/langgraph/issues/5135)
- [LangChain Issue #21479: bind_tools NotImplementedError with ChatOllama (non-OpenAI model)](https://github.com/langchain-ai/langchain/issues/21479)
- [langchain-mcp-adapters: MultiServerMCPClient — DeepWiki](https://deepwiki.com/langchain-ai/langchain-mcp-adapters/2.1-multiservermcpclient)
- [langchain-mcp-adapters — GitHub](https://github.com/langchain-ai/langchain-mcp-adapters)
- [langchain-mcp-adapters — PyPI](https://pypi.org/project/langchain-mcp-adapters/)
- [FastMCP Server documentation](https://gofastmcp.com/servers/server)
- [FastMCP Server lifecycle — DeepWiki](https://deepwiki.com/jlowin/fastmcp/2.1-server-lifecycle-and-initialization)
- [arq documentation v0.27.0](https://arq-docs.helpmanual.io/)
- [arq + SQLAlchemy: async lifecycle patterns](https://wazaari.dev/blog/arq-sqlalchemy-done-right)
- [anthropics/claude-agent-sdk-python Issue #573: CLAUDECODE=1 nested session](https://github.com/anthropics/claude-agent-sdk-python/issues/573)
- [anthropics/claude-code Issue #18666: subprocess hang and zombie processes](https://github.com/anthropics/claude-code/issues/18666)
- [Check Point Research: RCE via Claude Code project files (CVE-2025-59536)](https://research.checkpoint.com/2026/rce-and-api-token-exfiltration-through-claude-code-project-files-cve-2025-59536/)
- [phoenix.security: Command injection flaws in Claude Code CLI](https://phoenix.security/critical-ci-cd-nightmare-3-command-injection-flaws-in-claude-code-cli-allow-credential-exfiltration/)
- [Tavily rate limits documentation](https://docs.tavily.com/documentation/rate-limits)
- [Tavily Python SDK — PyPI](https://pypi.org/project/tavily-python/0.6.0/)
- [Python asyncio subprocess guide](https://docs.python.org/3/library/asyncio-dev.html)
- [LangGraph Discussion #1725: GraphRecursionError in tool loops](https://github.com/langchain-ai/langgraph/discussions/1725)
- [LangGraph Issue #5548: ReAct agent recursion limit not thrown](https://github.com/langchain-ai/langgraph/issues/5548)
- [LangChain Issue #33504: invalid_tool_calls dropped by ToolNode](https://github.com/langchain-ai/langchain/issues/33504)
- [github-copilot-sdk PyPI](https://pypi.org/project/github-copilot-sdk/)
- [Docker Compose inter-container networking](https://dohost.us/index.php/2025/07/28/networking-in-docker-compose-inter-container-communication/)
