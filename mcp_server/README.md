# copilot-mcp-server

FastMCP server providing stub tools for the Copilot LangGraph agent (Phase 20).

## Purpose

Phase 20 base layer: 4 stub tools + `/health` endpoint over streamable-http transport.
Real tool implementations (Tavily, PostgreSQL, Claude Code) are handled in Phase 22/23.

## Run locally

```bash
cd mcp_server
uv sync
uv run python server.py
```

Server binds to `0.0.0.0:8001`.

## Endpoints

- `http://localhost:8001/mcp` — MCP streamable-http endpoint (for MCP clients)
- `http://localhost:8001/health` — Docker healthcheck (`{"status": "ok"}`)

## Registered stub tools

| Tool | Args | Replacement plan |
|------|------|-----------------|
| `ping` | none | permanent (liveness check) |
| `web_search_stub` | `query: str` | Phase 22 — Tavily integration |
| `db_query_stub` | `sql: str` | Phase 23 — PostgreSQL SELECT |
| `claude_code_stub` | `command: str` | Phase 23 — subprocess execution |

## Docker Compose integration

Docker Compose service (`mcp-server`) and worker `depends_on` are configured in Plan 02.
