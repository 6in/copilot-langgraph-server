# Feature Landscape: v5.0 Agent Tool Platform

**Domain:** MCP-based tool execution layer for LangGraph multi-agent chat app
**Researched:** 2026-04-09
**Confidence:** HIGH (LangGraph/FastMCP docs verified; tool patterns from official sources)

---

## Context: What Already Exists

The following are built and must NOT be re-implemented:

| Component | Location | Relevance to v5.0 |
|-----------|----------|-------------------|
| `OrchestratorGraph` | `app/orchestrator/graph.py` | SubAgent nodes called via `agent.run()` — needs tool node injection |
| `SubAgent.run()` | `app/orchestrator/agent.py` | Currently calls `llm.ainvoke()` directly — v5.0 extends with `bind_tools` |
| `SubAgentRegistry` | `app/orchestrator/agent.py` | Registry knows agents, not tools — tool config is a new concern |
| `ScriptBackend` | `app/orchestrator/script_backend.py` | Loads `tools/*.py` with INPUT_SCHEMA validation — MCP replaces this for remote tools |
| `is_select_only()` | `app/jobs/handlers/iframe_rpc_handler.py` | SELECT-only guard, production-tested in v4.0 — reuse directly |
| `_json_default()` | `app/jobs/handlers/iframe_rpc_handler.py` | `datetime`/`Decimal` serializer — copy into MCP tool |
| `db_pools` context | `app/jobs/handlers/iframe_rpc_handler.py` | psycopg_pool already wired in arq worker ctx |

---

## Table Stakes

Features that must work for v5.0 to be usable. Without these the agent tool platform does not exist.

### 1. LangGraph bind_tools + ToolNode Loop

**What it is:** The core ReAct pattern. An LLM node with tools bound to it decides whether to call a tool or return a final answer. `ToolNode` executes the tool call; the graph loops back to the LLM until `tool_calls` is empty.

**Loop behavior (HIGH confidence — verified from LangGraph prebuilt docs and community reports):**

```
[agent_node] → LLM responds with tool_calls in AIMessage
    ↓  tools_condition returns "tools"
[tool_node]  → executes each tool_call, appends ToolMessage to state
    ↓
[agent_node] → LLM sees tool results, may call more tools or return final answer
    ↓  tools_condition returns END (last AIMessage has no tool_calls)
[END]
```

- `tools_condition` is a prebuilt helper in `langgraph.prebuilt`. It checks if the last `AIMessage` in state has non-empty `tool_calls`. If yes, routes to `"tools"`. If no, routes to `END`.
- Each agent→tool→agent round-trip consumes 2 steps against `recursion_limit`.
- LangGraph's default `recursion_limit` is **25** (confirmed from multiple issue reports and community discussions). This allows ~12 tool-call rounds at default.
- For this application's tools (web search, DB query), a `recursion_limit` of 10 (set in `graph.ainvoke(config={"recursion_limit": 10})`) allows up to 5 tool-call rounds — sufficient for single-topic queries.
- Known risk: LLM can get stuck calling the same tool repeatedly (duplicate tool_calls until recursion limit fires). Mitigations: system prompt instruction ("use each tool at most once per query"), or catching `GraphRecursionError` and returning a graceful error message.

**Integration point — SubAgent refactor required:**

Current `SubAgent.run()` calls `llm.ainvoke()` directly and returns `AgentState`. For tool-enabled agents, this must change. Two options:

Option A (recommended): Compile an inner `StateGraph` per tool-enabled agent at startup, wrapping the LLM+ToolNode loop. `SubAgent.run()` calls `inner_graph.ainvoke()`.

Option B: Use `create_react_agent(llm, tools)` from `langgraph.prebuilt` as the inner graph. Simpler but less customizable.

The `OrchestratorGraph` structure (`router → agent_node → END`) does not change. Only what happens inside the agent node changes.

**Complexity:** High — requires refactoring `SubAgent.run()` and threading MCP tool handles into per-agent graph compilation. The outer `OrchestratorGraph` topology is stable.

---

### 2. FastMCP Server — Docker Service

**What it is:** A Python process serving MCP tools over HTTP (streamable-http transport), defined in its own `mcp/` directory, running as a new Docker Compose service.

**Why a separate service:** The MCP server runs independently so tools can be updated without restarting the FastAPI app or arq worker. HTTP transport means both the `api` and `worker` containers can connect to it.

**FastMCP @mcp.tool basics (HIGH confidence — verified from gofastmcp.com/servers/tools):**

```python
from fastmcp import FastMCP

mcp = FastMCP("tool-server")

@mcp.tool(timeout=30)
async def web_search(query: str, max_results: int = 5) -> dict:
    """Search the web for current information.
    Returns a dict with 'answer' (summary) and 'sources' (list of URLs)."""
    ...

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8001)
```

Key constraints on `@mcp.tool`:
- Input schema is **auto-generated from type annotations**. Every parameter must be explicitly typed — no `*args`/`**kwargs` (raises an error at registration time).
- **Docstring becomes the tool description** shown to the LLM for tool selection. Write it to guide the model.
- `timeout` parameter is built-in — an MCP error is returned automatically if exceeded. Set this lower than the `subprocess` timeout for CLI tools.
- Return type `dict` produces structured content (JSON). `str` produces TextContent. Use `dict` for machine-readable results.
- Error handling: raise `ToolError` for expected failures (message shown to LLM). Raise standard exceptions for unexpected failures. No built-in error decorator exists — wrap each tool body in try/except.
- Optional parameters use Python defaults; parameters without defaults are required.

**Complexity:** Medium — FastMCP is well-documented. Main effort is Docker service wiring and per-tool dependency injection (API keys, DB pool).

---

### 3. langchain-mcp-adapters Client

**What it is:** `langchain-mcp-adapters` converts MCP tool definitions into LangChain `BaseTool` objects that can be passed to `bind_tools()`. `MultiServerMCPClient` connects to one or more MCP servers over stdio or HTTP.

**Pattern (MEDIUM confidence — from official github.com/langchain-ai/langchain-mcp-adapters):**

```python
from langchain_mcp_adapters.client import MultiServerMCPClient

client = MultiServerMCPClient({
    "tools": {
        "transport": "http",
        "url": "http://mcp:8001/mcp",
    }
})
tools = await client.get_tools()
llm_with_tools = llm.bind_tools(tools)
```

- `get_tools()` returns a list of LangChain `BaseTool` — these are compatible with `ToolNode([...])`.
- Transport must be `"http"` (streamable-http) for the Docker service scenario. `"stdio"` is only for local CLI subprocesses.
- The MCP client session must stay open during all tool calls. Manage via async context manager or application startup/shutdown lifecycle (same pattern as `db_pools` in the arq worker context).

**Complexity:** Medium — the adapter library handles protocol details. Main complexity is lifecycle: create `MultiServerMCPClient` once at startup, share the `tools` list across agents that need it.

---

### 4. config.yaml Tool-to-Agent Routing

**What it is:** A YAML config file that declares which tools exist, which are enabled, and which agents can use which tools. This decouples agent configuration from server topology.

**Is this a known pattern?** Partially. Google MCP Toolbox uses multi-document YAML (`kind: source` / `kind: tool` blocks). For this project, a flat single-document schema is sufficient and simpler:

```yaml
# mcp/config.yaml
server_url: "http://mcp:8001/mcp"

tools:
  web_search:
    description: "Real-time web search via Tavily"
    enabled: true
  db_query:
    description: "Read-only PostgreSQL SELECT query"
    enabled: true
  claude_code:
    description: "Execute Claude Code CLI"
    enabled: false  # disabled by default; enable per-agent after spike

agent_tools:
  research-assistant:
    - web_search
  sql-analyst:
    - db_query
  code-reviewer:
    - claude_code
    - web_search
```

**Behavior:** At startup (FastAPI lifespan or arq worker startup), a new `ToolRegistry` class reads `config.yaml`, loads all `enabled: true` tools from the MCP server via `MultiServerMCPClient`, and returns per-agent filtered tool lists. Only `agent_tools` entries are given to each `SubAgent` — no agent gets tools it has not been explicitly granted.

**Integration point:** `SubAgentRegistry` initializes `SubAgent` objects with a `tools: list[BaseTool]` parameter (currently absent). `ToolRegistry` provides this list based on the agent name from `config.yaml`.

**Complexity:** Low for the config format; Medium for the new `ToolRegistry` class and `SubAgent` constructor extension.

---

## Differentiators

Features that make the tool platform genuinely useful beyond the minimum viable wiring.

### 5. Web Search Tool (Tavily)

**What it is:** An MCP tool wrapping the Tavily Search API that returns structured web search results for real-time information retrieval.

**Response shape (HIGH confidence — from docs.tavily.com):**

```json
{
  "query": "...",
  "answer": "LLM-synthesized answer (when include_answer=true)",
  "results": [
    {
      "title": "Page title",
      "url": "https://...",
      "content": "Extracted text snippet (~200 words)",
      "score": 0.97
    }
  ],
  "response_time": 1.2
}
```

**Best practice for LLM consumption:** Use `include_answer=True` — the `answer` field is a pre-synthesized summary the LLM can directly cite, avoiding the need to parse raw snippets. For the `results` array, pass `title + url + content` only; do NOT pass `raw_content` (full HTML/markdown — too large, increases latency and token usage). Recommended MCP tool return shape:

```python
return {
    "answer": response["answer"],   # direct summary for the LLM
    "sources": [                    # for citation in output
        {"title": r["title"], "url": r["url"], "snippet": r["content"]}
        for r in response["results"]
    ]
}
```

**Configuration:**
- `TAVILY_API_KEY` environment variable → Docker Compose environment secret
- Default: `max_results=5`, `search_depth="basic"`, `include_answer=True`
- Cost: free tier is 1000 credits/month. `"basic"` depth = 1 credit/search; `"advanced"` = 2 credits.

**Complexity:** Low — Tavily has an official Python SDK (`tavily-python`). Response shape is clean and well-documented.

---

### 6. DB Query Tool (PostgreSQL SELECT-only)

**What it is:** An MCP tool that executes SELECT-only SQL against the application's PostgreSQL instance, returning rows as JSON.

**Reuse opportunity (HIGH confidence — code exists in codebase):**
- `is_select_only()` from `app/jobs/handlers/iframe_rpc_handler.py` — strips comments, rejects multi-statement, checks first token. Reuse as-is.
- `_json_default()` from the same file — serializes `datetime` → ISO 8601, `Decimal` → `float`. Reuse as-is.
- Recommended: extract both to `app/utils/sql_safety.py` so both the iframe handler and the MCP tool can import them.

**Key behaviors:**
- Strip SQL comments before check (already in `is_select_only`)
- Reject multi-statement input (semicolon in body after strip)
- Accept only `SELECT` and `WITH` as first token
- Enforce row count limit (add `FETCH FIRST 100 ROWS ONLY` if not present, or post-fetch slice)
- Pool connection from `DATABASE_URL` environment variable

**MCP tool signature:**

```python
@mcp.tool(timeout=30)
async def db_query(sql: str) -> dict:
    """Execute a read-only SQL SELECT query against the application PostgreSQL database.
    Returns {'rows': [...]} with results as list of dicts.
    Only SELECT and WITH statements are accepted."""
```

**Schema exposure for LLM:** The LLM needs table/column names to write useful queries. Options:
- (A) Include schema documentation in the agent's system prompt — simplest, works now.
- (B) Add a separate `db_schema()` MCP tool returning `INFORMATION_SCHEMA` data — more powerful but adds a tool-call round-trip.
- Recommendation: start with (A) for MVP; (B) is a v5.1 enhancement.

**Complexity:** Low — logic already exists and is production-tested. Main work is extracting shared utils and wiring pool management in the MCP server.

---

### 7. Claude Code CLI Tool

**What it is:** An MCP tool that executes the `claude` CLI as an async subprocess, sends a prompt non-interactively, and captures structured JSON output.

**Communication pattern (MEDIUM confidence — from Anthropic Agent SDK docs and GitHub issue #771):**

```python
import asyncio, json
from fastmcp import ToolError

@mcp.tool(timeout=150)
async def claude_code(prompt: str, working_directory: str = "/tmp") -> dict:
    """Execute a Claude Code task non-interactively.
    Returns {'response': '...', 'exit_code': 0}."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "claude", "--print", "--output-format", "json",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=working_directory,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(input=prompt.encode()),
            timeout=120,
        )
    except asyncio.TimeoutError:
        proc.kill()
        raise ToolError("Claude Code timed out after 120 seconds")
    if proc.returncode != 0:
        raise ToolError(f"claude exited {proc.returncode}: {stderr.decode()[:500]}")
    return json.loads(stdout)
```

**Key constraints and risks:**
- `claude` CLI must be installed inside the MCP Docker container. This requires a custom Dockerfile with Node.js + `npm install -g @anthropic-ai/claude-code`. Non-trivial image build.
- `--output-format json` produces structured output; `--print` disables interactive mode. Verify exact output format against the installed CLI version before implementing.
- The MCP `timeout` (150s) must exceed the subprocess `asyncio.wait_for` timeout (120s) plus a small buffer.
- GitHub issue #771 confirms Python subprocess works correctly for spawning Claude Code. Node.js spawning has issues, but that is not relevant here.
- The `working_directory` parameter scopes what files Claude Code can read/modify. Set carefully — do not default to the project root without explicit user intent.
- stdout format: may be JSON-lines (one object per line) or a single JSON object. Must be verified against the installed CLI version before the tool can be finalized.

**Recommendation: spike-first.** Build a standalone script that installs `claude` in Docker and captures its output format before integrating into the MCP server. Mark as `enabled: false` in `config.yaml` until the spike is done.

**Complexity:** High — Docker image build, output format verification, timeout layering, error handling. Do not include in initial MVP phases; implement after web search and DB query tools are stable.

---

## Anti-Features

Do NOT build these in v5.0.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Give all tools to all agents | Creates LLM confusion, wastes tokens on irrelevant tools, security risk (any agent gets DB access) | `agent_tools` allowlist in `config.yaml` — per-agent explicit grant |
| Streaming tool results over SSE | Copilot SDK does not support streaming (confirmed Out of Scope in PROJECT.md) | Return complete result after tool loop finishes |
| Tool result caching | Premature optimization; Tavily and db_query are fast enough for 200-user scale | Add in v5.1 if profiling shows a need |
| Forced parallel tool execution | LangGraph `ToolNode` supports parallel tool calls if LLM emits multiple `tool_calls` in one message, but Copilot SDK behavior with parallel calls is unverified | Let `ToolNode` handle it automatically; do not force it |
| Re-implementing is_select_only | Already production-tested in v4.0 | Import from `iframe_rpc_handler` or extract to `app/utils/sql_safety.py` |
| MCP tool for Copilot AI calls | Copilot SDK is already in `app/providers/copilot.py` — wrapping it in MCP adds a round-trip for no gain | Call `ChatCopilot` directly from `SubAgent`; MCP is for external tools only |

---

## Feature Dependencies

```
FastMCP Server (Docker service)
    ↑ required by
langchain-mcp-adapters Client (MultiServerMCPClient)
    ↑ required by
SubAgent bind_tools + ToolNode refactor
    ↑ required by
Web Search Tool / DB Query Tool / Claude Code Tool

config.yaml Tool Registry
    ↑ required by
Per-agent tool filtering (agent_tools mapping)
    ↑ feeds into
SubAgent constructor (tools: list[BaseTool])

is_select_only() + _json_default() (existing, v4.0)
    ↑ reused by
DB Query Tool (import from shared utils)
```

---

## MVP Recommendation

Build in this order:

1. **FastMCP Server + stub tool** — proves the Docker service architecture works; `MultiServerMCPClient.get_tools()` returns LangChain tools. A no-op `ping` tool suffices.
2. **LangGraph bind_tools integration in one SubAgent** — `research-assistant` gets tool support; validates the inner `StateGraph`, `ToolNode`, `tools_condition`, `recursion_limit=10`, and error handling.
3. **Web Search Tool (Tavily)** — highest value, lowest complexity, proves end-to-end tool execution in production.
4. **config.yaml Tool Registry** — enables per-agent tool control without code changes; needed before adding more tools.
5. **DB Query Tool** — most logic already exists; low risk; can reuse v4.0 SQL safety code.
6. **Claude Code CLI Tool** — do a spike first (Docker image + output format). Implement after the other tools are stable.

**Defer to v5.1:** Claude Code tool (spike-first), tool result caching, DB schema discovery tool.

---

## Complexity Summary

| Feature | Complexity | Primary Risk |
|---------|------------|-------------|
| FastMCP Server (Docker service) | Medium | Container networking, lifecycle management |
| langchain-mcp-adapters client | Medium | Session lifecycle in async context |
| LangGraph bind_tools + ToolNode refactor | High | SubAgent.run() rewrite, recursion_limit tuning, OrchestratorGraph compat |
| config.yaml Tool Registry | Medium | New ToolRegistry class, SubAgent constructor extension |
| Tavily web search tool | Low | API key management, credit cost awareness |
| DB query tool | Low | Extract shared utils, pool wiring in MCP server |
| Claude Code CLI tool | High | Docker image build, output format verification, timeout layering |

---

## Sources

- LangGraph ToolNode + tools_condition pattern: [Software Mansion — Building Agents with LangGraph Part 2](https://swmansion.com/blog/building-agents-with-langgraph-part-2-4-adding-tools-a7955432c220)
- LangGraph recursion_limit default=25: [LangGraph GRAPH_RECURSION_LIMIT docs](https://docs.langchain.com/oss/python/langgraph/errors/GRAPH_RECURSION_LIMIT), confirmed in [Discussion #1725](https://github.com/langchain-ai/langgraph/discussions/1725) and [Issue #6731](https://github.com/langchain-ai/langgraph/issues/6731)
- FastMCP @mcp.tool: [gofastmcp.com/servers/tools](https://gofastmcp.com/servers/tools) — HIGH confidence, official docs
- langchain-mcp-adapters MultiServerMCPClient: [github.com/langchain-ai/langchain-mcp-adapters](https://github.com/langchain-ai/langchain-mcp-adapters) — MEDIUM confidence
- Tavily response shape and best practices: [docs.tavily.com](https://docs.tavily.com/documentation/api-reference/endpoint/search) — HIGH confidence, official API reference
- Claude Code CLI subprocess from Python: [Anthropic Agent SDK Python docs](https://platform.claude.com/docs/en/agent-sdk/python), [GitHub issue #771 claude-code](https://github.com/anthropics/claude-code/issues/771) — MEDIUM confidence
- Config-driven tool routing patterns: [Google MCP Toolbox Codelabs](https://codelabs.developers.google.com/agentic-rag-toolbox-cloudsql), [teddynote-lab/langgraph-mcp-agents](https://github.com/teddynote-lab/langgraph-mcp-agents) — MEDIUM confidence
