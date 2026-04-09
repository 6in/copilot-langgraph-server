# Architecture: v5.0 Agent Tool Platform — MCP Integration

**Project:** Copilot LangGraph Chat
**Milestone:** v5.0 Agent Tool Platform
**Researched:** 2026-04-09
**Confidence:** HIGH (existing code read directly; library APIs verified via official sources)

---

## Executive Summary

v5.0 adds MCP-based tool execution to the existing OrchestratorGraph. The core integration is:

1. A new `mcp-server` Docker service (FastMCP 3.x, streamable-http transport) exposes tools as MCP methods.
2. The `worker` service connects via `langchain-mcp-adapters` (v0.2.2) `MultiServerMCPClient` — one client instance per-job, scoped inside `OrchestratorHandler.handle()`.
3. `OrchestratorGraph` gains a new `AgentNode` + `ToolNode` pair inside each agent node, replacing the current single `SubAgent.run()` call with a ReAct loop.
4. `RouterNode` is unchanged. Tool execution runs after routing, inside the selected agent.

The constraint driving all decisions: arq workers are short-lived async functions, not long-running servers. Connection lifecycle must be per-job (create in handle(), close before return). Persistent sessions across jobs are not feasible without shared state that arq does not provide.

---

## Component Diagram (ASCII)

```
Browser
  |
  | HTTP/SSE
  v
[FastAPI :8000]
  |  POST /api/chat  -->  Redis (arq queue)
  |  GET  /api/job/:id/stream  <--  Redis (result store)
  |
  v
[arq Worker]
  |
  |  TASK_HANDLERS["orchestrator"]
  v
[OrchestratorHandler]
  |
  |  per-job: MultiServerMCPClient({"mcp": {transport, url}})
  |           .get_tools()  -->  list[BaseTool]
  |
  v
[OrchestratorGraph]  (LangGraph StateGraph)
  |
  |  RouterNode  (keyword to LLM, unchanged)
  |      |
  |      v  (conditional edges by agent name)
  |  [AgentNode_1]  [AgentNode_2]  ...  [fallback]
  |      |
  |      |  llm.bind_tools(mcp_tools)
  |      |  "agent" node  ->  conditional ->  "tools" node  ->  back to "agent"
  |      |  (ReAct loop until no more tool_calls)
  |      |
  |      v
  |    output
  |
  v
  result  -->  Redis (job_store.save_result)  -->  SSE notification

[mcp-server :8001]  (FastMCP, streamable-http, Docker internal only)
  |
  |  /mcp  endpoint
  |
  +--  tool: web_search     -->  Tavily API (external HTTP)
  +--  tool: db_query       -->  PostgreSQL (read-only, is_select_only guard)
  +--  tool: claude_code    -->  subprocess: claude-code CLI
```

Docker network: all services on the default Compose network.
Worker reaches mcp-server at `http://mcp-server:8001/mcp`.

---

## Transport Decision: streamable-http (not stdio, not SSE)

| Transport | Viable for Docker? | Why |
|-----------|-------------------|-----|
| `stdio` | NO | Requires subprocess spawn from worker. Breaks Docker service isolation. Cannot reuse across tool calls in same job. |
| `sse` | Partially | SSE transport is legacy in MCP spec. Requires GET + POST pair. Session-affinity issues with multiple workers. |
| `streamable-http` | YES (recommended) | Single HTTP endpoint (`/mcp`). Worker connects over Docker internal DNS (`http://mcp-server:8001/mcp`). Stateless mode (`stateless_http=True`) eliminates session-affinity issues across multiple worker replicas. Official FastMCP recommendation for server deployments. |

FastMCP server config:
```python
# mcp_server/main.py
mcp.run(transport="streamable-http", host="0.0.0.0", port=8001)
# OR for stateless (preferred for multi-worker):
app = mcp.http_app(stateless_http=True)
```

MultiServerMCPClient config (in worker):
```python
MultiServerMCPClient({
    "mcp": {
        "transport": "streamable_http",
        "url": "http://mcp-server:8001/mcp"
    }
})
```

---

## MCP Client Lifecycle: Per-Job (not persistent)

**Decision:** Create and discard `MultiServerMCPClient` inside each `OrchestratorHandler.handle()` call.

**Rationale:**
- arq workers are stateless async functions. The `ctx` dict survives across jobs (worker process lifetime), but storing an open HTTP session in `ctx` risks connection leaks if a job fails mid-tool-call.
- `MultiServerMCPClient` with streamable-http transport is lightweight — each `.get_tools()` call does one HTTP round-trip to list tools, then individual tool calls do one HTTP request each. No persistent WebSocket.
- Per-job scope matches the existing pattern for `AsyncPostgresSaver` (created fresh per job in `OrchestratorHandler`).
- If performance profiling later shows per-job client creation is a bottleneck, migrate to a persistent client stored in `ctx["mcp_client"]` during `startup()`. But start simple.

Pattern:
```python
# Inside OrchestratorHandler.handle()
from langchain_mcp_adapters.client import MultiServerMCPClient

mcp_url = os.getenv("MCP_SERVER_URL", "http://mcp-server:8001/mcp")
client = MultiServerMCPClient({"mcp": {"transport": "streamable_http", "url": mcp_url}})
tools = await client.get_tools()
graph = build_orchestrator_graph(registry, github_token, tools=tools, checkpointer=checkpointer)
result = await graph.ainvoke(initial, config=config)
```

Note on async context manager: langchain-mcp-adapters v0.2.2 (March 2026) may or may not support `async with MultiServerMCPClient(...) as client:` — v0.1.0 explicitly removed this. Verify against current README on install. Fallback: direct instantiation with no context manager (tools are loaded before graph runs, no cleanup needed for stateless HTTP transport).

---

## OrchestratorGraph Changes: Where bind_tools Goes

### Current flow (v4.0)
```
RouterNode -> SubAgent.run() -> END
```
`SubAgent.run()` calls `self._llm.ainvoke(messages)` — single LLM call, no tool loop.

### New flow (v5.0)
```
RouterNode -> AgentNode (ReAct loop: llm.bind_tools -> ToolNode -> llm -> ...) -> END
```

**Where bind_tools happens:** Inside each SubAgent's internal ReAct graph, not in RouterNode.

Two architectural options were evaluated:

**Option A — Tool-aware SubAgent (recommended)**
Each `SubAgent` builds its own mini-graph with `llm.bind_tools(tools)` + `ToolNode`. The outer `OrchestratorGraph` stays unchanged (RouterNode still routes to `agent.run()`). `tools` is injected at graph-build time.

Benefits:
- RouterNode is untouched (low-risk change)
- Each agent can receive a filtered tool subset if needed
- Existing `SubAgent.run()` interface preserved for tool-free agents (backward compatible)

**Option B — Global ToolNode in OrchestratorGraph**
Add a shared ToolNode after all agent nodes at the outer graph level.

Drawback: All agents share the same tool set. Cannot give DB query only to data agents. Makes the graph structure more complex and harder to extend per-agent.

**Recommendation: Option A.**

Mini-graph inside SubAgent (pseudocode):
```python
class SubAgent:
    def __init__(self, ..., tools: list | None = None):
        self._tools = tools or []
        base_llm = ChatCopilot(model=model, github_token=github_token)
        self._llm = base_llm.bind_tools(self._tools) if self._tools else base_llm

    async def run(self, state: AgentState) -> AgentState:
        if self._tools:
            return await self._run_with_tools(state)
        # existing single-call path (backward compat)
        messages = [SystemMessage(content=self._system_prompt), HumanMessage(content=state["input"])]
        response = await self._llm.ainvoke(messages)
        return {"output": response.content, "agent_name": self.name, "messages": [...]}

    async def _run_with_tools(self, state: AgentState) -> AgentState:
        from langgraph.prebuilt import ToolNode
        from langgraph.graph import StateGraph, MessagesState, END

        def should_continue(s):
            return "tools" if s["messages"][-1].tool_calls else END

        tool_node = ToolNode(self._tools)
        g = StateGraph(MessagesState)
        g.add_node("agent", self._call_llm)
        g.add_node("tools", tool_node)
        g.set_entry_point("agent")
        g.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
        g.add_edge("tools", "agent")
        mini_graph = g.compile()
        result = await mini_graph.ainvoke({"messages": [SystemMessage(...), HumanMessage(...)]})
        final_content = result["messages"][-1].content
        return {"output": final_content, "agent_name": self.name, "messages": [...]}
```

The ReAct loop runs inside the agent node. The outer `AgentState` TypedDict requires no changes — the agent node still returns `{output, agent_name, messages}`.

---

## Tool Execution Isolation: In-Process vs Subprocess

| Tool | Where Runs | Isolation Approach |
|------|------------|-------------------|
| `web_search` | mcp-server process, calls Tavily HTTP API | Network isolation sufficient. Tavily is external read-only API. |
| `db_query` | mcp-server process, connects to postgres | `is_select_only` guard (already proven in iframe-rpc). Single PostgreSQL user with SELECT-only grants is the correct defense-in-depth. |
| `claude_code` | subprocess spawned from mcp-server | `subprocess.run(["claude", ...], timeout=120, capture_output=True)`. mcp-server container has no write access to host filesystem unless explicitly mounted. |

**Security configuration:**
- mcp-server must NOT mount `~/.copilot_sdk` volume (avoid token leak via claude_code tool).
- claude_code tool should run in a restricted working directory (e.g., `/tmp/claude_sandbox`).
- db_query should connect as a PostgreSQL read-only role, not the `postgres` superuser. Create a `mcp_readonly` role during initdb.
- mcp-server port 8001 must NOT be exposed to the host in docker-compose (omit `ports:` mapping). Worker reaches it via Docker internal DNS only.

---

## New vs Modified Components

### New Files

| Path | Type | Description |
|------|------|-------------|
| `mcp_server/main.py` | New service entrypoint | FastMCP app definition, tool registrations, `mcp.run()` |
| `mcp_server/tools/web_search.py` | New | `@mcp.tool` Tavily API wrapper |
| `mcp_server/tools/db_query.py` | New | `@mcp.tool` PostgreSQL SELECT with `is_select_only` guard |
| `mcp_server/tools/claude_code.py` | New | `@mcp.tool` subprocess claude CLI wrapper |
| `mcp_server/requirements.txt` | New | `fastmcp`, `tavily-python`, `psycopg[binary]` |
| `mcp_server/Dockerfile` | New | `python:3.12-slim`, install requirements |
| `config/mcp_tools.yaml` | New (optional) | Tool-to-agent allowlist mapping |
| `docker/initdb/02-mcp-readonly-role.sql` | New | CREATE ROLE mcp_readonly, GRANT SELECT |

### Modified Files

| Path | Change | Risk |
|------|--------|------|
| `docker-compose.yml` | Add `mcp-server` service. Add `MCP_SERVER_URL` env to `worker`. | LOW — additive |
| `app/orchestrator/agent.py` | `SubAgent.__init__` accepts optional `tools` param. Add `_run_with_tools()` path. | MEDIUM — core class, must preserve backward compat for tool-free agents |
| `app/orchestrator/graph.py` | `build_orchestrator_graph()` accepts `tools` param, passes to SubAgent constructors | LOW — signature extension only |
| `app/jobs/handlers/orchestrator_handler.py` | Create MCP client, load tools, pass to `build_orchestrator_graph` | MEDIUM — job lifecycle change |
| `app/providers/copilot.py` | Implement `bind_tools()` if Copilot SDK supports function calling — HIGH RISK, see below | HIGH — may require deep SDK research |
| `pyproject.toml` | Add `langchain-mcp-adapters>=0.2.2` | LOW |

### Unchanged Files (confirmed)

- `app/orchestrator/state.py` — `AgentState` TypedDict unchanged
- `app/orchestrator/registry.py` — `SubAgentRegistry` unchanged
- `app/orchestrator/context.py` — `RPCContext` unchanged
- `app/api/` — all API routes unchanged
- `app/jobs/handlers/langgraph_handler.py` — simple chat unchanged
- `app/jobs/handlers/debate_handler.py` — debate unchanged
- `app/jobs/handlers/iframe_rpc_handler.py` — iframe RPC unchanged
- `app/jobs/worker.py` — only env var read addition, no structural change

---

## Data Flow: Tool-Enabled Request

```
1. User sends message via React UI
2. POST /api/chat {task_type: "orchestrator", prompt: "...", ...}
3. FastAPI enqueues arq job -> Redis
4. arq worker picks up job -> OrchestratorHandler.handle()
5. OrchestratorHandler:
   a. SubAgentRegistry.load() (disk scan, as today)
   b. MultiServerMCPClient({"mcp": {streamable_http, url}})  [NEW]
   c. client.get_tools() -> [web_search, db_query, claude_code]  [NEW]
   d. build_orchestrator_graph(registry, github_token, tools=tools, checkpointer)  [MODIFIED]
   e. graph.ainvoke(initial_state)
6. OrchestratorGraph:
   a. RouterNode: keyword -> LLM -> picks agent name (UNCHANGED)
   b. Conditional edge -> selected AgentNode
7. AgentNode (SubAgent._run_with_tools):  [NEW PATH]
   a. llm.bind_tools(tools).invoke(messages)
   b. If tool_calls: route to ToolNode
   c. ToolNode: dispatch tool call -> HTTP POST to mcp-server:8001/mcp
   d. mcp-server executes tool (Tavily / pg / subprocess)
   e. Tool result injected as ToolMessage into messages
   f. Loop back to llm.invoke
   g. When no tool_calls: route to END, return output
8. OrchestratorHandler saves result -> Redis
9. SSE notification -> frontend
```

---

## Docker Compose Addition

```yaml
services:
  mcp-server:
    build:
      context: ./mcp_server
      dockerfile: Dockerfile
    environment:
      - TAVILY_API_KEY=${TAVILY_API_KEY}
      - DATABASE_URL=postgresql://mcp_readonly:readonly_password@postgres:5432/postgres?sslmode=disable
    # NO ports: mapping -- internal network only
    depends_on:
      postgres:
        condition: service_healthy

  worker:
    # existing config unchanged, add to environment:
    environment:
      - MCP_SERVER_URL=http://mcp-server:8001/mcp
      # ... existing vars unchanged
    depends_on:
      # existing deps +
      mcp-server:
        condition: service_started
```

All services share the default Compose bridge network. Worker reaches mcp-server via hostname `mcp-server` at port 8001. mcp-server reaches postgres via hostname `postgres`.

---

## Build Order (Phase Sequencing)

Components have strict dependencies:

```
Phase 1: mcp-server scaffold  [NO DEPS]
  - FastMCP Dockerfile + docker-compose service entry
  - One stub tool: web_search (Tavily)
  - Expose port temporarily for local curl testing
  - Deliverable: curl http://localhost:8001/mcp returns MCP response

Phase 2: Worker MCP client wiring  [DEPS: Phase 1]
  - Add langchain-mcp-adapters to pyproject.toml
  - MultiServerMCPClient in OrchestratorHandler (load tools, log them, not yet used in graph)
  - Deliverable: worker logs show "loaded tools: [web_search]"

Phase 3: OrchestratorGraph ReAct loop  [DEPS: Phase 1, Phase 2]
  - FIRST: verify ChatCopilot.bind_tools() capability (may require implementation)
  - SubAgent._run_with_tools() mini-graph
  - build_orchestrator_graph() tools param
  - Deliverable: "search for latest Python news" prompt triggers tool call

Phase 4: Additional tools  [DEPS: Phase 3]
  - db_query tool + mcp_readonly PostgreSQL role
  - claude_code tool + sandbox config
  - Security review: is_select_only guard, volume mounts
  - Deliverable: DB query and Claude Code prompts work end-to-end

Phase 5: Tool filtering per agent (optional)  [DEPS: Phase 4]
  - config/mcp_tools.yaml agent-to-tool allowlist
  - OrchestratorHandler reads config, filters tool list before passing to SubAgent
```

Phases 1 and 2 can be written in parallel but Phase 2 cannot be tested until Phase 1 is running. Phase 3 is the highest-risk phase due to the ChatCopilot bind_tools unknown.

---

## Key Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| `ChatCopilot.bind_tools()` not implemented — Copilot SDK Technical Preview may not expose function-calling API | HIGH | Investigate as first task of Phase 3. Fallback: system-prompt-based tool description with manual output parsing (ReAct prompting). |
| `langchain-mcp-adapters` async context manager API changed between versions | MEDIUM | Read current README on install day. Use direct instantiation if `async with` fails. |
| mcp-server startup race (worker starts before mcp-server HTTP is ready) | MEDIUM | Add `depends_on: mcp-server` in worker. Add retry with exponential backoff in client init. |
| claude_code subprocess hits arq job_timeout (300s) | LOW | Set subprocess timeout to 120s. Return timeout error as tool result, not exception. |
| is_select_only guard bypass via clever SQL in db_query | HIGH | Parameterize queries. Use mcp_readonly PostgreSQL role (no INSERT/UPDATE/DELETE grants at DB level). Two independent guards. |
| mcp-server port accidentally exposed to host | LOW | Omit `ports:` from docker-compose mcp-server service. Add comment in compose file. |

---

## Sources

- langchain-mcp-adapters GitHub: https://github.com/langchain-ai/langchain-mcp-adapters
- langchain-mcp-adapters PyPI (v0.2.2, 2026-03-16): https://pypi.org/project/langchain-mcp-adapters/
- MultiServerMCPClient DeepWiki: https://deepwiki.com/langchain-ai/langchain-mcp-adapters/2.1-multiservermcpclient
- FastMCP HTTP Deployment docs: https://gofastmcp.com/deployment/http
- FastMCP PyPI (v3.2.2, 2026-04-09): https://pypi.org/project/fastmcp/
- LangGraph ToolNode reference: https://reference.langchain.com/python/langgraph/agents
- LangGraph ReAct agent from scratch: https://langchain-ai.github.io/langgraph/how-tos/react-agent-from-scratch-functional/
- LangChain MCP adapters announcement: https://changelog.langchain.com/announcements/mcp-adapters-for-langchain-and-langgraph
